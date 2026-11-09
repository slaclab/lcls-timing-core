#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2ChannelReg register map observed with a walking-one walk and compared with PyRogue.

Test methodology:
    Sweep: NCHANNELS_G, EVR_CARD_G and DMA_ENABLE_G over (1, false, false),
        (3, false, true), (3, true, true) and (12, false, false), which gives
        group strides of 256 and 4096 bytes, one to twelve groups, and the
        BSA and DMA words with and without DMA_ENABLE_G.
    Stimulus: a cocotbext-axi AxiLiteMaster reads each register word, writes 0,
        then writes 1 << b for every bit b and reads the word back; the
        decoded channelConfig output is read two clocks after each write.
        Further entrypoints drive a distinct eventCount into every channel,
        write a distinct rateSel into every group, write all ones into one
        group at a time, read unmapped words, and write one decode window
        above group 0.
    Checks: the observed map (read-write bits, the configuration field and
        field bit each one drives, reset values, read-back) equals the
        layout table; the event count words follow the driven value and
        ignore writes; group i lands in channelConfig slice i and a write to
        one group leaves every other slice unchanged; bits and words gated by
        DMA_ENABLE_G read 0 and ignore writes when it is false; unmapped words
        read 0 with an OKAY response; addresses one decode window up alias
        group 0; the observed map is compared bit for
        bit with python/LclsTimingCore/EvrV2ChannelReg.py, which is read as
        text, and the disagreement is asserted exactly. The gated entrypoint
        asserts that there is no disagreement.
    Timing: 10 ns axilClk, every entrypoint is bounded by the cocotb timeout.
    Propagation sampling: the registers update after TPD_G (1 ns), so the
        configuration output is read 2 ns after the clock edges that follow
        each write.
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
)
from tests.lcls2_evr import register_walk as rw

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2ChannelRegWrapper.vhd"
PYROGUE_FILE = REPO_ROOT / "python/LclsTimingCore/EvrV2ChannelReg.py"

CHANNELS = env_int("NCHANNELS_G", default=1)
CARD = os.getenv("EVR_CARD_G", "false") == "true"
DMA = os.getenv("DMA_ENABLE_G", "false") == "true"

GATED_ENTRYPOINT = "chanreg_python_agrees_with_rtl"
STRIDE = rw.group_size(CARD)
ALL_ONES = 0xFFFFFFFF
CHANNEL_MASK = (1 << evr_model.CHANNEL_CONFIG_BITS) - 1

NAME_MAP = {
    "EnableReg": "enabled",
    "BsaEnabled": "bsaEnabled",
    "dmaEnabled": "dmaEnabled",
    "RateSel": "rateSel",
    "RateType": "rateSel",
    "DestSel": "destSel",
    "DestType": "destSel",
    "Count": "eventCount",
    "BsaWindowDelay": "bsaActiveDelay",
    "BsaWindowSetup": "bsaActiveSetup",
    "BsaWindowWidth": "bsaActiveWidth",
}

# RateSel (11 bits) and RateType (2 bits) cover the 13 RTL rateSel bits, but
# DestSel (16 bits) and DestType (2 bits) cover only 18 of the 19 RTL destSel
# bits: bit 31 of the word at +0x04 has no variable. Observed, intent
# unconfirmed.
OBSERVED_DRIFT = [
    ("width_mismatch", "DestType"),
    ("rtl_bits_without_python", "DestType"),
]

# The value each field takes after a write of all ones, per field.
ALL_ONES_FIELDS = {
    "enabled": 1,
    "rateSel": (1 << 13) - 1,
    "destSel": (1 << 19) - 1,
}
DMA_ALL_ONES_FIELDS = {
    "bsaEnabled": 1,
    "dmaEnabled": 1,
    "bsaActiveDelay": (1 << 20) - 1,
    "bsaActiveSetup": (1 << 6) - 1,
    "bsaActiveWidth": (1 << 20) - 1,
}


def conditions():
    return {"DMA_ENABLE"} if DMA else set()


def pyrogue_conditions():
    return {"dmaEnable"} if DMA else set()


def words():
    """Return the register words of one group that exist for the current generics."""
    return [
        word
        for word, fields in rw.CHANREG_LAYOUT.items()
        if any(entry.condition is None or entry.condition in conditions() for entry in fields)
    ]


def reset_word(word):
    """Return what a word reads after reset: the initial value of each read-write field."""
    value = 0
    for entry in rw.CHANREG_LAYOUT[word]:
        if entry.mode == "RW" and (entry.condition is None or entry.condition in conditions()):
            value |= evr_model.CHANNEL_CONFIG_DEFAULTS[entry.name] << entry.lsb
    return value


