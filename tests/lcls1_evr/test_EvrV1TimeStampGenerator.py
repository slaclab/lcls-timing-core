#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1TimeStampGenerator leaf test under Icarus Verilog.

Test methodology:
    Sweep: the first second after reset (20 consecutive clocks, taken after
        the initial reload) and the one-second reload boundary (the
        330556-clock period of the internal Count reload).
    Stimulus: Reset is held high for 3 Clock cycles, then released. The
        increment case samples 20 consecutive clocks starting 2 clocks
        after the release. The rollover case waits once for 330600 clocks
        after the release.
    Checks: TimeStamp rises by exactly 1 per clock with bits 63:32 equal
        to 0 inside the first second. After 330600 clocks bits 63:32 equal
        1 and bits 31:0 are below 64, so the lower word restarted from 0
        at the reload.
    Timing: 10 ns Clock; the Verilog has a 1 ns / 1 ps timescale.
    Propagation sampling: the module has no delayed assignments, so each
        sample settles through a ReadOnly phase after the rising edge
        (the rollover case after a single Timer) instead of a time offset.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge, Timer

from tests.common.regression_utils import (
    run_icarus_verilog_test,
    sample_after_delta_cycles,
)

CLOCK_PERIOD_NS = 10
RESET_CYCLES = 3
RELOAD_SKIP_CYCLES = 2
SAMPLE_CYCLES = 20
ROLLOVER_CLOCKS = 330600
LOWER_WORD_LIMIT = 64


async def reset_and_release(dut):
    """Drive Reset high for a few clocks, then release it just after an edge."""
    dut.Reset.value = 1
    cocotb.start_soon(Clock(dut.Clock, CLOCK_PERIOD_NS, unit="ns").start())
    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.Clock)
    dut.Reset.value = 0


@cocotb.test(timeout_time=10, timeout_unit="us")
async def timestamp_increments(dut):
    """TimeStamp counts up by 1 per clock with a zero upper word."""
    await reset_and_release(dut)

    # The first clock after release reloads Count and the second starts the
    # increment, so sampling begins after both.
    for _ in range(RELOAD_SKIP_CYCLES):
        await RisingEdge(dut.Clock)

    await sample_after_delta_cycles(dut.Clock)
    previous = int(dut.TimeStamp.value)
    for _ in range(SAMPLE_CYCLES):
        await sample_after_delta_cycles(dut.Clock)
        current = int(dut.TimeStamp.value)
        assert current >> 32 == 0, f"upper word is {current >> 32:#x} inside the first second"
        assert current == previous + 1, f"TimeStamp went {previous:#x} to {current:#x}, not +1"
        previous = current


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def timestamp_second_rollover(dut):
    """The upper word becomes 1 and the lower word restarts at the reload."""
    await reset_and_release(dut)

    await Timer(ROLLOVER_CLOCKS * CLOCK_PERIOD_NS, unit="ns")
    await ReadOnly()

    value = int(dut.TimeStamp.value)
    upper, lower = value >> 32, value & 0xFFFFFFFF
    assert upper == 1, f"upper word is {upper:#x} after {ROLLOVER_CLOCKS} clocks, expected 1"
    assert lower < LOWER_WORD_LIMIT, (
        f"lower word is {lower:#x} after {ROLLOVER_CLOCKS} clocks, expected below {LOWER_WORD_LIMIT}"
    )


def test_EvrV1TimeStampGenerator():
    run_icarus_verilog_test(
        test_file=Path(__file__),
        toplevel="EvrV1TimeStampGenerator",
    )
