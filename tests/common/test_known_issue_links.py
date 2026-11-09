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
        in it, every entry of ALLOWLIST in tests/common/register_drift.py, and
        the three issue link sources (KNOWN_GHDL_ISSUES, UNLOADED_SOURCES_ISSUE,
        docs/_data/header_issues.yaml).
    Stimulus: the test sources parsed with ast (never imported, so no
        simulator or Rogue is needed); implicitly concatenated string
        literals arrive as one constant.
    Checks: each skipif reason that starts with "known issue:" reads
        "known issue: <what>; see <slaclab/lcls-timing-core issue URL>; set
        RUN_KNOWN_ISSUE_TESTS=1 to reproduce"; a test named *known_issue*
        whose skipif reason is not a string literal fails, because its link
        cannot be read; validate_allowlist accepts ALLOWLIST with
        require_filed=True, so no entry is left at the pending placeholder;
        no skipif reason starts with "pending issue:"; every value of
        KNOWN_GHDL_ISSUES, UNLOADED_SOURCES_ISSUE, and the header_issues.yaml
        issue fields is an issue URL; no generated page says "issue pending";
        and the GHDL baseline links exactly five distinct issues, one per root
        cause.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import ast
import re
from pathlib import Path

from tests.common import gen_docs, ghdl_analysis, register_drift, source_inventory

TESTS_DIR = Path(__file__).resolve().parents[1]

KNOWN_ISSUE_PREFIX = "known issue:"
PENDING_PREFIX = "pending issue:"
EXPECTED_GHDL_ROOT_CAUSES = 5
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


def test_no_pending_issue_link_remains():
    pending_reasons = []
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, line, value in _skipif_reasons(tree):
            if isinstance(value, ast.Constant) and str(value.value).startswith(PENDING_PREFIX):
                pending_reasons.append(f"{path.relative_to(TESTS_DIR.parent)}:{line} {name}")
    assert not pending_reasons, "skip reasons still pending an issue:\n" + "\n".join(pending_reasons)

    sources = {
        **{f"KNOWN_GHDL_ISSUES[{key!r}]": url for key, url in ghdl_analysis.KNOWN_GHDL_ISSUES.items()},
        "UNLOADED_SOURCES_ISSUE": source_inventory.UNLOADED_SOURCES_ISSUE,
        **{
            f"header_issues.yaml {path}": entry["issue"]
            for path, entry in gen_docs.load_sidecar("header_issues.yaml").items()
        },
    }
    unlinked = [f"{where}: {url!r}" for where, url in sources.items() if not register_drift.ISSUE_URL_RE.match(url)]
    assert not unlinked, "issue values that are not filed issue URLs:\n" + "\n".join(unlinked)

    pages = gen_docs.render_all()
    pending_pages = [path for path, text in pages.items() if "issue pending" in text]
    assert not pending_pages, f"generated pages that still say 'issue pending': {pending_pages}"


def test_ghdl_baseline_links_one_issue_per_root_cause():
    urls = set(ghdl_analysis.KNOWN_GHDL_ISSUES.values())
    assert len(urls) == EXPECTED_GHDL_ROOT_CAUSES, sorted(urls)
