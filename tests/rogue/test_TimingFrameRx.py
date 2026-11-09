#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingFrameRx against its reviewed table, round trip, and bus recording.

Test methodology:
    Sweep: both argument sets of the table (default, where clkselMode is
        'SELECT', and LCLSII, where it is anything else and ClkSel, ModeSel,
        and ModeSelEn become read-only), in sorted order so the parametrized
        ids are identical across xdist workers; then every RW variable of
        the default build for the round trip and the write placement, and
        both RemoteCommands.
    Stimulus: the class is built under a Rogue root on an in-process memory.
        The round trip writes the boundary values of each RW variable (all
        ones, one, the top bit, and a walking one for fields of 8 bits or
        fewer) on a fresh memory. The recording tests back the root with a
        RecordingSlave that logs every transaction and returns what was
        written; the read-only status and counter words are preloaded in the
        slave. Each RemoteCommand is called once with the log cleared.
    Checks: the built variable set equals the table exactly (path, absolute
        bit position, width, mode, Rogue base type, enum map, kind); no two
        variables share a bit; each written value reads back and leaves every
        other variable of its 32-bit word unchanged; each write transaction
        sets exactly the bits of its variable; each RemoteCommand issues two
        plain writes to the control word, the first with its own bit set and
        the second with it clear, and no read between them; read-only
        variables return the slave-supplied bits, and set() on the counter,
        which owns its whole word, writes nothing.
    Timing: no simulator and no polling; the Rogue root is built with polling
        off and is stopped when its test ends.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import pytest

from tests.common import register_tables
from tests.rogue import rogue_tree

CLASS = "TimingFrameRx"
TABLE = register_tables.load_table(CLASS)
ARG_SETS = {arg_set.id: arg_set for arg_set in TABLE.ARG_SETS}
ARG_SET_IDS = sorted(ARG_SETS)

CONTROL_WORD = 0x20
COMMAND_BITS = {"ClearRxCounters": 0, "C_RxReset": 3}

# RxLinkUp is bit 1 of the control word and RxPolarity bit 2. Every other bit
# of the preloaded word is a one too, so a mask error would show.
CONTROL_PATTERN = 0xFFFF_FFFF
COUNTER_WORD = 0x00
COUNTER_PATTERN = 0xA5C3_1E7F


def _all_ones(entry):
    if entry.base == "Bool":
        return True
    if entry.enum:
        return list(entry.enum)[-1]
    return (1 << entry.bit_size) - 1


@pytest.mark.parametrize("arg_set_id", ARG_SET_IDS)
def test_TimingFrameRx_table(rogue_build_module, arg_set_id):
    arg_set = ARG_SETS[arg_set_id]
    _, device, _ = rogue_build_module(CLASS, **arg_set.args)
    assert rogue_tree.check_table(device, CLASS, arg_set) == []


def test_TimingFrameRx_no_overlap(rogue_build_module):
    _, device, _ = rogue_build_module(CLASS)
    assert register_tables.find_overlaps(rogue_tree.tree_entries(device)) == []


def test_TimingFrameRx_round_trip(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert rogue_tree.round_trip(device) == []


def test_TimingFrameRx_writes_land_on_table_bits(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    expected = register_tables.expand(TABLE, ARG_SETS["default"])
    assert expected
    for path, entry in sorted(expected.items()):
        if entry.mode not in ("RW", "WO") or entry.kind != "RemoteVariable":
            continue
        var = device.variables[path]
        recording_slave.clear()
        var.set(_all_ones(entry))
        bits = rogue_tree.written_bits(recording_slave.log)
        want = set(range(entry.abs_bit, entry.abs_bit + entry.bit_size))
        assert bits == want, f"{path}: wrote bits {sorted(bits)}, table says {sorted(want)}"
        # Put the variable back so the next write is not mixed with its bits.
        var.set(False if entry.base == "Bool" else 0)


@pytest.mark.parametrize("command", sorted(COMMAND_BITS))
def test_TimingFrameRx_remote_command_toggle(rogue_build, recording_slave, command):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    bit = COMMAND_BITS[command]
    target = 1 << bit

    recording_slave.clear()
    device.commands[command]()

    # Exactly two plain writes of the control word and nothing else: no
    # Verify read follows either write.
    assert len(recording_slave.log) == 2, recording_slave.log
    first, second = recording_slave.log
    for direction, _, address, size, _ in (first, second):
        assert (direction, address, size) == ("W", CONTROL_WORD, 4)
    assert int.from_bytes(first[4], "little") & target == target
    assert int.from_bytes(first[4], "little") == target
    assert int.from_bytes(second[4], "little") & target == 0
    assert recording_slave.reads() == []


def test_TimingFrameRx_read_only_readback(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    recording_slave.preload(CONTROL_WORD, CONTROL_PATTERN.to_bytes(4, "little"))
    recording_slave.preload(COUNTER_WORD, COUNTER_PATTERN.to_bytes(4, "little"))

    link_up = device.variables["RxLinkUp"]
    polarity = device.variables["RxPolarity"]
    assert link_up.get(read=True) == 1
    assert polarity.get(read=True) == 1

    recording_slave.clear()
    link_up.set(0)
    # The control word is shared with RW variables, so Rogue writes the whole
    # word back; the write may touch only that word and must carry the RW
    # neighbor's value unchanged.
    for _, _, address, size, data in recording_slave.writes():
        assert (address, size) == (CONTROL_WORD, 4)
        assert int.from_bytes(data, "little") >> 2 & 1 == 1
    assert polarity.get(read=True) == 1

    counter = device.variables["sofCount"]
    assert counter.get(read=True) == COUNTER_PATTERN
    recording_slave.clear()
    counter.set(5)
    assert recording_slave.writes() == []
    assert counter.get(read=True) == COUNTER_PATTERN
