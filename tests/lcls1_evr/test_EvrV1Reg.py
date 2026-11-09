#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1Reg register file test over AXI-Lite through a flat-port wrapper.

Test methodology:
    Sweep: the version words and the control register walk (this task of the
        file); every writable word with USE_WSTRB_G false and true, and the
        read-only words, the latch latency, the interrupts and the decode
        errors as later entrypoints are added.
    Stimulus: a cocotbext-axi AxiLiteMaster on the S_AXI port, 10 ns axilClk,
        reset held for three clocks. The build information is fixed by the
        wrapper to the firmware version 0xA1B2C3D4. Reads of EvrV1Reg wait
        for a latch-latency counter, so every blocking master read is
        bounded by the cocotb timeout.
    Checks: the version words read the values the read decode builds from
        the firmware version; the control register resets to 0 and every bit
        reads back as written except the self-clearing latch bit; the
        configuration outputs each bit drives are the ones measured under
        GHDL. Every checked output is resolvable after reset release.
    Timing: 10 ns axilClk; a register write reaches its configuration output
        after the clock edges that follow the write response.
    Propagation sampling: the registers update after TPD_G (1 ns), so every
        configuration output is sampled 2 ns after a rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiResp

from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-I/wrappers/EvrV1RegWrapper.vhd"

CLOCK_NS = 10
RESET_CLOCKS = 3
SETTLE_CLOCKS = 4
PROPAGATION_NS = 2
WORD_BITS = 32
WORD_BYTES = 4

FW_VERSION = 0xA1B2C3D4
# Word 11 is the fixed prefix 0001 1111 above the low 24 bits of the firmware
# version; word 12 is the firmware version with its bytes reversed.
VERSION_WORD = 0x1F000000 | (FW_VERSION & 0xFFFFFF)
VERSION_SWAPPED_WORD = int.from_bytes(FW_VERSION.to_bytes(4, "big"), "little")

CONTROL_WORD = 1
CONTROL_LATCH_BIT = 10
CONTROL_MAP_PAGE_BIT = 8
CONTROL_ENABLE_BIT = 31

# Flat configuration outputs of the wrapper and the width of each.
CONFIG_PORTS = (
    ("configLatchTs", 1),
    ("configPulseControl", 384),
    ("configPulsePrescale", 384),
    ("configPulseDelay", 384),
    ("configPulseWidth", 384),
    ("configTsFifoRdEna", 1),
    ("configEventRamData", 32),
    ("configEventRamCs", 8),
    ("configEventRamAddr", 8),
    ("configEventRamWe", 8),
    ("configMapRamPage", 1),
    ("configEvrEnable", 1),
    ("configOutputMap", 192),
    ("configUSecDivider", 32),
    ("configIntControl", 32),
    ("configDbena", 1),
    ("configDbdis", 1),
    ("configDben", 1),
    ("configDbRdAddr", 9),
    ("configIrqClr", 32),
    ("configIntEventEn", 1),
    ("configExtEventEn", 1),
    ("configIntEventCode", 8),
    ("configExtEventCode", 8),
    ("configIntEventCount", 32),
)


def snapshot(dut):
    """Return every flat configuration output as an integer after checking it is resolvable."""
    result = {}
    for name, _ in CONFIG_PORTS:
        value = getattr(dut, name).value
        assert value.is_resolvable, f"{name} carries unresolved bits: {value}"
        result[name] = int(value)
    return result


# Every write presents its data and the decoded address bits on these outputs
# whatever word it targets, so they are left out of the per-register field maps.
BUS_PORTS = (
    "configEventRamData",
    "configEventRamAddr",
    "configEventRamCs",
    "configEventRamWe",
    "configDbRdAddr",
)


def changed_ports(before, after, *, ignore=BUS_PORTS):
    """Return the names of the configuration outputs that differ between two snapshots."""
    return sorted(name for name in before if name not in ignore and before[name] != after[name])


