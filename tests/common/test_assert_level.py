#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Self-test: a severity error assertion must fail a regression case.

Test methodology:
    Sweep: one DUT, AssertLevelFail, whose only behavior is a severity error
        assertion at 5 ns.
    Stimulus: the DUT is built and run through the shared runner, with the
        cocotb entrypoint idling for 10 ns so the assertion fires first.
    Checks: the runner raises SystemExit naming a nonzero ghdl exit, and the
        captured simulator output contains the assertion report text. The text
        proves the failure came from the assertion and not from a compile
        error.
    Timing: the assertion fires at 5 ns, before the cocotb test returns at
        10 ns. No clock is needed.
"""

import logging
from pathlib import Path

import cocotb
from cocotb.triggers import Timer
import pytest

from tests.common.regression_utils import run_lcls_vhdl_test


@cocotb.test(timeout_time=1, timeout_unit="us")
async def idle(dut):
    """Wait past the assertion so the DUT can fail the simulation."""
    await Timer(10, unit="ns")


def test_severity_error_fails_the_case(capfd, caplog):
    caplog.set_level(logging.INFO)
    with pytest.raises(SystemExit) as exc:
        run_lcls_vhdl_test(
            test_file=Path(__file__),
            toplevel="lcls_timing_core.assertlevelfail",
            extra_vhdl_sources={
                "lcls_timing_core": [
                    str(Path(__file__).with_name("assert_level_fail.vhd"))
                ],
            },
        )

    assert "terminated with error 1" in str(exc.value)
    # cocotb-test relays the simulator output through the logging module, so
    # the report text is read from the log records and the file descriptors.
    captured = capfd.readouterr()
    assert "deliberate failure" in caplog.text + captured.out + captured.err
