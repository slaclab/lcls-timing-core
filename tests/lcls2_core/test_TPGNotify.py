#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGNotify leaf test: each interrupt presents one tValid cycle with the count.

TPGNotify.vhd is not loaded by any ruckus.tcl, so it is compiled here as an
extra source together with the TPGNotifyWrapper that flattens the
AxiStreamMasterType output into plain ports.

Test methodology:
    Sweep: none, the entity has only the TPD_G generic (default 1 ns).
    Stimulus: txRst is held for 5 txClk cycles with irqEnable=1 and
        irqReq=0. Three interrupts follow: irqReq is raised, held for 5
        cycles, then dropped, and the outputs are sampled for 20 cycles
        per interrupt. A fourth irqReq pulse is applied with irqEnable=0.
    Checks: tValid is high on exactly one sampled cycle per interrupt,
        tData carries the interrupt count (0, 1, 2) on that cycle with
        tLast=1 and tDest=0xFF, and tValid stays low for the whole window
        when irqEnable is low.
    Timing: 10 ns txClk.
    Propagation sampling: every sample waits 2 ns past the rising edge
        because the registers update ``after TPD_G`` (1 ns).
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common.regression_utils import REPO_ROOT, run_lcls_vhdl_test, sample_after_tpd

NOTIFY = REPO_ROOT / "LCLS-II/core/rtl/TPGNotify.vhd"
WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TPGNotifyWrapper.vhd"

RESET_CYCLES = 5
IRQ_HOLD_CYCLES = 5
WINDOW_CYCLES = 20
INTERRUPTS = 3


async def interrupt_window(dut):
    """Pulse irqReq and return the (tValid, tData, tLast, tDest) trace."""
    dut.irqReq.value = 1
    trace = []
    for cycle in range(WINDOW_CYCLES):
        if cycle == IRQ_HOLD_CYCLES:
            dut.irqReq.value = 0
        await sample_after_tpd(dut.txClk, propagation_time=2)
        trace.append((
            int(dut.tValid.value),
            int(dut.tData.value),
            int(dut.tLast.value),
            int(dut.tDest.value),
        ))
    return trace


@cocotb.test(timeout_time=100, timeout_unit="us")
async def one_tvalid_cycle_per_interrupt(dut):
    """Each synchronized interrupt gives exactly one tValid beat with the count.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    dut.txRst.value = 1
    dut.irqReq.value = 0
    dut.irqEnable.value = 1

    cocotb.start_soon(Clock(dut.txClk, 10, unit="ns").start())

    for _ in range(RESET_CYCLES):
        await sample_after_tpd(dut.txClk, propagation_time=2)
    dut.txRst.value = 0
    for _ in range(RESET_CYCLES):
        await sample_after_tpd(dut.txClk, propagation_time=2)
        assert int(dut.tValid.value) == 0, "tValid high before any interrupt"

    for interrupt in range(INTERRUPTS):
        trace = await interrupt_window(dut)
        valid = [index for index, (flag, _, _, _) in enumerate(trace) if flag]
        assert len(valid) == 1, f"interrupt {interrupt}: tValid high in cycles {valid}"
        _, data, last, dest = trace[valid[0]]
        assert data == interrupt, f"interrupt {interrupt}: tData {data}"
        assert last == 1, f"interrupt {interrupt}: tLast {last}"
        assert dest == 0xFF, f"interrupt {interrupt}: tDest 0x{dest:02x}"

    dut.irqEnable.value = 0
    trace = await interrupt_window(dut)
    valid = [index for index, (flag, _, _, _) in enumerate(trace) if flag]
    assert valid == [], f"irqEnable=0: tValid high in cycles {valid}"


def test_TPGNotify():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.tpgnotifywrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(NOTIFY), str(WRAPPER)]},
    )
