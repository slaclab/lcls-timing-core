#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reproducers for the release tooling, packaging, and submodule lock findings.

Test methodology:
    Sweep: every tracked ruckus.tcl outside tests/ for the surf submodule
        lock, plus releaseNotes.py and setup.py at the repository root.
    Stimulus: a regex read of the ruckus.tcl files; releaseNotes.py run
        through runpy under stubbed git, github, and pyperclip modules and a
        patched input(); setup.py run only as a copy under tmp_path, either
        in a subprocess with its site packages disabled or through runpy with
        stubbed distutils and git modules. The real tree and the network are
        never touched.
    Checks: one gated reproducer per finding, each failing on the unmodified
        tree. The surf versions required by the ruckus.tcl files must agree;
        a pull request with no description must not crash the release notes;
        an https origin URL must reach the GitHub API as owner/repository;
        setup.py must import under the running interpreter; running setup.py
        must leave the package __init__.py unchanged. One ungated test proves
        the release notes harness itself works with an ssh remote.
    Timing: each subprocess has a 60 s timeout; no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import os
import re

import pytest

from tests.common import source_inventory
from tests.common.regression_utils import REPO_ROOT

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

LOCK_RE = re.compile(r"SubmoduleCheck\s+\{(\w+)\}\s+\{([\d.]+)\}")


def submodule_locks(repo_root):
    """Return {(repo-relative ruckus.tcl, submodule name): version} for every lock line."""
    locks = {}
    for rel in source_inventory.repo_ruckus_files(repo_root):
        text = (repo_root / rel).read_text(encoding="utf-8")
        for name, version in LOCK_RE.findall(text):
            locks[(rel, name)] = version
    return locks


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "pending issue: the root ruckus.tcl requires surf 2.53.0 while LCLS-II/gtx7/ruckus.tcl "
        "requires surf 2.74.0; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_ruckus_known_issue_surf_locks_agree():
    surf = {key[0]: version for key, version in submodule_locks(REPO_ROOT).items() if key[1] == "surf"}
    assert len(set(surf.values())) == 1, "surf locks disagree: " + ", ".join(
        f"{path} requires {version}" for path, version in sorted(surf.items())
    )