async def start_axi_master(dut):
    """Reset the block, start the clock, release reset, and return ``(master, clock_task)``.

    The order matters on cocotb 2.x: reset is driven and the master built
    (which drives the valids low) before the clock starts.
    """
    dut.axilRst.value = 1
    for name in ("S_AXI_AWADDR", "S_AXI_ARADDR", "S_AXI_WDATA", "S_AXI_WSTRB", "S_AXI_AWPROT", "S_AXI_ARPROT"):
        getattr(dut, name).value = 0
    master = AxiLiteMaster(
        AxiLiteBus.from_prefix(dut, "S_AXI"),
        dut.axilClk,
        dut.axilRst,
        reset_active_level=True,
    )
    await Timer(1, unit="ns")
    clock_task = cocotb.start_soon(Clock(dut.axilClk, CLOCK_NS, unit="ns").start(start_high=False))
    for _ in range(RESET_CLOCKS):
        await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)
    dut.axilRst.value = 0
    return master, clock_task


async def watch_config(dut, history):
    """Lifetime agent: append the configuration outputs after every clock edge until cancelled.

    Propagation sampling: each snapshot is taken 2 ns after the edge.
    """
    while True:
        await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)
        history.append(snapshot(dut))


def moved_ports(baseline, history):
    """Return the configuration outputs that left ``baseline`` in any recorded cycle."""
    seen = set()
    for entry in history:
        seen.update(changed_ports(baseline, entry))
    return sorted(seen)


async def settle(dut, clocks=SETTLE_CLOCKS):
    """Wait for the registered outputs to follow a write."""
    for _ in range(clocks):
        await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)


async def read_word(master, word, *, expect=AxiResp.OKAY):
    """Read one 32-bit word by index, assert the response, and return the value."""
    result = await master.read(word * WORD_BYTES, WORD_BYTES)
    assert result.resp == expect, f"read of word {word} answered {result.resp!r}, expected {expect!r}"
    return int.from_bytes(result.data, "little")


async def write_word(master, word, value, *, expect=AxiResp.OKAY):
    """Write one 32-bit word by index and assert the response."""
    result = await master.write(word * WORD_BYTES, value.to_bytes(WORD_BYTES, "little"))
    assert result.resp == expect, f"write of word {word} answered {result.resp!r}, expected {expect!r}"


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def evrv1reg_reset_version_and_control(dut):
    """Version words, control register reset, and the control bit walk.

    Propagation sampling: configuration outputs are sampled 2 ns after the
    clock edges that follow each write.
    """
    master, clock_task = await start_axi_master(dut)

    assert await read_word(master, 11) == VERSION_WORD, "word 11 does not hold the fixed prefix and the low 24 version bits"
    assert await read_word(master, 12) == VERSION_SWAPPED_WORD, "word 12 does not hold the byte-reversed version"

    assert await read_word(master, CONTROL_WORD) == 0, "control register does not reset to 0"
    await settle(dut)
    baseline = snapshot(dut)

    expected_outputs = {
        CONTROL_MAP_PAGE_BIT: ["configMapRamPage"],
        CONTROL_LATCH_BIT: ["configLatchTs"],
        CONTROL_ENABLE_BIT: ["configEvrEnable"],
    }
    for bit in range(WORD_BITS):
        await write_word(master, CONTROL_WORD, 0)
        await settle(dut)
        history = []
        watcher = cocotb.start_soon(watch_config(dut, history))
        await write_word(master, CONTROL_WORD, 1 << bit)
        await settle(dut)
        watcher.cancel()
        seen = moved_ports(baseline, history)
        readback = await read_word(master, CONTROL_WORD)
        expected_readback = 0 if bit == CONTROL_LATCH_BIT else 1 << bit
        assert readback == expected_readback, f"control bit {bit} read back 0x{readback:08X}"
        assert seen == expected_outputs.get(bit, []), f"control bit {bit} moved {seen}"
        if bit == CONTROL_LATCH_BIT:
            pulse = sum(entry["configLatchTs"] for entry in history)
            assert pulse == 1, f"latch output was high for {pulse} cycles, expected 1"
    clock_task.cancel()


def test_EvrV1Reg():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv1regwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