def channel_slice(dut, index):
    """Return channel ``index`` of the flattened configuration output as a field dictionary."""
    value = rw.flat_value(dut.channelConfig, "channelConfig")
    return evr_model.unpack_channel_config((value >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK)


def drive_event_count(dut, value):
    dut.eventCount.value = value


def event_pattern(index):
    """Return a distinct 32-bit event count for channel ``index``."""
    return (0x01000193 * (index + 3) + 0x5A5A5A5A) & ALL_ONES


async def bring_up(dut):
    master, clock_task = await rw.start_axi_master(dut)
    return master, rw.make_settle(dut), clock_task


async def walk_channels(dut, master, settle, groups):
    """Walk every register word of the first ``groups`` groups; return walks and read-only fields."""
    config_bits = rw.channel_config_bits(CHANNELS)
    walks = []
    read_only = []
    for group in range(groups):
        for word in words():
            walks.append(
                await rw.walk_word(
                    master,
                    group * STRIDE + word,
                    lambda: rw.flat_value(dut.channelConfig, "channelConfig"),
                    settle,
                    config_bits,
                    ignore=(),
                )
            )
        mask = await rw.read_only_mask(
            master,
            group * STRIDE + 0x08,
            lambda value: drive_event_count(dut, value),
            (1 << (32 * CHANNELS)) - 1,
        )
        read_only.append((group * STRIDE + 0x08, mask, group, "eventCount"))
    return walks, read_only


def check_walks(walks, read_only, groups):
    """Assert reset values, the observed map, and the read-back masks; return the observed map."""
    for walk in walks:
        word = walk.address % STRIDE
        assert walk.reset_value == reset_word(word), (
            f"word 0x{walk.address:03X} read 0x{walk.reset_value:08X} after reset, expected 0x{reset_word(word):08X}"
        )
    observed = rw.rtl_bit_map(walks, read_only)
    expected = rw.chanreg_bit_map(groups, CARD, DMA)
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


def pyrogue_drift(rtl_map):
    variables = pyrogue_ast.read_remote_variables(PYROGUE_FILE)
    return rw.compare_with_pyrogue(
        rtl_map,
        variables,
        NAME_MAP,
        base=0,
        enabled_conditions=pyrogue_conditions(),
        window=(0, STRIDE),
    )


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def chanreg_walk_all_groups(dut):
    """Every group walks to the layout table at its own base address and disagrees with EvrV2ChannelReg.py as observed.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    reset_config = rw.flat_value(dut.channelConfig, "channelConfig")
    default = evr_model.pack_channel_config()
    for index in range(CHANNELS):
        got = (reset_config >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK
        assert got == default, f"channel {index} reset configuration 0x{got:X}, expected 0x{default:X}"

    walks, read_only = await walk_channels(dut, master, settle, CHANNELS)
    observed = check_walks(walks, read_only, CHANNELS)
    drift = pyrogue_drift({key: info for key, info in observed.items() if info.group == 0})
    assert [(entry.kind, entry.python_name) for entry in drift] == OBSERVED_DRIFT, f"PyRogue drift changed: {drift}"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def chanreg_event_count_read_only(dut):
    """eventCount of each channel reads back at +0x08, follows the driven value, and ignores writes.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    patterns = [event_pattern(index) for index in range(CHANNELS)]
    drive_event_count(dut, sum(pattern << (32 * index) for index, pattern in enumerate(patterns)))
    await settle()
    for index, pattern in enumerate(patterns):
        assert await rw.read_word(master, index * STRIDE + 0x08) == pattern, f"channel {index} did not read its event count"
    for index in range(CHANNELS):
        await rw.write_word(master, index * STRIDE + 0x08, ALL_ONES)
    await settle()
    for index, pattern in enumerate(patterns):
        assert await rw.read_word(master, index * STRIDE + 0x08) == pattern, f"a write changed the event count of channel {index}"
    drive_event_count(dut, sum(((~pattern) & ALL_ONES) << (32 * index) for index, pattern in enumerate(patterns)))
    await settle()
    for index, pattern in enumerate(patterns):
        assert await rw.read_word(master, index * STRIDE + 0x08) == (~pattern) & ALL_ONES, f"channel {index} did not follow eventCount"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def chanreg_group_isolation_and_order(dut):
    """Group i lands in slice i, and writing one group leaves every other slice unchanged.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    rates = [0x101 + 0x111 * index for index in range(CHANNELS)]
    for index, rate in enumerate(rates):
        await rw.write_word(master, index * STRIDE + 0x04, rate)
    await settle()
    for index, rate in enumerate(rates):
        assert channel_slice(dut, index)["rateSel"] == rate, f"group {index} rateSel is not in slice {index}"
        assert await rw.read_word(master, index * STRIDE + 0x04) == rate, f"group {index} reads back another rateSel"

    for target in range(CHANNELS):
        before = rw.flat_value(dut.channelConfig, "channelConfig")
        for word in words():
            if word != 0x08:
                await rw.write_word(master, target * STRIDE + word, ALL_ONES)
        await settle()
        after = rw.flat_value(dut.channelConfig, "channelConfig")
        for index in range(CHANNELS):
            old = (before >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK
            new = (after >> (evr_model.CHANNEL_CONFIG_BITS * index)) & CHANNEL_MASK
            if index != target:
                assert new == old, f"writing group {target} changed slice {index}: 0x{old:X} to 0x{new:X}"
        written = channel_slice(dut, target)
        for name, value in ALL_ONES_FIELDS.items():
            assert written[name] == value, f"group {target} field {name} is {written[name]:#x} after all ones"
        for name, value in DMA_ALL_ONES_FIELDS.items():
            want = value if DMA else evr_model.CHANNEL_CONFIG_DEFAULTS[name]
            assert written[name] == want, f"group {target} field {name} is {written[name]:#x}, expected {want:#x}"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def chanreg_zero_and_unmapped(dut):
    """Writing 0 everywhere leaves only the event count readable, and unmapped words read 0 with OKAY.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    patterns = [event_pattern(index) for index in range(CHANNELS)]
    drive_event_count(dut, sum(pattern << (32 * index) for index, pattern in enumerate(patterns)))
    for group in range(CHANNELS):
        for word in words():
            await rw.write_word(master, group * STRIDE + word, ALL_ONES)
    for group in range(CHANNELS):
        for word in words():
            await rw.write_word(master, group * STRIDE + word, 0)
    await settle()
    for group in range(CHANNELS):
        for word in words():
            got = await rw.read_word(master, group * STRIDE + word)
            want = patterns[group] if word == 0x08 else 0
            assert got == want, f"group {group} word 0x{word:02X} reads 0x{got:08X} after writing 0, expected 0x{want:08X}"
        slice_now = channel_slice(dut, group)
        assert slice_now["enabled"] == 0 and slice_now["rateSel"] == 0 and slice_now["destSel"] == 0

    gap_words = [0x14, 0x20, STRIDE - 4]
    if not DMA:
        gap_words += [0x0C, 0x10]
    if CARD:
        gap_words.append(0x800)
    unmapped = [group * STRIDE + word for group in range(CHANNELS) for word in gap_words]
    before = rw.flat_value(dut.channelConfig, "channelConfig")
    for address in unmapped:
        assert await rw.read_word(master, address) == 0, f"unmapped word 0x{address:03X} did not read 0"
        await rw.write_word(master, address, ALL_ONES)
        assert await rw.read_word(master, address) == 0, f"unmapped word 0x{address:03X} kept a written value"
    await settle()
    assert rw.flat_value(dut.channelConfig, "channelConfig") == before, "a write to an unmapped word changed the configuration"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def chanreg_decode_aliasing(dut):
    """The block compares only bitSize(NCHANNELS * group size - 1) address bits, so higher addresses alias.

    Observed, intent unconfirmed: the word one decode window above group 0
    reads and writes the rateSel of group 0, and the space between the last
    group and the end of the decode window reads 0.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    window = 1 << evr_model.bit_size(CHANNELS * STRIDE - 1)
    await rw.write_word(master, 0x04, 0x123)
    await settle()
    assert await rw.read_word(master, window + 0x04) == 0x123, f"0x{window + 4:X} does not alias the rateSel of group 0"
    await rw.write_word(master, window + 0x04, 0x321)
    await settle()
    assert channel_slice(dut, 0)["rateSel"] == 0x321, "a write one decode window up did not reach group 0"
    if CHANNELS * STRIDE < window:
        assert await rw.read_word(master, CHANNELS * STRIDE + 0x04) == 0, "the gap above the last group did not read 0"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def chanreg_python_agrees_with_rtl(dut):
    """EvrV2ChannelReg.py declares the same bits as the RTL decodes.

    Known issue entrypoint: it fails on the current file because DestSel and
    DestType cover 18 of the 19 RTL destSel bits.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    walks, read_only = await walk_channels(dut, master, settle, 1)
    drift = pyrogue_drift(rw.rtl_bit_map(walks, read_only))
    assert not drift, "PyRogue bit drift: " + "; ".join(f"{entry.python_name} {entry.kind}: {entry.detail}" for entry in drift)
    clock_task.cancel()


def run_chanreg_simulation(parameters, test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2channelregwrapper",
        parameters=parameters,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(parameters, test_filter),
    )


@pytest.mark.parametrize(
    "params",
    [
        parameter_case("one_tight", NCHANNELS_G=1, EVR_CARD_G="false", DMA_ENABLE_G="false"),
        parameter_case("three_tight_dma", NCHANNELS_G=3, EVR_CARD_G="false", DMA_ENABLE_G="true"),
        parameter_case("three_card_dma", NCHANNELS_G=3, EVR_CARD_G="true", DMA_ENABLE_G="true"),
        parameter_case("twelve_tight", NCHANNELS_G=12, EVR_CARD_G="false", DMA_ENABLE_G="false"),
    ],
)
def test_EvrV2ChannelReg(params):
    run_chanreg_simulation(params, cocotb_test_filter_excluding(GATED_ENTRYPOINT))


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2ChannelReg.py covers 18 of the 19 RTL destSel bits; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2ChannelReg_known_issue_field_width():
    run_chanreg_simulation({"DMA_ENABLE_G": "true"}, cocotb_test_filter(GATED_ENTRYPOINT))
