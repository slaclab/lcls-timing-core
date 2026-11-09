#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2TrigReg register map observed with a walking-one walk and compared with PyRogue.

Test methodology:
    Sweep: TRIGGERS_G, EVR_CARD_G and USE_TAP_G over (1, false, false),
        (3, false, true), (3, true, false) and (16, false, false), which
        gives group strides of 256 and 4096 bytes, one to sixteen groups,
        and the delay tap words with and without USE_TAP_G.
    Stimulus: a cocotbext-axi AxiLiteMaster reads each register word, writes 0,
        then writes 1 << b for every bit b and reads the word back; the
        decoded triggerConfig output is read two clocks after each write.
        Further entrypoints write a distinct delay into every group, write all
        ones into one group at a time, drive delay_rd with a per-trigger
        pattern, and read unmapped words.
    Checks: the observed map (read-write bits, the configuration field and
        field bit each one drives, reset values, read-back) equals the
        layout table; every register word reads its reset value after reset
        release; group i always lands in triggerConfig slice i and a write to
        one group leaves every other slice unchanged; a write to the delay
        tap word pulses loadTap once; unmapped words read 0 with an OKAY
        response; addresses one decode window up alias group 0; the observed map is compared bit for bit with
        python/LclsTimingCore/EvrV2TriggerReg.py, which is read as text, and
        the disagreement is asserted exactly. The gated entrypoint asserts
        that there is no disagreement.
    Timing: 10 ns axilClk, every entrypoint is bounded by the cocotb timeout.
    Propagation sampling: the registers update after TPD_G (1 ns), so the
        configuration output is read 2 ns after the clock edges that follow
        each write.
