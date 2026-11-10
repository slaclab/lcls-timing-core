#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Tests of the ordered tool version table written to the job summary.

Test methodology:
    Sweep: item order, repeated and unknown items, the empty item list, a
        failing or missing tool, an empty or malformed SHA, a summary file
        that already holds text, and the local-clone and remote-dependency
        modes for surf and ruckus.
    Stimulus: tool_versions.main() with resolvers or the one command helper
        replaced by fakes, temporary git repositories for the local clone
        mode, and GITHUB_STEP_SUMMARY and GITHUB_JOB set or removed.
    Checks: exit status 0, 1, or 2; the data rows in command-line order; the
        item named when a tool cannot be resolved; the summary file gaining
        a table per call without losing earlier text; the exact ls-remote
        command and the label on a remote SHA; no local surf or ruckus read
        in remote mode.
    Timing: none. No simulator runs; only git and the Python interpreter are
        started as subprocesses.
"""

import subprocess
import sys

import pytest

from tests.common import tool_versions as tv

SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_SHA = "fedcba9876543210fedcba9876543210fedcba98"


def fake(version):
    return lambda remote_deps=False: version


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.delenv("GITHUB_JOB", raising=False)


def data_rows(text):
    lines = [ln for ln in text.splitlines() if ln.startswith("| ")]
    return [tuple(c.strip() for c in ln.strip("|").split("|", 1))
            for ln in lines[1:]]


def test_rows_follow_the_command_line_order(monkeypatch, capsys):
    monkeypatch.setitem(tv.RESOLVERS, "ghdl", fake("GHDL 5"))
    monkeypatch.setitem(tv.RESOLVERS, "python", fake("3.12.0"))
    assert tv.main(["ghdl", "python"]) == 0
    assert data_rows(capsys.readouterr().out) == [
        ("ghdl", "GHDL 5"), ("python", "3.12.0")]
    assert tv.main(["python", "ghdl"]) == 0
    assert data_rows(capsys.readouterr().out) == [
        ("python", "3.12.0"), ("ghdl", "GHDL 5")]


def test_table_has_a_title_and_header(monkeypatch, capsys):
    monkeypatch.setitem(tv.RESOLVERS, "ghdl", fake("GHDL 5"))
    assert tv.main(["--title", "Mine", "ghdl"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[:3] == ["### Mine", "| Item | Version |",
                         "|------|---------|"]


def test_title_uses_the_job_name_when_set(monkeypatch, capsys):
    monkeypatch.setitem(tv.RESOLVERS, "ghdl", fake("GHDL 5"))
    monkeypatch.setenv("GITHUB_JOB", "lint")
    assert tv.main(["ghdl"]) == 0
    assert "### Tool versions (lint)" in capsys.readouterr().out


def test_title_is_local_without_a_job_name(monkeypatch, capsys):
    monkeypatch.setitem(tv.RESOLVERS, "ghdl", fake("GHDL 5"))
    assert tv.main(["ghdl"]) == 0
    assert "### Tool versions (local)" in capsys.readouterr().out


def test_a_pipe_in_a_version_does_not_split_the_row(monkeypatch, capsys):
    monkeypatch.setitem(tv.RESOLVERS, "ghdl", fake("a|b"))
    assert tv.main(["ghdl"]) == 0
    assert "| ghdl | a\\|b |" in capsys.readouterr().out


def test_a_repeated_item_is_a_usage_error(monkeypatch, capsys):
    monkeypatch.setitem(tv.RESOLVERS, "ghdl", fake("GHDL 5"))
    assert tv.main(["ghdl", "ghdl"]) == 2
    assert "ghdl" in capsys.readouterr().err


def test_an_unknown_item_is_a_usage_error(capsys):
    assert tv.main(["nosuchtool"]) == 2
    assert "nosuchtool" in capsys.readouterr().err


def test_no_items_is_a_usage_error():
    assert tv.main([]) == 2


def test_a_usage_error_resolves_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(tv, "_run", lambda argv: calls.append(argv) or "x")
    assert tv.main(["ghdl", "nosuchtool"]) == 2
    assert calls == []


def test_a_missing_command_is_a_tool_version_error():
    with pytest.raises(tv.ToolVersionError):
        tv._run(["definitely-not-a-command-lcls"])


def test_a_missing_tool_names_the_item_and_returns_one(monkeypatch, capsys):
    def runner(argv):
        raise tv.ToolVersionError("no such command")

    monkeypatch.setattr(tv, "_run", runner)
    assert tv.main(["ghdl"]) == 1
    assert "cannot resolve ghdl: no such command" in capsys.readouterr().err


def test_a_failing_command_is_a_tool_version_error():
    with pytest.raises(tv.ToolVersionError):
        tv._run([sys.executable, "-c", "raise SystemExit(3)"])


def test_run_returns_the_standard_output():
    assert tv._run([sys.executable, "-c", "print('hello')"]).strip() == "hello"


def test_a_resolver_failure_returns_one_and_names_the_item(monkeypatch,
                                                           capsys):
    def broken(remote_deps=False):
        raise tv.ToolVersionError("not installed")

    monkeypatch.setitem(tv.RESOLVERS, "ghdl", broken)
    monkeypatch.setitem(tv.RESOLVERS, "python", fake("3.12.0"))
    assert tv.main(["python", "ghdl"]) == 1
    captured = capsys.readouterr()
    assert "cannot resolve ghdl: not installed" in captured.err
    assert "| python |" not in captured.out


def test_ghdl_uses_the_first_line_of_its_version_output(monkeypatch, capsys):
    monkeypatch.setattr(tv, "_run",
                        lambda argv: "GHDL 5.1.1 (x)\nsecond line\n")
    assert tv.main(["ghdl"]) == 0
    assert data_rows(capsys.readouterr().out) == [("ghdl", "GHDL 5.1.1 (x)")]


def test_iverilog_requires_the_icarus_banner(monkeypatch, capsys):
    monkeypatch.setattr(tv, "_run", lambda argv: "something else\n")
    assert tv.main(["iverilog"]) == 1
    assert "cannot resolve iverilog" in capsys.readouterr().err


def test_iverilog_reports_its_first_line(monkeypatch, capsys):
    monkeypatch.setattr(tv, "_run",
                        lambda argv: "Icarus Verilog version 12.0\nCopyright\n")
    assert tv.main(["iverilog"]) == 0
    assert data_rows(capsys.readouterr().out) == [
        ("iverilog", "Icarus Verilog version 12.0")]


def test_python_reports_the_running_interpreter(capsys):
    assert tv.main(["python"]) == 0
    rows = data_rows(capsys.readouterr().out)
    assert rows[0][0] == "python" and rows[0][1].count(".") == 2


def test_package_items_report_the_installed_distribution(capsys):
    assert tv.main(["cocotb", "cocotb-test", "flake8"]) == 0
    rows = data_rows(capsys.readouterr().out)
    assert [name for name, _ in rows] == ["cocotb", "cocotb-test", "flake8"]
    assert all(version and version[0].isdigit() for _, version in rows)


def test_rogue_reports_its_version(monkeypatch, capsys):
    class Version:
        @staticmethod
        def current():
            return "v6.16.0"

    class Module:
        pass

    module = Module()
    module.Version = Version
    monkeypatch.setitem(sys.modules, "rogue", module)
    assert tv.main(["rogue"]) == 0
    assert data_rows(capsys.readouterr().out) == [("rogue", "v6.16.0")]


def test_missing_rogue_names_the_item(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rogue", None)
    assert tv.main(["rogue"]) == 1
    assert "cannot resolve rogue" in capsys.readouterr().err


def test_two_calls_append_to_the_summary(monkeypatch, tmp_path, capsys):
    summary = tmp_path / "summary.md"
    summary.write_text("earlier text\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setitem(tv.RESOLVERS, "ghdl", fake("GHDL 5"))
    monkeypatch.setitem(tv.RESOLVERS, "python", fake("3.12.0"))
    assert tv.main(["--title", "One", "ghdl"]) == 0
    assert tv.main(["--title", "Two", "python"]) == 0
    text = summary.read_text()
    assert text.startswith("earlier text\n")
    assert text.index("### One") < text.index("### Two")
    assert "| ghdl | GHDL 5 |" in text and "| python | 3.12.0 |" in text


def test_a_failure_leaves_the_summary_untouched(monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    summary.write_text("earlier text\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setattr(tv, "_run", lambda argv: "")
    assert tv.main(["python", "doxygen"]) == 1
    assert summary.read_text() == "earlier text\n"


def make_clone(path):
    path.mkdir()
    env = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), *env, "commit", "-q",
                    "--allow-empty", "-m", "x"], check=True)
    out = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                         check=True, stdout=subprocess.PIPE, text=True)
    return out.stdout.strip()


def test_a_local_clone_reports_its_bare_sha(monkeypatch, tmp_path, capsys):
    sha = make_clone(tmp_path / "surf")
    make_clone(tmp_path / "ruckus")
    monkeypatch.chdir(tmp_path)
    assert tv.main(["surf", "ruckus"]) == 0
    rows = data_rows(capsys.readouterr().out)
    assert rows[0] == ("surf", sha) and rows[1][0] == "ruckus"


def test_a_missing_clone_cannot_be_resolved(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    assert tv.main(["surf"]) == 1
    assert "cannot resolve surf" in capsys.readouterr().err


@pytest.mark.parametrize("output", ["", "abc\n", SHA.upper() + "\n",
                                    SHA + "0\n"])
def test_a_local_value_that_is_not_a_sha_is_rejected(monkeypatch, tmp_path,
                                                     capsys, output):
    (tmp_path / "surf").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tv, "_run", lambda argv: output)
    assert tv.main(["surf"]) == 1
    assert "cannot resolve surf" in capsys.readouterr().err


def test_remote_mode_asks_git_ls_remote_for_main(monkeypatch, tmp_path,
                                                 capsys):
    (tmp_path / "surf").mkdir()
    monkeypatch.chdir(tmp_path)
    calls = []

    def runner(argv):
        calls.append(argv)
        sha = SHA if argv[-2].endswith("/surf") else OTHER_SHA
        return sha + "\trefs/heads/main\n"

    monkeypatch.setattr(tv, "_run", runner)
    assert tv.main(["--remote-deps", "surf", "ruckus"]) == 0
    assert calls == [
        ["git", "ls-remote", "--exit-code",
         "https://github.com/slaclab/surf", "refs/heads/main"],
        ["git", "ls-remote", "--exit-code",
         "https://github.com/slaclab/ruckus", "refs/heads/main"],
    ]
    assert data_rows(capsys.readouterr().out) == [
        ("surf", SHA + " (main, ls-remote)"),
        ("ruckus", OTHER_SHA + " (main, ls-remote)")]


def test_remote_mode_creates_no_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tv, "_run", lambda argv: SHA + "\trefs/heads/main\n")
    assert tv.main(["--remote-deps", "surf", "ruckus"]) == 0
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("output", ["", "\n", "abc\trefs/heads/main\n",
                                    SHA.upper() + "\trefs/heads/main\n"])
def test_a_remote_value_that_is_not_a_sha_is_rejected(monkeypatch, capsys,
                                                      output):
    monkeypatch.setattr(tv, "_run", lambda argv: output)
    assert tv.main(["--remote-deps", "surf"]) == 1
    assert "cannot resolve surf" in capsys.readouterr().err


def test_a_failing_ls_remote_names_the_item(monkeypatch, capsys):
    def runner(argv):
        raise tv.ToolVersionError("exit 2")

    monkeypatch.setattr(tv, "_run", runner)
    assert tv.main(["--remote-deps", "ruckus"]) == 1
    assert "cannot resolve ruckus: exit 2" in capsys.readouterr().err


def test_remote_mode_leaves_other_items_on_their_normal_path(monkeypatch,
                                                             capsys):
    monkeypatch.setattr(tv, "_run", lambda argv: "git version 2.43.0\n")
    assert tv.main(["--remote-deps", "git"]) == 0
    assert data_rows(capsys.readouterr().out) == [
        ("git", "git version 2.43.0")]
