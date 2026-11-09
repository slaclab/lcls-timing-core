#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1Databuff leaf test under GHDL, using the shared Databuff vectors.

Test methodology:
    Sweep: the vector set in databuff_vectors.py: a full word, a word
        written one lane at a time out of order, a single byte in lane 3,
        the last word, 64 consecutive bytes, and words never written. A
        second case writes one byte twice.
    Stimulus: no reset exists. clka runs at 10 ns and clkb at 7 ns. Inputs
        change on falling edges of their own clock. Bytes are written back
        to back with wea high, then one address is presented per clkb cycle,
        back to back, and each word is checked as it appears.
    Checks: every word read through port B equals the little-endian packing
        of the bytes written through port A, never-written words read 0,
        and the read latency is READ_LATENCY clkb edges. The very same
        assertion coroutine runs against the test-only Verilog model in
        test_EvrV1DatabuffModel.py, which is what ties the model to this
        production RAM.
    Timing: 10 ns clka, 7 ns clkb.
    Propagation sampling: the data output updates ``after TPD_G`` (1 ns),
        so every sample is taken 2 ns after the clkb rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd
from tests.lcls1_evr.databuff_vectors import run_databuff_vectors, run_last_write_wins

CLKA_PERIOD_NS = 10
CLKB_PERIOD_NS = 7


def start_clocks(dut):
    cocotb.start_soon(Clock(dut.clka, CLKA_PERIOD_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.clkb, CLKB_PERIOD_NS, unit="ns").start())


@cocotb.test(timeout_time=200, timeout_unit="us")
async def databuff_shared_vectors(dut):
    """The shared vector set passes on the production RAM.

    Propagation sampling: samples are taken 2 ns after the clkb edge, past
    the 1 ns ``after TPD_G`` delay.
    """
    start_clocks(dut)
    await run_databuff_vectors(
        dut, lambda: sample_after_tpd(dut.clkb, propagation_time=2), dut._log
    )


@cocotb.test(timeout_time=100, timeout_unit="us")
async def databuff_last_write_wins(dut):
    """Of two writes to one byte, the second is the one read.

    Propagation sampling: samples are taken 2 ns after the clkb edge.
    """
    start_clocks(dut)
    await run_last_write_wins(
        dut, lambda: sample_after_tpd(dut.clkb, propagation_time=2), dut._log
    )


def test_EvrV1Databuff():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv1databuff",
    )