"""

import os
from pathlib import Path

import cocotb
import pytest

from tests.common import evr_model, pyrogue_ast, timing_model
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

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2TrigRegWrapper.vhd"
PYROGUE_FILE = REPO_ROOT / "python/LclsTimingCore/EvrV2TriggerReg.py"

TRIGGERS = env_int("TRIGGERS_G", default=1)
CARD = os.getenv("EVR_CARD_G", "false") == "true"
TAP = os.getenv("USE_TAP_G", "false") == "true"

GATED_ENTRYPOINT = "trigreg_python_agrees_with_rtl"
TAP_ENTRYPOINT = "trigreg_tap_readback_and_load"
STRIDE = rw.group_size(CARD)
ALL_ONES = 0xFFFFFFFF
TRIGGER_MASK = (1 << evr_model.TRIGGER_CONFIG_BITS) - 1
# loadTap is a one-cycle pulse after a write to the delay tap word, so it is
# left out of comparisons of the configuration at an arbitrary time.
LOAD_TAP_BIT = timing_model.field_layout(evr_model.TRIGGER_CONFIG_FIELDS)["loadTap"][0]
STEADY_MASK = TRIGGER_MASK & ~(1 << LOAD_TAP_BIT)
# Observed: loadTap is high this many clocks after the write response returns.
LOAD_TAP_LATENCY = 2

NAME_MAP = {
    "EnableTrig": "enabled",
    "Source": "channel",
    "Polarity": "polarity",
    "ComplEn": "complEn",
    "ComplAnd": "complAnd",
    "Delay": "delay",
    "Width": "width",
    "DelayTap": "delayTap",
    "DelayTapReadback": "delay_rd",
}

# The PyRogue file puts ComplEn one bit above the RTL decode (29 against 28)
# and ComplAnd two bits above (30 against 29); the RTL complEn bit is left
# without a variable. Observed, intent unconfirmed.
OBSERVED_DRIFT = [
    ("field_mismatch", "ComplEn"),
    ("python_bits_without_rtl", "ComplAnd"),
    ("rtl_bits_without_python", "ComplEn"),
]

# The value written to each field by a write of all ones, per layout word.
ALL_ONES_FIELDS = {
    "channel": 0xF,
    "polarity": 1,
    "complEn": 1,
    "complAnd": 1,
    "enabled": 1,
    "delay": (1 << evr_model.TRIG_WIDTH) - 1,
    "width": (1 << evr_model.TRIG_WIDTH) - 1,
    "delayTap": 0x3F,
}


def conditions():
    return {"USE_TAP"} if TAP else set()


def pyrogue_conditions():
    return {"useTap"} if TAP else set()


def words():
    """Return the register words of one group that exist for the current generics."""
    return [word for word in rw.TRIGREG_LAYOUT if word != 0x0C or TAP]


def reset_word(word):
    """Return what a word reads after reset: the initial value of each read-write field."""
    value = 0
    for entry in rw.TRIGREG_LAYOUT[word]:
        if entry.mode == "RW" and (entry.condition is None or entry.condition in conditions()):
            value |= evr_model.TRIGGER_CONFIG_DEFAULTS[entry.name] << entry.lsb
    return value


def trigger_slice(dut, index):
    """Return trigger ``index`` of the flattened configuration output as a field dictionary."""
    value = rw.flat_value(dut.triggerConfig, "triggerConfig")
    return evr_model.unpack_trigger_config((value >> (evr_model.TRIGGER_CONFIG_BITS * index)) & TRIGGER_MASK)


def drive_delay_rd(dut, value):
    dut.delay_rd.value = value


async def bring_up(dut):
    master, clock_task = await rw.start_axi_master(dut)
    return master, rw.make_settle(dut), clock_task


async def walk_triggers(dut, master, settle, groups):
    """Walk every register word of the first ``groups`` groups; return walks and read-only fields."""
    config_bits = rw.trigger_config_bits(TRIGGERS)
    walks = []
    read_only = []
    for group in range(groups):
        for word in words():
            walks.append(
                await rw.walk_word(
                    master,
                    group * STRIDE + word,
                    lambda: rw.flat_value(dut.triggerConfig, "triggerConfig"),
                    settle,
                    config_bits,
                )
            )
        if TAP:
            mask = await rw.read_only_mask(
                master,
                group * STRIDE + 0x0C,
                lambda value: drive_delay_rd(dut, value),
                (1 << (6 * TRIGGERS)) - 1,
            )
            read_only.append((group * STRIDE + 0x0C, mask, group, "delay_rd"))
    return walks, read_only


def check_walks(walks, read_only, groups):
    """Assert reset values, the observed map, and the read-back masks; return the observed map."""
    for walk in walks:
        word = walk.address % STRIDE
        assert walk.reset_value == reset_word(word), (
            f"word 0x{walk.address:03X} read 0x{walk.reset_value:08X} after reset, expected 0x{reset_word(word):08X}"
        )
    observed = rw.rtl_bit_map(walks, read_only)
    expected = rw.trigreg_bit_map(groups, CARD, TAP)
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
async def trigreg_walk_matches_rtl_map(dut):
    """The walk of trigger 0 equals the layout table and disagrees with EvrV2TriggerReg.py as observed.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    reset_config = rw.flat_value(dut.triggerConfig, "triggerConfig")
    default = evr_model.pack_trigger_config()
    for index in range(TRIGGERS):
        got = (reset_config >> (evr_model.TRIGGER_CONFIG_BITS * index)) & TRIGGER_MASK
        assert got == default, f"trigger {index} reset configuration 0x{got:X}, expected 0x{default:X}"

    walks, read_only = await walk_triggers(dut, master, settle, 1)
    observed = check_walks(walks, read_only, 1)
    drift = pyrogue_drift(observed)
    assert [(entry.kind, entry.python_name) for entry in drift] == OBSERVED_DRIFT, f"PyRogue drift changed: {drift}"
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def trigreg_walk_all_groups(dut):
    """Every group walks to the layout table at its own base address, with its own configuration slice.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    walks, read_only = await walk_triggers(dut, master, settle, TRIGGERS)
    check_walks(walks, read_only, TRIGGERS)
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def trigreg_group_isolation_and_order(dut):
    """Group i lands in slice i, and writing one group leaves every other slice unchanged.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    delays = [0x0100001 + 0x1111 * index for index in range(TRIGGERS)]
    for index, delay in enumerate(delays):
        await rw.write_word(master, index * STRIDE + 0x04, delay)
    await settle()
    for index, delay in enumerate(delays):
        assert trigger_slice(dut, index)["delay"] == delay, f"group {index} delay is not in slice {index}"
        assert await rw.read_word(master, index * STRIDE + 0x04) == delay, f"group {index} reads back another delay"

    for target in range(TRIGGERS):
        before = rw.flat_value(dut.triggerConfig, "triggerConfig")
        for word in words():
            await rw.write_word(master, target * STRIDE + word, ALL_ONES)
        await settle()
        after = rw.flat_value(dut.triggerConfig, "triggerConfig")
        for index in range(TRIGGERS):
            old = (before >> (evr_model.TRIGGER_CONFIG_BITS * index)) & STEADY_MASK
            new = (after >> (evr_model.TRIGGER_CONFIG_BITS * index)) & STEADY_MASK
            if index != target:
                assert new == old, f"writing group {target} changed slice {index}: 0x{old:X} to 0x{new:X}"
        written = trigger_slice(dut, target)
        for name, value in ALL_ONES_FIELDS.items():
            if name == "delayTap" and not TAP:
                continue
            assert written[name] == value, f"group {target} field {name} is {written[name]:#x} after all ones"
        assert written["channels"] == 0, "writing a group moved the unused channels field"
    clock_task.cancel()


