#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""BsaControl test: acquisition state of one BSA definition.

Only the ruckus loaded BsaControlv2.vhd is tested (it declares entity
BsaControl); the unloaded BsaControl.vhd is not. The block is reached through
BsaControlWrapper, which flattens the BsaDefType and Slv16Array inputs.

Test methodology:
    Sweep: ASYNC_REGCLK_G false and true, one compiled simulation each, with
        every entrypoint run in both. Inside the entrypoints (nToAvg, avgToWr)
        covers (3, 2), (2, 2) and (5, 3) for the average and done cadence;
        (1, 1), (1, 3), (2, 1), (0, 2) and (1, 0) for the boundaries; avgToWr
        0xFFFF for persist; tmocnt 0 and 2 with noTmo 0 and 1 for the
        timeout; maxSevr 0 to 3; all four destSel modes with every beam
        destination index; and rateSel types 00, 01 and 10.
    Stimulus: a 10 ns txclk and an 8 ns sysclk. Every scenario drives one set
        of inputs per txclk cycle from a drive-then-sample bench, starting
        after a 3 cycle reset and a 20 cycle idle wait. The rate is selected
        through fixedRate or expSeq held in Python and the acquisition is
        started with a bsadef.init pulse.
    Checks: bsaInit is a one cycle pulse one cycle after the init input
        rises while enabled; bsaActive and bsaAvgDone show maxSevr(0) and
        maxSevr(1) in that cycle; bsaAvgDone, bsaDone and the nToAvgOut and
        avgToWrOut counters follow the cadence listed below; every checked
        output is resolvable on every cycle after reset release.
    Observed cadence (intent unconfirmed, there is no written definition of
        the thresholds): with the rate selected on every cycle a fresh
        acquisition makes its first bsaActive cycle two cycles after the init
        input and ends an average on the nToAvg + 1 th active cycle for
        nToAvg of 2 or more, on every active cycle for nToAvg = 1, and never
        for nToAvg = 0 (the 13 bit counter has to wrap). It finishes with
        bsaDone on the avgToWr th average, one average later for nToAvg = 1
        and avgToWr of 2 or more, because the last-average flag lags the
        counter by one cycle, and never for avgToWr = 0 or 0xFFFF. A timeout
        pulse ends nothing by itself: it pulses bsaDone but the acquisition
        keeps running when the rate returns.
    Timing: bsaActive follows the rate, destination and enable inputs in the
        same cycle they are applied; the registered nToAvg and avgToWr
        counters follow a cycle later. With ASYNC_REGCLK_G true the counters
        reach nToAvgOut and avgToWrOut through a surf synchronizer FIFO that
        drops its first writes (about 7 cycles of data) after the init pulse
        and then updates in bursts; the measured lag of the output behind the
        counter is 5 to 10 txclk cycles and the checks allow 3 to 12.
    Propagation sampling: the registered outputs settle TPD_G = 1 ns after a
        txclk edge, so every sample is taken 2 ns after the edge and the next
        cycle's inputs are applied right after it.
