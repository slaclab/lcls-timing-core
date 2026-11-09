#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""GthRxAlignCheck against its reviewed table, round trip, and link math.

Test methodology:
    Sweep: the one argument set of the table (the class takes no arguments);
        then every RW variable of the build, which are the three fields of
        the configuration word at 0x100; then both LinkVariables.
    Stimulus: the class is built under a Rogue root on an in-process memory.
        The round trip writes the boundary values of each RW variable (all
        ones, one, the top bit, and a walking one for fields of 8 bits or
        fewer) on a fresh memory. The recording tests back the root with a
        RecordingSlave that logs every transaction and returns what was
        written. The link math tests preload the raw frequency register with
        1000000 and then 0xFFFFFFFF, and the read-only tests preload the
        last-phase word and one histogram word with the bits outside each
        field set, so a mask error shows.
    Checks: the built variable set equals the table exactly (path, absolute
        bit position, width, mode, Rogue base type, enum map, kind, and the
        LinkVariable dependencies); no two variables share a bit; each
        written value reads back and leaves every other variable of its
        32-bit word unchanged; each write transaction sets exactly the bits
        of its variable; TxClkFreq and RxClkFreq return the raw register times
        1.0e-6 (1.0 and 4294.967295 within a relative 1e-9) and issue at
        least one read of the raw address; read-only variables return the
        slave-supplied bits and set() writes nothing, because each owns its
        whole word.
    Timing: no simulator and no polling; the Rogue root is built with polling
        off and is stopped when its test ends.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import pytest

from tests.common import register_tables
from tests.rogue import rogue_tree

CLASS = "GthRxAlignCheck"
TABLE = register_tables.load_table(CLASS)
ARG_SETS = {arg_set.id: arg_set for arg_set in TABLE.ARG_SETS}
ARG_SET_IDS = sorted(ARG_SETS)

# LinkVariable name, raw register address.
LINK_CASES = {"TxClkFreq": 0x108, "RxClkFreq": 0x10C}

# Word, preloaded word, and the field value it must yield, per read-only case.
READ_ONLY_CASES = {
    "LastPhase": (0x104, 0xFFFF_FFA5, 0x25),
    "PhaseCount[3]": (0x0C, 0xA5C3_1E7F, 0xA5C3_1E7F),
}


def _all_ones(entry):
    if entry.base == "Bool":
        return True
    if entry.enum:
        return list(entry.enum)[-1]
    return (1 << entry.bit_size) - 1


@pytest.mark.parametrize("arg_set_id", ARG_SET_IDS)
def test_GthRxAlignCheck_table(rogue_build_module, arg_set_id):
    arg_set = ARG_SETS[arg_set_id]
    _, device, _ = rogue_build_module(CLASS, **arg_set.args)
    assert rogue_tree.check_table(device, CLASS, arg_set) == []


def test_GthRxAlignCheck_no_overlap(rogue_build_module):
    _, device, _ = rogue_build_module(CLASS)
    assert register_tables.find_overlaps(rogue_tree.tree_entries(device)) == []


def test_GthRxAlignCheck_round_trip(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert rogue_tree.round_trip(device) == []


def test_GthRxAlignCheck_writes_land_on_table_bits(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    expected = register_tables.expand(TABLE, ARG_SETS["default"])
    variables = rogue_tree.tree_variables(device)
    assert expected
    for path, entry in sorted(expected.items()):
        if entry.mode not in ("RW", "WO") or entry.kind != "RemoteVariable":
            continue
        var = variables[path]
        recording_slave.clear()
        var.set(_all_ones(entry))
        bits = rogue_tree.written_bits(recording_slave.log)
        want = set(range(entry.abs_bit, entry.abs_bit + entry.bit_size))
        assert bits == want, f"{path}: wrote bits {sorted(bits)}, table says {sorted(want)}"
        # Put the variable back so the next write is not mixed with its bits.
        var.set(False if entry.base == "Bool" else 0)


@pytest.mark.parametrize("name", sorted(LINK_CASES))
def test_GthRxAlignCheck_link_variable_math(rogue_build, recording_slave, name):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    address = LINK_CASES[name]
    link = device.variables[name]

    for raw, want in ((1_000_000, 1.0), (0xFFFF_FFFF, 4294.967295)):
        recording_slave.preload(address, raw.to_bytes(4, "little"))
        recording_slave.clear()
        assert link.get() == pytest.approx(want, rel=1e-9)
        # The count of reads is not pinned, only that the raw register was read.
        raw_reads = [entry for entry in recording_slave.reads() if entry[2] == address]
        assert raw_reads, f"{name}: no read of 0x{address:03X} in {recording_slave.log}"


@pytest.mark.parametrize("name", sorted(READ_ONLY_CASES))
def test_GthRxAlignCheck_read_only_readback(rogue_build, recording_slave, name):
    word, pattern, value = READ_ONLY_CASES[name]
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    recording_slave.preload(word, pattern.to_bytes(4, "little"))

    var = rogue_tree.tree_variables(device)[name]
    assert var.get(read=True) == value

    recording_slave.clear()
    var.set(0)
    assert recording_slave.writes() == []
    assert var.get(read=True) == value
