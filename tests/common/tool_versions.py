#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Print an ordered tool version table and append it to the job summary.

Usage::

    python tests/common/tool_versions.py [--remote-deps] [--title TITLE] \\
        ITEM [ITEM ...]

Items: surf, ruckus, ghdl, iverilog, git, python, cocotb, cocotb-test,
flake8, vsg, rogue, sphinx, sphinx-rtd-theme, sphinx-copybutton. Rows appear
in the order the items are given. The table goes to stdout and, when
GITHUB_STEP_SUMMARY is set, is appended to that file.

surf and ruckus are reported as the commit SHA of the job's own clone (the
surf/ and ruckus/ directories in the current directory). With --remote-deps
they are reported as the SHA of refs/heads/main on GitHub instead, labelled
(main, ls-remote), for jobs that clone neither repository. That mode never
creates a directory.

Exit status: 0 table written, 1 an item could not be resolved (nothing is
written), 2 no items, an unknown item, or a repeated item. The module uses
only the standard library.
"""

import argparse
import importlib
import importlib.metadata
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REMOTE_LABEL = " (main, ls-remote)"
REPOSITORY_URL = "https://github.com/slaclab/{}"


class ToolVersionError(Exception):
    """A version could not be determined."""


def _run(argv):
    """Run a command and return its standard output."""
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                check=False)
    except OSError as exc:
        raise ToolVersionError("cannot run %s: %s" % (argv[0], exc))
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise ToolVersionError(
            "%s exited with status %d%s" % (
                " ".join(argv), result.returncode,
                ": " + detail[-1] if detail else ""))
    return result.stdout


def _first_line(text):
    lines = text.strip().splitlines()
    if not lines:
        raise ToolVersionError("no version output")
    return lines[0].strip()


def _check_sha(value):
    if not SHA_PATTERN.match(value):
        raise ToolVersionError("not a 40-character commit SHA: %r" % value)
    return value


def _dependency(name):
    def resolve(remote_deps=False):
        if remote_deps:
            out = _run(["git", "ls-remote", "--exit-code",
                        REPOSITORY_URL.format(name), "refs/heads/main"])
            fields = out.split()
            sha = _check_sha(fields[0] if fields else "")
            return sha + REMOTE_LABEL
        if not Path(name).is_dir():
            raise ToolVersionError(
                "no %s/ clone in %s and --remote-deps not given" % (
                    name, os.getcwd()))
        return _check_sha(_run(["git", "-C", name, "rev-parse",
                                "HEAD"]).strip())
    return resolve


def _command_line(argv):
    def resolve(remote_deps=False):
        return _first_line(_run(argv))
    return resolve


def _iverilog(remote_deps=False):
    line = _first_line(_run(["iverilog", "-V"]))
    if "Icarus Verilog" not in line:
        raise ToolVersionError("unexpected iverilog banner: %r" % line)
    return line


def _distribution(name):
    def resolve(remote_deps=False):
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            raise ToolVersionError("distribution %s is not installed" % name)
    return resolve


def _python(remote_deps=False):
    return platform.python_version()


def _rogue(remote_deps=False):
    try:
        rogue = importlib.import_module("rogue")
        return str(rogue.Version.current())
    except (ImportError, AttributeError) as exc:
        raise ToolVersionError("cannot use rogue: %s" % exc)


RESOLVERS = {
    "surf": _dependency("surf"),
    "ruckus": _dependency("ruckus"),
    "ghdl": _command_line(["ghdl", "--version"]),
    "iverilog": _iverilog,
    "git": _command_line(["git", "--version"]),
    "python": _python,
    "cocotb": _distribution("cocotb"),
    "cocotb-test": _distribution("cocotb-test"),
    "flake8": _distribution("flake8"),
    "vsg": _distribution("vsg"),
    "rogue": _rogue,
    "sphinx": _distribution("sphinx"),
    "sphinx-rtd-theme": _distribution("sphinx-rtd-theme"),
    "sphinx-copybutton": _distribution("sphinx-copybutton"),
}


def render(rows, title):
    """Return the markdown table for (item, version) rows, in order."""
    lines = ["### " + title, "| Item | Version |", "|------|---------|"]
    for item, version in rows:
        lines.append("| %s | %s |" % (item, version.replace("|", "\\|")))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print an ordered tool version table.")
    parser.add_argument("items", nargs="*", metavar="ITEM")
    parser.add_argument("--title")
    parser.add_argument("--remote-deps", action="store_true",
                        help="report surf and ruckus from git ls-remote of "
                             "refs/heads/main instead of a local clone")
    args = parser.parse_args(argv)

    if not args.items:
        print("no items given; choose from: %s" % ", ".join(RESOLVERS),
              file=sys.stderr)
        return 2
    unknown = [i for i in args.items if i not in RESOLVERS]
    if unknown:
        print("unknown item: %s; choose from: %s" % (
            ", ".join(unknown), ", ".join(RESOLVERS)), file=sys.stderr)
        return 2
    repeated = sorted({i for i in args.items if args.items.count(i) > 1})
    if repeated:
        print("repeated item: %s" % ", ".join(repeated), file=sys.stderr)
        return 2

    rows = []
    failed = False
    for item in args.items:
        try:
            rows.append((item, RESOLVERS[item](remote_deps=args.remote_deps)))
        except ToolVersionError as exc:
            print("cannot resolve %s: %s" % (item, exc), file=sys.stderr)
            failed = True
    if failed:
        return 1

    title = args.title or "Tool versions (%s)" % os.environ.get(
        "GITHUB_JOB", "local")
    table = render(rows, title)
    print(table, end="")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(table + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