"""

import os
from pathlib import Path
from typing import NamedTuple

import cocotb
import pytest
from cocotb.clock import Clock

from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/BsaControlWrapper.vhd"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
KNOWN_ISSUE_ENTRYPOINT = "bsa_rate_field_comment_mapping"

TX_PERIOD_NS = 10
SYS_PERIOD_NS = 8
RESET_CYCLES = 3
IDLE_CYCLES = 20

# destSel(17:16) modes
DEST_BEAM = 0b00
DEST_NO_BEAM = 0b01
DEST_DONT_CARE = 0b10
DEST_RESERVED = 0b11
SEQ_WORDS = 18
SEQ_WORD_MASK = 0xFFFF
RATE_TYPE_FIXED = 0
RATE_TYPE_AC = 1
RATE_TYPE_SEQ = 2
PERSIST = 0xFFFF

# async counter outputs lag the counter by 5 to 10 cycles, measured
ASYNC_LAG_MIN = 3
ASYNC_LAG_MAX = 12
ASYNC_SETTLE_CYCLES = 40

DEFAULTS = {
    "bsadefNToAvg": 0,
    "bsadefAvgToWr": 0,
    "bsadefRateSel": 0,
    "bsadefDestSel": DEST_DONT_CARE << 16,
    "bsadefMaxSevr": 0,
    "bsadefNoTmo": 0,
    "bsadefInit": 0,
    "tmo": 0,
    "tmocnt": 0xF,
    "enable": 1,
    "fixedRate": 0,
    "acRate": 0,
    "acTS": 1,
    "beamSeq": 0,
    "expSeq": 0,
    "sysrst": 0,
}

OUTPUTS = ("bsaInit", "bsaActive", "bsaAvgDone", "bsaDone", "nToAvgOut", "avgToWrOut")


class Sample(NamedTuple):
    """Outputs of one txclk cycle."""

    cycle: int
    init: int
    active: int
    avg_done: int
    done: int
    n_to_avg: int
    avg_to_wr: int


class Bench:
    """Drive-then-sample bench: inputs set before ``tick`` act on the sample it returns."""

    def __init__(self, dut):
        self.dut = dut
        self.trace = []
        self.checked = False
        self.async_regclk = os.environ.get("ASYNC_REGCLK_G", "false") == "true"
        self.clocks = [
            cocotb.start_soon(Clock(dut.txclk, TX_PERIOD_NS, unit="ns").start(start_high=False)),
            cocotb.start_soon(Clock(dut.sysclk, SYS_PERIOD_NS, unit="ns").start(start_high=False)),
        ]

    @property
    def cycle(self):
        """Index of the next sample."""
        return len(self.trace)

    def drive(self, **values):
        for name, value in values.items():
            getattr(self.dut, name).value = value

    def read(self):
        values = []
        for name in OUTPUTS:
            value = getattr(self.dut, name).value
            if self.checked:
                assert value.is_resolvable, f"{name} carries unresolved bits at cycle {self.cycle}: {value}"
            values.append(int(value) if value.is_resolvable else 0)
        return Sample(self.cycle, *values)

    async def tick(self, count=1):
        for _ in range(count):
            await sample_after_tpd(self.dut.txclk, propagation_time=2)
            self.trace.append(self.read())

    async def reset(self):
        """Apply the default inputs, reset for 3 cycles and idle for 20."""
        self.checked = False
        self.drive(**DEFAULTS)
        self.drive(txrst=1)
        await self.tick(RESET_CYCLES)
        self.drive(txrst=0)
        await self.tick(IDLE_CYCLES)
        self.checked = True

    async def start(self, n_to_avg, avg_to_wr, init_cycles=2, **values):
        """Reset, load a definition and pulse init; return the cycle the init input rose."""
        await self.reset()
        self.drive(bsadefNToAvg=n_to_avg, bsadefAvgToWr=avg_to_wr, **values)
        rise = self.cycle
        self.drive(bsadefInit=1)
        await self.tick(init_cycles)
        self.drive(bsadefInit=0)
        return rise

    def since(self, first):
        return self.trace[first:]


def cycles_of(samples, field):
    return [sample.cycle for sample in samples if getattr(sample, field)]


def avg_period(n_to_avg):
    """Active cycles per average, observed: 1 for nToAvg 1, nToAvg + 1 otherwise."""
    return 1 if n_to_avg == 1 else n_to_avg + 1


def averages_to_done(n_to_avg, avg_to_wr):
    """Averages before bsaDone, observed; None when the run never finishes."""
    if avg_to_wr in (0, PERSIST) or n_to_avg == 0:
        return None
    return avg_to_wr + 1 if n_to_avg == 1 and avg_to_wr >= 2 else avg_to_wr


def avg_offsets(n_to_avg, window):
    """Offsets, in active cycles from the first one, of every bsaAvgDone in the window."""
    if n_to_avg == 0:
        return []
    period = avg_period(n_to_avg)
    return [k * period - 1 for k in range(1, window // period + 1)]


def counters_after(n_to_avg, index):
    """(nToAvg, avgToWr) after active cycle ``index`` of a run that has not finished, observed."""
    if n_to_avg == 0:
        return index + 1, 0
    period = avg_period(n_to_avg)
    return (index + 1) % period, (index + 1) // period


def first_active(rise):
    """bsaInit shows one cycle after the init input rises, bsaActive two cycles after."""
    return rise + 2


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_init_and_severity(dut):
    """bsaInit pulses once per init rise while enabled and shows maxSevr in that cycle.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    for severity in range(4):
        rise = await bench.start(3, 2, init_cycles=1, bsadefMaxSevr=severity)
        await bench.tick(6)
        samples = bench.since(rise)
        assert cycles_of(samples, "init") == [rise + 1], (
            f"maxSevr {severity}: bsaInit at {cycles_of(samples, 'init')}, expected [{rise + 1}]"
        )
        init_sample = bench.trace[rise + 1]
        assert (init_sample.active, init_sample.avg_done, init_sample.done) == (severity & 1, severity >> 1, 0), (
            f"maxSevr {severity}: init cycle shows active {init_sample.active}, "
            f"avg_done {init_sample.avg_done}, done {init_sample.done}"
        )
        for sample in samples:
            if sample.cycle != rise + 1:
                assert not (sample.active or sample.avg_done or sample.done), (
                    f"maxSevr {severity}: unexpected output at cycle {sample.cycle}: {sample}"
                )

    # held high: one pulse; dropped and raised again: a second pulse
    await bench.reset()
    rise = bench.cycle
    bench.drive(bsadefInit=1)
    await bench.tick(30)
    bench.drive(bsadefInit=0)
    await bench.tick(3)
    rise2 = bench.cycle
    bench.drive(bsadefInit=1)
    await bench.tick(3)
    bench.drive(bsadefInit=0)
    await bench.tick(3)
    assert cycles_of(bench.since(rise), "init") == [rise + 1, rise2 + 1], (
        f"held init: bsaInit at {cycles_of(bench.since(rise), 'init')}, expected {[rise + 1, rise2 + 1]}"
    )

    # disabled: no pulse; the pulse follows the enable rise while init is still high
    await bench.reset()
    disabled = bench.cycle
    bench.drive(enable=0, bsadefInit=1)
    await bench.tick(10)
    assert not cycles_of(bench.since(disabled), "init"), "bsaInit pulsed while disabled"
    rise = bench.cycle
    bench.drive(enable=1)
    await bench.tick(6)
    assert cycles_of(bench.since(rise), "init") == [rise + 1], (
        f"enable rise: bsaInit at {cycles_of(bench.since(rise), 'init')}, expected [{rise + 1}]"
    )


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_average_and_done(dut):
    """bsaAvgDone follows the observed cadence and bsaDone ends the acquisition on the last average.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    for n_to_avg, avg_to_wr in ((3, 2), (2, 2), (5, 3)):
        label = f"(nToAvg {n_to_avg}, avgToWr {avg_to_wr})"
        window = 40
        rise = await bench.start(n_to_avg, avg_to_wr, fixedRate=1)
        await bench.tick(window)
        first = first_active(rise)
        samples = bench.since(rise)
        done_count = averages_to_done(n_to_avg, avg_to_wr)
        offsets = avg_offsets(n_to_avg, window)[:done_count]
        assert cycles_of(samples, "avg_done") == [first + offset for offset in offsets], (
            f"{label}: bsaAvgDone at {cycles_of(samples, 'avg_done')}, expected {[first + o for o in offsets]}"
        )
        done_cycle = first + offsets[-1]
        assert cycles_of(samples, "done") == [done_cycle], (
            f"{label}: bsaDone at {cycles_of(samples, 'done')}, expected [{done_cycle}]"
        )
        assert cycles_of(samples, "active") == list(range(first, done_cycle + 1)), (
            f"{label}: bsaActive at {cycles_of(samples, 'active')}, expected {first} to {done_cycle}"
        )
        if not bench.async_regclk:
            for index in range(done_cycle - first):
                sample = bench.trace[first + index]
                expected = counters_after(n_to_avg, index)
                assert (sample.n_to_avg, sample.avg_to_wr) == expected, (
                    f"{label}: counters at active cycle {index} are {(sample.n_to_avg, sample.avg_to_wr)}, "
                    f"expected {expected}"
                )
        final = bench.trace[-1]
        assert (final.n_to_avg, final.avg_to_wr) == (0, avg_to_wr), (
            f"{label}: final counters {(final.n_to_avg, final.avg_to_wr)}, expected {(0, avg_to_wr)}"
        )


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_boundary_counts(dut):
    """Smallest and zero thresholds: (1, 1), (2, 1), (1, 3), nToAvg 0 and avgToWr 0.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    for n_to_avg, avg_to_wr in ((1, 1), (2, 1), (1, 3)):
        label = f"(nToAvg {n_to_avg}, avgToWr {avg_to_wr})"
        rise = await bench.start(n_to_avg, avg_to_wr, fixedRate=1)
        await bench.tick(20)
        first = first_active(rise)
        samples = bench.since(rise)
        done_count = averages_to_done(n_to_avg, avg_to_wr)
        offsets = avg_offsets(n_to_avg, 20)[:done_count]
        assert cycles_of(samples, "avg_done") == [first + offset for offset in offsets], (
            f"{label}: bsaAvgDone at {cycles_of(samples, 'avg_done')}, expected {[first + o for o in offsets]}"
        )
        assert cycles_of(samples, "done") == [first + offsets[-1]], (
            f"{label}: bsaDone at {cycles_of(samples, 'done')}, expected [{first + offsets[-1]}]"
        )
        assert cycles_of(samples, "active") == list(range(first, first + offsets[-1] + 1)), (
            f"{label}: bsaActive at {cycles_of(samples, 'active')}"
        )
    # nToAvg 1 with avgToWr 1 finishes on the first active cycle itself
    rise = await bench.start(1, 1, fixedRate=1)
    await bench.tick(8)
    sample = bench.trace[first_active(rise)]
    assert (sample.active, sample.avg_done, sample.done) == (1, 1, 1), (
        f"(1, 1) first active cycle shows {sample}"
    )

    # nToAvg 0: no average ends in 200 active cycles (the 13 bit counter has to wrap)
    rise = await bench.start(0, 2, fixedRate=1)
    await bench.tick(200)
    samples = bench.since(rise)
    first = first_active(rise)
    assert not cycles_of(samples, "avg_done"), f"nToAvg 0: bsaAvgDone at {cycles_of(samples, 'avg_done')}"
    assert not cycles_of(samples, "done"), "nToAvg 0: bsaDone pulsed"
    assert cycles_of(samples, "active") == list(range(first, bench.cycle)), "nToAvg 0: bsaActive did not stay high"
    if not bench.async_regclk:
        for index in (0, 1, 50, 150):
            assert bench.trace[first + index].n_to_avg == index + 1, (
                f"nToAvg 0: counter at active cycle {index} is {bench.trace[first + index].n_to_avg}"
            )

    # avgToWr 0: averages keep ending, bsaDone never pulses
    rise = await bench.start(1, 0, fixedRate=1)
    await bench.tick(150)
    samples = bench.since(rise)
    first = first_active(rise)
    assert cycles_of(samples, "avg_done") == list(range(first, bench.cycle)), "avgToWr 0: averages stopped"
    assert not cycles_of(samples, "done"), "avgToWr 0: bsaDone pulsed"
    if not bench.async_regclk:
        assert bench.trace[first + 99].avg_to_wr == 100, "avgToWr 0: write counter did not count up"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_persist(dut):
    """avgToWr = 0xFFFF never finishes; a later init with a normal avgToWr finishes again.

    The counter lag of the ASYNC_REGCLK_G true outputs is measured on a long
    average: every sample must equal the counter value some 3 to 12 cycles
    earlier.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    rise = await bench.start(1, PERSIST, fixedRate=1)
    await bench.tick(250)
    samples = bench.since(rise)
    first = first_active(rise)
    assert not cycles_of(samples, "done"), "persist: bsaDone pulsed"
    assert cycles_of(samples, "active") == list(range(first, bench.cycle)), "persist: bsaActive dropped"
    assert cycles_of(samples, "avg_done") == list(range(first, bench.cycle)), "persist: averages stopped"

    # leaving persist: init low then a new definition with avgToWr 2 finishes
    await bench.tick(3)
    rise = bench.cycle
    bench.drive(bsadefNToAvg=3, bsadefAvgToWr=2, bsadefInit=1)
    await bench.tick(2)
    bench.drive(bsadefInit=0)
    await bench.tick(20)
    samples = bench.since(rise)
    first = first_active(rise)
    expected_done = first + avg_offsets(3, 20)[1]
    assert cycles_of(samples, "done") == [expected_done], (
        f"after persist: bsaDone at {cycles_of(samples, 'done')}, expected [{expected_done}]"
    )

    # one long average for the counter outputs
    n_to_avg = 200
    rise = await bench.start(n_to_avg, PERSIST, fixedRate=1)
    await bench.tick(2 * n_to_avg + 10)
    first = first_active(rise)
    period = avg_period(n_to_avg)
    assert cycles_of(bench.since(rise), "avg_done") == [first + period - 1, first + 2 * period - 1], (
        f"long average: bsaAvgDone at {cycles_of(bench.since(rise), 'avg_done')}"
    )

    def counter(cycle):
        return counters_after(n_to_avg, cycle - first)[0]

    if bench.async_regclk:
        # the FIFO drops its first writes; compare from 25 cycles after the first active cycle
        for cycle in range(first + 25, first + 2 * period):
            seen = bench.trace[cycle].n_to_avg
            lags = [lag for lag in range(ASYNC_LAG_MIN, ASYNC_LAG_MAX + 1)
                    if cycle - lag >= first and counter(cycle - lag) == seen]
            assert lags, (
                f"long average: nToAvgOut {seen} at cycle {cycle} matches no counter value "
                f"{ASYNC_LAG_MIN} to {ASYNC_LAG_MAX} cycles earlier"
            )
    else:
        for cycle in range(first, first + 2 * period):
            assert bench.trace[cycle].n_to_avg == counter(cycle), (
                f"long average: nToAvgOut {bench.trace[cycle].n_to_avg} at cycle {cycle}, expected {counter(cycle)}"
            )


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_timeout(dut):
    """The tmo path pulses bsaDone on the (tmocnt + 1) th tmo pulse after an average, unless noTmo is set.

    The timeout does not stop the acquisition: when the rate returns it
    keeps averaging (observed, intent unconfirmed). Pulses before the first
    average are ignored.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    pulse_gap = 3
    for tmocnt, no_tmo in ((2, 0), (0, 0), (2, 1)):
        label = f"(tmocnt {tmocnt}, noTmo {no_tmo})"
        rise = await bench.start(3, 10, fixedRate=1, tmocnt=tmocnt, bsadefNoTmo=no_tmo)
        first = first_active(rise)
        # tmo pulse before any average: ignored
        await bench.tick(first + 1 - bench.cycle)
        bench.drive(tmo=1)
        await bench.tick(1)
        bench.drive(tmo=0)
        # two averages (active cycles first to first + 7), then the rate drops
        await bench.tick(first + 8 - bench.cycle)
        bench.drive(fixedRate=0)
        await bench.tick(10)
        pulses = []
        for _ in range(6):
            pulses.append(bench.cycle)
            bench.drive(tmo=1)
            await bench.tick(1)
            bench.drive(tmo=0)
            await bench.tick(pulse_gap - 1)
        samples = bench.since(rise)
        assert cycles_of(samples, "avg_done") == [first + 3, first + 7], (
            f"{label}: bsaAvgDone at {cycles_of(samples, 'avg_done')}"
        )
        expected = [] if no_tmo else [pulses[tmocnt]]
        assert cycles_of(samples, "done") == expected, (
            f"{label}: bsaDone at {cycles_of(samples, 'done')}, expected {expected}"
        )
        if not no_tmo:
            # the timeout leaves the acquisition armed: the rate returning resumes it
            resume = bench.cycle
            bench.drive(fixedRate=1)
            await bench.tick(10)
            resumed = bench.since(resume)
            assert resumed[0].active == 1, f"{label}: bsaActive did not resume with the rate"
            assert cycles_of(resumed, "avg_done"), f"{label}: no average after the rate returned"
            assert not cycles_of(resumed, "done"), f"{label}: bsaDone pulsed after the timeout"


