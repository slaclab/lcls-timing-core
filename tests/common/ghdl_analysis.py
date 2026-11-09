#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""GHDL analysis gate for every imported design unit.

``make analysis`` (vhdeps) cannot be the gate for this repository: it aborts on
the architecture-local component declarations in the EVR sources before it
reports anything per unit. The gate here imports every library with ``ghdl -i``
and then analyzes one unit at a time with ``ghdl -m``, so each unit gets its
own verdict.

A handful of production units do not analyze under GHDL today. They are
recorded in ``KNOWN_GHDL_UNANALYZABLE`` with a substring of the message GHDL
prints, and the gate stays green only while each of them keeps failing with
that message. A unit outside the baseline that fails, a listed unit that now
analyzes, and a listed unit that fails with a different message all turn the
gate red.

Run ``python -m tests.common.ghdl_analysis --report`` from the repository root
for a one-line-per-unit report that ends with ``GATE: PASS`` or ``GATE: FAIL``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from tests.common.regression_utils import (
    BASE_GHDL_COMPILE_ARGS,
    BUILD_SRC_ROOT,
    REPO_ROOT,
    TESTS_ROOT,
    build_vhdl_sources,
)

LIB = "lcls_timing_core"

# Minimum fragment length. Anything shorter matches too much GHDL output to
# prove that a unit still fails for the recorded reason.
MIN_FRAGMENT_LENGTH = 8

IMPORT_HINT = 'make MODULES="$PWD" import'

# Unit name (lowercase) to a version-stable substring of the GHDL output. The
# fragments carry no line numbers and no surf file paths, so they survive a
# GHDL upgrade and a surf refactor. Matching is case-insensitive.
KNOWN_GHDL_UNANALYZABLE: dict[str, str] = {
    # A case choice that GHDL cannot prove locally static.
    "tpgminireg": "not locally static",
    # The next two fail while re-analyzing TPGMiniReg and report its errors.
    "tpgminicore": "not locally static",
    "timingcore": "not locally static",
    # An index and a range expression that are not locally static.
    "evrv2module": "must be locally static",
    # A string literal whose length differs from the surf tKeep width.
    "evrv1coreisrctrl": "string length does not match",
    # The testbench names a type that its package does not declare.
    "evrv2_tb": 'no declaration for "exptbustype"',
    # The file uses "ieee" without a library clause.
    "timinggthwrapper": 'no declaration for "ieee"',
}

# Units that analyze cleanly (so they must never be listed in
# KNOWN_GHDL_UNANALYZABLE) but cannot be simulated. The coverage gate in
# tests/common/test_core_inventory.py accepts them without a dedicated test,
# and rejects an entry as soon as a test simulates the unit.
NOT_SIMULATED: dict[str, str] = {
    "evrv1eventreceiver": (
        "it instantiates EvrV1EventReceiverChannel, EvrV1TimeofDayReceiver, "
        "EvrV1TimeStampGenerator, and EvrV1DbusDecode, which are Verilog modules "
        "declared as VHDL components; GHDL cannot bind Verilog and Icarus cannot "
        "elaborate VHDL, so the mixed-language top is not simulated; the four "
        "Verilog leaves and its VHDL children are tested on their own"
    ),
    "evrv1core": (
        "it instantiates EvrV1EventReceiver, so it inherits the same "
        "mixed-language limit; its EvrV1Reg child is tested on its own"
    ),
}

# Production files that no ruckus.tcl loads, so they are absent from the
# imported library. They are analyzed directly with ghdl -a.
UNLOADED_FILES: dict[str, str] = {
    "timinggthwrapper": "LCLS-II/core/rtl/TimingGthWrapper.vhd",
}

ENTITY_RE = re.compile(
    r"^\s*entity\s+([a-z][a-z0-9_]*)\s+is\b",
    re.IGNORECASE | re.MULTILINE,
)


def _strip_comments(source: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in source.splitlines())


def discover_units(src_dir: Path = BUILD_SRC_ROOT / LIB) -> list[str]:
    """Return the sorted lowercase entity names declared under src_dir."""
    src_dir = Path(src_dir)
    if not src_dir.is_dir():
        raise FileNotFoundError(
            f"{src_dir} does not exist; run `{IMPORT_HINT}` first."
        )

    declared_in: dict[str, Path] = {}
    for path in sorted(src_dir.iterdir()):
        if path.suffix.lower() not in {".vhd", ".vhdl"} or not path.is_file():
            continue
        source = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        for name in {match.lower() for match in ENTITY_RE.findall(source)}:
            if name in declared_in:
                raise ValueError(
                    f"entity {name} is declared by both "
                    f"{declared_in[name]} and {path}"
                )
            declared_in[name] = path
    return sorted(declared_in)


