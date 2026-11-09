#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPG: the Rogue rejection pinned as observed, with a gated build.

Test methodology:
    Sweep: the one argument set of the table (the class takes no arguments);
        the four child devices TPGControl, TPGStatus, TPGSeqState, and
        TPGSeqJump.
    Stimulus: the class is built under a Rogue root, which raises at start()
        on Rogue 6.16.0; the child placement is read from the source text
        with ast, so the tree is never needed for the snapshot.
    Checks: the exact Rogue message names the inherited CountSeq overlap of
        TPGStatus (root.TPG.TPGStatus.CountSeq[0], address 0x00000544, and
        CountSeq[1]); the child placement read from source equals the
        reviewed table, in order; TPGStatus and TPGSeqJump share offset
        0x400 and no other offset is shared. The gated test builds the tree
        and expects success, so it fails while the defect exists and skips
        by default.
    Timing: no simulator and no polling; the Rogue root is stopped when the
        build ends, including when start() raises.
    Propagation sampling: not applicable, there is no propagation delay.

TPG fails for two reasons. The first is inherited: TPGStatus declares
CountSeq with a stride of 2 bytes for 32 bit counters, and TPGSeqJump,
TPGSeqState, and TPGStatus each have a leaf overlap of their own. The second
is the placement: TPGStatus and TPGSeqJump are both added at 0x400. Rogue
reports only the first overlap it meets, which hides the placement.
"""

import os
import re
from collections import Counter
from pathlib import Path

import pytest

from tests.common import register_tables
from tests.common.pyrogue_ast import read_child_devices
from tests.rogue import rogue_tree

import rogue

CLASS = "TPG"
TABLE = register_tables.load_table(CLASS)
SOURCE = Path(__file__).resolve().parents[2] / "python" / "LclsTimingCore" / f"{CLASS}.py"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

REJECTED_MESSAGE = (
    "Variable bit overlap detected for block root.TPG.TPGStatus.CountSeq[0] "
    "with address 0x00000544 and variable CountSeq[1]"
)


def test_TPG_overlap_pinned():
    with pytest.raises(rogue.GeneralError, match=re.escape(REJECTED_MESSAGE)):
        with rogue_tree.build_tree(CLASS):
            pass


def test_TPG_child_placement():
    """Observed, intent unconfirmed: TPGStatus and TPGSeqJump are both at 0x400."""
    declared = [(child.name, child.cls, child.offset) for child in read_child_devices(SOURCE)]
    expected = [(child.name, child.table, child.offset) for child in TABLE.CHILDREN]
    assert declared == expected
    assert TABLE.ROWS == ()
    shared = {offset: count for offset, count in Counter(o for _, _, o in declared).items() if count > 1}
    assert shared == {0x400: 2}
    assert sorted(name for name, _, offset in declared if offset == 0x400) == ["TPGSeqJump", "TPGStatus"]


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPG.py inherits the TPGStatus CountSeq overlap (and the other leaf overlaps), and also adds "
        "TPGStatus and TPGSeqJump both at 0x400, so Rogue rejects the tree; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_TPG_known_issue_overlap(rogue_build):
    """Fixing the leaf overlaps alone still leaves the 0x400 placement overlap.

    Measured on a copy of the package outside the repository: with the four
    leaf classes fixed, TPG still fails at root.start() because
    TPGSeqJump.StartAddr[0] at 0x400 overlaps TPGStatus.BsaStat[0] at 0x400.
    """
    _, device, _ = rogue_build(CLASS)
    assert "TPGSeqJump.StartAddr[0]" in rogue_tree.tree_variables(device)
