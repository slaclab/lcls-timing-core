#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Unit tests for the text and vsg lint checks in lint_checks.py.

Test methodology:
    Sweep: one temporary git repository per case, holding the smallest set
        of .vhd, .tcl, and .py files that exercises a single rule or edge
        (trailing blanks, raw non-ASCII bytes, tabs, the three exempt
        paths and their near misses, CRLF endings, empty scans).
    Stimulus: lint_checks.main() is called with a repo_root override on
        each temporary repository and once on the real repository with
        untracked files included.
    Checks: exit codes (0 clean, 1 findings, 2 nothing scanned), the
        printed path:line: rule: detail lines and their order, the scanned
        file count, and that a run leaves file contents and mtimes alone.
    Timing: none, the checks are pure file scans (no simulator).
"""

import subprocess
from pathlib import Path

from tests.common import lint_checks

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
       "-c", "commit.gpgsign=false"]

TAB_EXEMPT_PATH = "LCLS-II/core/rtl/TPGMiniStream.vhd"


def make_repo(tmp_path, files):
    """Create a git repository at tmp_path holding the given raw files."""
    subprocess.run(GIT + ["init", "-q", str(tmp_path)], check=True)
    for name, data in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    subprocess.run(GIT + ["add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def run_text(repo, capsys, *flags):
    code = lint_checks.main([*flags, "text"], repo_root=repo)
    return code, capsys.readouterr().out


def test_trailing_whitespace_is_reported_sorted_by_path(tmp_path, capsys):
    repo = make_repo(tmp_path, {
        "b.tcl": b"set a 1\t\nset b 2\n",
        "a.vhd": b"entity a is\nend a; \n",
        "c.py": b"x = 1\n",
    })
    code, out = run_text(repo, capsys)
    lines = out.splitlines()
    trailing = [x for x in lines if "trailing-whitespace" in x]
    assert code == 1
    assert trailing[0].startswith("a.vhd:2: trailing-whitespace")
    assert trailing[1].startswith("b.tcl:1: trailing-whitespace")
    # a trailing tab is also a tab, so b.tcl carries two findings
    assert lines[-1] == "3 file(s) scanned, 3 finding(s)"


def test_non_ascii_is_reported_for_vhd_only_on_raw_bytes(tmp_path, capsys):
    payload = b"-- dash \xe2\x80\x94 end\n-- bad \xff byte\n"
    repo = make_repo(tmp_path, {"a.vhd": payload, "b.py": payload})
    code, out = run_text(repo, capsys)
    non_ascii = [x for x in out.splitlines() if "non-ascii" in x]
    assert code == 1
    assert len(non_ascii) == 2
    assert non_ascii[0].startswith("a.vhd:1: non-ascii")
    assert non_ascii[1].startswith("a.vhd:2: non-ascii")
    assert not any(x.startswith("b.py") for x in out.splitlines())


def test_tab_is_reported_outside_the_exempt_files(tmp_path, capsys):
    repo = make_repo(tmp_path, {"tests/x.py": b"if True:\n\tpass\n"})
    code, out = run_text(repo, capsys)
    assert code == 1
    assert "tests/x.py:2: tab" in out


def test_tab_in_exact_exempt_path_is_not_reported(tmp_path, capsys):
    repo = make_repo(tmp_path, {TAB_EXEMPT_PATH: b"a\tb\n"})
    code, out = run_text(repo, capsys)
    assert code == 0
    assert "1 file(s) scanned, 0 finding(s)" in out


def test_tab_exemption_does_not_cover_near_misses(tmp_path, capsys):
    near = [
        "LCLS-II/core/rtl/TPGMiniStream2.vhd",
        "tests/TPGMiniStream.vhd",
        "LCLS-II/core/rtl/tpgministream.vhd",
    ]
    repo = make_repo(tmp_path, {name: b"a\tb\n" for name in near})
    code, out = run_text(repo, capsys)
    assert code == 1
    for name in near:
        assert "%s:1: tab" % name in out


def test_tab_exempt_set_is_exactly_the_three_production_files():
    assert lint_checks.TAB_EXEMPT == frozenset({
        "LCLS-II/core/rtl/TPGMiniEdefTb.vhd",
        "LCLS-II/core/rtl/TPGMiniStream.vhd",
        "LCLS-II/core/rtl/TimingSerialDelay.vhd",
    })


def test_crlf_alone_is_not_trailing_whitespace(tmp_path, capsys):
    repo = make_repo(tmp_path, {
        "a.vhd": b"entity a is\r\nend a;\r\n",
        "b.vhd": b"entity b is \r\nend b;\r\n",
    })
    code, out = run_text(repo, capsys)
    assert code == 1
    findings = [x for x in out.splitlines() if "trailing-whitespace" in x]
    assert findings == ["b.vhd:1: trailing-whitespace: line ends in a blank"]


def test_final_line_without_newline_is_still_checked(tmp_path, capsys):
    repo = make_repo(tmp_path, {"a.py": b"x = 1\ny = 2 "})
    code, out = run_text(repo, capsys)
    assert code == 1
    assert "a.py:2: trailing-whitespace" in out


def test_no_matching_files_exits_2_naming_the_pathspecs(tmp_path, capsys):
    repo = make_repo(tmp_path, {"README.md": b"hello\n"})
    code, out = run_text(repo, capsys)
    assert code == 2
    assert "no files matched" in out
    assert "*.vhd" in out and "*.tcl" in out and "*.py" in out


def test_vsg_without_new_vhdl_exits_2(tmp_path, capsys):
    repo = make_repo(tmp_path, {"LCLS-II/core/rtl/a.vhd": b"entity a is\n"})
    code = lint_checks.main(["vsg"], repo_root=repo)
    assert code == 2
    assert "no files matched" in capsys.readouterr().out


def test_untracked_files_need_the_include_flag(tmp_path, capsys):
    repo = make_repo(tmp_path, {"a.py": b"x = 1\n"})
    (repo / "b.py").write_bytes(b"y = 2 \n")
    code, _ = run_text(repo, capsys)
    assert code == 0
    code, out = run_text(repo, capsys, "--include-untracked")
    assert code == 1
    assert "b.py:1: trailing-whitespace" in out


def test_text_run_writes_nothing(tmp_path, capsys):
    repo = make_repo(tmp_path, {"a.vhd": b"a \n", "b.py": b"x = 1\n"})

    def snapshot():
        out = {}
        for path in sorted(repo.rglob("*")):
            if ".git" in path.relative_to(repo).parts:
                continue
            out[str(path)] = (path.read_bytes() if path.is_file() else None,
                              path.stat().st_mtime_ns)
        return out

    before = snapshot()
    run_text(repo, capsys)
    run_text(repo, capsys)
    assert snapshot() == before


def test_real_repository_has_no_text_findings(capsys):
    root = Path(lint_checks.REPO_ROOT)
    assert (root / "LCLS-II").is_dir()
    code = lint_checks.main(["--include-untracked", "text"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert out.strip().splitlines()[-1].endswith(", 0 finding(s)")
