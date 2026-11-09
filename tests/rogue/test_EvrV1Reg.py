#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1Reg: the Rogue rejection pinned as observed, with a gated build.

Test methodology:
    Sweep: the one argument set of the table (the class takes no arguments);
        33 declarations, 13 of them arrays (twelve Pulse arrays of 4, OutputMap
        of 12); 80 variables.
    Stimulus: the class is built under a Rogue root, which raises at start()
        on Rogue 6.16.0; the declarations themselves are read from the
        source text with ast, so the tree is never needed for the snapshot.
    Checks: the exact Rogue message names IrqFlagWr, address 0x00000008, and
        IrqFlagRd; the declarations read from source equal the reviewed
        table on name, absolute bit position, width, mode, base type, enum
        map, and overlapEn; the set of overlapping name pairs found from
        the source is exactly {(IrqFlagRd, IrqFlagWr)}, so a partial fix changes
        the result. The gated test builds the tree and expects success, so
        it fails while the defect exists and skips by default.
    Timing: no simulator and no polling; the Rogue root is stopped when the
        build ends, including when start() raises.
    Propagation sampling: not applicable, there is no propagation delay.

IrqFlagWr and IrqFlagRd are the write and read views of one interrupt flag
register at 0x08, declared without overlapEn, so Rogue rejects the tree; see
https://github.com/slaclab/lcls-timing-core/issues/217. The rejection is
observed, and the fix is a decision for the maintainers.
"""

import os
import re
from pathlib import Path

import pytest

from tests.common import register_tables
from tests.common.pyrogue_ast import expected_entries, read_remote_variables
from tests.rogue import rogue_tree

import rogue

CLASS = "EvrV1Reg"
TABLE = register_tables.load_table(CLASS)
DEFAULT = TABLE.ARG_SETS[0]
SOURCE = Path(__file__).resolve().parents[2] / "python" / "LclsTimingCore" / f"{CLASS}.py"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

REJECTED_MESSAGE = (
    "Variable bit overlap detected for block root.EvrV1Reg.IrqFlagWr "
    "with address 0x00000008 and variable IrqFlagRd"
)

OVERLAPPING_NAMES = {("IrqFlagRd", "IrqFlagWr")}


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


def test_EvrV1Reg_overlap_pinned():
    with pytest.raises(rogue.GeneralError, match=re.escape(REJECTED_MESSAGE)):
        with rogue_tree.build_tree(CLASS):
            pass


def test_EvrV1Reg_ast_snapshot():
    declared = expected_entries(read_remote_variables(SOURCE))
    assert len(declared) == 80
    expected = register_tables.expand(TABLE, DEFAULT)
    assert register_tables.diff_variables(expected, declared) == []


def test_EvrV1Reg_overlap_pairs():
    declared = expected_entries(read_remote_variables(SOURCE))
    assert _name_pairs(declared) == OVERLAPPING_NAMES


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV1Reg.py declares IrqFlagWr and IrqFlagRd on the same bits of 0x08 without overlapEn, "
        "so Rogue rejects the tree; see https://github.com/slaclab/lcls-timing-core/issues/217; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV1Reg_known_issue_overlap(rogue_build):
    _, device, _ = rogue_build(CLASS)
    assert len(rogue_tree.tree_variables(device)) == 80
