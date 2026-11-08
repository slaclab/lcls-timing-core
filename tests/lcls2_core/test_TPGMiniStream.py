#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGMiniStream test: LCLS-I frames agree with the simulation outputs and event definitions follow their rules.

TPGMiniStreamWrapper maps AC_PERIOD and NUM_EDEFS to generics and flattens
the TPGMiniEdefConfigType input and the simData output.

Test methodology:
    Sweep: one compiled simulation with AC_PERIOD_G 2 (a base strobe every
        2 clocks) and NUM_EDEFS_G 4. Because the transmitter takes a
        fiducial only while it is idle, the generator sends frames back to
        back with a measured period of 682 clocks, and only the strobe that
        starts a frame is followed by a frame. The event-definition run
        configures EDEF 1 (navg 1, nsmp 2, slot 3, rate 0, sevr 2) and EDEF
        3 (navg 0, nsmp 1, slot 0, rate 3, sevr 1); the out-of-range run
        writes EDEF 4 (the first index with no instance) and 15.
    Stimulus: txRst is held for 3 txClk cycles, then released. An
        edefConfig write is a single cycle pulse of edefWrEn with the
        configuration on the other edef ports. Every cycle is sampled; the
        wide simData and simEvents are read on each simStrobe cycle.
    Checks: every frame, from one K28.0 start symbol to the next, decodes
        with timing_model.decode_lcls1_frame to a data buffer equal to
        simData and to event codes equal to simEvents with event code 0 added
        (the receiver grammar sets code 0 for every idle symbol), taken at
        the strobe in the cycle before the start symbol; no code above 69
        is set; the frame pulse id equals the pulse id carried in the
        epicsTime field minus 2 and advances by one per strobe between
        frames; dtype and version are 1. For an event definition the
        expected init, active, average-done and all-done sequence is
        computed here from the TPGMiniEdef rules and the strobe selection
        read from simData and simEvents (the generated rate bit chosen by
        rate and slot): the write is taken at the first strobe after it,
        init follows one strobe later, counting starts one strobe after
        that, an average completes every navg + 1 selected strobes and all
        samples after (navg + 1) * (nsmp + 1); the severity bits stay set
        after the definition completes; all-done is reported in bit 20 + e of
        edefMinor; the other definitions stay silent. A write for an index
        without an instance leaves every event-definition bit unchanged
        (observed, intent unconfirmed). Every checked output is resolvable on
        every sampled cycle after reset release.
    Timing: 10 ns txClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        are stable; writes are applied right after a sample.
