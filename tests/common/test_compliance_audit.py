#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Unit tests for the warn-only regression compliance audit.

Test methodology:
    Sweep: one small Python source string (or temporary directory tree)
        per audit rule, covering the firing form and the compliant form of
        the same construct (methodology block, cocotb timeout, skip
        reason, direct simulator launch, loop and task ownership).
    Stimulus: compliance_audit.audit_source() on the source text, and
        compliance_audit.main() on temporary trees with an explicit
        repo_root so the real repository is never audited.
    Checks: the rule ids reported, finding de-duplication keys, sorted and
        byte-identical output across runs, the files-audited count, exit
        code 0 for every audit (warn-only) and 2 for a missing path, and
        that auditing leaves the audited tree unchanged.
    Timing: none, the audit only parses source text (no simulator).
"""

import json
from pathlib import Path

import pytest

from tests.common import compliance_audit as audit

METHODOLOGY = '"""Doc.\n\nTest methodology:\n    Sweep: none.\n"""\n'


def rules(source, path="tests/lcls2_core/test_x.py"):
    findings = audit.audit_source(
        source, path, repo_root=Path("/nonexistent"),
        imported_sources=frozenset())
    return [f.rule for f in findings]


def test_test_file_without_methodology_is_reported():
    assert rules("def test_a():\n    pass\n") == ["missing-methodology"]


def test_test_file_with_methodology_is_not_reported():
    assert rules(METHODOLOGY + "def test_a():\n    pass\n") == []


def test_cocotb_file_without_methodology_is_reported_once():
    source = ("import cocotb\n\n\n"
              "@cocotb.test(timeout_time=1, timeout_unit='us')\n"
              "async def check(dut):\n    pass\n")
    assert rules(source) == ["missing-methodology"]


def test_cocotb_test_without_timeout_is_reported():
    source = (METHODOLOGY + "import cocotb\n\n\n"
              "@cocotb.test()\nasync def check(dut):\n    pass\n\n\n"
              "@cocotb.test(timeout_time=5, timeout_unit='us')\n"
              "async def bounded(dut):\n    pass\n")
    findings = audit.audit_source(
        source, "tests/lcls2_core/test_x.py",
        repo_root=Path("/nonexistent"), imported_sources=frozenset())
    assert [(f.rule, f.symbol) for f in findings] == [
        ("cocotb-test-no-timeout", "check")]


@pytest.mark.parametrize("snippet", [
    "@pytest.mark.skip\ndef test_a():\n    pass\n",
    "@pytest.mark.skip()\ndef test_a():\n    pass\n",
    "@pytest.mark.skipif(True)\ndef test_a():\n    pass\n",
    "def test_a():\n    pytest.skip()\n",
    "def test_a():\n    pytest.importorskip('x')\n",
])
def test_skip_without_reason_is_reported(snippet):
    source = METHODOLOGY + "import pytest\n\n\n" + snippet
    assert rules(source) == ["skip-without-reason"]


@pytest.mark.parametrize("snippet", [
    "@pytest.mark.skip(reason='r')\ndef test_a():\n    pass\n",
    "@pytest.mark.skip('r')\ndef test_a():\n    pass\n",
    "@pytest.mark.skipif(True, reason='r')\ndef test_a():\n    pass\n",
    "def test_a():\n    pytest.skip('r')\n",
    "def test_a():\n    pytest.skip(reason='r')\n",
    "def test_a():\n    pytest.importorskip('x', reason='r')\n",
])
def test_skip_with_reason_is_not_reported(snippet):
    source = METHODOLOGY + "import pytest\n\n\n" + snippet
    assert rules(source) == []


DIRECT = ("from cocotb_test.simulator import run\n\n\n"
          "def test_a():\n    run(toplevel='x')\n")


def test_direct_runner_is_reported_and_names_the_shared_runner():
    source = METHODOLOGY + DIRECT
    findings = audit.audit_source(
        source, "tests/lcls2_core/test_x.py",
        repo_root=Path("/nonexistent"), imported_sources=frozenset())
    assert [f.rule for f in findings] == ["direct-runner"]
    assert "run_lcls_vhdl_test()" in findings[0].detail


def test_direct_runner_is_allowed_in_the_shared_runner_only():
    assert audit.DOCUMENTED_DIRECT_RUNNERS == {
        "tests/common/regression_utils.py"}
    assert rules(METHODOLOGY + DIRECT, "tests/common/regression_utils.py") == []


def test_two_rules_on_one_line_stay_two_findings():
    source = (METHODOLOGY + "import cocotb\n\n\n"
              "@cocotb.test(timeout_time=5, timeout_unit='us')\n"
              "async def check(dut):\n"
              "    while True: cocotb.start_soon(dut.work())\n")
    found = rules(source)
    assert sorted(found) == ["open-ended-loop", "unretained-start-soon"]


def test_findings_dedupe_only_on_rule_path_line_and_symbol():
    first = audit.Finding("r", "p", 1, "s", "one")
    second = audit.Finding("r", "p", 1, "s", "two")
    other = audit.Finding("r", "p", 1, "t", "one")
    assert len(audit.dedupe_findings([first, second, other])) == 2


def make_tree(root, files):
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def test_audit_exits_zero_with_findings_and_reports_the_file_count(
        tmp_path, capsys):
    make_tree(tmp_path, {
        "tests/test_a.py": "def test_a():\n    pass\n",
        "tests/test_b.py": METHODOLOGY + "def test_b():\n    pass\n",
    })
    code = audit.main(["audit", "tests"], repo_root=tmp_path)
    out = capsys.readouterr().out
    assert code == 0
    assert "tests/test_a.py:1: missing-methodology" in out
    assert "2 file(s) audited" in out


def test_audit_of_an_empty_directory_reports_zero_files(tmp_path, capsys):
    (tmp_path / "tests").mkdir()
    code = audit.main(["audit", "tests"], repo_root=tmp_path)
    out = capsys.readouterr().out
    assert code == 0
    assert "0 file(s) audited" in out


def test_audit_of_a_missing_path_exits_2_naming_the_path(tmp_path, capsys):
    with pytest.raises(SystemExit) as raised:
        audit.main(["audit", "does-not-exist"], repo_root=tmp_path)
    assert raised.value.code == 2
    assert "does-not-exist" in capsys.readouterr().err


def test_json_output_is_identical_across_runs_and_sorted(tmp_path, capsys):
    make_tree(tmp_path, {
        "tests/test_b.py": "def test_b():\n    pass\n",
        "tests/test_a.py": "def test_a():\n    pass\n",
    })
    audit.main(["audit", "tests", "--json"], repo_root=tmp_path)
    first = capsys.readouterr().out
    audit.main(["audit", "tests", "--json"], repo_root=tmp_path)
    second = capsys.readouterr().out
    assert first == second
    report = json.loads(first)
    assert report["files_audited"] == 2
    keys = [(f["rule"], f["path"], f["line"], f["symbol"], f["detail"])
            for f in report["findings"]]
    assert keys == sorted(keys)


def test_audit_does_not_modify_the_audited_tree(tmp_path, capsys):
    make_tree(tmp_path, {"tests/test_a.py": "def test_a():\n    pass\n"})

    def snapshot():
        return {str(p): (p.read_bytes() if p.is_file() else None,
                         p.stat().st_mtime_ns)
                for p in sorted(tmp_path.rglob("*"))}

    before = snapshot()
    audit.main(["audit", "tests"], repo_root=tmp_path)
    audit.main(["audit", "tests", "--json"], repo_root=tmp_path)
    capsys.readouterr()
    assert snapshot() == before
