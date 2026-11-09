#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""RTL files that no ruckus.tcl loads: an exact baseline, with a gated test that wants none left.

Test methodology:
    Sweep: every tracked .vhd and .v file under LCLS-I and LCLS-II outside
        the wrappers directories (68 at the time of writing), compared with
        the files named by the loadSource -path and -dir lines of every
        tracked ruckus.tcl outside tests/.
    Stimulus: text parsing of the ruckus.tcl files and git ls-files, no
        simulator and no Vivado.
    Checks: the set of unloaded files equals the keys of UNLOADED_SOURCES in
        both directions, naming the new or the vanished path; every reason
        is a plain ASCII sentence; the issue is a filed
        slaclab/lcls-timing-core issue URL or pending; and the gated test
        asserts that no unloaded file remains, which fails today.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import os

import pytest

from tests.common.register_drift import ISSUE_URL_RE, PENDING_ISSUE
from tests.common.regression_utils import REPO_ROOT
from tests.common.source_inventory import (
    UNLOADED_SOURCES,
    UNLOADED_SOURCES_ISSUE,
    unloaded_sources,
)

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"


def test_unloaded_sources_are_exact():
    found = unloaded_sources(REPO_ROOT)
    recorded = set(UNLOADED_SOURCES)
    new = sorted(found - recorded)
    vanished = sorted(recorded - found)
    assert not new, f"RTL files that no ruckus.tcl loads and UNLOADED_SOURCES does not list: {new}"
    assert not vanished, f"UNLOADED_SOURCES lists files that are now loaded or gone: {vanished}"
    assert len(recorded) == 8


def test_unloaded_reasons_are_plain_ascii():
    for path, reason in UNLOADED_SOURCES.items():
        assert reason.strip() == reason and reason, f"{path}: empty or padded reason"
        assert reason.isascii(), f"{path}: reason is not ASCII"
        assert "\n" not in reason, f"{path}: reason spans lines"
        assert not reason.endswith("."), f"{path}: reason is a phrase, without a final period"


def test_unloaded_issue_is_a_link_or_pending():
    assert UNLOADED_SOURCES_ISSUE == PENDING_ISSUE or ISSUE_URL_RE.match(UNLOADED_SOURCES_ISSUE), (
        f"UNLOADED_SOURCES_ISSUE is neither an issue URL nor {PENDING_ISSUE!r}: {UNLOADED_SOURCES_ISSUE!r}"
    )


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "pending issue: eight RTL files are loaded by no ruckus.tcl, and BsaControl.vhd declares the "
        "same entity as the loaded BsaControlv2.vhd; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_unloaded_sources_known_issue_every_rtl_file_is_loaded():
    found = sorted(unloaded_sources(REPO_ROOT))
    assert not found, f"{len(found)} RTL files are loaded by no ruckus.tcl: " + ", ".join(found)
