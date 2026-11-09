#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1TimeofDayReceiver leaf test under Icarus Verilog.

Test methodology:
    Sweep: seconds values 0, 0xFFFFFFFF and 0x80000001, plus 20 seeded
        random values; other event codes between the bits; a latch in the
        middle of a word; Reset in the middle of a word.
    Stimulus: Reset is held high for 3 Clock cycles, then released. A
        seconds value is sent as 32 event codes, 0x71 for a 1 and 0x70 for
        a 0, most significant bit first, one code per clock, followed by
        0x7D. Inputs are driven one time step after a rising edge, so the
        next edge captures them. The seed of the random values is logged.
    Checks: secondsShift follows the bits as they arrive, and the position
        in timeDebug counts the bits sent and wraps to 0 after 32. Two
        clocks after 0x7D the upper word of TimeStamp equals the seconds
        value and the lower word is 0; it then rises by 1 per clock. Codes
        other than 0x70, 0x71 and 0x7D do not move the pointer or change
        the seconds. 0x7D clears the pointer. Reset clears the seconds, the
        pointer and TimeStamp, and wins over a 0x7D in the same cycle.
        Every output is resolvable after the Reset cycles.
    Timing: 10 ns Clock. The language mode is the runner default: cocotb-test
        passes -g2012 to Icarus, and -g2005 also compiles this file.
    Propagation sampling: the module has no delayed assignments, so each
        sample settles through a ReadOnly phase after the rising edge
        instead of a time offset.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep

from tests.common import timing_model
from tests.common.regression_utils import (
    run_icarus_verilog_test,
    sample_after_delta_cycles,
)

CLOCK_PERIOD_NS = 10
RESET_CYCLES = 3
BITS = 32
ZERO_CODE = 0x70
ONE_CODE = 0x71
LATCH_CODE = 0x7D
IDLE_CODE = 0x00
# Codes that must not move the pointer or change the seconds.
OTHER_CODES = (0x00, 0x7A, 0x7B, 0x7C, 0x6F, 0x72, 0x01, 0xFF)
DIRECTED_SECONDS = (0x00000000, 0xFFFFFFFF, 0x80000001)
RANDOM_SECONDS = 20
# TimeStamp shows the latched value this many clocks after the 0x7D edge.
LATCH_LATENCY = 2
FOLLOW_CYCLES = 6


class Snapshot:
    """Outputs after one rising edge."""

    def __init__(self, dut):
        for name in ("TimeStamp", "timeDebug", "secondsShift"):
            assert getattr(dut, name).value.is_resolvable, f"{name} is not resolvable"
        self.time_stamp = int(dut.TimeStamp.value)
        debug = int(dut.timeDebug.value)
        self.seconds = debug & 0xFFFFFFFF
        self.position = debug >> 32
        self.seconds_shift = int(dut.secondsShift.value)
        assert self.seconds_shift == self.seconds, "secondsShift differs from the seconds in timeDebug"


async def step(dut, code, reset=0):
    """Drive one cycle, wait for the edge that captures it, and sample.

    Propagation sampling: the sample settles through a ReadOnly phase after
    the edge, then the test moves one time step on before it drives again.
    """
    dut.EventStream.value = code
    dut.Reset.value = reset
    await sample_after_delta_cycles(dut.Clock)
    snapshot = Snapshot(dut)
    await NextTimeStep()
    return snapshot


async def start_and_release(dut):
    """Hold Reset for a few clocks, then release it after an edge."""
    dut.EventStream.value = IDLE_CODE
    dut.Reset.value = 1
    cocotb.start_soon(Clock(dut.Clock, CLOCK_PERIOD_NS, unit="ns").start())
    for _ in range(RESET_CYCLES):
        await sample_after_delta_cycles(dut.Clock)
        await NextTimeStep()
    dut.Reset.value = 0


async def send_bits(dut, value, between=()):
    """Send `value` MSB first and return the snapshot after each bit."""
    snapshots = []
    for index in range(BITS):
        bit = (value >> (BITS - 1 - index)) & 1
        snapshots.append(await step(dut, ONE_CODE if bit else ZERO_CODE))
        for code in between:
            await step(dut, code)
    return snapshots


async def latch_and_follow(dut):
    """Send 0x7D and return the snapshots from the 0x7D edge onwards."""
    trace = [await step(dut, LATCH_CODE)]
    for _ in range(LATCH_LATENCY + FOLLOW_CYCLES):
        trace.append(await step(dut, IDLE_CODE))
    return trace


def check_latched(trace, value):
    """TimeStamp shows {value, 0} two clocks after 0x7D and then counts by 1."""
    for offset in range(LATCH_LATENCY, len(trace)):
        expected = (value << 32) | (offset - LATCH_LATENCY)
        got = trace[offset].time_stamp
        assert got == expected, (
            f"TimeStamp {got:#018x} {offset} clocks after 0x7D, expected {expected:#018x}"
        )