@cocotb.test(skip=not TAP, timeout_time=2, timeout_unit="ms")
async def trigreg_tap_readback_and_load(dut):
    """delay_rd reads back at +0x0C bits 16 to 21 per trigger, and a write to +0x0C pulses loadTap once.

    The pulse arrives two clocks after the write response returns (observed,
    intent unconfirmed) and is one clock wide.

    Propagation sampling: loadTap is sampled every clock 2 ns after the edge.
    """
    master, settle, clock_task = await bring_up(dut)
    patterns = [(5 + 11 * index) & 0x3F for index in range(TRIGGERS)]
    dut.delay_rd.value = sum(pattern << (6 * index) for index, pattern in enumerate(patterns))
    await settle()
    for index, pattern in enumerate(patterns):
        got = await rw.read_word(master, index * STRIDE + 0x0C)
        assert got == pattern << 16, f"group {index} read 0x{got:08X}, expected delay_rd pattern {pattern:#x} at bit 16"

    samples = []

    async def monitor():
        """Lifetime agent: samples loadTap on every clock until the entrypoint cancels it."""
        while True:
            await sample_after_tpd(dut.axilClk, propagation_time=rw.PROPAGATION_NS)
            samples.append([trigger_slice(dut, index)["loadTap"] for index in range(TRIGGERS)])

    for target, value in ((0, 0x2A), (TRIGGERS - 1, 0)):
        samples.clear()
        watcher = cocotb.start_soon(monitor())
        await rw.write_word(master, target * STRIDE + 0x0C, value)
        issued = len(samples)
        for _ in range(12):
            await sample_after_tpd(dut.axilClk, propagation_time=rw.PROPAGATION_NS)
        watcher.cancel()
        pulses = [(cycle, trigger) for cycle, row in enumerate(samples) for trigger, bit in enumerate(row) if bit]
        assert len(pulses) == 1 and pulses[0][1] == target, (
            f"write to group {target} +0x0C produced loadTap pulses {pulses}, expected exactly one on trigger {target}"
        )
        assert pulses[0][0] - issued == LOAD_TAP_LATENCY, (
            f"loadTap pulsed {pulses[0][0] - issued} clocks after the write returned, observed {LOAD_TAP_LATENCY}"
        )
        await settle()
        assert trigger_slice(dut, target)["delayTap"] == value, "delayTap did not take the written value"

    samples.clear()
    watcher = cocotb.start_soon(monitor())
    await rw.write_word(master, 0x04, 0x55)
    for _ in range(12):
        await sample_after_tpd(dut.axilClk, propagation_time=rw.PROPAGATION_NS)
    watcher.cancel()
    assert not any(any(row) for row in samples), "a write to the delay word pulsed loadTap"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def trigreg_zero_and_unmapped(dut):
    """Writing 0 everywhere leaves only read-only bits set, and unmapped words read 0 with OKAY.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    for group in range(TRIGGERS):
        for word in words():
            await rw.write_word(master, group * STRIDE + word, ALL_ONES)
    patterns = [(9 + 7 * index) & 0x3F for index in range(TRIGGERS)]
    if TAP:
        dut.delay_rd.value = sum(pattern << (6 * index) for index, pattern in enumerate(patterns))
    for group in range(TRIGGERS):
        for word in words():
            await rw.write_word(master, group * STRIDE + word, 0)
    await settle()
    for group in range(TRIGGERS):
        for word in words():
            got = await rw.read_word(master, group * STRIDE + word)
            want = patterns[group] << 16 if TAP and word == 0x0C else 0
            assert got == want, f"group {group} word 0x{word:02X} reads 0x{got:08X} after writing 0, expected 0x{want:08X}"
        slice_now = trigger_slice(dut, group)
        assert slice_now["enabled"] == 0 and slice_now["delay"] == 0 and slice_now["width"] == 0

    unmapped = [group * STRIDE + word for group in range(TRIGGERS) for word in (0x10, 0x14, 0x20, STRIDE - 4)]
    if not TAP:
        unmapped += [group * STRIDE + 0x0C for group in range(TRIGGERS)]
    if CARD:
        unmapped += [group * STRIDE + 0x800 for group in range(TRIGGERS)]
    before = rw.flat_value(dut.triggerConfig, "triggerConfig")
    for address in unmapped:
        assert await rw.read_word(master, address) == 0, f"unmapped word 0x{address:03X} did not read 0"
        await rw.write_word(master, address, ALL_ONES)
        assert await rw.read_word(master, address) == 0, f"unmapped word 0x{address:03X} kept a written value"
    await settle()
    assert rw.flat_value(dut.triggerConfig, "triggerConfig") == before, "a write to an unmapped word changed the configuration"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def trigreg_decode_aliasing(dut):
    """The block compares only bitSize(TRIGGERS * group size - 1) address bits, so higher addresses alias.

    Observed, intent unconfirmed: the word one decode window above group 0
    reads and writes the delay of group 0, and the space between the last
    group and the end of the decode window reads 0.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    window = 1 << evr_model.bit_size(TRIGGERS * STRIDE - 1)
    await rw.write_word(master, 0x04, 0x123456)
    await settle()
    assert await rw.read_word(master, window + 0x04) == 0x123456, f"0x{window + 4:X} does not alias the delay of group 0"
    await rw.write_word(master, window + 0x04, 0x654321)
    await settle()
    assert trigger_slice(dut, 0)["delay"] == 0x654321, "a write one decode window up did not reach group 0"
    if TRIGGERS * STRIDE < window:
        assert await rw.read_word(master, TRIGGERS * STRIDE + 0x04) == 0, "the gap above the last group did not read 0"
    clock_task.cancel()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def trigreg_python_agrees_with_rtl(dut):
    """EvrV2TriggerReg.py declares the same bits as the RTL decodes.

    Known issue entrypoint: it fails on the current files because ComplEn and
    ComplAnd sit one bit above the RTL fields.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, settle, clock_task = await bring_up(dut)
    walks, read_only = await walk_triggers(dut, master, settle, 1)
    drift = pyrogue_drift(rw.rtl_bit_map(walks, read_only))
    assert not drift, "PyRogue bit drift: " + "; ".join(f"{entry.python_name} {entry.kind}: {entry.detail}" for entry in drift)
    clock_task.cancel()


def run_trigreg_simulation(parameters, test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2trigregwrapper",
        parameters=parameters,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(parameters, test_filter),
    )


@pytest.mark.parametrize(
    "params",
    [
        parameter_case("one_tight", TRIGGERS_G=1, EVR_CARD_G="false", USE_TAP_G="false"),
        parameter_case("three_tight_tap", TRIGGERS_G=3, EVR_CARD_G="false", USE_TAP_G="true"),
        parameter_case("three_card", TRIGGERS_G=3, EVR_CARD_G="true", USE_TAP_G="false"),
        parameter_case("sixteen_tight", TRIGGERS_G=16, EVR_CARD_G="false", USE_TAP_G="false"),
    ],
)
def test_EvrV2TrigReg(params):
    excluded = [GATED_ENTRYPOINT] if params["USE_TAP_G"] == "true" else [GATED_ENTRYPOINT, TAP_ENTRYPOINT]
    run_trigreg_simulation(params, cocotb_test_filter_excluding(*excluded))


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2TriggerReg.py places ComplEn and ComplAnd one bit above the RTL decode; "
        "see https://github.com/slaclab/lcls-timing-core/issues/214; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2TrigReg_known_issue_compl_bits():
    run_trigreg_simulation({"USE_TAP_G": "true"}, cocotb_test_filter(GATED_ENTRYPOINT))
