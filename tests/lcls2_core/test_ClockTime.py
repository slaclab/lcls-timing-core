#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""ClockTime leaf test: fractional step accumulation and second rollover.

Test methodology:
    Sweep: step=5 with remainder=5 and divisor=13 (the rational 5 + 5/13 ns
        step), and step=5 with remainder=0 (the integer step). The default
        TPD_G of 1 ns and FRACTION_DEPTH_G of 5 are kept.
    Stimulus: two unrelated clocks, clkA at 10 ns and clkB at 5 ns, started
        low after the inputs are driven. rst is held for 10 clkB cycles and
        40 more cycles pass before the first load. A time is loaded by
        driving wrData and pulsing wrEnA for one clkA cycle with wrEnB held
        high; the load lands in the clkB domain through the synchronizer
        FIFO.
    Checks: after a load, the nanosecond word of dataO advances by exactly
        70 over 13 clkB cycles and 140 over 26 with the rational step, with
        every cycle adding 5 or 6, so the fractional remainder carries with
        no drift; with remainder=0 it advances exactly 5 per cycle. Loading
        999999995 ns makes the next clkB cycle roll the nanosecond word to 0
        and increment the seconds word, loading 999999994 ns does not roll
        (the sum is 999999999 ns), and a further step rolls from there.
    Timing: clkA 10 ns, clkB 5 ns.
    Propagation sampling: dataO updates after TPD_G (1 ns), so every sample
        is taken 2 ns past a rising clkB edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd

ONE_SECOND_NS = 1000000000
LOAD_LATENCY_LIMIT = 20


async def start_clocks_and_reset(dut, *, remainder):
    dut.step.value = 5
    dut.remainder.value = remainder
    dut.divisor.value = 13
    dut.rst.value = 1
    dut.wrEnA.value = 0
    dut.wrEnB.value = 1
    dut.wrData.value = 0

    cocotb.start_soon(Clock(dut.clkA, 10, unit="ns").start(start_high=False))
    cocotb.start_soon(Clock(dut.clkB, 5, unit="ns").start(start_high=False))

    for _ in range(10):
        await RisingEdge(dut.clkB)
    dut.rst.value = 0
    # The FIFO reset synchronizers release over several cycles in each clock
    # domain; a write before they release is silently dropped.
    for _ in range(40):
        await RisingEdge(dut.clkB)


def split(dut):
    value = int(dut.dataO.value)
    return value >> 32, value & 0xFFFFFFFF


async def load(dut, seconds, nanos):
    """Load a time and return once the loaded value is visible on dataO.

    Propagation sampling: dataO is sampled 2 ns past each clkB edge.
    """
    dut.wrData.value = (seconds << 32) | nanos
    dut.wrEnA.value = 1
    await RisingEdge(dut.clkA)
    dut.wrEnA.value = 0

    for _ in range(LOAD_LATENCY_LIMIT):
        await sample_after_tpd(dut.clkB, propagation_time=2)
        if split(dut) == (seconds, nanos):
            return
    raise AssertionError(
        f"loaded value ({seconds}, {nanos}) not visible on dataO within "
        f"{LOAD_LATENCY_LIMIT} clkB cycles, last seen {split(dut)}"
    )


async def sample_nanos(dut, cycles):
    """Sample the nanosecond word for the next cycles clkB edges."""
    samples = []
    for _ in range(cycles):
        await sample_after_tpd(dut.clkB, propagation_time=2)
        samples.append(split(dut))
    return samples


@cocotb.test(timeout_time=100, timeout_unit="us")
async def clocktime_rational_step(dut):
    """The 5 + 5/13 ns step advances 70 ns per 13 cycles with no drift."""
    await start_clocks_and_reset(dut, remainder=5)
    await load(dut, 1, 1000)
    base = 1000

    samples = await sample_nanos(dut, 26)
    nanos = [base] + [n for _, n in samples]
    assert all(s == 1 for s, _ in samples), f"seconds changed: {samples}"
    deltas = [later - earlier for earlier, later in zip(nanos, nanos[1:])]
    assert all(delta in (5, 6) for delta in deltas), f"per-cycle deltas {deltas}"
    assert nanos[13] - base == 70, f"13 cycles advanced {nanos[13] - base} ns"
    assert nanos[26] - base == 140, f"26 cycles advanced {nanos[26] - base} ns"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def clocktime_integer_step(dut):
    """With remainder=0 every clkB cycle adds exactly the step."""
    await start_clocks_and_reset(dut, remainder=0)
    await load(dut, 1, 1000)

    samples = await sample_nanos(dut, 26)
    expected = [(1, 1000 + 5 * (k + 1)) for k in range(26)]
    assert samples == expected, f"integer step samples {samples}"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def clocktime_second_rollover(dut):
    """The nanosecond word rolls into seconds at exactly 1000000000."""
    await start_clocks_and_reset(dut, remainder=0)

    await load(dut, 7, ONE_SECOND_NS - 5)
    (rolled,) = await sample_nanos(dut, 1)
    assert rolled == (8, 0), f"999999995 + 5 gave {rolled}, expected (8, 0)"

    await load(dut, 7, ONE_SECOND_NS - 6)
    (held,) = await sample_nanos(dut, 1)
    assert held == (7, ONE_SECOND_NS - 1), (
        f"999999994 + 5 gave {held}, expected (7, 999999999)"
    )
    (carried,) = await sample_nanos(dut, 1)
    assert carried == (8, 4), f"999999999 + 5 gave {carried}, expected (8, 4)"


def test_ClockTime():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.clocktime",
    )
