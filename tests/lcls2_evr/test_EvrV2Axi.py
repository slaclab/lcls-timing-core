#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2Axi register block observed with a walking-one walk and compared with EvrV2Core.py.

Test methodology:
    Sweep: CHANNELS_G and DMA_ENABLE_G over (1, false), (12, false),
        (12, true) and (1, true), which gives one and twelve channel
        groups at a 32 byte stride and the interrupt, debug, threshold and
        BSA words with and without DMA_ENABLE_G.
    Stimulus: a cocotbext-axi AxiLiteMaster reads each register word, writes 0,
        then writes 1 << b for every bit b and reads the word back; the
        channelConfig, irqEnable, rstCount, trigSel and dmaFullThr outputs are
        read together two clocks after each write. The event count rows,
        gtxDebug and irqReq inputs are driven with distinct patterns.
        Further entrypoints write a distinct rateSel into every channel, read
        the unmapped words, including the word 0x008 where the link address
        register is commented out of the RTL, and pulse axilRst.
    Checks: the observed map (read-write bits, the output field and field bit
        each one drives, reset values, read-back) equals the layout table;
        the read-only words follow the driven inputs and ignore writes;
        channel i lands in channelConfig slice i; every output and word holds
        its initial value before any write; a reset pulse clears nothing;
        unmapped words read 0 with an OKAY response; with twelve channels and DMA_ENABLE_G true the
        observed map is compared bit for bit with
        python/LclsTimingCore/EvrV2Core.py, which is read as text, and the
        disagreement is asserted exactly, each entry tagged as a defect or a
        question. The gated entrypoint asserts that there is no defect.
    Timing: 10 ns axilClk, every entrypoint is bounded by the cocotb timeout.
    Propagation sampling: the registers update on the clock edge, so the
        outputs are read 2 ns after the clock edges that follow each write.
