#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Test-only Verilog model of EvrV1Databuff under Icarus, same vectors as GHDL.

This test exists to prove that the behavioral model in
tests/lcls1_evr/models/EvrV1Databuff_model.v equals the production RAM. It is
not coverage of the production file: the production EvrV1Databuff.vhd is
covered by test_EvrV1Databuff.py with the very same vectors and assertions.

Test methodology:
    Sweep: the vector set in databuff_vectors.py (the same one the GHDL test
        runs), plus the repeated write to one byte.
    Stimulus: no reset exists. clka runs at 10 ns and clkb at 7 ns. Inputs
        change on falling edges of their own clock.
    Checks: identical to the GHDL test: little-endian word packing, zero for
        never-written words, and a read latency of READ_LATENCY clkb edges.
    Timing: 10 ns clka, 7 ns clkb; the model has a 1 ns / 100 ps timescale.
    Propagation sampling: the model has no delayed assignments, so each
        sample settles through a ReadOnly phase after the clkb rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common.regression_utils import (
    REPO_ROOT,
    run_icarus_verilog_test,
    sample_after_delta_cycles,
)
from tests.lcls1_evr.databuff_vectors import run_databuff_vectors, run_last_write_wins

CLKA_PERIOD_NS = 10
CLKB_PERIOD_NS = 7
MODEL_SOURCE = REPO_ROOT / "tests/lcls1_evr/models/EvrV1Databuff_model.v"


def start_clocks(dut):
    cocotb.start_soon(Clock(dut.clka, CLKA_PERIOD_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.clkb, CLKB_PERIOD_NS, unit="ns").start())


@cocotb.test(timeout_time=200, timeout_unit="us")
async def databuff_model_shared_vectors(dut):
    """The shared vector set passes on the Verilog model.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the clkb edge.
    """
    start_clocks(dut)
    await run_databuff_vectors(
        dut, lambda: sample_after_delta_cycles(dut.clkb), dut._log
    )


@cocotb.test(timeout_time=100, timeout_unit="us")
async def databuff_model_last_write_wins(dut):
    """Of two writes to one byte, the second is the one read.

    Propagation sampling: each sample settles through a ReadOnly phase.
    """
    start_clocks(dut)
    await run_last_write_wins(
        dut, lambda: sample_after_delta_cycles(dut.clkb), dut._log
    )


def test_EvrV1DatabuffModel():
    run_icarus_verilog_test(
        test_file=Path(__file__),
        toplevel="EvrV1Databuff",
        verilog_sources=[str(MODEL_SOURCE)],
    )
