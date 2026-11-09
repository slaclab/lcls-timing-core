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
    Sweep: the default generics (one trigger, tight 256 byte groups, no delay
        tap).
    Stimulus: a cocotbext-axi AxiLiteMaster reads each register word, writes 0,
        then writes 1 << b for every bit b and reads the word back; the
        decoded triggerConfig output is read two clocks after each write.
    Checks: the observed map (read-write bits, the configuration field and
        field bit each one drives, reset values, read-back) equals the
        layout table; every register word reads its reset value after reset
        release; the observed map is then compared bit for bit with
        python/LclsTimingCore/EvrV2TriggerReg.py, which is read as text, and
        the disagreement is asserted exactly.
    Timing: 10 ns axilClk, every walk is bounded by the cocotb timeout.
    Propagation sampling: the registers update after TPD_G (1 ns), so the
        configuration output is read 2 ns after the clock edges that follow
        each write.
"""

import os
from pathlib import Path

import cocotb

from tests.common import evr_model, pyrogue_ast
from tests.common.regression_utils import (
    REPO_ROOT,
    env_int,
    run_lcls_vhdl_test,
)
from tests.lcls2_evr import register_walk as rw

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2TrigRegWrapper.vhd"
PYROGUE_FILE = REPO_ROOT / "python/LclsTimingCore/EvrV2TriggerReg.py"

TRIGGERS = env_int("TRIGGERS_G", default=1)
CARD = os.getenv("EVR_CARD_G", "false") == "true"
TAP = os.getenv("USE_TAP_G", "false") == "true"

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


def conditions():
    return {"USE_TAP"} if TAP else set()


def pyrogue_conditions():
    return {"useTap"} if TAP else set()


def reset_word(word):
    """Return what a word reads after reset: the initial value of each read-write field."""
    value = 0
    for entry in rw.TRIGREG_LAYOUT[word]:
        if entry.mode == "RW" and (entry.condition is None or entry.condition in conditions()):
            value |= evr_model.TRIGGER_CONFIG_DEFAULTS[entry.name] << entry.lsb
    return value


async def walk_triggers(dut, master, settle, groups):
    """Walk every register word of the first ``groups`` groups; return walks and read-only fields."""
    stride = rw.group_size(CARD)
    config_bits = rw.trigger_config_bits(TRIGGERS)
    walks = []
    read_only = []

    def drive_delay_rd(value):
        dut.delay_rd.value = value

    for group in range(groups):
        for word in rw.TRIGREG_LAYOUT:
            address = group * stride + word
            if word == 0x0C and not TAP:
                continue
            walks.append(
                await rw.walk_word(
                    master,
                    address,
                    lambda: rw.flat_value(dut.triggerConfig, "triggerConfig"),
                    settle,
                    config_bits,
                )
            )
        if TAP:
            mask = await rw.read_only_mask(master, group * stride + 0x0C, drive_delay_rd, (1 << (6 * TRIGGERS)) - 1)
            read_only.append((group * stride + 0x0C, mask, group, "delay_rd"))
    return walks, read_only


def pyrogue_drift(rtl_map):
    variables = pyrogue_ast.read_remote_variables(PYROGUE_FILE)
    return rw.compare_with_pyrogue(
        rtl_map,
        variables,
        NAME_MAP,
        base=0,
        enabled_conditions=pyrogue_conditions(),
        window=(0, rw.group_size(CARD)),
    )


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def trigreg_walk_matches_rtl_map(dut):
    """The walking-one map equals the layout table and disagrees with EvrV2TriggerReg.py as observed.

    Propagation sampling: the configuration output is read 2 ns after the
    clock edges that follow each write.
    """
    master, clock_task = await rw.start_axi_master(dut)
    settle = rw.make_settle(dut)
    reset_config = rw.flat_value(dut.triggerConfig, "triggerConfig")
    default = evr_model.pack_trigger_config()
    for index in range(TRIGGERS):
        got = (reset_config >> (evr_model.TRIGGER_CONFIG_BITS * index)) & ((1 << evr_model.TRIGGER_CONFIG_BITS) - 1)
        assert got == default, f"trigger {index} reset configuration 0x{got:X}, expected 0x{default:X}"

    walks, read_only = await walk_triggers(dut, master, settle, TRIGGERS)
    stride = rw.group_size(CARD)
    for walk in walks:
        word = walk.address % stride
        assert walk.reset_value == reset_word(word), (
            f"word 0x{walk.address:03X} read 0x{walk.reset_value:08X} after reset, expected 0x{reset_word(word):08X}"
        )

    observed = rw.rtl_bit_map(walks, read_only)
    expected = rw.trigreg_bit_map(TRIGGERS, CARD, TAP)
    assert observed == expected, (
        f"observed bits differ from the layout table: missing {sorted(set(expected) - set(observed))}, "
        f"extra {sorted(set(observed) - set(expected))}"
    )
    for walk in walks:
        rw_bits = {bit for (address, bit), info in expected.items() if address == walk.address and info.mode == "RW"}
        assert {bit for bit in range(rw.WORD_BITS) if walk.readback_mask >> bit & 1} == rw_bits, (
            f"word 0x{walk.address:03X} read-back mask 0x{walk.readback_mask:08X} differs from its read-write bits"
        )

    drift = pyrogue_drift(observed)
    assert [(entry.kind, entry.python_name) for entry in drift] == OBSERVED_DRIFT, f"PyRogue drift changed: {drift}"
    clock_task.cancel()


def test_EvrV2TrigReg():
    parameters = {"EVR_CARD_G": "false", "TRIGGERS_G": 1, "USE_TAP_G": "false"}
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2trigregwrapper",
        parameters=parameters,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