@cocotb.test(timeout_time=200, timeout_unit="us")
async def tod_latches_seconds(dut):
    """32 codes shift the seconds in MSB first and 0x7D latches them.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    previous = 0
    for value in DIRECTED_SECONDS:
        snapshots = await send_bits(dut, value)
        for sent, snapshot in enumerate(snapshots, start=1):
            mask = ((1 << sent) - 1) << (BITS - sent)
            expected = (value & mask) | (previous & ~mask & 0xFFFFFFFF)
            assert snapshot.seconds_shift == expected, (
                f"after {sent} bits of {value:#010x} secondsShift is {snapshot.seconds_shift:#010x}, "
                f"expected {expected:#010x}"
            )
            assert snapshot.position == sent % BITS, (
                f"position {snapshot.position} after {sent} bits, expected {sent % BITS}"
            )
        trace = await latch_and_follow(dut)
        assert trace[0].position == 0, f"position {trace[0].position} after 0x7D, expected 0"
        check_latched(trace, value)
        previous = value


@cocotb.test(timeout_time=200, timeout_unit="us")
async def tod_ignores_other_codes(dut):
    """Other codes between the bits do not move the pointer, and 0x7D restarts it.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    value = 0xA5C3_3C5A
    for sent in range(1, BITS + 1):
        bit = (value >> (BITS - sent)) & 1
        before = await step(dut, ONE_CODE if bit else ZERO_CODE)
        for code in OTHER_CODES:
            snapshot = await step(dut, code)
            assert snapshot.position == before.position, (
                f"code {code:#04x} moved the position from {before.position} to {snapshot.position}"
            )
            assert snapshot.seconds == before.seconds, (
                f"code {code:#04x} changed the seconds from {before.seconds:#x} to {snapshot.seconds:#x}"
            )
    trace = await latch_and_follow(dut)
    check_latched(trace, value)

    # 0x7D in the middle of a word clears the pointer: the next bit lands in
    # bit 31 again, and the latched upper word holds the bits sent so far on
    # top of the previous word.
    for _ in range(10):
        await step(dut, ZERO_CODE)
    trace = await latch_and_follow(dut)
    assert trace[0].position == 0, f"position {trace[0].position} after a mid-word 0x7D, expected 0"
    partial = value & 0x003FFFFF
    check_latched(trace, partial)
    after = await step(dut, ONE_CODE)
    assert after.seconds >> 31 == 1, "the first bit after 0x7D did not land in bit 31"
    assert after.position == 1, f"position {after.position} after the first bit, expected 1"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def tod_reset(dut):
    """Reset clears the seconds, the pointer and TimeStamp, and beats 0x7D.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    await send_bits(dut, 0xDEADBEEF)
    await latch_and_follow(dut)
    for _ in range(5):
        await step(dut, ONE_CODE)

    snapshot = await step(dut, LATCH_CODE, reset=1)
    assert snapshot.seconds == 0, f"seconds {snapshot.seconds:#x} after Reset, expected 0"
    assert snapshot.position == 0, f"position {snapshot.position} after Reset, expected 0"
    assert snapshot.time_stamp == 0, f"TimeStamp {snapshot.time_stamp:#x} after Reset, expected 0"
    for _ in range(3):
        snapshot = await step(dut, IDLE_CODE, reset=1)
        assert (snapshot.seconds, snapshot.position, snapshot.time_stamp) == (0, 0, 0), (
            "outputs left zero while Reset is held"
        )

    # After release the lower word counts again with the usual two clock lag.
    counts = [(await step(dut, IDLE_CODE)).time_stamp for _ in range(FOLLOW_CYCLES)]
    assert counts == [0, 0] + list(range(1, FOLLOW_CYCLES - 1)), (
        f"TimeStamp after Reset release is {counts}"
    )


@cocotb.test(timeout_time=200, timeout_unit="us")
async def tod_random_seconds(dut):
    """Directed and seeded random seconds values round-trip through 0x7D.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")
    values = list(DIRECTED_SECONDS) + [rng.getrandbits(BITS) for _ in range(RANDOM_SECONDS)]
    for value in values:
        await send_bits(dut, value)
        trace = await latch_and_follow(dut)
        assert trace[LATCH_LATENCY].time_stamp >> 32 == value, (
            f"latched upper word {trace[LATCH_LATENCY].time_stamp >> 32:#010x}, expected {value:#010x}"
        )
        check_latched(trace, value)


def test_EvrV1TimeofDayReceiver():
    run_icarus_verilog_test(
        test_file=Path(__file__),
        toplevel="EvrV1TimeofDayReceiver",
    )
