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
import runpy
import subprocess
import sys
import types

import pytest

from tests.common import source_inventory
from tests.common.regression_utils import REPO_ROOT

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

SSH_REMOTE = "git@github.com:slaclab/lcls-timing-core.git"
HTTPS_REMOTE = "https://github.com/slaclab/lcls-timing-core.git"
LOG_RECORD = "Author: Example Author\nDate: Mon Jan 1 00:00:00 2024\n    Merge pull request #5 from slaclab/example\n"

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


@pytest.fixture
def release_notes(monkeypatch, capsys):
    """Return run(remote_url, pr_body) -> (repository name passed to get_repo, stdout).

    releaseNotes.py parses arguments, asks for a token, and talks to git and
    GitHub at import time, so it is run through runpy with stub modules and a
    patched input(). Nothing leaves the process.
    """

    def run(remote_url, pr_body):
        seen = {}

        class Pull:
            title = "Example"
            body = pr_body
            additions = 1
            deletions = 2
            changed_files = 1

        class Repo:
            def get_pull(self, number):
                return Pull()

        class Github:
            def __init__(self, token):
                seen["token"] = token

            def get_repo(self, name):
                seen["repo"] = name
                return Repo()

        class Git:
            def __init__(self, path):
                pass

            def fetch(self):
                pass

            def remote(self, *args):
                return remote_url

            def log(self, *args):
                return LOG_RECORD

        git_stub = types.ModuleType("git")
        git_stub.Git = Git
        github_stub = types.ModuleType("github")
        github_stub.Github = Github
        clipboard_stub = types.ModuleType("pyperclip")
        clipboard_stub.copy = lambda text: None
        monkeypatch.setitem(sys.modules, "git", git_stub)
        monkeypatch.setitem(sys.modules, "github", github_stub)
        monkeypatch.setitem(sys.modules, "pyperclip", clipboard_stub)
        monkeypatch.setattr("builtins.input", lambda prompt="": "not-a-real-token")
        monkeypatch.setattr(sys, "argv", ["releaseNotes.py", "v1.0.0"])
        runpy.run_path(str(REPO_ROOT / "releaseNotes.py"), run_name="__main__")
        return seen["repo"], capsys.readouterr().out

    return run


def test_release_notes_harness_runs_with_an_ssh_remote(release_notes):
    repo, out = release_notes(SSH_REMOTE, "notes")
    assert repo == "slaclab/lcls-timing-core"
    assert "Example" in out
    assert "> notes" in out


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "pending issue: releaseNotes.py raises AttributeError on a pull request with no description; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_release_notes_known_issue_pull_request_without_description(release_notes):
    _, out = release_notes(SSH_REMOTE, None)
    assert "Example" in out


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "pending issue: releaseNotes.py turns an https origin URL into ps://github.com/slaclab/lcls-timing-core; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_release_notes_known_issue_https_remote(release_notes):
    repo, _ = release_notes(HTTPS_REMOTE, "notes")
    assert repo == "slaclab/lcls-timing-core"


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "pending issue: setup.py imports distutils, which Python 3.12 removed; "
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
        "pending issue: setup.py appends __version__ to the tracked package __init__.py on every run; "
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