"""

from pathlib import Path
from typing import NamedTuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    env_int,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TPGMiniStreamWrapper.vhd"

RESET_CYCLES = 3
FRAME_PERIOD = 682
CLOCKS_PER_STROBE = 2
EVENT_BITS = 70
PIPELINE_STAGE_BITS = 10
FRAME_RUN_CYCLES = 5 * FRAME_PERIOD
EDEF_RUN_CYCLES = 700
OUT_OF_RANGE_RUN_CYCLES = 300
ACTIVE_FIXED_RATE_MASK = 0b111 << 15
BASE_RATE_BIT = 4 * 32 + 20
BEAM_FULL_BIT = 4 * 32 + 28
ACTIVE_BIT = 4 * 32


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


class Sample(NamedTuple):
    """Outputs of one txClk cycle; data and events are only read on a strobe."""

    symbol: tuple
    strobe: int
    data: dict | None
    events: int | None


class Edef(NamedTuple):
    """One event-definition configuration written through edefConfig."""

    edef: int
    navg: int
    nsmp: int
    slot: int
    rate: int
    sevr: int


EDEF_PORTS = ("edefNavg", "edefNsmp", "edefEdef", "edefSlot", "edefRate", "edefSevr")


def bit(value, index):
    return (value >> index) & 1


def bit_field(value, offset, width):
    return (value >> offset) & ((1 << width) - 1)


def write_values(config, enable=1):
    values = dict(zip(EDEF_PORTS, (config.navg, config.nsmp, config.edef, config.slot, config.rate, config.sevr)))
    values["edefWrEn"] = enable
    return values


async def start_stream(dut):
    """Drive defined inputs, start the clock, hold reset 3 cycles and release it."""
    dut.txRst.value = 1
    dut.txRdy.value = 1
    dut.cfgTimeStamp.value = 0
    dut.cfgTimeStampWrEn.value = 0
    for name, value in write_values(Edef(0, 0, 0, 0, 0, 0), enable=0).items():
        getattr(dut, name).value = value
    clock_task = cocotb.start_soon(Clock(dut.txClk, 10, unit="ns").start(start_high=False))
    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.txClk)
    dut.txRst.value = 0
    return clock_task


async def record(dut, cycles, writes=None):
    """Sample ``cycles`` cycles; ``writes`` maps a cycle to port values applied right after it."""
    writes = writes or {}
    samples = []
    for cycle in range(cycles):
        await sample_after_tpd(dut.txClk, propagation_time=2)
        strobe = resolved_int(dut.simStrobe)
        samples.append(
            Sample(
                (resolved_int(dut.txData), resolved_int(dut.txDataK)),
                strobe,
                timing_model.unpack_databuff(resolved_int(dut.simData)) if strobe else None,
                resolved_int(dut.simEvents) if strobe else None,
            )
        )
        for name, value in writes.get(cycle, {}).items():
            getattr(dut, name).value = value
    return samples


def start_cycles(samples):
    """Cycles where a symbol carries K28.0 on the high lane, which starts an LCLS-I frame."""
    return [
        cycle
        for cycle, sample in enumerate(samples)
        if sample.symbol[1] & 0b10 and sample.symbol[0] >> 8 == timing_model.K_280
    ]


def strobe_cycles(samples):
    return [cycle for cycle, sample in enumerate(samples) if sample.strobe]


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def tpgministream_frames_match_sim_outputs(dut):
    """Each frame carries the data buffer and event codes of the strobe that started it.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_stream(dut)
    samples = await record(dut, FRAME_RUN_CYCLES)
    starts = start_cycles(samples)
    assert len(starts) >= 5, f"only {len(starts)} frame starts in {len(samples)} cycles"
    assert all(b - a == FRAME_PERIOD for a, b in zip(starts, starts[1:])), f"frame starts {starts}"
    strobes = strobe_cycles(samples)
    assert all(b - a == CLOCKS_PER_STROBE for a, b in zip(strobes, strobes[1:])), "strobes are not every 2 clocks"

    previous_pulse_id = None
    previous_start = None
    checked = 0
    for start, following in zip(starts, starts[1:]):
        if start == 0:
            continue
        accepted = samples[start - 1]
        assert accepted.strobe, f"no strobe in the cycle before the frame start at {start}"
        frame = timing_model.decode_lcls1_frame([sample.symbol for sample in samples[start:following]])
        assert frame.databuff == accepted.data, (
            f"frame at {start}: data buffer differs from simData in "
            f"{[name for name in accepted.data if frame.databuff[name] != accepted.data[name]]}"
        )
        assert frame.event_codes == accepted.events | 1, (
            f"frame at {start}: event codes 0x{frame.event_codes:X}, simEvents 0x{accepted.events:X}"
        )
        assert frame.event_codes >> EVENT_BITS == 0, f"frame at {start} sets an event code above {EVENT_BITS - 1}"
        epics_pulse_id = (bit_field(accepted.data["epicsTime"], 32, 17) - 2) % (1 << 17)
        assert frame.pulse_id == epics_pulse_id, (
            f"frame at {start}: pulse id {frame.pulse_id}, epicsTime carries {epics_pulse_id} + 2"
        )
        assert (accepted.data["dtype"], accepted.data["version"]) == (1, 1), "dtype or version is not 1"
        if previous_pulse_id is not None:
            strobes_between = len([c for c in strobes if previous_start - 1 < c <= start - 1])
            assert frame.pulse_id - previous_pulse_id == strobes_between, (
                f"pulse id advanced by {frame.pulse_id - previous_pulse_id} over {strobes_between} strobes"
            )
        previous_pulse_id, previous_start = frame.pulse_id, start
        checked += 1
    assert checked >= 3, f"only {checked} frames were compared"
    clock_task.cancel()


def selection(config, sample):
    """Whether the strobe selects this definition, read from the generated rate bits.

    Slot 0 uses the live fixed rate bit (visible for rate 0 and 2 to 6), slots
    2 to 5 the pipeline stage slot - 1 (visible as event code bits).
    """
    if config.slot == 0:
        assert config.rate != 1, "fixed rate 1 is not visible in simData"
        dmod = sample.data["dmod"]
        return bit(dmod, BEAM_FULL_BIT) if config.rate == 0 else bit(dmod, BASE_RATE_BIT + config.rate - 2)
    assert 2 <= config.slot <= 5, "pipeline stage 0 is not visible in simEvents"
    return bit(sample.events, (config.slot - 1) * PIPELINE_STAGE_BITS + config.rate)


class Expected(NamedTuple):
    """Per-strobe expected event-definition outputs."""

    init: list
    active: list
    avg_done: list
    all_done: list


