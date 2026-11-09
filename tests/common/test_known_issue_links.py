#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Every known-issue skip and every register drift allowlist entry links a filed issue.

Test methodology:
    Sweep: every tests/**/test_*.py module, each pytest.mark.skipif decorator
        in it, and every entry of ALLOWLIST in tests/common/register_drift.py.
    Stimulus: the test sources parsed with ast (never imported, so no
        simulator or Rogue is needed); implicitly concatenated string
        literals arrive as one constant.
    Checks: each skipif reason that starts with "known issue:" reads
        "known issue: <what>; see <slaclab/lcls-timing-core issue URL>; set
        RUN_KNOWN_ISSUE_TESTS=1 to reproduce"; a test named *known_issue*
        whose skipif reason is not a string literal fails, because its link
        cannot be read; and validate_allowlist accepts ALLOWLIST with
        require_filed=True, so no entry is left at the pending placeholder.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import ast
import re
from pathlib import Path

from tests.common import register_drift

TESTS_DIR = Path(__file__).resolve().parents[1]

KNOWN_ISSUE_PREFIX = "known issue:"
KNOWN_ISSUE_RE = re.compile(
    r"^known issue: .+; see https://github\.com/slaclab/lcls-timing-core/issues/\d+; "
    r"set RUN_KNOWN_ISSUE_TESTS=1 to reproduce$"
)


def _is_skipif(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "skipif"


def _skipif_reasons(tree):
    """Yield (test name, line, reason node) for every skipif reason keyword in a module."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not _is_skipif(decorator):
                continue
            for keyword in decorator.keywords:
                if keyword.arg == "reason":
                    yield node.name, keyword.value.lineno, keyword.value


def _collect():
    linked, problems = [], []
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        where = path.relative_to(TESTS_DIR.parent)
        for name, line, value in _skipif_reasons(tree):
            literal = isinstance(value, ast.Constant) and isinstance(value.value, str)
            if not literal:
                if "known_issue" in name:
                    problems.append(f"{where}:{line} {name}: skip reason is not a string literal")
                continue
            if not value.value.startswith(KNOWN_ISSUE_PREFIX):
                continue
            if KNOWN_ISSUE_RE.match(value.value):
                linked.append(f"{where}:{line}")
            else:
                problems.append(f"{where}:{line} {name}: {value.value!r}")
    return linked, problems


def test_known_issue_skip_reasons_link_filed_issues():
    linked, problems = _collect()
    assert linked, "no known-issue skip reason found under tests/"
    assert not problems, "known-issue skip reasons without a filed issue link:\n" + "\n".join(problems)


def test_allowlist_links_filed_issues():
    assert register_drift.REQUIRE_FILED_ISSUES
    assert register_drift.PENDING_ISSUE not in register_drift.ALLOWLIST.values()
    register_drift.validate_allowlist(register_drift.ALLOWLIST, require_filed=True)
