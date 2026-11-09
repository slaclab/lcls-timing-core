#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""The --expect-known-issues pytest plugin in tests/common/known_issues.py.

Test methodology:
    Sweep: the option on and off, the environment variable set and unset, and
        a temporary tree with one reproducing gated test, one fixed gated
        test, one gated test whose reason starts with "open question:", and
        one plain test.
    Stimulus: a pytest subprocess per case, run as
        [sys.executable, "-m", "pytest", "-p", "tests.common.known_issues",
        "-p", "no:cacheprovider", "-c", <tmp>/pytest.ini, "--rootdir", <tmp>,
        "--confcutdir", <tmp>, "-rxX", ...] with cwd set to the temporary
        tree and PYTHONPATH set to the repository root, so the plugin loads
        without the cocotb setup of tests/conftest.py.
    Checks: a reproducing issue and the open question both report xfailed and
        the run exits 0; a fixed issue exits 1 with XPASS(strict) and its
        reason text; the option without the variable exits 4 with the usage
        message; without the option the gated tests skip and the plain test
        passes; selection follows the skipif mark, not the test name.
    Timing: each subprocess is bounded by its 120 s timeout.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_S = 120

REPRODUCING_URL = "https://github.com/slaclab/lcls-timing-core/issues/901"
FIXED_URL = "https://github.com/slaclab/lcls-timing-core/issues/902"

CASES = {
    "reproducing": (
        f'"known issue: still broken; see {REPRODUCING_URL}; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"',
        "assert False, 'still broken'",
    ),
    "fixed": (
        f'"known issue: already repaired; see {FIXED_URL}; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"',
        "assert True",
    ),
    "open_question": (
        '"open question: intent not confirmed; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"',
        "assert False, 'intent not confirmed'",
    ),
}


def write_tree(root, gated):
    """Write a temporary test tree holding the named gated tests and one plain test."""
    lines = [
        "import os",
        "import pytest",
        'SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"',
        "",
    ]
    for name in gated:
        reason, body = CASES[name]
        lines += [
            f"@pytest.mark.skipif(SKIP, reason={reason})",
            f"def test_{name}_known_issue():",
            f"    {body}",
            "",
        ]
    lines += ["def test_known_issue_lookalike():", "    assert True", ""]
    (root / "test_sample.py").write_text("\n".join(lines), encoding="utf-8")
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    return root


def run_pytest(root, *args, variable=None, summary=None):
    """Run pytest on the temporary tree and return the completed process."""
    env = {key: value for key, value in os.environ.items()
           if key not in ("RUN_KNOWN_ISSUE_TESTS", "GITHUB_STEP_SUMMARY", "PYTEST_ADDOPTS")}
    env["PYTHONPATH"] = str(REPO_ROOT)
    if variable is not None:
        env["RUN_KNOWN_ISSUE_TESTS"] = variable
    if summary is not None:
        env["GITHUB_STEP_SUMMARY"] = str(summary)
    command = [
        sys.executable, "-m", "pytest", "-p", "tests.common.known_issues", "-p", "no:cacheprovider",
        "-c", str(root / "pytest.ini"), "--rootdir", str(root), "--confcutdir", str(root), "-rxX", *args,
    ]
    return subprocess.run(
        command, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=TIMEOUT_S, check=False,
    )


def test_reproducing_issue_is_xfail_and_the_run_passes(tmp_path):
    write_tree(tmp_path, ["reproducing", "open_question"])
    result = run_pytest(tmp_path, "--expect-known-issues", variable="1")
    assert result.returncode == 0, result.stdout
    assert "2 xfailed" in result.stdout, result.stdout
    assert "1 deselected" in result.stdout, result.stdout


def test_fixed_issue_fails_naming_its_reason(tmp_path):
    write_tree(tmp_path, ["reproducing", "fixed"])
    result = run_pytest(tmp_path, "--expect-known-issues", variable="1")
    assert result.returncode == 1, result.stdout
    assert "XPASS(strict)" in result.stdout, result.stdout
    assert f"already repaired; see {FIXED_URL}" in result.stdout, result.stdout
    assert "1 xfailed" in result.stdout, result.stdout


def test_option_needs_the_environment_variable(tmp_path):
    write_tree(tmp_path, ["reproducing"])
    result = run_pytest(tmp_path, "--expect-known-issues")
    assert result.returncode == 4, result.stdout
    assert "--expect-known-issues needs RUN_KNOWN_ISSUE_TESTS=1" in result.stdout, result.stdout
    assert "passed" not in result.stdout and "skipped" not in result.stdout, result.stdout


def test_without_the_option_gated_tests_skip(tmp_path):
    write_tree(tmp_path, ["reproducing", "fixed", "open_question"])
    result = run_pytest(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "3 skipped" in result.stdout, result.stdout
    assert "1 passed" in result.stdout, result.stdout


def test_selection_uses_the_mark_not_the_name(tmp_path):
    write_tree(tmp_path, ["reproducing"])
    result = run_pytest(tmp_path, "--expect-known-issues", "-v", variable="1")
    assert result.returncode == 0, result.stdout
    assert "test_reproducing_known_issue XFAIL" in result.stdout, result.stdout
    assert "test_known_issue_lookalike" not in result.stdout, result.stdout
    assert "1 deselected" in result.stdout, result.stdout