def validate_baseline() -> None:
    """Reject baseline entries that could not prove a specific failure."""
    for unit, fragment in KNOWN_GHDL_UNANALYZABLE.items():
        if unit != unit.lower():
            raise ValueError(f"baseline unit {unit} must be lowercase")
        if len(fragment.strip()) < MIN_FRAGMENT_LENGTH:
            raise ValueError(
                f"baseline unit {unit} needs a message fragment of at least "
                f"{MIN_FRAGMENT_LENGTH} characters, got {fragment!r}"
            )


def _ghdl_command() -> list[str]:
    return shlex.split(os.environ.get("GHDL_CMD", "ghdl"))


def analyze(unit: str, workdir: Path) -> tuple[int, str]:
    """Analyze one unit in a fresh work directory and return (rc, output).

    GHDL runs with the work directory as the process cwd and without
    --workdir, which is how cocotb-test runs it: the other libraries are found
    in the cwd. A missing ghdl binary or a failed ghdl -i raises, so an
    environment problem can never be mistaken for a known failure.
    """
    workdir = Path(workdir)
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    ghdl = _ghdl_command()
    for library, files in build_vhdl_sources().items():
        subprocess.run(
            [*ghdl, "-i", *BASE_GHDL_COMPILE_ARGS, f"--work={library}", *files],
            cwd=workdir,
            check=True,
            capture_output=True,
            text=True,
        )

    if unit in UNLOADED_FILES:
        command = [
            *ghdl, "-a", *BASE_GHDL_COMPILE_ARGS, f"--work={LIB}",
            str(REPO_ROOT / UNLOADED_FILES[unit]),
        ]
    else:
        command = [*ghdl, "-m", *BASE_GHDL_COMPILE_ARGS, f"--work={LIB}", unit]
    result = subprocess.run(command, cwd=workdir, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def verdict(unit: str, returncode: int, output: str) -> str | None:
    """Return None when the unit behaves as the baseline says, else a reason."""
    unit = unit.lower()
    expected = KNOWN_GHDL_UNANALYZABLE.get(unit)
    if expected is None:
        if returncode == 0:
            return None
        return f"{unit}: new analysis failure:\n{output}"
    if returncode == 0:
        return (
            f"{unit}: listed in KNOWN_GHDL_UNANALYZABLE but now analyzes "
            "(surf drift or fix?); remove the entry"
        )
    if expected.lower() not in output.lower():
        return (
            f"{unit}: fails, but without the recorded message "
            f"{expected!r}:\n{output}"
        )
    return None


def _first_error_line(output: str) -> str:
    for line in output.splitlines():
        if "error:" in line:
            return re.sub(r"(?:[^\s:]*/)+", "", line).strip()
    return ""


def _ghdl_version_line() -> str:
    result = subprocess.run(
        [*_ghdl_command(), "--version"], check=True, capture_output=True, text=True
    )
    return result.stdout.splitlines()[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--report",
        action="store_true",
        help="analyze every unit and print one line per unit and a GATE line",
    )
    args = parser.parse_args(argv)
    if not args.report:
        parser.error("--report is required")

    validate_baseline()
    units = discover_units()
    if not units:
        print(f"GATE: FAIL (no entities discovered; run `{IMPORT_HINT}` first)")
        return 1
    units = sorted(set(units) | set(UNLOADED_FILES))

    print(_ghdl_version_line())
    root = TESTS_ROOT / "sim_build" / "common" / "ghdl_analysis_report"
    failing_units = 0
    known_failures = 0
    for unit in units:
        returncode, output = analyze(unit, root / unit)
        problem = verdict(unit, returncode, output)
        if problem is None:
            status = "ok"
            if returncode != 0:
                known_failures += 1
        else:
            status = problem.splitlines()[0]
            failing_units += 1
        print(f"{unit}\trc={returncode}\t{status}\t{_first_error_line(output)}")

    if failing_units:
        print(
            f"GATE: FAIL ({len(units)} units, {failing_units} unexpected, "
            f"{known_failures} known failures)"
        )
        return 1
    print(f"GATE: PASS ({len(units)} units, {known_failures} known failures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
