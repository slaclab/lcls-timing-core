#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGMiniCore against its reviewed tables, round trip, and known issues.

Test methodology:
    Sweep: three argument sets of the table, NARRAYSBSA 1, 2 (default), and 4
        (1 and 4 are the smallest meaningful value and the largest one the
        Python accepts today; 0 builds but is not a BSA configuration), in
        sorted order so the parametrized ids are identical across xdist
        workers; then every RW and WO variable of the default build for the
        round trip and the write placement; then NARRAYSBSA 5 for the
        rejection and 32 for the gated known issue.
    Stimulus: the class is built under a Rogue root on an in-process memory.
        The round trip writes the boundary values of each RW variable (all
        ones, one, the top bit, and a walking one for fields of 8 bits or
        fewer) on a fresh memory, skipping the neighbor comparison for the
        pairs in OBSERVED_OVERLAPS. The recording tests back the root with a
        RecordingSlave that logs every transaction and returns what was
        written; the 64 bit read-only BsaCompleteRd is preloaded with
        0xFEDCBA9876543210.
    Checks: the built variable set equals the table exactly (path, absolute
        bit position, width, mode, Rogue base type, enum map, kind,
        overlapEn); the overlaps that remain when the declared overlapEn flag
        is ignored equal OBSERVED_OVERLAPS exactly, so a fix or a new overlap
        fails the test; each written value reads back and leaves every other
        variable of its 32-bit word unchanged, except the observed pairs;
        each write transaction sets exactly the bits of its variable,
        write-only variables included; BsaCompleteRd returns the 64 bit
        slave value exactly; NARRAYSBSA 5 raises the Rogue overlap error that
        names BsaActive[4] and address 0x200. The two gated tests state the
        layout the RTL decodes (BsaAvgToWr 16 bytes apart, NARRAYSBSA up to
        32) and fail on the current Python.
    Timing: no simulator and no polling; the Rogue root is built with polling
        off and is stopped when its test ends.
    Propagation sampling: not applicable, there is no propagation delay.

