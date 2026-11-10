#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Tests of the production-bytes guard classifier and pull request CLI.

Test methodology:
    Sweep: a table of protected and unprotected paths for the classifier, and
        a set of temporary git repositories for the diff and exit status
        behavior.
    Stimulus: is_protected on each path; main() and the script run as a
        subprocess against temporary repositories whose head commit adds,
        deletes, modifies, or renames files; malformed base and head values.
    Checks: exit status 0, 1, or 2; one ::error line per offending path with
        its A, D, or M status in path order; the bypass label named in the
        failure summary; percent, CR, and LF escaped in workflow commands;
        the script working from a copy placed outside the repository.
    Timing: no simulator and no clocks. Temporary repositories are created
        under tmp_path with a fixed identity, so no user git configuration is
        read for author data.
"""

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.common import production_guard
from tests.common.production_guard import (
    BYPASS_LABEL,
    changed_paths,
    escape_workflow_data,
    is_protected,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_FILE = Path(production_guard.__file__).resolve()

PROTECTED_PATHS = [
    "LCLS-II/core/rtl/Divider.vhd",
    "LCLS-II/core/rtl/default/TimingExtnPkg.vhd",
    "LCLS-I/evr/EvrV1TimeStampGenerator.v",
    "LCLS-II/evr/tb/EvrV2_tb.vhd",
    "newdir/New.vhd",
    "LCLS-II/core/rtl/Foo.VHD",
    "LCLS-II/core/rtl/Foo.Vhd",
    "LCLS-I/evr/Upper.V",
    "wrappers/Top.vhd",
    "LCLS-II/tests/x.vhd",
    "LCLS-II/gthUltraScale/coregen/2025.1/TimingGth_fixedlat.xci",
    "LCLS-II/gtyUltraScale+/coregen/x.dcp",
    "coregen/x.xci",
    "python/LclsTimingCore/__init__.py",
    "python/LclsTimingCore/TPG.py",
    "python/LclsTimingCore/sub/Deep.py",
    "yaml/TPG.yaml",
    "yaml/sub/EvrV2Core.yaml",
    "LCLS-II/ruckus.tcl",
    "LCLS-II/core/ruckus.tcl",
    "LCLS-II/core/wrappers/ruckus.tcl",
    "LCLS-I/ruckus.tcl",
    "docs/ruckus.tcl",
]

UNPROTECTED_PATHS = [
    "ruckus.tcl",
    "Makefile",
    "setup.py",
    "conda-recipe/meta.yaml",
    "releaseNotes.py",
    ".github/workflows/timing_ci.yml",
    "tests/ghdl/ruckus.tcl",
    "tests/common/assert_level_fail.vhd",
    "tests/a.vhd",
    "tests/lcls2_core/test_Divider.py",
    "LCLS-II/core/wrappers/WordSerializerWrapper.vhd",
    "LCLS-II/core/wrappers/sub/Deep.vhd",
    "LCLS-I/wrappers/EvrV1RegWrapper.vhd",
    "python/other/x.py",
    "LCLS-II/core/rtl/notes.txt",
    "LCLS-II/core/rtl/header.vh",
    "LCLS-II/core/rtl/top.sv",
    "LCLS-II/core/rtl/old.vhdl",
    "docs/index.rst",
    "README.md",
]

GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@example.invalid",
          "-c", "commit.gpgsign=false"]


def git(cwd, *args):
    result = subprocess.run(
        ["git", *GIT_ID, *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def write(root, relpath, text):
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A temporary repository with a base commit, as the current directory."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    write(root, "LCLS-II/core/rtl/Divider.vhd", "entity Divider is end;\n")
    write(root, "LCLS-II/core/rtl/WordSerializer.vhd", "entity WS is end;\n")
    write(root, "yaml/TPG.yaml", "TPG: {}\n")
    write(root, "ruckus.tcl", "# root\n")
    write(root, "Makefile", "all:\n")
    write(root, "tests/keep.txt", "keep\n")
    base = commit_all(root, "base")
    monkeypatch.chdir(root)
    monkeypatch.delenv("BASE_SHA", raising=False)
    monkeypatch.delenv("HEAD_SHA", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return root, base


@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_protected_paths_are_protected(path):
    assert is_protected(path)


@pytest.mark.parametrize("path", UNPROTECTED_PATHS)
def test_other_paths_are_not_protected(path):
    assert not is_protected(path)


def test_escape_workflow_data_escapes_percent_cr_and_lf():
    assert escape_workflow_data("a%b\r\nc") == "a%25b%0D%0Ac"


def test_escape_workflow_data_escapes_percent_first():
    assert escape_workflow_data("%0A") == "%250A"


def test_mixed_change_lists_every_violation_in_path_order(repo, capsys):
    root, base = repo
    write(root, "LCLS-II/core/rtl/Divider.vhd", "entity Divider is end; --\n")
    (root / "LCLS-II/core/rtl/WordSerializer.vhd").rename(
        root / "LCLS-II/core/rtl/WordSerializer2.vhd")
    (root / "yaml/TPG.yaml").unlink()
    write(root, "LCLS-II/core/wrappers/NewWrapper.vhd", "-- wrapper\n")
    write(root, "tests/a.vhd", "-- test\n")
    write(root, "ruckus.tcl", "# root edited\n")
    write(root, "Makefile", "all:\n\t@true\n")
    head = commit_all(root, "head")

    assert main(["--base", base, "--head", head]) == 1

    out = capsys.readouterr().out
    errors = [line for line in out.splitlines() if line.startswith("::error")]
    assert [line.split("::")[-1] for line in errors] == [
        "LCLS-II/core/rtl/Divider.vhd (M)",
        "LCLS-II/core/rtl/WordSerializer.vhd (D)",
        "LCLS-II/core/rtl/WordSerializer2.vhd (A)",
        "yaml/TPG.yaml (D)",
    ]
    assert "4 protected path(s) changed" in out
    assert BYPASS_LABEL in out


def test_unprotected_change_passes(repo, capsys):
    root, base = repo
    write(root, "tests/a.vhd", "-- test\n")
    write(root, "LCLS-II/core/wrappers/NewWrapper.vhd", "-- wrapper\n")
    write(root, "ruckus.tcl", "# root edited\n")
    write(root, "Makefile", "all:\n\t@true\n")
    head = commit_all(root, "head")

    assert main(["--base", base, "--head", head]) == 0

    out = capsys.readouterr().out
    assert "::error" not in out
    assert "No protected paths changed (4 file(s) changed)" in out


def test_empty_diff_passes(repo, capsys):
    _, base = repo

    assert main(["--base", base, "--head", base]) == 0

    assert "No protected paths changed (0 file(s) changed)" in (
        capsys.readouterr().out)


def test_changed_paths_reports_rename_as_delete_and_add(repo):
    root, base = repo
    (root / "LCLS-II/core/rtl/WordSerializer.vhd").rename(
        root / "LCLS-II/core/rtl/Moved.vhd")
    head = commit_all(root, "head")

    assert sorted(changed_paths(base, head)) == [
        ("A", "LCLS-II/core/rtl/Moved.vhd"),
        ("D", "LCLS-II/core/rtl/WordSerializer.vhd"),
    ]


def test_workflow_command_characters_in_a_path_are_escaped(repo, capsys):
    root, base = repo
    write(root, "LCLS-II/core/rtl/we%ird\nname.vhd", "-- odd\n")
    head = commit_all(root, "head")

    assert main(["--base", base, "--head", head]) == 1

    out = capsys.readouterr().out
    errors = [line for line in out.splitlines() if line.startswith("::error")]
    assert len(errors) == 1
    assert "we%25ird%0Aname.vhd (A)" in errors[0]


def test_step_summary_is_appended_not_truncated(repo, tmp_path, monkeypatch):
    root, base = repo
    summary = tmp_path / "summary.md"
    summary.write_text("earlier content\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    write(root, "yaml/TPG.yaml", "TPG: {a: 1}\n")
    head = commit_all(root, "head")

    assert main(["--base", base, "--head", head]) == 1

    text = summary.read_text()
    assert text.startswith("earlier content\n")
    assert "yaml/TPG.yaml" in text
    assert BYPASS_LABEL in text


@pytest.mark.parametrize("argv", [
    [],
    ["--base", "abc1234"],
    ["--head", "abc1234"],
    ["--base", "HEAD~1", "--head", "abc1234"],
    ["--base", "abc1234", "--head", "HEAD"],
    ["--base", "--output=x", "--head", "abc1234"],
    ["--base=--output=x", "--head", "abc1234"],
    ["--base", "nothex", "--head", "abc1234"],
    ["--base", "ABC1234", "--head", "abc1234"],
    ["--base", "abc123", "--head", "abc1234"],
    ["--base", "a" * 41, "--head", "abc1234"],
    ["--base", "", "--head", "abc1234"],
])
def test_bad_arguments_exit_2(repo, argv, capsys):
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert "::error" not in captured.out


def test_environment_supplies_base_and_head(repo, monkeypatch, capsys):
    _, base = repo
    monkeypatch.setenv("BASE_SHA", base)
    monkeypatch.setenv("HEAD_SHA", base)

    assert main([]) == 0

    assert "0 file(s) changed" in capsys.readouterr().out


def test_unknown_commit_exits_2_with_git_error(repo, capsys):
    assert main(["--base", "deadbeef", "--head", "deadbeef"]) == 2

    assert capsys.readouterr().err.strip()


def test_script_runs_from_a_copy_outside_the_repository(repo, tmp_path):
    root, base = repo
    write(root, "LCLS-II/core/rtl/Divider.vhd", "entity Divider is end; --\n")
    head = commit_all(root, "head")
    copy_dir = tmp_path / "elsewhere"
    copy_dir.mkdir()
    copy = copy_dir / "production_guard.py"
    shutil.copyfile(GUARD_FILE, copy)

    result = subprocess.run(
        [sys.executable, "-I", str(copy), "--base", base, "--head", head],
        cwd=root, capture_output=True, text=True,
    )

    assert result.returncode == 1
    assert "LCLS-II/core/rtl/Divider.vhd (M)" in result.stdout


def test_script_rejects_a_bad_sha_from_the_command_line(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", str(GUARD_FILE),
         "--base", "nothex", "--head", "abc1234"],
        cwd=tmp_path, capture_output=True, text=True,
    )

    assert result.returncode == 2


def test_guard_imports_only_the_standard_library():
    tree = ast.parse(GUARD_FILE.read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import in the guard"
            modules.add((node.module or "").split(".")[0])

    assert modules
    assert modules <= set(sys.stdlib_module_names)


def test_guard_never_reads_its_own_location():
    assert "__file__" not in GUARD_FILE.read_text()
