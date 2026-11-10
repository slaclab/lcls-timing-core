#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Fail a pull request that changes production bytes.

Usage::

    python3 tests/common/production_guard.py --base SHA --head SHA

The base and head default to the BASE_SHA and HEAD_SHA environment variables.
Exit status: 0 no protected path changed, 1 at least one did, 2 usage or git
error.

A path is protected when it is any of:

* a .vhd or .v file anywhere except under tests/ or a wrappers/ directory
  below the repository root (the suffix match ignores case);
* anything under python/LclsTimingCore/ or yaml/;
* any path with a coregen directory component;
* any ruckus.tcl except the repository-root one and those under tests/.

The repository-root ruckus.tcl is deliberately unprotected: it carries the
guard that lets ruckus run in its GHDL mode. Every change kind counts as a
violation (add, delete, modify), and a rename is reported as a delete of the
old path plus an add of the new one.

The module imports only the standard library and runs git in the current
working directory. It never resolves anything relative to its own file, so a
copy taken from another commit can be run against any checkout.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import PurePosixPath

BYPASS_LABEL = "production-change"
RTL_SUFFIXES = frozenset({".vhd", ".v"})
SHA_RE = re.compile(r"[0-9a-f]{7,40}")


def is_protected(path: str) -> bool:
    """Return True when a change to this repository path must be refused."""
    parts = PurePosixPath(path).parts
    if not parts:
        return False
    if parts[0] == "tests":
        return False
    if parts[-1] == "ruckus.tcl":
        return len(parts) > 1
    if parts[:2] == ("python", "LclsTimingCore"):
        return True
    if parts[0] == "yaml":
        return True
    if "coregen" in parts[:-1]:
        return True
    if PurePosixPath(path).suffix.lower() in RTL_SUFFIXES:
        return "wrappers" not in parts[1:-1]
    return False


def changed_paths(base: str, head: str) -> list[tuple[str, str]]:
    """Return (status, path) pairs for the base...head diff of the cwd repo."""
    result = subprocess.run(
        ["git", "diff", "--name-status", "--no-renames", "-z",
         f"{base}...{head}"],
        check=True, capture_output=True,
    )
    fields = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    return list(zip(fields[0::2], fields[1::2]))


def escape_workflow_data(text: str) -> str:
    """Escape text for the data part of a GitHub Actions workflow command."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _usage_error(message: str) -> int:
    print(f"usage error: {message}", file=sys.stderr)
    print("usage: production_guard.py --base SHA --head SHA "
          "(7 to 40 lowercase hex characters)", file=sys.stderr)
    return 2


def _write_summary(lines: list[str]) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a pull request changes production bytes.")
    parser.add_argument("--base", default=os.environ.get("BASE_SHA", ""))
    parser.add_argument("--head", default=os.environ.get("HEAD_SHA", ""))
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    for name, value in (("base", args.base), ("head", args.head)):
        if not SHA_RE.fullmatch(value):
            return _usage_error(
                f"--{name} is missing or is not a hex SHA: {value!r}")

    try:
        changes = changed_paths(args.base, args.head)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        print(f"git diff failed: {stderr}", file=sys.stderr)
        return 2

    violations = [(status, path) for status, path in changes
                  if is_protected(path)]
    for status, path in violations:
        print(f"::error title=Production code changed::"
              f"{escape_workflow_data(path)} ({status})")

    if not violations:
        message = f"No protected paths changed ({len(changes)} file(s) changed)"
        print(message)
        _write_summary(["### Production guard", "", message])
        return 0

    message = (
        f"{len(violations)} protected path(s) changed. Production code "
        "(RTL, python/LclsTimingCore/, yaml/, coregen/, child ruckus.tcl) "
        "must stay byte-identical; a maintainer can apply the "
        f"{BYPASS_LABEL} label to bypass this check after review."
    )
    print(message)
    _write_summary(
        ["### Production guard", "", message, ""]
        + [f"- `{status}` `{path}`" for status, path in violations]
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
