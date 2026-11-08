#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""No-crash smoke of the legacy TPGMiniEdefTb testbench.

Test methodology:
    Sweep: none, one compiled simulation of TPGMiniEdefTb, which has no
        ports. The file sits in LCLS-II/core/rtl/ but no ruckus.tcl loads it
        (and it is not part of the imported source set), so it is added as an
        extra source of the lcls_timing_core library.
    Stimulus: none from Python. The testbench generates its own clock with a
        100 ns period, releases reset after 4 cycles, writes one EDEF
        configuration into a TPGMiniStream at cycle 40, and finishes by
        itself after 1600 cycles (160 us) by stopping its clock. It prints a
        trace and has no assertions of its own.
    Checks: the simulation runs under --assert-level=error, so any error
        level assertion in the testbench or in the library ends the run as a
        failure. The cocotb entrypoint lets the testbench run for 150 us,
        10 us below its natural end, and requires the simulated time to have
        reached 150 us, the testbench clock to be resolvable and its cycle
        counter to be past 1490 with the done flag still low.
    Timing: 100 ns testbench clock. The 150 us bound is a property of the
        smoke, not of the design: it keeps cocotb ahead of the point where the
        testbench stops its own clock, after which the simulation would have
        no more events.
    Real-time timing: the entrypoint waits for 150 us of simulated time with
        a single timer, so no edge relative sampling is needed.
"""

from pathlib import Path

import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

from tests.common.regression_utils import REPO_ROOT, run_lcls_vhdl_test

TESTBENCH = REPO_ROOT / "LCLS-II/core/rtl/TPGMiniEdefTb.vhd"

MIN_CYCLES = 1490


@cocotb.test(timeout_time=400, timeout_unit="us")
async def edef_tb_no_crash(dut):
    """The testbench runs for 150 us, below its 160 us natural end, without an error level assertion.

    Real-time timing: one timer for the whole run, then the signals are read once.
    """
    await Timer(150, unit="us")

    assert get_sim_time(unit="us") >= 150, "the simulation stopped before 150 us"
    assert dut.clk.value.is_resolvable, f"the testbench clock is unresolved: {dut.clk.value}"
    assert dut.cnt.value.is_resolvable, f"the cycle counter is unresolved: {dut.cnt.value}"
    assert int(dut.cnt.value) >= MIN_CYCLES, f"only {int(dut.cnt.value)} testbench cycles in 150 us"
    assert int(dut.don.value) == 0, "the testbench finished before 150 us"


def test_TPGMiniEdefTb():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.tpgminiedeftb",
        extra_vhdl_sources={"lcls_timing_core": [str(TESTBENCH)]},
    )
