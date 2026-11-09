#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2CoreChannels against its child-rule table, numTrig guard, and bus recording.

Test methodology:
    Sweep: every argument set of the table (default, numTrig 16, dmaEnable,
        useTap) in sorted order so the parametrized ids are identical across
        xdist workers; numTrig 0, 1, 16, and 17 for the constructor guard;
        every group index of a numTrig 16 build for the group placement.
    Stimulus: the class is built under a Rogue root on an in-process memory.
        The guard cases call the constructor directly. The round trip writes
        the boundary values of each RW variable on a fresh memory. The
        recording tests back the root with a RecordingSlave that logs every
        transaction and returns what was written; the read-only Count
        register of channel group 0 is preloaded in the slave.
    Checks: the built variable set equals the expansion of the child rule
        over the EvrV2ChannelReg leaf table (path, absolute bit position,
        width, mode, Rogue base type, enum map, kind); numTrig 0 and 17 raise
        ValueError naming the offending value, while 1 and 16 build exactly
        that many channel groups; the EnableReg of group i lands at byte
        i * 0x100; useTap and tickUnit change nothing; each written value
        reads back and leaves every other variable of its 32-bit word
        unchanged; each write transaction sets exactly the bits of its
        variable; the read-only Count returns the slave-supplied bits and its
        set() writes nothing.
    Timing: no simulator and no polling; the Rogue root is built with polling
        off and is stopped when its test ends.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import re

import pytest

from tests.common import register_tables
from tests.rogue import rogue_tree

CLASS = "EvrV2CoreChannels"
TABLE = register_tables.load_table(CLASS)
ARG_SETS = {arg_set.id: arg_set for arg_set in TABLE.ARG_SETS}
ARG_SET_IDS = sorted(ARG_SETS)

GROUP_STRIDE = 0x100
MAX_TRIG = 16
COUNT_WORD = 0x08
COUNT_PATTERN = 0x3C5A_9E21


def _group_indexes(device, prefix):
    pattern = re.compile(rf"^{re.escape(prefix)}\[(\d+)\]$")
    return sorted(
        int(match.group(1))
        for match in (pattern.match(name) for name in device.devices)
        if match
    )


def _all_ones(entry):
    if entry.base == "Bool":
        return True
    if entry.enum:
        return list(entry.enum)[-1]
    return (1 << entry.bit_size) - 1


@pytest.mark.parametrize("arg_set_id", ARG_SET_IDS)
def test_EvrV2CoreChannels_table(rogue_build_module, arg_set_id):
    arg_set = ARG_SETS[arg_set_id]
    _, device, _ = rogue_build_module(CLASS, **arg_set.args)
    assert rogue_tree.check_table(device, CLASS, arg_set) == []


def test_EvrV2CoreChannels_use_tap_is_unused(rogue_build_module):
    """useTap and tickUnit are accepted and unused.

    Observed behavior, intent unconfirmed: the class takes both arguments but
    only EvrV2CoreTriggers forwards them to a trigger group, so the tree for
    useTap=True equals the default expansion.
    """
    _, device, _ = rogue_build_module(CLASS, useTap=True, tickUnit="ns")
    assert rogue_tree.check_table(device, CLASS, ARG_SETS["default"]) == []


def test_EvrV2CoreChannels_no_overlap(rogue_build_module):
    _, device, _ = rogue_build_module(CLASS, numTrig=MAX_TRIG, dmaEnable=True)
    assert register_tables.find_overlaps(rogue_tree.tree_entries(device)) == []


@pytest.mark.parametrize("num_trig", [0, 1, 16, 17])
def test_EvrV2CoreChannels_num_trig_guard(rogue_build, num_trig):
    if num_trig < 1 or num_trig > MAX_TRIG:
        with pytest.raises(ValueError, match=rf"\({num_trig}\) is out of range"):
            rogue_tree.rogue_class(CLASS)(numTrig=num_trig)
        return
    _, device, _ = rogue_build(CLASS, numTrig=num_trig)
    assert _group_indexes(device, "EvrV2ChannelReg") == list(range(num_trig))


def test_EvrV2CoreChannels_group_placement(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave, numTrig=MAX_TRIG)
    for i in range(MAX_TRIG):
        enable = device.devices[f"EvrV2ChannelReg[{i}]"].variables["EnableReg"]
        recording_slave.clear()
        enable.set(True)
        assert rogue_tree.written_bits(recording_slave.log) == {i * GROUP_STRIDE * 8}, (
            f"EvrV2ChannelReg[{i}].EnableReg is not at byte {i * GROUP_STRIDE:#x}"
        )
        enable.set(False)


def test_EvrV2CoreChannels_round_trip(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert rogue_tree.round_trip(device) == []


def test_EvrV2CoreChannels_writes_land_on_table_bits(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    expected = register_tables.expand(TABLE, ARG_SETS["default"])
    variables = rogue_tree.tree_variables(device)
    assert expected
    for path, entry in sorted(expected.items()):
        if entry.mode != "RW":
            continue
        var = variables[path]
        recording_slave.clear()
        var.set(_all_ones(entry))
        bits = rogue_tree.written_bits(recording_slave.log)
        want = set(range(entry.abs_bit, entry.abs_bit + entry.bit_size))
        assert bits == want, f"{path}: wrote bits {sorted(bits)}, table says {sorted(want)}"
        # Put the variable back so the next write is not mixed with its bits.
        var.set(False if entry.base == "Bool" else 0)


def test_EvrV2CoreChannels_read_only_readback(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    recording_slave.preload(COUNT_WORD, COUNT_PATTERN.to_bytes(4, "little"))

    count = device.devices["EvrV2ChannelReg[0]"].variables["Count"]
    assert count.get(read=True) == COUNT_PATTERN

    recording_slave.clear()
    count.set(5)
    assert recording_slave.writes() == []
    assert count.get(read=True) == COUNT_PATTERN
