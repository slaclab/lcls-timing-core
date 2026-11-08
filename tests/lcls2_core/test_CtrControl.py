#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""CtrControl test: a counter of qualifying cycles that is latched on a ctrrst rising edge.

CtrControl instantiates surf.SynchronizerEdge for ctrrst and has a UNISIM
use clause; the clause resolves to the stub library that make import builds
from tests/ghdl/unisim. The block is reached through CtrControlWrapper, which
flattens the CtrDefType and Slv16Array inputs.

Test methodology:
    Sweep: one compiled simulation (ASYNC_REGCLK_G is not used by the RTL).
        Counting is checked over a 300 cycle pattern with six ctrrst edges and
        over four 48 cycle patterns, one per destSel mode (beam, no beam,
        don't care, reserved), with enable, the fixed rate bit, the beam bit
        and the beam destination index all changing; static probes cover the
        AC rate, the sequence rate mapping and the disabled block.
    Stimulus: a 10 ns txclk and an 8 ns sysclk. Inputs are applied per txclk
        cycle after a 3 cycle reset and a 20 cycle idle wait. A pattern is a
        list of per cycle inputs; the expected series is computed in Python
        from the per cycle qualifying flag (enable, selected rate and
        destination) and the ctrrst rising edges.
    Checks: the count output holds the number of qualifying cycles between
        two latch edges and is unchanged between them; the latch edge is 3
        cycles after the ctrrst rising edge (the SynchronizerEdge latency,
        measured); the qualifying cycle on the latch edge itself is lost
        because the count restarts from zero there; a ctrrst held high does
        not latch again; txrst clears the latched value; the count output is
        resolvable on every cycle after reset release.
    Timing: the count register settles TPD_G = 1 ns after a txclk edge.
    Propagation sampling: every sample is taken 2 ns after the edge and the
        next cycle's inputs are applied right after it.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/CtrControlWrapper.vhd"

TX_PERIOD_NS = 10
SYS_PERIOD_NS = 8
RESET_CYCLES = 3
IDLE_CYCLES = 20
# ctrrst applied before cycle c shows in the count output at the sample of cycle c + 3
LATCH_LATENCY = 3

DEST_BEAM = 0b00
DEST_NO_BEAM = 0b01
DEST_DONT_CARE = 0b10
DEST_RESERVED = 0b11
RATE_TYPE_AC = 1
RATE_TYPE_SEQ = 2

DEFAULTS = {
    "ctrdefRateSel": 0,
    "ctrdefDestSel": DEST_DONT_CARE << 16,
    "ctrrst": 0,
    "enable": 1,
    "fixedRate": 0,
    "acRate": 0,
    "acTS": 1,
    "beamSeq": 0,
    "expSeq": 0,
    "sysrst": 0,
}


class Bench:
    """Drive-then-sample bench: inputs set before ``tick`` act on the sample it returns."""

    def __init__(self, dut):
        self.dut = dut
        self.counts = []
        self.checked = False
        self.clocks = [
            cocotb.start_soon(Clock(dut.txclk, TX_PERIOD_NS, unit="ns").start(start_high=False)),
            cocotb.start_soon(Clock(dut.sysclk, SYS_PERIOD_NS, unit="ns").start(start_high=False)),
        ]

    @property
    def cycle(self):
        """Index of the next sample."""
        return len(self.counts)

    def drive(self, **values):
        for name, value in values.items():
            getattr(self.dut, name).value = value

    async def tick(self, count=1):
        for _ in range(count):
            await sample_after_tpd(self.dut.txclk, propagation_time=2)
            value = self.dut.count.value
            if self.checked:
                assert value.is_resolvable, f"count carries unresolved bits at cycle {self.cycle}: {value}"
            self.counts.append(int(value) if value.is_resolvable else 0)

    async def reset(self):
        """Apply the default inputs, reset for 3 cycles and idle for 20."""
        self.checked = False
        self.drive(**DEFAULTS)
        self.drive(txrst=1)
        await self.tick(RESET_CYCLES)
        self.drive(txrst=0)
        await self.tick(IDLE_CYCLES)
        self.checked = True

    async def run(self, rows):
        """Apply one dict of inputs per cycle; return the first cycle index."""
        first = self.cycle
        for row in rows:
            self.drive(**row)
            await self.tick(1)
        return first


def dest_selected(dest_sel, beam_seq):
    """Expected destination match for a destSel value and a beamSeq word."""
    mode = (dest_sel >> 16) & 3
    beam = beam_seq & 1
    index = (beam_seq >> 4) & 0xF
    hit = bool(beam and (dest_sel >> index) & 1)
    return {DEST_DONT_CARE: True, DEST_BEAM: hit, DEST_NO_BEAM: not hit, DEST_RESERVED: False}[mode]


def expected_series(qualify, rises, length):
    """Expected count output per cycle.

    ``qualify[k]`` says cycle k counts, ``rises`` lists the cycles where
    ctrrst is applied high after being low. The output changes at
    rise + LATCH_LATENCY to the number of qualifying cycles strictly between
    the previous latch edge and that one.
    """
    edges = {rise + LATCH_LATENCY for rise in rises}
    out = []
    latched = 0
    previous = -1
    for cycle in range(length):
        if cycle in edges:
            latched = sum(1 for k in range(previous + 1, cycle) if qualify[k])
            previous = cycle
        out.append(latched)
    return out


def rising_edges(rows):
    rises = []
    level = 0
    for cycle, row in enumerate(rows):
        now = row.get("ctrrst", level)
        if now and not level:
            rises.append(cycle)
        level = now
    return rises


@cocotb.test(timeout_time=200, timeout_unit="us")
async def ctr_counts_and_latches(dut):
    """The latched count equals the qualifying cycles between ctrrst edges; a held ctrrst latches once.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    await bench.reset()
    length = 300
    # fixed marker 0 is selected by ctrdefRateSel = 0; fixedRate is the qualifying flag
    high = set(range(10, 30)) | set(range(41, 47)) | set(range(50, 53)) | {70}
    high |= set(range(100, 160)) | set(range(171, 180))
    # ctrrst rises at these cycles; it is held high for 16 cycles at 40 and 30 cycles at 120
    rises = [40, 60, 90, 120, 170, 200, 203, 250]
    held = {40: 16, 120: 30}
    rows = [
        {
            "fixedRate": int(cycle in high),
            "ctrrst": int(any(rise <= cycle < rise + held.get(rise, 1) for rise in rises)),
        }
        for cycle in range(length)
    ]
    start = await bench.run(rows)
    qualify = [False] * start + [bool(row["fixedRate"]) for row in rows]
    edges = [start + rise for rise in rising_edges(rows)]
    expected = expected_series(qualify, edges, bench.cycle)
    for cycle in range(start, bench.cycle):
        assert bench.counts[cycle] == expected[cycle], (
            f"cycle {cycle - start}: count {bench.counts[cycle]}, expected {expected[cycle]}"
        )
    latched = [bench.counts[start + rise + LATCH_LATENCY] for rise in rising_edges(rows)]
    # first latch: qualifying cycles 10 to 29 (20) and 41, 42 (2); the cycle on the latch edge, 43, is lost
    assert latched[0] == 22, f"first latch {latched[0]}, expected 22"
    # second latch: 44 to 46 (3) and 50 to 52 (3)
    assert latched[1] == 6, f"second latch {latched[1]}, expected 6"
    assert len(set(latched)) > 3, f"latched values {latched} do not vary"
    # a held ctrrst latches once: the count output is flat across the hold
    held_window = bench.counts[start + 44:start + 56]
    assert len(set(held_window)) == 1, f"count changed while ctrrst was held: {held_window}"

    # txrst clears the latched value
    bench.drive(txrst=1, ctrrst=0, fixedRate=0)
    await bench.tick(2)
    bench.drive(txrst=0)
    await bench.tick(5)
    assert bench.counts[-5:] == [0] * 5, f"count after txrst: {bench.counts[-5:]}"


def dest_rows(mode, length):
    """Per cycle inputs of one destination mode: enable, rate bit, beam bit, index and mask all move."""
    rows = []
    for cycle in range(length):
        index = cycle % 16
        beam = (cycle // 2) % 2
        mask = (0x0F0F >> (cycle % 5)) | (1 << index if cycle % 3 else 0)
        junk = (0x6D6D6D6D * (cycle + 5)) & 0xFFFFFF0E
        rows.append({
            "enable": int((cycle // 4) % 3 != 0),
            "fixedRate": int((cycle // 3) % 2 == 0),
            "beamSeq": junk | (index << 4) | beam,
            "ctrdefDestSel": (mode << 16) | (mask & 0xFFFF),
        })
    return rows


async def count_window(bench, setup, window=10):
    """Latch the count of a static configuration over ``window`` cycles; return (count, window cycles)."""
    bench.drive(**setup)
    await bench.tick(4)
    first = bench.cycle
    bench.drive(ctrrst=1)
    await bench.tick(1)
    bench.drive(ctrrst=0)
    await bench.tick(window)
    second = bench.cycle
    bench.drive(ctrrst=1)
    await bench.tick(LATCH_LATENCY + 1)
    bench.drive(ctrrst=0)
    await bench.tick(2)
    # qualifying cycles are those strictly between the two latch edges
    cycles = (second + LATCH_LATENCY) - (first + LATCH_LATENCY) - 1
    return bench.counts[second + LATCH_LATENCY], cycles


@cocotb.test(timeout_time=200, timeout_unit="us")
async def ctr_enable_and_destination(dut):
    """Only cycles with enable, the selected rate and a matching destination are counted.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    bench = Bench(dut)
    length = 48
    totals = {}
    for mode in (DEST_BEAM, DEST_NO_BEAM, DEST_DONT_CARE, DEST_RESERVED):
        await bench.reset()
        rows = dest_rows(mode, length)
        qualify_rows = [
            row["enable"] and row["fixedRate"] and dest_selected(row["ctrdefDestSel"], row["beamSeq"])
            for row in rows
        ]
        # ctrrst rises once, right after the pattern, and the latched value is read after the latency
        rise = length
        rows = rows + [{"ctrrst": 1}] + [{"ctrrst": 0}] * 2
        rows = [dict(row, ctrrst=row.get("ctrrst", 0)) for row in rows]
        start = await bench.run(rows)
        await bench.tick(LATCH_LATENCY + 2)
        qualify = [False] * start + [bool(q) for q in qualify_rows]
        qualify += [False] * (bench.cycle - len(qualify))
        expected = expected_series(qualify, [start + rise], bench.cycle)
        for cycle in range(start, bench.cycle):
            assert bench.counts[cycle] == expected[cycle], (
                f"mode {mode} cycle {cycle - start}: count {bench.counts[cycle]}, expected {expected[cycle]}"
            )
        totals[mode] = bench.counts[-1]
    enabled_rate = sum(
        1 for row in dest_rows(DEST_DONT_CARE, length) if row["enable"] and row["fixedRate"]
    )
    assert totals[DEST_DONT_CARE] == enabled_rate, (
        f"don't care count {totals[DEST_DONT_CARE]}, expected {enabled_rate}"
    )
    assert totals[DEST_RESERVED] == 0, f"reserved destination mode counted {totals[DEST_RESERVED]}"
    assert 0 < totals[DEST_BEAM] < enabled_rate, f"beam mode count {totals[DEST_BEAM]} not a strict subset"
    assert 0 < totals[DEST_NO_BEAM] < enabled_rate, f"no beam mode count {totals[DEST_NO_BEAM]} not a strict subset"
    assert totals[DEST_BEAM] + totals[DEST_NO_BEAM] == enabled_rate, "beam and no beam do not partition the cycles"

    # static probes: the rate fields of types AC and sequence, and enable low
    await bench.reset()
    always = {"ctrdefDestSel": DEST_DONT_CARE << 16}
    count, cycles = await count_window(bench, {**always, "ctrdefRateSel": (RATE_TYPE_AC << 11) | (0x3F << 3) | 2,
                                               "acRate": 1 << 2, "acTS": 3})
    assert count == cycles, f"AC rate selected: count {count}, expected {cycles}"
    count, _ = await count_window(bench, {**always, "ctrdefRateSel": (RATE_TYPE_AC << 11) | (0x3F << 3) | 2,
                                          "acRate": 1 << 1, "acTS": 3})
    assert count == 0, f"AC rate not selected: count {count}"
    count, _ = await count_window(bench, {**always, "ctrdefRateSel": (RATE_TYPE_AC << 11) | ((0x3F ^ 4) << 3) | 2,
                                          "acRate": 1 << 2, "acTS": 3})
    assert count == 0, f"AC timeslot masked: count {count}"
    # sequence mode, RTL mapping (word in rateSel(10:5), bit in rateSel(4:0)): word 1 bit 3 counts every cycle
    seq = {**always, "expSeq": (1 << 3) << 16, "acRate": 0}
    count, cycles = await count_window(bench, {**seq, "ctrdefRateSel": (RATE_TYPE_SEQ << 11) | (1 << 5) | 3})
    assert count == cycles, f"sequence word 1 bit 3 selected: count {count}, expected {cycles}"
    # the commented placement (sequence 1 at rateSel(10:6)) selects word 2 instead, as in BsaControl
    count, _ = await count_window(bench, {**seq, "ctrdefRateSel": (RATE_TYPE_SEQ << 11) | (1 << 6) | 3})
    assert count == 0, f"commented sequence 1 encoding selected word 1: count {count}"
    count, _ = await count_window(bench, {"ctrdefRateSel": 0, "fixedRate": 1, "expSeq": 0, "enable": 0})
    assert count == 0, f"disabled block counted {count}"
    count, cycles = await count_window(bench, {"enable": 1})
    assert count == cycles, f"enabled again: count {count}, expected {cycles}"


def test_CtrControl():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.ctrcontrolwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
