#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reproducers for the packaging and submodule lock findings.

Test methodology:
    Sweep: every tracked ruckus.tcl outside tests/ for the surf submodule
        lock, plus setup.py at the repository root.
    Stimulus: a regex read of the ruckus.tcl files; setup.py run only as a
        copy under tmp_path, either in a subprocess with its site packages
        disabled or through runpy with stubbed distutils and git modules.
        The real tree and the network are never touched.
    Checks: one gated reproducer per finding, each failing on the unmodified
        tree. The surf versions required by the ruckus.tcl files must agree;
        setup.py must import under the running interpreter; running setup.py
        must leave the package __init__.py unchanged.
    Timing: each subprocess has a 60 s timeout; no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import os
import re
import runpy
import subprocess
import sys
import types

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
        "known issue: the root ruckus.tcl requires surf 2.53.0 while LCLS-II/gtx7/ruckus.tcl "
        "requires surf 2.74.0; see https://github.com/slaclab/lcls-timing-core/issues/229; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_ruckus_known_issue_surf_locks_agree():
    surf = {key[0]: version for key, version in submodule_locks(REPO_ROOT).items() if key[1] == "surf"}
    assert len(set(surf.values())) == 1, "surf locks disagree: " + ", ".join(
        f"{path} requires {version}" for path, version in sorted(surf.items())
    )


@pytest.fixture(autouse=True)
def tracked_package_init_stays_clean():
    """Fail any test that leaves python/LclsTimingCore/__init__.py modified in the real tree."""
    yield
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", "python/LclsTimingCore/__init__.py"],
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, "a test modified the tracked python/LclsTimingCore/__init__.py"


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: setup.py imports distutils, which Python 3.12 removed; "
        "see https://github.com/slaclab/lcls-timing-core/issues/232; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_setup_known_issue_imports_on_python_312(tmp_path):
    (tmp_path / "setup.py").write_bytes((REPO_ROOT / "setup.py").read_bytes())
    result = subprocess.run(
        [sys.executable, "-S", "setup.py", "--version"],
        cwd=tmp_path,
        timeout=60,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "No module named 'distutils'" not in result.stderr, result.stderr.strip().splitlines()[-1]


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: setup.py appends __version__ to the tracked package __init__.py on every run; "
        "see https://github.com/slaclab/lcls-timing-core/issues/233; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_setup_known_issue_build_leaves_the_package_unchanged(tmp_path, monkeypatch):
    (tmp_path / "setup.py").write_bytes((REPO_ROOT / "setup.py").read_bytes())
    package = tmp_path / "python" / "LclsTimingCore"
    package.mkdir(parents=True)
    init = package / "__init__.py"
    init.write_bytes((REPO_ROOT / "python" / "LclsTimingCore" / "__init__.py").read_bytes())
    before = init.read_bytes()

    class Git:
        def describe(self, *args):
            return "v3.12.0-5-gabcdef0"

    class Repo:
        git = Git()

    distutils_stub = types.ModuleType("distutils")
    core_stub = types.ModuleType("distutils.core")
    core_stub.setup = lambda **kwargs: None
    distutils_stub.core = core_stub
    git_stub = types.ModuleType("git")
    git_stub.Repo = Repo
    monkeypatch.setitem(sys.modules, "distutils", distutils_stub)
    monkeypatch.setitem(sys.modules, "distutils.core", core_stub)
    monkeypatch.setitem(sys.modules, "git", git_stub)
    monkeypatch.chdir(tmp_path)

    for _ in range(2):
        runpy.run_path(str(tmp_path / "setup.py"), run_name="__main__")

    after = init.read_bytes()
    assert after == before, f"setup.py appended {len(after) - len(before)} bytes to the package __init__.py"
