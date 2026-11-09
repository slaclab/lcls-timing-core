#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGControl against its reviewed table, round trip, and bus recording.

Test methodology:
    Sweep: the one argument set of the table (the class takes no arguments);
        then every RW variable of the build, which includes the 6 byte wide
        AC rate dividers, the 64 BSA event and status selects, and the
        interrupt enables that share the words at 0x74 and 0x78.
    Stimulus: the class is built under a Rogue root on an in-process memory.
        The round trip writes the boundary values of each RW variable (all
        ones, one, the top bit, and a walking one for fields of 8 bits or
        fewer) on a fresh memory. The recording tests back the root with a
        RecordingSlave that logs every transaction and returns what was
        written; the read-only status words are preloaded in the slave with
        the bits outside each field set, so a mask error shows.
    Checks: the built variable set equals the table exactly (path, absolute
        bit position, width, mode, Rogue base type, enum map, kind); no two
        variables share a bit; each written value reads back and leaves every
        other variable of its 32-bit word unchanged; each write transaction
        sets exactly the bits of its variable, write-only variables
        included; each read-only variable returns the slave-supplied bits of
        its field and its set() writes nothing, because both own their whole
        word.
    Timing: no simulator and no polling; the Rogue root is built with polling
        off and is stopped when its test ends.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import pytest

from tests.common import register_tables
from tests.rogue import rogue_tree

CLASS = "TPGControl"
TABLE = register_tables.load_table(CLASS)
ARG_SETS = {arg_set.id: arg_set for arg_set in TABLE.ARG_SETS}
ARG_SET_IDS = sorted(ARG_SETS)

# Word, preloaded word, and the field value it must yield, per read-only case.
# NAllowSeq is bits 7:4 of byte 3, so the word 0x00 carries it in bits 31:28;
# SeqFifoData owns the whole word at 0x7C.
READ_ONLY_CASES = {
    "NAllowSeq": (0x00, 0xA5FF_FFFF, 0xA),
    "SeqFifoData": (0x7C, 0xA5C3_1E7F, 0xA5C3_1E7F),
}


def _all_ones(entry):
    if entry.base == "Bool":
        return True
    if entry.enum:
        return list(entry.enum)[-1]
    return (1 << entry.bit_size) - 1


@pytest.mark.parametrize("arg_set_id", ARG_SET_IDS)
def test_TPGControl_table(rogue_build_module, arg_set_id):
    arg_set = ARG_SETS[arg_set_id]
    _, device, _ = rogue_build_module(CLASS, **arg_set.args)
    assert rogue_tree.check_table(device, CLASS, arg_set) == []


def test_TPGControl_no_overlap(rogue_build_module):
    _, device, _ = rogue_build_module(CLASS)
    assert register_tables.find_overlaps(rogue_tree.tree_entries(device)) == []


def test_TPGControl_round_trip(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert rogue_tree.round_trip(device) == []


def test_TPGControl_writes_land_on_table_bits(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    expected = register_tables.expand(TABLE, ARG_SETS["default"])
    variables = rogue_tree.tree_variables(device)
    assert expected
    for path, entry in sorted(expected.items()):
        if entry.mode not in ("RW", "WO"):
            continue
        var = variables[path]
        recording_slave.clear()
        var.set(_all_ones(entry))
        bits = rogue_tree.written_bits(recording_slave.log)
        want = set(range(entry.abs_bit, entry.abs_bit + entry.bit_size))
        assert bits == want, f"{path}: wrote bits {sorted(bits)}, table says {sorted(want)}"
        # Put the variable back so the next write is not mixed with its bits.
        var.set(False if entry.base == "Bool" else 0)


@pytest.mark.parametrize("name", sorted(READ_ONLY_CASES))
def test_TPGControl_read_only_readback(rogue_build, recording_slave, name):
    word, pattern, value = READ_ONLY_CASES[name]
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    recording_slave.preload(word, pattern.to_bytes(4, "little"))

    var = device.variables[name]
    assert var.get(read=True) == value

    recording_slave.clear()
    var.set(0)
    assert recording_slave.writes() == []
    assert var.get(read=True) == value
