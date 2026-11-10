#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""cocotbext-axi AXI-Lite master smoke test under the installed cocotb.

This test proves that cocotbext-axi works under the installed cocotb before
any AXI-Lite register test in this repository depends on it. The DUT is surf's
own flat-port IP integrator wrapper, surf.AxiLiteRegsIpIntegrator, which is
already imported into build/SRC_VHDL/surf, so no VHDL is added here.

Test methodology:
    Sweep: one DUT, surf.AxiLiteRegsIpIntegrator with its default generics,
        which gives one read register at 0x000 and one write register at
        0x100. Every other address answers DECERR.
    Stimulus: a cocotbext-axi AxiLiteMaster writes 0xDEADBEEF to 0x100,
        reads it back, reads the read register at 0x000 (driven to
        0x11223344), and reads the unmapped address 0x080.
    Checks: response codes (OKAY for the mapped addresses, DECERR for the
        unmapped one), the read-back data, and the flattened
        writeRegisterOut value.
    Timing: 10 ns axilClk, every transaction is bounded by the cocotb
        timeout.
    Propagation sampling: AxiLiteRegs registers update ``after TPD_G``
        (1 ns), so register outputs are sampled 2 ns past the edge with
        sample_after_tpd.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiResp

from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd

WRITE_REG_ADDR = 0x100
READ_REG_ADDR = 0x000
UNMAPPED_ADDR = 0x080
WRITE_DATA = 0xDEADBEEF
READ_DATA = 0x11223344


@cocotb.test(timeout_time=50, timeout_unit="us")
async def axil_write_read_smoke(dut):
    """Write, read back, read the read-only window and hit DECERR.

    Propagation sampling: register outputs are sampled 2 ns after the edge,
    past the 1 ns ``after TPD_G`` register delay.
    """
    # Order matters on cocotb 2.x: reset and the read register are driven and
    # the master constructed (which drives the valids to 0) before the clock
    # starts, otherwise the first reads of the flat ports return U.
    dut.axilRst.value = 1
    dut.readRegisterIn.value = READ_DATA
    master = AxiLiteMaster(
        AxiLiteBus.from_prefix(dut, "S_AXI"),
        dut.axilClk,
        dut.axilRst,
        reset_active_level=True,
    )
    await Timer(1, unit="ns")

    clock_task = cocotb.start_soon(Clock(dut.axilClk, 10, unit="ns").start(start_high=False))

    for _ in range(3):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
    dut.axilRst.value = 0
    for _ in range(3):
        await sample_after_tpd(dut.axilClk, propagation_time=2)

    write_resp = await master.write(WRITE_REG_ADDR, WRITE_DATA.to_bytes(4, "little"))
    assert write_resp.resp == AxiResp.OKAY, f"write response {write_resp.resp!r}"

    read_back = await master.read(WRITE_REG_ADDR, 4)
    assert read_back.resp == AxiResp.OKAY, f"read-back response {read_back.resp!r}"
    assert int.from_bytes(read_back.data, "little") == WRITE_DATA, (
        f"read back 0x{int.from_bytes(read_back.data, 'little'):08X}"
    )

    for _ in range(2):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
    assert int(dut.writeRegisterOut.value) == WRITE_DATA, (
        f"writeRegisterOut 0x{int(dut.writeRegisterOut.value):08X}"
    )

    read_only = await master.read(READ_REG_ADDR, 4)
    assert read_only.resp == AxiResp.OKAY, f"read window response {read_only.resp!r}"
    assert int.from_bytes(read_only.data, "little") == READ_DATA, (
        f"read window 0x{int.from_bytes(read_only.data, 'little'):08X}"
    )

    unmapped = await master.read(UNMAPPED_ADDR, 4)
    assert unmapped.resp == AxiResp.DECERR, f"unmapped response {unmapped.resp!r}"

    clock_task.cancel()


def test_cocotbext_axi_smoke():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="surf.axiliteregsipintegrator",
    )
