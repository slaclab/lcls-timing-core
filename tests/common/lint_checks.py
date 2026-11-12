#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Lint checks that run identically locally and in CI.

Usage::

    python tests/common/lint_checks.py [--include-untracked] text
    python tests/common/lint_checks.py [--include-untracked] vsg

Subcommands:

``text``
    Trailing whitespace in .vhd, .tcl, and .py files, non-ASCII bytes in
    .vhd files, and tab characters in .vhd, .tcl, and .py files (except
    the production files listed in TAB_EXEMPT). Files are scanned as raw
    bytes, so a file that is not valid UTF-8 is still checked.
``vsg``
    Runs vsg with vsg-linter.yml on the new VHDL only: the simulation
    wrappers and the files owned by the regression tree.

The file list comes from ``git ls-files`` with ``--exclude-standard``, so
the surf/, ruckus/, and build/ checkouts are never scanned. The script
never writes a file. Exit status: 0 clean, 1 findings, 2 nothing scanned
or vsg missing.
"""

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

WHITESPACE_SUFFIXES = (".vhd", ".tcl", ".py")
NON_ASCII_SUFFIXES = (".vhd",)
TAB_SUFFIXES = (".vhd", ".tcl", ".py")

# These production files already contain tabs and cannot be edited, so they
# are matched by exact repo-relative path (near misses are still reported).
TAB_EXEMPT = frozenset({
    "LCLS-II/core/rtl/TPGMiniStream.vhd",
    "LCLS-II/core/rtl/TimingSerialDelay.vhd",
})

# Without :(glob) magic a pathspec * also matches /, so tests/*.vhd covers
# every depth under tests/.
NEW_VHDL_PATHSPECS = ("*/wrappers/*.vhd", "tests/*.vhd")

TEXT_PATHSPECS = tuple("*" + suffix for suffix in WHITESPACE_SUFFIXES)

VSG_CONFIG = "vsg-linter.yml"


@dataclass(frozen=True, order=True)
class LintFinding:
    path: str
    line: int
    rule: str
    detail: str


def list_files(pathspecs, *, include_untracked=False, repo_root=REPO_ROOT):
    """Return the sorted, existing files git knows about for the pathspecs."""
    cmd = ["git", "ls-files", "-z"]
    if include_untracked:
        cmd += ["--cached", "--others", "--exclude-standard"]
    cmd += ["--", *pathspecs]
    result = subprocess.run(cmd, cwd=repo_root, check=True,
                            stdout=subprocess.PIPE)
    names = {n.decode("utf-8", "surrogateescape")
             for n in result.stdout.split(b"\0") if n}
    return sorted(n for n in names if (Path(repo_root) / n).is_file())


def scan_text(paths, repo_root):
    """Scan the files as raw bytes and return the sorted findings."""
    findings = []
    for path in paths:
        data = (Path(repo_root) / path).read_bytes()
        for number, raw in enumerate(data.split(b"\n"), start=1):
            body = raw[:-1] if raw.endswith(b"\r") else raw
            if path.endswith(WHITESPACE_SUFFIXES) and body[-1:] in (b" ", b"\t"):
                findings.append(LintFinding(
                    path, number, "trailing-whitespace",
                    "line ends in a blank"))
            if path.endswith(NON_ASCII_SUFFIXES):
                bad = [i for i, byte in enumerate(raw) if byte > 0x7F]
                if bad:
                    findings.append(LintFinding(
                        path, number, "non-ascii",
                        "byte above 0x7F at column %d" % (bad[0] + 1)))
            if (path.endswith(TAB_SUFFIXES) and path not in TAB_EXEMPT
                    and b"\t" in raw):
                findings.append(LintFinding(
                    path, number, "tab",
                    "tab at column %d" % (raw.index(b"\t") + 1)))
    return sorted(findings)


def run_vsg(paths, repo_root):
    """Run vsg with the project configuration on the given files."""
    vsg = Path(sys.executable).with_name("vsg")
    exe = str(vsg) if vsg.is_file() else shutil.which("vsg")
    if exe is None:
        print("vsg not found: install it with "
              "pip install -r pip_requirements.txt")
        return 2
    cmd = [exe, "-f", *paths, "-c", VSG_CONFIG, "-of", "syntastic"]
    return subprocess.run(cmd, cwd=repo_root).returncode


def main(argv=None, repo_root=REPO_ROOT):
    parser = argparse.ArgumentParser(
        description="Run the LCLS Timing Core lint checks.")
    parser.add_argument("command", choices=("text", "vsg"))
    parser.add_argument(
        "--include-untracked", action="store_true",
        help="also scan untracked, non-ignored files (local use; CI scans "
             "tracked files only)")
    args = parser.parse_args(argv)

    pathspecs = TEXT_PATHSPECS if args.command == "text" else NEW_VHDL_PATHSPECS
    paths = list_files(pathspecs, include_untracked=args.include_untracked,
                       repo_root=repo_root)
    if not paths:
        print("no files matched %s" % " ".join(pathspecs))
        return 2

    if args.command == "vsg":
        return run_vsg(paths, repo_root)

    findings = scan_text(paths, repo_root)
    for f in findings:
        print("%s:%d: %s: %s" % (f.path, f.line, f.rule, f.detail))
    print("%d file(s) scanned, %d finding(s)" % (len(paths), len(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
