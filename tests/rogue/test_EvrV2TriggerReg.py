#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2TriggerReg against its reviewed table, round trip, and bus recording.

Test methodology:
    Sweep: both argument sets of the table (default arguments, and useTap=True
        which adds DelayTap and DelayTapReadback), in sorted order so the
        parametrized ids are identical across xdist workers; then every RW
        variable of the default build.
    Stimulus: the class is built under a Rogue root on an in-process memory.
        The round trip writes the boundary values of each RW variable (all
        ones, one, the top bit, and a walking one for fields of 8 bits or
        fewer) on a fresh memory. The recording tests back the root with a
        RecordingSlave that logs every transaction and returns what was
        written, and for the read-only register preload the slave memory.
    Checks: the built variable set equals the table exactly (path, absolute
        bit position, width, mode, Rogue base type, enum map, kind); no two
        variables share a bit; each written value reads back and leaves every
        other variable of its 32-bit word unchanged; each write transaction
        sets exactly the bits of its variable; a read-only variable returns
        the slave-supplied bits and its set() cannot reach beyond its word.
    Timing: no simulator and no polling; the Rogue root is built with polling
        off and is stopped when its test ends.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import pytest

from tests.common import register_tables
from tests.rogue import rogue_tree

CLASS = "EvrV2TriggerReg"
TABLE = register_tables.load_table(CLASS)
ARG_SETS = {arg_set.id: arg_set for arg_set in TABLE.ARG_SETS}
ARG_SET_IDS = sorted(ARG_SETS)

# Word 0x0C of the useTap build: DelayTap in bits 5:0, DelayTapReadback in 21:16.
TAP_WORD = 0x0C
TAP_PATTERN = 0x002A0015


def _all_ones(var, entry):
    if entry.base == "Bool":
        return True
    if entry.enum:
        return list(entry.enum)[-1]
    return (1 << entry.bit_size) - 1


@pytest.mark.parametrize("arg_set_id", ARG_SET_IDS)
def test_EvrV2TriggerReg_table(rogue_build_module, arg_set_id):
    arg_set = ARG_SETS[arg_set_id]
    _, device, _ = rogue_build_module(CLASS, **arg_set.args)
    assert rogue_tree.check_table(device, CLASS, arg_set) == []


def test_EvrV2TriggerReg_no_overlap(rogue_build_module):
    _, device, _ = rogue_build_module(CLASS, useTap=True)
    assert register_tables.find_overlaps(rogue_tree.tree_entries(device)) == []


def test_EvrV2TriggerReg_round_trip(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert rogue_tree.round_trip(device) == []


def test_EvrV2TriggerReg_writes_land_on_table_bits(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    expected = register_tables.expand(TABLE, ARG_SETS["default"])
    assert expected
    for path, entry in sorted(expected.items()):
        if entry.mode != "RW":
            continue
        var = device.variables[path]
        value = _all_ones(var, entry)
        recording_slave.clear()
        var.set(value)
        bits = rogue_tree.written_bits(recording_slave.log)
        want = set(range(entry.abs_bit, entry.abs_bit + entry.bit_size))
        assert bits == want, f"{path}: wrote bits {sorted(bits)}, table says {sorted(want)}"
        # Put the variable back so the next write is not mixed with its bits.
        var.set(False if entry.base == "Bool" else 0)


def test_EvrV2TriggerReg_read_only_readback(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave, useTap=True)
    recording_slave.preload(TAP_WORD, TAP_PATTERN.to_bytes(4, "little"))

    readback = device.variables["DelayTapReadback"]
    assert readback.get(read=True) == (TAP_PATTERN >> 16) & 0x3F
    assert device.variables["DelayTap"].get(read=True) == TAP_PATTERN & 0x3F

    recording_slave.clear()
    readback.set(5)
    # The register word is shared with the RW DelayTap, so Rogue writes the
    # whole word back; the write may touch only that word and must carry the
    # RW neighbor's value unchanged.
    for _, _, address, size, data in recording_slave.writes():
        assert (address, size) == (TAP_WORD, 4)
        assert int.from_bytes(data, "little") & 0x3F == TAP_PATTERN & 0x3F
    assert device.variables["DelayTap"].get(read=True) == TAP_PATTERN & 0x3F
