#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Divider leaf test: the trigO pulse train divides sysClk by divisor.

Test methodology:
    Sweep: Width=4 with divisor=3 in the main run, then divisor 1, 2, 15
        and 0 in the boundary run (the default TPD_G of 1 ns is kept).
        divisor=0 documents the 4-bit counter wrap: the count passes
        through 15 and wraps to 0 before it matches, so the period is 16.
    Stimulus: sysReset is held high for 3 sysClk cycles, then enable=1 and
        clear=0 for the rest of the run. The boundary run resets for 2
        cycles per divisor, samples 40 cycles, freezes the counter with
        trigO high (enable=0, clear=0), then sets clear=1 for 3 cycles.
    Checks: trigO is high on exactly one sampled cycle in every 3
        consecutive cycles, and the gap between two pulses is exactly 3
        cycles. At least 9 pulses are seen over 30 sampled cycles. In the
        boundary run the gaps equal 1, 2, 15 and 16 cycles for divisor 1,
        2, 15 and 0; trigO holds while enable and clear are low, and clear
        with enable low forces trigO low.
    Timing: 10 ns sysClk.
    Propagation sampling: every sample waits 2 ns past the rising edge
        because the registers update ``after TPD_G`` (1 ns).
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd

DIVISOR = 3
SAMPLE_CYCLES = 30
BOUNDARY_SAMPLE_CYCLES = 40
BOUNDARY_PERIODS = ((1, 1), (2, 2), (15, 15), (0, 16))


@cocotb.test(timeout_time=100, timeout_unit="us")
async def divider_divides_by_divisor(dut):
    """Pulse spacing equals divisor.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    dut.sysReset.value = 1
    dut.enable.value = 0
    dut.clear.value = 0
    dut.divisor.value = DIVISOR

    cocotb.start_soon(Clock(dut.sysClk, 10, unit="ns").start())

    for _ in range(3):
        await RisingEdge(dut.sysClk)
    dut.sysReset.value = 0
    dut.enable.value = 1

    pulses = []
    for cycle in range(SAMPLE_CYCLES):
        await sample_after_tpd(dut.sysClk, propagation_time=2)
        if int(dut.trigO.value) == 1:
            pulses.append(cycle)

    assert len(pulses) >= 9, f"expected at least 9 pulses, saw {len(pulses)}: {pulses}"
    gaps = [later - earlier for earlier, later in zip(pulses, pulses[1:])]
    assert all(gap == DIVISOR for gap in gaps), f"pulse gaps {gaps} are not all {DIVISOR}"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def divider_boundary_divisors(dut):
    """Pulse period at divisor 1, 2, 15 and the 4-bit wrap at divisor 0.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    dut.sysReset.value = 1
    dut.enable.value = 0
    dut.clear.value = 0
    dut.divisor.value = 1

    cocotb.start_soon(Clock(dut.sysClk, 10, unit="ns").start())

    for divisor, period in BOUNDARY_PERIODS:
        dut.divisor.value = divisor
        dut.enable.value = 0
        dut.sysReset.value = 1
        for _ in range(2):
            await RisingEdge(dut.sysClk)
        dut.sysReset.value = 0
        dut.enable.value = 1

        pulses = []
        for cycle in range(BOUNDARY_SAMPLE_CYCLES):
            await sample_after_tpd(dut.sysClk, propagation_time=2)
            if int(dut.trigO.value) == 1:
                pulses.append(cycle)

        assert len(pulses) >= 2, f"divisor={divisor}: pulses {pulses}"
        gaps = [later - earlier for earlier, later in zip(pulses, pulses[1:])]
        assert all(gap == period for gap in gaps), (
            f"divisor={divisor}: pulse gaps {gaps} are not all {period}"
        )

    # Freeze the counter with trigO high: it holds until clear drops it.
    for _ in range(BOUNDARY_SAMPLE_CYCLES):
        await sample_after_tpd(dut.sysClk, propagation_time=2)
        if int(dut.trigO.value) == 1:
            break
    assert int(dut.trigO.value) == 1, "no pulse seen while waiting to freeze"
    dut.enable.value = 0
    dut.clear.value = 0
    await sample_after_tpd(dut.sysClk, propagation_time=2)
    assert int(dut.trigO.value) == 1, "trigO must hold with enable and clear low"
    dut.clear.value = 1
    for _ in range(3):
        await sample_after_tpd(dut.sysClk, propagation_time=2)
        assert int(dut.trigO.value) == 0, "clear with enable low must force trigO low"


def test_Divider():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.divider",
        parameters={"Width": 4},
    )
