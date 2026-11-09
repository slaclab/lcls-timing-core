#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1HeartBeat leaf test under GHDL.

Test methodology:
    Sweep: uSecDividerReg of 0, 1, 100 and 1000 for the timeout latency;
        a 50 cycle refresh period against a divider of 100; a reset in the
        cycle where the pulse would be set; a reset held for several cycles.
    Stimulus: reset is held high for 3 eventClk cycles, then released.
        eventCode is driven for one cycle at a time: 0x7A reloads the
        counter, any other code (0x00 here) lets it count down. Inputs are
        changed just after a rising edge, so the next edge captures them.
    Checks: a 0x7A at cycle i is followed by one heartBeatTimeOut cycle,
        which is high only at cycle i + divider + OFFSET, where OFFSET was
        measured under GHDL and is asserted for every divider. A 0x7A that
        arrives before the timeout restarts the count, so a 0x7A every 50
        cycles with a divider of 100 never produces a pulse. Reset forces
        the output low and clears the count. heartBeatTimeOut is resolvable
        on every sample taken after reset release.
    Timing: 10 ns eventClk. The counter is 32 bits wide, so when no 0x7A
        arrives it wraps after 2^32 cycles and times out again; that wrap
        is documented here and not simulated.
    Propagation sampling: the registers update ``after TPD_G`` (1 ns), so
        every sample is taken 2 ns after the rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd

CLOCK_PERIOD_NS = 10
RESET_CYCLES = 3
HEARTBEAT_CODE = 0x7A
IDLE_CODE = 0x00
DIVIDERS = (0, 1, 100, 1000)
# Cycles from a 0x7A to the timeout level: the count is loaded on the edge
# that captures the code, runs down to 0 after `divider` more edges, and the
# edge after that sets the output.
TIMEOUT_OFFSET = 1
REFRESH_DIVIDER = 100
REFRESH_PERIOD = 50
REFRESH_COUNT = 20


async def start_and_release(dut):
    """Hold reset for a few clocks, then release it just after an edge."""
    dut.reset.value = 1
    dut.eventCode.value = IDLE_CODE
    dut.uSecDividerReg.value = 0
    cocotb.start_soon(Clock(dut.eventClk, CLOCK_PERIOD_NS, unit="ns").start())
    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.eventClk)
    dut.reset.value = 0


async def run_cycles(dut, steps):
    """Drive (reset, eventCode) per cycle and return the output after each edge.

    Propagation sampling: each sample is taken 2 ns after the edge that
    captured that cycle's inputs, past the 1 ns ``after TPD_G`` delay.
    """
    trace = []
    for reset, code in steps:
        dut.reset.value = reset
        dut.eventCode.value = code
        await sample_after_tpd(dut.eventClk, propagation_time=2)
        assert dut.heartBeatTimeOut.value.is_resolvable, "heartBeatTimeOut is not resolvable"
        trace.append(int(dut.heartBeatTimeOut.value))
    return trace


def idle(cycles):
    return [(0, IDLE_CODE)] * cycles


def pulses_in(trace):
    return [index for index, level in enumerate(trace) if level == 1]


@cocotb.test(timeout_time=200, timeout_unit="us")
async def heartbeat_times_out_after_divider(dut):
    """One timeout cycle arrives divider + OFFSET cycles after a 0x7A.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_and_release(dut)
    # The counter is 0 after reset, so the first cycle after release times
    # out; run past it and let the free-running count move away from 0.
    await run_cycles(dut, idle(4))

    for divider in DIVIDERS:
        dut.uSecDividerReg.value = divider
        steps = [(0, HEARTBEAT_CODE)] + idle(divider + 10)
        trace = await run_cycles(dut, steps)
        expected = divider + TIMEOUT_OFFSET
        assert pulses_in(trace) == [expected], (
            f"divider {divider}: timeout cycles {pulses_in(trace)}, expected only [{expected}]"
        )


@cocotb.test(timeout_time=200, timeout_unit="us")
async def heartbeat_refresh_suppresses_timeout(dut):
    """A 0x7A before the timeout restarts the count, so no pulse is produced.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_and_release(dut)
    await run_cycles(dut, idle(4))

    dut.uSecDividerReg.value = REFRESH_DIVIDER
    steps = []
    for _ in range(REFRESH_COUNT):
        steps += [(0, HEARTBEAT_CODE)] + idle(REFRESH_PERIOD - 1)
    trace = await run_cycles(dut, steps)
    assert pulses_in(trace) == [], f"timeout cycles {pulses_in(trace)} with a 0x7A every {REFRESH_PERIOD}"

    # Stop refreshing: the last 0x7A is at the first cycle of the final
    # period, which is REFRESH_PERIOD - 1 idle cycles back from the end.
    trace = await run_cycles(dut, idle(REFRESH_DIVIDER + 10))
    expected = REFRESH_DIVIDER + TIMEOUT_OFFSET - REFRESH_PERIOD
    assert pulses_in(trace) == [expected], (
        f"after the refresh stops, timeout cycles {pulses_in(trace)}, expected only [{expected}]"
    )


@cocotb.test(timeout_time=200, timeout_unit="us")
async def heartbeat_reset_clears(dut):
    """Reset forces the output low, including in the cycle a pulse was due.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_and_release(dut)
    await run_cycles(dut, idle(4))

    divider = 20
    dut.uSecDividerReg.value = divider
    due = divider + TIMEOUT_OFFSET
    steps = [(0, HEARTBEAT_CODE)] + idle(due - 1) + [(1, IDLE_CODE)]
    trace = await run_cycles(dut, steps)
    assert trace[due] == 0, "reset in the cycle the timeout was due did not suppress it"
    assert pulses_in(trace) == [], f"timeout cycles {pulses_in(trace)} before the reset took effect"

    # A reset held for several cycles keeps the output low throughout.
    trace = await run_cycles(dut, [(1, IDLE_CODE)] * 5)
    assert trace == [0] * 5, f"output {trace} while reset is held"

    # Reset also drops a count that is still running: the pulse that was
    # scheduled for later never shows up.
    dut.uSecDividerReg.value = 50
    trace = await run_cycles(dut, [(0, HEARTBEAT_CODE)] + idle(10) + [(1, IDLE_CODE)] + idle(80))
    scheduled = 50 + TIMEOUT_OFFSET
    assert trace[scheduled] == 0, "pulse scheduled before the reset still appeared"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def heartbeat_pulse_after_reset_release(dut):
    """The counter restarts at 0, so a timeout follows reset release.

    This is observed, intent unconfirmed: the reset value of the counter is
    0, which the logic reads as an expired heartbeat, so the output pulses
    for one cycle in the first cycle after release.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_and_release(dut)
    trace = await run_cycles(dut, idle(10))
    assert pulses_in(trace) == [0], f"timeout cycles {pulses_in(trace)} after the first release, expected [0]"

    trace = await run_cycles(dut, [(1, IDLE_CODE)] * 3 + idle(10))
    assert trace[:3] == [0, 0, 0], f"output {trace[:3]} while reset is held"
    assert pulses_in(trace) == [3], f"timeout cycles {pulses_in(trace)} after a second release, expected [3]"


def test_EvrV1HeartBeat():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv1heartbeat",
    )