"""

import os
from pathlib import Path

import cocotb
import pytest

from tests.common import evr_model, pyrogue_ast
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    env_int,
    parameter_case,
    run_lcls_vhdl_test,
    sample_after_tpd,
)
from tests.lcls2_evr import register_walk as rw

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2AxiWrapper.vhd"
PYROGUE_FILE = REPO_ROOT / "python/LclsTimingCore/EvrV2Core.py"

CHANNELS = env_int("CHANNELS_G", default=1)
DMA = os.getenv("DMA_ENABLE_G", "false") == "true"

GATED_ENTRYPOINT = "axi_python_agrees_with_rtl"
COMPARE_ENTRYPOINT = "axi_compare_with_evrv2core"
FULL_BLOCK = CHANNELS == 12 and DMA
ALL_ONES = 0xFFFFFFFF
CHANNEL_MASK = (1 << evr_model.CHANNEL_CONFIG_BITS) - 1
EXTRA_BASE = CHANNELS * evr_model.CHANNEL_CONFIG_BITS
TRIGGER_BLOCK = 0x200
TRIGGER_COUNT = 12
GTX_DEBUG_PATTERN = 0xA5
DEFAULTS = {"irqEnable": 0, "countReset": 0, "trigSel": 0, "dmaFullThr": 0xFFFFFF}

NAME_MAP = {
    "IrqEnable": "irqEnable",
    "IrqStatus": "irqReq",
    "gtxDebug": "gtxDebug",
    "CountReset": "countReset",
    "ModeSel": "trigSel",
    "DmaFullThr": "dmaFullThr",
    "ChannelEnable": "enabled",
    "ChannelBsaEnable": "bsaEnabled",
    "ChannelDmaEnable": "dmaEnabled",
    "ChannelRateSel": "rateSel",
    "ChannelDestSel": "destSel",
    "ChannelEventCnt": "eventCount",
    "ChannelBsaDelay": "bsaActiveDelay",
    "ChannelBsaSetup": "bsaActiveSetup",
    "ChannelBsaWidth": "bsaActiveWidth",
    "GlobalEventCnt": "globalCount",
    "TriggerChannel": "channel",
    "TriggerPolarity": "polarity",
    "TriggerEnable": "enabled",
    "TriggerDelay": "delay",
    "TriggerFineDelay": "delayTap",
}

QUESTION_KINDS = {"mode_mismatch"}

# Measured disagreements between EvrV2Core.py and the EvrV2Axi decode with
# twelve channels and DMA_ENABLE_G true, as (kind, PyRogue name, tag).
# Defects: ChannelBsaSetup is 12 bits against 6; ChannelDestSel is 18 bits
# against 19; ChannelEnable and ChannelRateSel are declared for channel 0
# only. Questions: the event counts are read-write in PyRogue and read-only in
# the RTL. Observed, intent unconfirmed.
OBSERVED_CSR_DRIFT = [
    ("mode_mismatch", "ChannelEventCnt", "question"),
    ("python_bits_without_rtl", "ChannelBsaSetup", "defect"),
    ("mode_mismatch", "GlobalEventCnt", "question"),
    ("width_mismatch", "ChannelDestSel", "defect"),
    ("width_mismatch", "ChannelBsaSetup", "defect"),
    ("rtl_bits_without_python", "ChannelDestSel", "defect"),
    ("rtl_bits_without_python", "ChannelEnable", "defect"),
    ("rtl_bits_without_python", "ChannelRateSel", "defect"),
]

# The trigger block of EvrV2Core.py (offset 0x200, 16 byte stride) against the
# EvrV2TrigReg layout at the same base with its 256 byte group stride. Every
# entry is a question: EvrV2Axi decodes nothing at those addresses, so the
# PyRogue trigger block describes a layout no block in this library has.
# Trigger 0 lines up for TriggerChannel, TriggerPolarity, TriggerEnable and
# TriggerFineDelay; TriggerDelay sits on the width word.
OBSERVED_TRIGGER_DRIFT = [
    ("python_bits_without_rtl", "TriggerChannel", "question"),
    ("python_bits_without_rtl", "TriggerPolarity", "question"),
    ("python_bits_without_rtl", "TriggerEnable", "question"),
    ("field_mismatch", "TriggerDelay", "question"),
    ("python_bits_without_rtl", "TriggerDelay", "question"),
    ("python_bits_without_rtl", "TriggerFineDelay", "question"),
    ("rtl_bits_without_python", "(rtl complEn)", "question"),
    ("rtl_bits_without_python", "(rtl complAnd)", "question"),
    ("rtl_bits_without_python", "TriggerDelay", "question"),
    ("rtl_bits_without_python", "TriggerChannel", "question"),
    ("rtl_bits_without_python", "TriggerPolarity", "question"),
    ("rtl_bits_without_python", "TriggerEnable", "question"),
    ("rtl_bits_without_python", "(rtl width)", "question"),
    ("rtl_bits_without_python", "TriggerFineDelay", "question"),
]


def conditions():
    return {"DMA_ENABLE"} if DMA else set()


def pyrogue_conditions():
    return {"dmaEnable"} if DMA else set()


def channel_address(channel, word):
    return rw.AXI_CHANNEL_BASE + channel * rw.AXI_CHANNEL_STRIDE + word


def event_pattern(index):
    """Return a distinct 32-bit event count for row ``index``."""
    return (0x01000193 * (index + 3) + 0x5A5A5A5A) & ALL_ONES


def drive_patterns(dut):
    dut.eventCount.value = sum(event_pattern(row) << (32 * row) for row in range(CHANNELS + 1))
    dut.gtxDebug.value = GTX_DEBUG_PATTERN
    dut.irqReq.value = 1


def axi_config(dut):
    """Return the configuration outputs as one vector in the order of rw.AXI_EXTRA_CONFIG_FIELDS."""
    channels = rw.flat_value(dut.channelConfig, "channelConfig")
    return (
        channels
        | rw.flat_value(dut.irqEnable, "irqEnable") << EXTRA_BASE
        | rw.flat_value(dut.rstCount, "rstCount") << (EXTRA_BASE + 1)
        | rw.flat_value(dut.trigSel, "trigSel") << (EXTRA_BASE + 2)
        | rw.flat_value(dut.dmaFullThr, "dmaFullThr") << (EXTRA_BASE + 3)
    )


def channel_slice(dut, index):
    value = rw.flat_value(dut.channelConfig, "channelConfig")
    return evr_model.unpack_channel_config((value >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK)


def driven_value(group, field):
    """Return the value held on the input that feeds a read-only field."""
    if field == "eventCount":
        return event_pattern(group)
    if field == "globalCount":
        return event_pattern(CHANNELS)
    if field == "gtxDebug":
        return GTX_DEBUG_PATTERN
    if field == "irqReq":
        return 1
    raise KeyError(field)


def expected_reset(expected, address):
    """Return what a word reads after reset with the patterns driven."""
    value = 0
    for (word, bit), info in expected.items():
        if word != address:
            continue
        source = DEFAULTS.get(info.field)
        if source is None:
            source = (
                evr_model.CHANNEL_CONFIG_DEFAULTS[info.field]
                if info.mode == "RW"
                else driven_value(info.group, info.field)
            )
        value |= (source >> info.field_bit & 1) << bit
    return value


async def restore_defaults(master, settle):
    """Write every read-write word back to its initial value.

    EvrV2Axi never uses its reset input, so a reset does not clear what an
    earlier entrypoint of the same simulation wrote.
    """
    expected = rw.axi_bit_map(CHANNELS, DMA)
    for address in sorted({word for (word, _), info in expected.items() if info.mode == "RW"}):
        await rw.write_word(master, address, expected_reset(expected, address))
    await settle()


async def bring_up(dut, *, restore=True):
    drive_patterns(dut)
    master, clock_task = await rw.start_axi_master(dut)
    settle = rw.make_settle(dut)
    if restore:
        await restore_defaults(master, settle)
    return master, settle, clock_task


async def walk_axi(dut, master, settle):
    """Walk every register word that exists for the generics; return walks and read-only fields."""
    expected = rw.axi_bit_map(CHANNELS, DMA)
    config_bits = rw.channel_config_bits(CHANNELS, rw.AXI_EXTRA_CONFIG_FIELDS)
    walks = []
    for address in sorted({word for word, _ in expected}):
        walks.append(
            await rw.walk_word(master, address, lambda: axi_config(dut), settle, config_bits, ignore=())
        )

    full_events = (1 << (32 * (CHANNELS + 1))) - 1
    read_only = []

    def drive_events(value):
        dut.eventCount.value = value

    for channel in range(CHANNELS):
        address = channel_address(channel, 0x08)
        read_only.append((address, await rw.read_only_mask(master, address, drive_events, full_events), channel, "eventCount"))
    read_only.append(
        (rw.AXI_GLOBAL_COUNT, await rw.read_only_mask(master, rw.AXI_GLOBAL_COUNT, drive_events, full_events), 0, "globalCount")
    )
    if DMA:
        read_only.append((0x004, await rw.read_only_mask(master, 0x004, lambda v: setattr(dut.irqReq, "value", v), 1), 0, "irqReq"))
        read_only.append((0x00C, await rw.read_only_mask(master, 0x00C, lambda v: setattr(dut.gtxDebug, "value", v), 0xFF), 0, "gtxDebug"))
    drive_patterns(dut)
    return walks, read_only


def check_walks(walks, read_only):
    """Assert reset values, the observed map and the read-back masks; return the observed map."""
    expected = rw.axi_bit_map(CHANNELS, DMA)
    for walk in walks:
        want = expected_reset(expected, walk.address)
        assert walk.reset_value == want, f"word 0x{walk.address:03X} read 0x{walk.reset_value:08X} after reset, expected 0x{want:08X}"
    observed = rw.rtl_bit_map(walks, read_only)
    assert observed == expected, (
        f"observed bits differ from the layout table: missing {sorted(set(expected) - set(observed))}, "
        f"extra {sorted(set(observed) - set(expected))}"
    )
    for walk in walks:
        rw_bits = {bit for (address, bit), info in expected.items() if address == walk.address and info.mode == "RW"}
        assert {bit for bit in range(rw.WORD_BITS) if walk.readback_mask >> bit & 1} == rw_bits, (
            f"word 0x{walk.address:03X} read-back mask 0x{walk.readback_mask:08X} differs from its read-write bits"
        )
    return observed


def severity_of(kind, name):
    return "question" if kind in QUESTION_KINDS else "defect"


def csr_drift(observed):
    variables = [var for var in pyrogue_ast.read_remote_variables(PYROGUE_FILE) if var.offset < TRIGGER_BLOCK]
    return rw.compare_with_pyrogue(
        observed,
        variables,
        NAME_MAP,
        base=0,
        enabled_conditions=pyrogue_conditions(),
        window=(0, TRIGGER_BLOCK),
        severity=severity_of,
    )


def trigger_block_drift():
    variables = [var for var in pyrogue_ast.read_remote_variables(PYROGUE_FILE) if var.offset >= TRIGGER_BLOCK]
    layout = rw.trigreg_bit_map(TRIGGER_COUNT, False, True, base=TRIGGER_BLOCK)
    return rw.compare_with_pyrogue(
        layout,
        variables,
        NAME_MAP,
        base=0,
        enabled_conditions=set(),
        window=(TRIGGER_BLOCK, TRIGGER_BLOCK + TRIGGER_COUNT * rw.TRIGGER_GROUP_TIGHT),
        severity=lambda kind, name: "question",
    )


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def axi_power_on_values(dut):
    """Before any write, every output and every register word holds its initial value.

    This entrypoint is defined first so that it runs on a fresh simulation.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow reset release.
    """
    master, settle, clock_task = await bring_up(dut, restore=False)
    default = evr_model.pack_channel_config()
    reset = rw.flat_value(dut.channelConfig, "channelConfig")
    for index in range(CHANNELS):
        got = (reset >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK
        assert got == default, f"channel {index} reset configuration 0x{got:X}, expected 0x{default:X}"
    assert rw.flat_value(dut.dmaFullThr, "dmaFullThr") == DEFAULTS["dmaFullThr"]
    for name in ("irqEnable", "rstCount", "trigSel"):
        assert rw.flat_value(getattr(dut, name), name) == 0, f"{name} is not 0 after reset"
    expected = rw.axi_bit_map(CHANNELS, DMA)
    for address in sorted({word for word, _ in expected}):
        got = await rw.read_word(master, address)
        want = expected_reset(expected, address)
        assert got == want, f"word 0x{address:03X} read 0x{got:08X} at power on, expected 0x{want:08X}"
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def axi_walk_csr(dut):
    """Every register word walks to the layout table, and countReset and trigSel reach their outputs.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    walks, read_only = await walk_axi(dut, master, settle)
    check_walks(walks, read_only)
    await rw.write_word(master, 0x010, 1)
    await rw.write_word(master, 0x014, 1)
    await settle()
    assert rw.flat_value(dut.rstCount, "rstCount") == 1 and rw.flat_value(dut.trigSel, "trigSel") == 1
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def axi_read_only_inputs(dut):
    """The event count rows, the global count, gtxDebug and irqReq read back, follow their inputs, and ignore writes.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    for row in range(CHANNELS):
        got = await rw.read_word(master, channel_address(row, 0x08))
        assert got == event_pattern(row), f"channel {row} event count 0x{got:08X}, expected 0x{event_pattern(row):08X}"
    got = await rw.read_word(master, rw.AXI_GLOBAL_COUNT)
    assert got == event_pattern(CHANNELS), f"global count 0x{got:08X}, expected 0x{event_pattern(CHANNELS):08X}"
    assert await rw.read_word(master, 0x004) == (1 if DMA else 0), "irqReq read-back"
    assert await rw.read_word(master, 0x00C) == (GTX_DEBUG_PATTERN if DMA else 0), "gtxDebug read-back"

    for address in [channel_address(row, 0x08) for row in range(CHANNELS)] + [rw.AXI_GLOBAL_COUNT, 0x004, 0x00C]:
        await rw.write_word(master, address, ALL_ONES)
    await settle()
    for row in range(CHANNELS):
        assert await rw.read_word(master, channel_address(row, 0x08)) == event_pattern(row), f"a write changed event count {row}"
    assert await rw.read_word(master, rw.AXI_GLOBAL_COUNT) == event_pattern(CHANNELS), "a write changed the global count"

    dut.eventCount.value = sum(((~event_pattern(row)) & ALL_ONES) << (32 * row) for row in range(CHANNELS + 1))
    await settle()
    for row in range(CHANNELS):
        assert await rw.read_word(master, channel_address(row, 0x08)) == (~event_pattern(row)) & ALL_ONES
    assert await rw.read_word(master, rw.AXI_GLOBAL_COUNT) == (~event_pattern(CHANNELS)) & ALL_ONES
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def axi_link_addr_gap(dut):
    """The commented-out link address word and every other gap read 0 with OKAY and ignore writes.

    Observed, intent unconfirmed: 0x008 answers OKAY with 0 although a
    physical link address register is named in a comment of the RTL.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    gaps = [0x008, 0x01C, 0x020 - 4]
    gaps += [channel_address(row, word) for row in range(CHANNELS) for word in (0x14, 0x18, 0x1C)]
    if not DMA:
        gaps += [0x000, 0x004, 0x00C, 0x018]
        gaps += [channel_address(row, word) for row in range(CHANNELS) for word in (0x0C, 0x10)]
    before = axi_config(dut)
    for address in gaps:
        assert await rw.read_word(master, address) == 0, f"unmapped word 0x{address:03X} did not read 0"
        await rw.write_word(master, address, ALL_ONES)
        assert await rw.read_word(master, address) == 0, f"unmapped word 0x{address:03X} kept a written value"
    await settle()
    assert axi_config(dut) == before, "a write to an unmapped word changed an output"
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def axi_group_order(dut):
    """Channel i lands in channelConfig slice i, and writing one channel leaves every other slice unchanged.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    rates = [0x101 + 0x111 * index for index in range(CHANNELS)]
    for index, rate in enumerate(rates):
        await rw.write_word(master, channel_address(index, 0x04), rate)
    await settle()
    for index, rate in enumerate(rates):
        assert channel_slice(dut, index)["rateSel"] == rate, f"channel {index} rateSel is not in slice {index}"
        assert await rw.read_word(master, channel_address(index, 0x04)) == rate, f"channel {index} reads back another rateSel"
    for target in range(CHANNELS):
        before = rw.flat_value(dut.channelConfig, "channelConfig")
        await rw.write_word(master, channel_address(target, 0x00), ALL_ONES)
        await rw.write_word(master, channel_address(target, 0x04), ALL_ONES)
        await settle()
        after = rw.flat_value(dut.channelConfig, "channelConfig")
        for index in range(CHANNELS):
            old = (before >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK
            new = (after >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK
            if index != target:
                assert new == old, f"writing channel {target} changed slice {index}: 0x{old:X} to 0x{new:X}"
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def axi_reset_retains_registers(dut):
    """A pulse on axilRst does not clear the registers of EvrV2Axi.

    Observed, intent unconfirmed: the axiRst port is listed in the process
    sensitivity list but never used, so a reset only restarts the bus master.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow each write and the reset release.
    """
    master, settle, clock_task = await bring_up(dut)
    await rw.write_word(master, 0x014, 1)
    await rw.write_word(master, channel_address(0, 0x04), 0x155)
    await settle()
    dut.axilRst.value = 1
    for _ in range(3):
        await sample_after_tpd(dut.axilClk, propagation_time=rw.PROPAGATION_NS)
    dut.axilRst.value = 0
    await settle()
    assert rw.flat_value(dut.trigSel, "trigSel") == 1, "reset cleared trigSel"
    assert channel_slice(dut, 0)["rateSel"] == 0x155, "reset cleared rateSel"
    assert await rw.read_word(master, channel_address(0, 0x04)) == 0x155, "reset changed the rateSel read-back"
    clock_task.cancel()


@cocotb.test(skip=not FULL_BLOCK, timeout_time=5, timeout_unit="ms")
async def axi_compare_with_evrv2core(dut):
    """The observed map disagrees with EvrV2Core.py exactly as recorded, each entry tagged.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    walks, read_only = await walk_axi(dut, master, settle)
    observed = check_walks(walks, read_only)
    got = [(entry.kind, entry.python_name, entry.severity) for entry in csr_drift(observed)]
    assert got == OBSERVED_CSR_DRIFT, f"EvrV2Core.py disagreement changed: {csr_drift(observed)}"
    trigger = [(entry.kind, entry.python_name, entry.severity) for entry in trigger_block_drift()]
    assert trigger == OBSERVED_TRIGGER_DRIFT, f"EvrV2Core.py trigger block disagreement changed: {trigger_block_drift()}"
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def axi_python_agrees_with_rtl(dut):
    """EvrV2Core.py declares the same channel bits as the RTL decodes.

    Known issue entrypoint: it fails on the current file because the channel
    variables disagree with the decode in width and in channel count.

    Propagation sampling: the outputs are read 2 ns after the clock edges
    that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    walks, read_only = await walk_axi(dut, master, settle)
    defects = [entry for entry in csr_drift(rw.rtl_bit_map(walks, read_only)) if entry.severity == "defect"]
    assert not defects, "PyRogue bit drift: " + "; ".join(f"{entry.python_name} {entry.kind}: {entry.detail}" for entry in defects)
    clock_task.cancel()


def run_axi_simulation(parameters, test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2axiwrapper",
        parameters=parameters,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(parameters, test_filter),
    )


@pytest.mark.parametrize(
    "params",
    [
        parameter_case("one", CHANNELS_G=1, DMA_ENABLE_G="false"),
        parameter_case("twelve", CHANNELS_G=12, DMA_ENABLE_G="false"),
        parameter_case("twelve_dma", CHANNELS_G=12, DMA_ENABLE_G="true"),
        parameter_case("one_dma", CHANNELS_G=1, DMA_ENABLE_G="true"),
    ],
)
def test_EvrV2Axi(params):
    excluded = [GATED_ENTRYPOINT]
    if not (params["CHANNELS_G"] == 12 and params["DMA_ENABLE_G"] == "true"):
        excluded.append(COMPARE_ENTRYPOINT)
    run_axi_simulation(params, cocotb_test_filter_excluding(*excluded))


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2Core.py channel variables disagree with the EvrV2Axi decode in width and channel count; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2Axi_known_issue_channel_width():
    run_axi_simulation({"CHANNELS_G": 12, "DMA_ENABLE_G": "true"}, cocotb_test_filter(GATED_ENTRYPOINT))