def dest_selected(dest_sel, beam_seq):
    """Expected destination match for a destSel value and a beamSeq word."""
    mode = (dest_sel >> 16) & 3
    beam = beam_seq & 1
    index = (beam_seq >> 4) & 0xF
    hit = bool(beam and (dest_sel >> index) & 1)
    return {DEST_DONT_CARE: True, DEST_BEAM: hit, DEST_NO_BEAM: not hit, DEST_RESERVED: False}[mode]


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_destination_modes(dut):
    """bsaActive needs the destination to match: the four modes over every beam destination index.

    The acquisition is persistent (avgToWr 0xFFFF, nToAvg 1) with the rate on
    every cycle, so bsaActive is the destination match, registered with the
    inputs of the same cycle. beamSeq bits 31 to 8 and 3 to 1 carry changing
    junk that must not matter.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    await bench.start(1, PERSIST, fixedRate=1)
    await bench.tick(4)
    seen = {True: 0, False: 0}
    cycle_count = 0
    for mode in (DEST_BEAM, DEST_NO_BEAM, DEST_DONT_CARE, DEST_RESERVED):
        for index in range(16):
            for beam in (0, 1):
                for mask in (1 << index, 0xFFFF ^ (1 << index)):
                    junk = (0x5A5A5A5A * (cycle_count + 3)) & 0xFFFFFF0E
                    beam_seq = junk | (index << 4) | beam
                    dest_sel = (mode << 16) | mask
                    bench.drive(bsadefDestSel=dest_sel, beamSeq=beam_seq)
                    await bench.tick(1)
                    expected = dest_selected(dest_sel, beam_seq)
                    seen[expected] += 1
                    assert bench.trace[-1].active == int(expected), (
                        f"mode {mode} index {index} beam {beam} mask 0x{mask:04x}: "
                        f"bsaActive {bench.trace[-1].active}, expected {int(expected)}"
                    )
                    cycle_count += 1
    assert seen[True] and seen[False], "destination sweep never saw both outcomes"
    bench.drive(enable=0)
    await bench.tick(2)
    assert not any(sample.done for sample in bench.trace), "bsaDone pulsed during the destination sweep"


async def selected_cell(bench, rate_sel):
    """(word, bit) of expSeq that rateSel selects in sequence mode, or None; the bench is persistent."""
    bench.drive(bsadefRateSel=rate_sel, expSeq=0)
    await bench.tick(3)
    hits = []
    for word in range(SEQ_WORDS):
        bench.drive(expSeq=SEQ_WORD_MASK << (16 * word))
        await bench.tick(3)
        if bench.trace[-1].active:
            hits.append(word)
    if not hits:
        return None
    assert len(hits) == 1, f"rateSel 0x{rate_sel:04x} selects several words: {hits}"
    bits = []
    for bit in range(16):
        bench.drive(expSeq=(1 << bit) << (16 * hits[0]))
        await bench.tick(3)
        if bench.trace[-1].active:
            bits.append(bit)
    assert len(bits) == 1, f"rateSel 0x{rate_sel:04x} selects bits {bits} of word {hits[0]}"
    return hits[0], bits[0]


def seq_rate_sel_rtl(word, bit):
    """rateSel the RTL decodes as (seqword = bits 10 to 5, seqbit = bits 4 to 0)."""
    return (RATE_TYPE_SEQ << 11) | (word << 5) | bit


def seq_rate_sel_comment(seq, bit):
    """rateSel the TPGPkg comment (seq = 10:6, bit = 5:0) and the register block write."""
    return (RATE_TYPE_SEQ << 11) | (seq << 6) | bit


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_rate_field_mapping(dut):
    """rateSel fields: fixed marker, AC marker with timeslot mask, and the sequence word and bit.

    The sequence mode mapping is measured, not assumed. The RTL decodes
    seqword from rateSel(10:5) and seqbit from rateSel(4:0); the TPGPkg
    comment (and the register block that writes the field) places the
    sequence at 10:6 and the bit at 3:0. Both encodings are probed: the
    commented one selects word 2 * seq, not seq (a known issue, held by the
    gated entrypoint bsa_rate_field_comment_mapping). rateSel(4) set in
    sequence mode indexes a 16 bit word out of range and aborts the
    simulation, so no probe sets it.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    await bench.start(1, PERSIST)
    await bench.tick(4)

    # fixed rate: rateSel(3:0) picks a fixedRate bit
    seen = set()
    for marker in range(10):
        bench.drive(bsadefRateSel=(RATE_TYPE_FIXED << 11) | marker)
        for pattern_bit in range(10):
            bench.drive(fixedRate=1 << pattern_bit)
            await bench.tick(2)
            expected = int(pattern_bit == marker)
            seen.add(expected)
            assert bench.trace[-1].active == expected, (
                f"fixed marker {marker} pattern bit {pattern_bit}: bsaActive {bench.trace[-1].active}"
            )
    assert seen == {0, 1}, "fixed rate sweep never saw both outcomes"
    bench.drive(fixedRate=0)

    # AC rate: rateSel(2:0) picks an acRate bit, rateSel(8:3) masks the timeslot acTS
    seen = set()
    for marker in (0, 2, 5):
        for slot in (1, 4, 6):
            for mask_name, mask in (("all", 0x3F), ("none", 0x00), ("slot", 1 << (slot - 1)), ("other", 0x3F ^ (1 << (slot - 1)))):
                bench.drive(bsadefRateSel=(RATE_TYPE_AC << 11) | (mask << 3) | marker, acTS=slot)
                for pattern_bit in range(6):
                    bench.drive(acRate=1 << pattern_bit)
                    await bench.tick(2)
                    expected = int(pattern_bit == marker and bool((mask >> (slot - 1)) & 1))
                    seen.add(expected)
                    assert bench.trace[-1].active == expected, (
                        f"AC marker {marker} slot {slot} mask {mask_name} pattern bit {pattern_bit}: "
                        f"bsaActive {bench.trace[-1].active}, expected {expected}"
                    )
    assert seen == {0, 1}, "AC rate sweep never saw both outcomes"
    bench.drive(acRate=0)

    # sequence: the RTL mapping, then what the commented mapping selects
    for word, bit in ((0, 0), (1, 0), (2, 5), (17, 15)):
        cell = await selected_cell(bench, seq_rate_sel_rtl(word, bit))
        assert cell == (word, bit), f"RTL encoding of word {word} bit {bit} selects {cell}"
    assert await selected_cell(bench, seq_rate_sel_rtl(18, 0)) is None, "word 18 is out of range but selects a cell"
    for seq, bit in ((0, 0), (1, 0), (2, 5), (8, 15)):
        cell = await selected_cell(bench, seq_rate_sel_comment(seq, bit))
        assert cell == (2 * seq, bit), (
            f"commented encoding of sequence {seq} bit {bit} selects {cell}, observed word {2 * seq}"
        )
    assert await selected_cell(bench, seq_rate_sel_comment(9, 0)) is None, "commented sequence 9 selects a cell"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def bsa_rate_field_comment_mapping(dut):
    """The commented rateSel encoding (sequence at 10:6, bit at 3:0) selects that sequence and bit.

    Gated known issue: the RTL decodes the sequence from rateSel(10:5), so
    the commented encoding of sequence s selects word 2 * s. Fails on the
    current RTL.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    await bench.start(1, PERSIST)
    await bench.tick(4)
    for seq, bit in ((0, 0), (1, 0), (2, 5), (8, 15), (17, 3)):
        cell = await selected_cell(bench, seq_rate_sel_comment(seq, bit))
        assert cell == (seq, bit), (
            f"rateSel with sequence {seq} at bits 10:6 and bit {bit} at bits 3:0 selects {cell}, "
            f"expected word {seq} bit {bit}: the RTL decodes the sequence from bits 10:5"
        )


@pytest.mark.parametrize("async_regclk", ["false", "true"])
def test_BsaControl(async_regclk):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.bsacontrolwrapper",
        parameters={"ASYNC_REGCLK_G": async_regclk},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(
            {"ASYNC_REGCLK_G": async_regclk},
            cocotb_test_filter_excluding(KNOWN_ISSUE_ENTRYPOINT),
        ),
    )


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPGPkg rateSel comment disagrees with the sequence-mode field mapping; "
        "see https://github.com/slaclab/lcls-timing-core/issues/209; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_BsaControl_known_issue_rate_field_comment():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.bsacontrolwrapper",
        parameters={"ASYNC_REGCLK_G": "false"},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(
            {"ASYNC_REGCLK_G": "false"},
            cocotb_test_filter(KNOWN_ISSUE_ENTRYPOINT),
        ),
    )