def edef_reference(gates, first, config):
    """Expected init, active, average-done and all-done per strobe for one write.

    ``first`` is the index of the first strobe after the write. The
    definition is idle there, init is high at the next strobe, and
    counting of selected strobes starts at the one after.
    """
    count = len(gates)
    init, active, avg_done, all_done = ([0] * count for _ in range(4))
    if first + 1 < count:
        init[first + 1] = 1
    running = True
    avg_left = config.navg
    smp_left = config.nsmp
    for index in range(first + 2, count):
        if not running:
            break
        if gates[index]:
            active[index] = 1
            if avg_left == 0:
                avg_done[index] = 1
                if smp_left == 0:
                    all_done[index] = 1
                    running = False
                else:
                    smp_left -= 1
                    avg_left = config.navg
            else:
                avg_left -= 1
    return Expected(init, active, avg_done, all_done)


def edef_bits(data, edef):
    """Event-definition outputs of EDEF ``edef`` in one data buffer."""
    return {
        "init": bit(data["edefInit"], edef),
        "active": bit(data["dmod"], ACTIVE_BIT + edef),
        "avg_done": bit(data["edefAvgDn"], edef),
        "all_done": bit(data["edefMinor"], 20 + edef),
        "minor": bit(data["edefMinor"], edef),
        "major": bit(data["edefMajor"], edef),
    }


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def tpgministream_edef_sequence(dut):
    """EDEF 1 and 3 follow init, averaging and all-done as the TPGMiniEdef rules prescribe.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    configs = [Edef(1, 1, 2, 3, 0, 0b10), Edef(3, 0, 1, 0, 3, 0b01)]
    write_cycles = (100, 110)
    writes = {}
    for config, cycle in zip(configs, write_cycles):
        writes[cycle] = write_values(config)
        writes[cycle + 1] = {"edefWrEn": 0}
    clock_task = await start_stream(dut)
    samples = await record(dut, EDEF_RUN_CYCLES, writes)
    strobes = [sample for sample in samples if sample.strobe]
    cycles = strobe_cycles(samples)

    for config, write_cycle in zip(configs, write_cycles):
        first = next(index for index, cycle in enumerate(cycles) if cycle >= write_cycle + 1)
        gates = [selection(config, sample) for sample in strobes]
        expected = edef_reference(gates, first, config)
        assert sum(expected.all_done) == 1, f"EDEF {config.edef}: the run ends before all samples are done"
        assert sum(expected.avg_done) == config.nsmp + 1 and sum(expected.init) == 1
        for index, sample in enumerate(strobes):
            seen = edef_bits(sample.data, config.edef)
            loaded = index >= first + 1
            wanted = {
                "init": expected.init[index],
                "active": expected.active[index],
                "avg_done": expected.avg_done[index],
                "all_done": expected.all_done[index],
                "minor": int(loaded) * (config.sevr & 1),
                "major": int(loaded) * (config.sevr >> 1),
            }
            assert seen == wanted, f"EDEF {config.edef}, strobe {index} (cycle {cycles[index]}): {seen}, expected {wanted}"

    for silent in (0, 2):
        for index, sample in enumerate(strobes):
            assert not any(edef_bits(sample.data, silent).values()), f"EDEF {silent} is not silent at strobe {index}"
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def tpgministream_edef_out_of_range(dut):
    """A write for an index without an instance changes no event-definition bit (observed, intent unconfirmed).

    NUM_EDEFS_G is the first index with no instance, and 15 is the last index
    the 4-bit field can hold. A definition that did start would show init,
    average-done and all-done within a few dozen strobes at rate 0, slot 0.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    first_missing = env_int("NUM_EDEFS_G", default=4)
    writes = {}
    for edef, cycle in ((first_missing, 100), (15, 160)):
        writes[cycle] = write_values(Edef(edef, 1, 2, 0, 0, 0b11))
        writes[cycle + 1] = {"edefWrEn": 0}
    clock_task = await start_stream(dut)
    samples = await record(dut, OUT_OF_RANGE_RUN_CYCLES, writes)
    strobes = [sample for sample in samples if sample.strobe]
    assert len(strobes) >= OUT_OF_RANGE_RUN_CYCLES // CLOCKS_PER_STROBE - 2
    for index, sample in enumerate(strobes):
        data = sample.data
        assert data["edefInit"] == 0, f"strobe {index}: edefInit 0x{data['edefInit']:X}"
        assert data["edefMinor"] == 0, f"strobe {index}: edefMinor 0x{data['edefMinor']:X}"
        assert data["edefMajor"] == 0, f"strobe {index}: edefMajor 0x{data['edefMajor']:X}"
        assert bit_field(data["dmod"], ACTIVE_BIT, 4) == 0, f"strobe {index}: an event definition is active"
        assert data["edefAvgDn"] == bit_field(data["dmod"], ACTIVE_BIT, 20) & ACTIVE_FIXED_RATE_MASK, (
            f"strobe {index}: edefAvgDn 0x{data['edefAvgDn']:X} carries more than the fixed rate bits"
        )
    clock_task.cancel()


def test_TPGMiniStream():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.tpgministreamwrapper",
        parameters={"AC_PERIOD_G": 2, "NUM_EDEFS_G": 4},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
