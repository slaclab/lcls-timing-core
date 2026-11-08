#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Bounded smoke of the legacy TimingSerialDelayTb self-checking testbench.

Test methodology:
    Sweep: none, one compiled simulation of TimingSerialDelayTb, which has no
        ports; it is loaded from LCLS-II/core/tb/ (it is not part of the
        imported source set).
    Stimulus: none from Python. The testbench generates its own 10 ns clock,
        a fiducial every 66 clocks, 16 word frames, and a periodic reset of
        the delay line, and checks the frames and their delay itself with
        assertions. The simulation is stopped after 160 us.
    Checks: the testbench runs under --assert-level=error, so any failed
        assertion ("Frame error", "FIFO overflow", "Unexpected frame delay")
        ends the run as a failure. After 160 us the simulated time is at
        least 160 us, the clock and the overflow flag are resolvable and
        overflow is low, and the delay line has produced strobes.
    Timing: 10 ns testbench clock. The bound is a property of the stale
        testbench, not of TimingSerialDelay: its frame tag is 8 bits wide, so
        256 fiducials x 66 clocks x 10 ns = 168.96 us is the tag wrap, and the
        delay check "Unexpected frame delay" fails at about 170.68 us because
        the tag it compares against has wrapped. Running past that point is a
        testbench failure (candidate maintainer question: refresh or
        retire the testbench), so the smoke stops at 160 us.
    Propagation sampling: the entrypoint reads signals once, long after the
        last edge activity it cares about, so no edge-relative sampling is
        needed; strobes are counted from signal edges.
"""

from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.utils import get_sim_time

from tests.common.regression_utils import REPO_ROOT, run_lcls_vhdl_test

TESTBENCH = REPO_ROOT / "LCLS-II/core/tb/TimingSerialDelay_tb.vhd"

MIN_STROBES = 100


@cocotb.test(timeout_time=300, timeout_unit="us")
async def serialdelay_tb_smoke(dut):
    """The testbench runs for 160 us, below the 168.96 us tag wrap, without an error-level assertion.

    The testbench would fail at about 170.68 us ("Unexpected frame delay");
    that is documented in the module docstring and not simulated.

    Propagation sampling: signals are read once at the end of the run.
    """
    strobes = [0]

    async def count_strobes():
        for _ in range(16000):
            await RisingEdge(dut.strobe)
            strobes[0] += 1

    counter = cocotb.start_soon(count_strobes())
    await Timer(160, unit="us")
    counter.cancel()

    assert get_sim_time(unit="us") >= 160, "the simulation stopped before 160 us"
    assert dut.clk.value.is_resolvable, f"the testbench clock is unresolved: {dut.clk.value}"
    assert dut.overflow.value.is_resolvable, f"overflow is unresolved: {dut.overflow.value}"
    assert int(dut.overflow.value) == 0, "the delay FIFO overflowed"
    assert strobes[0] >= MIN_STROBES, f"only {strobes[0]} strobes in 160 us"


def test_TimingSerialDelayTb():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingserialdelaytb",
        extra_vhdl_sources={"lcls_timing_core": [str(TESTBENCH)]},
    )
