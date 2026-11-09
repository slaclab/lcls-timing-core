#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGSeqJump: the Rogue rejection pinned as observed, with a gated build.

Test methodology:
    Sweep: the one argument set of the table (the class takes no arguments);
        three declarations of 1024 words each (3072 variables).
    Stimulus: the class is built under a Rogue root, which raises at start()
        on Rogue 6.16.0; the declarations themselves are read from the
        source text with ast, so the tree is never needed for the snapshot.
    Checks: the exact Rogue message names StartAddr[0], address 0x00000000,
        and Class[0]; the declarations read from source equal the reviewed
        table on name, absolute bit position, width, mode, base type, enum
        map, and overlapEn; the set of overlapping name pairs found from
        the source is exactly {(Class, StartAddr)}, so a partial fix changes
        the result. The gated test builds the tree and expects success, so
        it fails while the defect exists and skips by default.
    Timing: no simulator and no polling; the Rogue root is stopped when the
        build ends, including when start() raises.
    Propagation sampling: not applicable, there is no propagation delay.

Class is declared at byte 1 bit 0, on bits 8 to 11 of StartAddr, where
yaml/TPGSeqJump.yaml puts it at bit 4 of byte 1. The rejection is observed,
and its intent is unconfirmed.
"""

import os
import re
from pathlib import Path

import pytest

from tests.common import register_tables
from tests.common.pyrogue_ast import expected_entries, read_remote_variables
from tests.rogue import rogue_tree

import rogue

CLASS = "TPGSeqJump"
TABLE = register_tables.load_table(CLASS)
DEFAULT = TABLE.ARG_SETS[0]
SOURCE = Path(__file__).resolve().parents[2] / "python" / "LclsTimingCore" / f"{CLASS}.py"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

REJECTED_MESSAGE = (
    "Variable bit overlap detected for block root.TPGSeqJump.StartAddr[0] "
    "with address 0x00000000 and variable Class[0]"
)

OVERLAPPING_NAMES = {("Class", "StartAddr")}


def _name_pairs(entries):
    """Overlapping pairs with the array indices stripped from each name."""
    strip = rogue_tree.INDEX_RE
    names = set()
    for first, second in register_tables.find_overlaps(entries):
        pair = []
        for path in (first, second):
            match = strip.match(path)
            pair.append(match.group("base") if match else path)
        names.add(tuple(sorted(pair)))
    return names


def test_TPGSeqJump_overlap_pinned():
    with pytest.raises(rogue.GeneralError, match=re.escape(REJECTED_MESSAGE)):
        with rogue_tree.build_tree(CLASS):
            pass


def test_TPGSeqJump_ast_snapshot():
    declared = expected_entries(read_remote_variables(SOURCE))
    assert len(declared) == 3072
    expected = register_tables.expand(TABLE, DEFAULT)
    assert register_tables.diff_variables(expected, declared) == []


def test_TPGSeqJump_overlap_pairs():
    declared = expected_entries(read_remote_variables(SOURCE))
    assert _name_pairs(declared) == OVERLAPPING_NAMES


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPGSeqJump.py declares Class at byte 1 bit 0, overlapping bits 8 to 11 of StartAddr, "
        "so Rogue rejects the tree; see https://github.com/slaclab/lcls-timing-core/issues/220; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_TPGSeqJump_known_issue_overlap(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert len(rogue_tree.tree_variables(device)) == 3072