BsaAvgToWr is declared with a stride of 8 where TPGMiniReg indexes the
sequences 16 bytes apart. Rogue builds the tree without complaint because the
array variables are declared with overlapEn=True, which switches its check
off for them. The observed pairs are therefore recorded, not endorsed.
"""

import os
import re

import pytest

from tests.common import register_tables
from tests.rogue import rogue_tree

import rogue

CLASS = "TPGMiniCore"
TABLE = register_tables.load_table(CLASS)
ARG_SETS = {arg_set.id: arg_set for arg_set in TABLE.ARG_SETS}
ARG_SET_IDS = sorted(ARG_SETS)

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

# Observed at NARRAYSBSA 2 with the declared overlapEn flag ignored: element 1
# of BsaAvgToWr (word 0x210, bits 31:16) shares bits with three variables of
# sequence 1. Whether this overlap is intended is unconfirmed.
OBSERVED_OVERLAPS = (
    ("BsaAvgToWr[1]", "BsaDestMode[1]"),
    ("BsaAvgToWr[1]", "BsaSequenceBitSelect[1]"),
    ("BsaAvgToWr[1]", "BsaSequenceSelect[1]"),
)

# BsaCompleteWr (WO) and BsaCompleteRd (RO) share one 64 bit address by design.
DOCUMENTED_SHARED = frozenset({"BsaCompleteWr", "BsaCompleteRd"})

REJECTED_MESSAGE = (
    "Variable bit mask overlap detected for block root.TPGMiniCore.BsaActive[4] "
    "with address 0x00000200"
)

COMPLETE_WORD = 0x50
COMPLETE_PATTERN = 0xFEDC_BA98_7654_3210


def _all_ones(entry):
    if entry.base == "Bool":
        return True
    if entry.enum:
        return list(entry.enum)[-1]
    return (1 << entry.bit_size) - 1


def _overlaps_ignoring_flag(entries):
    """Overlapping pairs when the declared overlapEn flag is ignored.

    find_overlaps skips a pair when both variables carry overlap_en, which is
    exactly what hides the BsaAvgToWr overlap, so the flag is cleared on every
    variable except the documented BsaCompleteWr and BsaCompleteRd pair.
    """
    cleared = {
        path: entry if path in DOCUMENTED_SHARED else entry._replace(overlap_en=False)
        for path, entry in entries.items()
    }
    return register_tables.find_overlaps(cleared)


@pytest.mark.parametrize("arg_set_id", ARG_SET_IDS)
def test_TPGMiniCore_table(rogue_build_module, arg_set_id):
    arg_set = ARG_SETS[arg_set_id]
    _, device, _ = rogue_build_module(CLASS, **arg_set.args)
    assert rogue_tree.check_table(device, CLASS, arg_set) == []


def test_TPGMiniCore_no_overlap(rogue_build_module):
    # With the declared overlapEn flags honored, which is what Rogue itself
    # does, nothing overlaps; the next test shows what the flags hide.
    _, device, _ = rogue_build_module(CLASS)
    assert register_tables.find_overlaps(rogue_tree.tree_entries(device)) == []


def test_TPGMiniCore_observed_overlaps(rogue_build_module):
    """Observed, intent unconfirmed: the overlap list is pinned so a fix is noticed."""
    _, device, _ = rogue_build_module(CLASS)
    entries = rogue_tree.tree_entries(device)
    assert _overlaps_ignoring_flag(entries) == list(OBSERVED_OVERLAPS)


def test_TPGMiniCore_round_trip(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert rogue_tree.round_trip(device, exempt=frozenset(OBSERVED_OVERLAPS)) == []


def test_TPGMiniCore_writes_land_on_table_bits(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    expected = register_tables.expand(TABLE, ARG_SETS["default"])
    variables = rogue_tree.tree_variables(device)
    assert expected
    for path, entry in sorted(expected.items()):
        if entry.mode not in ("RW", "WO"):
            continue
        var = variables[path]
        want = set(range(entry.abs_bit, entry.abs_bit + entry.bit_size))
        # An enumerated variable cannot always be set to all ones (a 4 bit
        # enum with keys 0 to 6 has no key 15), so every key is written; each
        # write must stay inside the field and together they must reach its
        # lowest bit. The field width itself is checked by the table.
        values = list(entry.enum) if entry.enum else [_all_ones(entry)]
        covered = set()
        for value in values:
            recording_slave.clear()
            var.set(value)
            bits = rogue_tree.written_bits(recording_slave.log)
            assert bits <= want, f"{path}: wrote bits {sorted(bits)}, table says {sorted(want)}"
            covered |= bits
            # Put the variable back so the next write is not mixed with its bits.
            var.set(False if entry.base == "Bool" else 0)
        if entry.enum:
            assert min(want) in covered, f"{path}: no write reached bit {min(want)}"
        else:
            assert covered == want, f"{path}: wrote bits {sorted(covered)}, table says {sorted(want)}"


def test_TPGMiniCore_read_only_readback(rogue_build, recording_slave):
    _, device, _ = rogue_build(CLASS, memory=recording_slave)
    recording_slave.preload(COMPLETE_WORD, COMPLETE_PATTERN.to_bytes(8, "little"))

    var = device.variables["BsaCompleteRd"]
    assert var.get(read=True) == COMPLETE_PATTERN

    recording_slave.clear()
    var.set(5)
    # BsaCompleteRd shares its 64 bits with the write-only BsaCompleteWr (both
    # overlapEn), so the block is written whole; the write may touch only
    # that block.
    for _, _, address, size, _ in recording_slave.writes():
        assert (address, size) == (COMPLETE_WORD, 8)
    # Restore the slave word: the readback must come from the bus, not the cache.
    recording_slave.preload(COMPLETE_WORD, COMPLETE_PATTERN.to_bytes(8, "little"))
    assert var.get(read=True) == COMPLETE_PATTERN


def test_TPGMiniCore_narraysbsa_5_rejected():
    """Observed: Python rejects 5 although the RTL allows up to 32."""
    with pytest.raises(rogue.GeneralError, match=re.escape(REJECTED_MESSAGE)):
        with rogue_tree.build_tree(CLASS, NARRAYSBSA=5):
            pass


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPGMiniCore.py declares BsaAvgToWr with a stride of 8 where TPGMiniReg decodes "
        "16 bytes per sequence; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_TPGMiniCore_known_issue_bsa_avg_to_wr_stride(rogue_build):
    _, device, _ = rogue_build(CLASS)
    entries = rogue_tree.tree_entries(device)
    overlaps = _overlaps_ignoring_flag(entries)
    assert overlaps == [], f"BsaAvgToWr stride 8 overlaps other variables: {overlaps}"
    for index in range(2):
        want = (0x208 + 16 * index) * 8 + 16
        got = entries[f"BsaAvgToWr[{index}]"].abs_bit
        assert got == want, (
            f"BsaAvgToWr[{index}] is at absolute bit {got}, the RTL decode puts it at bit {want}"
        )


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPGMiniCore.py declares BsaActive with a byte stride where TPGMiniReg decodes "
        "one bit per sequence, so NARRAYSBSA above 4 is rejected; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_TPGMiniCore_known_issue_narraysbsa_32(rogue_build):
    _, device, _ = rogue_build(CLASS, NARRAYSBSA=32)
    assert "BsaActive[31]" in rogue_tree.tree_variables(device)
