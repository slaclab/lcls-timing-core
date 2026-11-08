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
    Sweep: Width=4 with divisor=3 (the default TPD_G of 1 ns is kept).
    Stimulus: sysReset is held high for 3 sysClk cycles, then enable=1 and
        clear=0 for the rest of the run.
    Checks: trigO is high on exactly one sampled cycle in every 3
        consecutive cycles, and the gap between two pulses is exactly 3
        cycles. At least 9 pulses are seen over 30 sampled cycles.
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


def test_Divider():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.divider",
        parameters={"Width": 4},
    )
