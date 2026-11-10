#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Analysis gate: every imported design unit must still analyze under GHDL.

Test methodology:
    Sweep: every entity found in build/SRC_VHDL/lcls_timing_core plus the one
        production file that no ruckus.tcl loads (TimingGthWrapper.vhd), one
        pytest case per unit. The pure tests below sweep the verdict rules,
        the baseline sanity rules and the entity discovery edge cases.
    Stimulus: ghdl -i of every imported library into a per-unit scratch work
        directory, then ghdl -m for the unit (ghdl -a for the unloaded file).
        No simulation runs, analysis only.
    Checks: verdict() returns None, so a unit outside the baseline must
        analyze, and a unit inside the baseline must still fail with its
        recorded message. A missing build tree or an empty library is one
        failing case, never zero cases and never a pass.
    Timing: not applicable, no clock and no simulated time.
"""

import re
import subprocess

import pytest

from tests.common import ghdl_analysis
from tests.common.ghdl_analysis import (
    KNOWN_GHDL_UNANALYZABLE,
    UNLOADED_FILES,
    analyze,
    discover_units,
    validate_baseline,
    verdict,
)
from tests.common.regression_utils import TESTS_ROOT

MISSING_TREE_ID = "missing-build-tree"
EMPTY_LIBRARY_ID = "no-entities-discovered"
IMPORT_HINT = 'make MODULES="$PWD" import'


def _collect_unit_ids(discover=discover_units):
    try:
        units = discover()
    except FileNotFoundError:
        return [MISSING_TREE_ID]
    if not units:
        return [EMPTY_LIBRARY_ID]
    return sorted(set(units) | set(UNLOADED_FILES))


UNIT_IDS = _collect_unit_ids()


@pytest.mark.parametrize("unit", UNIT_IDS)
def test_unit_analysis(unit):
    if unit in (MISSING_TREE_ID, EMPTY_LIBRARY_ID):
        pytest.fail(
            f"no imported units to analyze ({unit}); run {IMPORT_HINT} first"
        )
    workdir = TESTS_ROOT / "sim_build" / "common" / "ghdl_analysis" / unit
    returncode, output = analyze(unit, workdir)
    problem = verdict(unit, returncode, output)
    assert problem is None, f"{problem}\n--- ghdl output ---\n{output}"


def test_baseline_keys_exist():
    try:
        units = set(discover_units())
    except FileNotFoundError:
        pytest.skip(f"build tree missing, run {IMPORT_HINT} first")
    unknown = sorted(set(KNOWN_GHDL_UNANALYZABLE) - units - set(UNLOADED_FILES))
    assert not unknown, f"baseline entries without a matching unit: {unknown}"


def test_baseline_is_specific():
    validate_baseline()
    assert len(KNOWN_GHDL_UNANALYZABLE) == 6
    for unit, fragment in KNOWN_GHDL_UNANALYZABLE.items():
        assert not re.search(r":\d+:\d+", fragment), f"{unit}: line number in fragment"
        assert ".vhd" not in fragment, f"{unit}: file path in fragment"


def test_baseline_rejects_weak_fragments(monkeypatch):
    for weak in ("", "   ", "short", "  tiny  "):
        monkeypatch.setattr(
            ghdl_analysis, "KNOWN_GHDL_UNANALYZABLE", {"someunit": weak}
        )
        with pytest.raises(ValueError, match="someunit"):
            validate_baseline()


def test_baseline_rejects_mixed_case_key(monkeypatch):
    monkeypatch.setattr(
        ghdl_analysis, "KNOWN_GHDL_UNANALYZABLE", {"SomeUnit": "not locally static"}
    )
    with pytest.raises(ValueError, match="SomeUnit"):
        validate_baseline()


def test_verdict_new_failure_is_reported():
    assert "new analysis failure" in verdict("newunit", 1, "x.vhd:1:1:error: bad")


def test_verdict_clean_unit_is_none():
    assert verdict("newunit", 0, "") is None


def test_verdict_stale_baseline_entry_is_reported():
    problem = verdict("timingcore", 0, "")
    assert "now analyzes" in problem
    assert "surf drift or fix?" in problem


def test_verdict_wrong_message_is_reported():
    problem = verdict("timingcore", 1, "unrelated error")
    assert "without the recorded message" in problem


def test_verdict_is_case_insensitive():
    assert verdict("TimingCore", 1, "x: CHOICE IS NOT LOCALLY STATIC") is None


def test_verdict_known_failure_with_message_is_none():
    for unit, fragment in KNOWN_GHDL_UNANALYZABLE.items():
        assert verdict(unit, 2, f"file.vhd: error: {fragment}") is None, unit


def test_discover_units_sorted_lowercase_and_comment_stripped(tmp_path):
    (tmp_path / "b.vhd").write_text("entity B is\nend entity B;\n")
    (tmp_path / "c.vhd").write_text("-- entity Hidden is\nlibrary ieee;\n")
    (tmp_path / "a.vhd").write_text("  ENTITY Alpha_One IS\nend;\n")
    assert discover_units(tmp_path) == ["alpha_one", "b"]


def test_discover_units_duplicate_entity_names_both_files(tmp_path):
    (tmp_path / "first.vhd").write_text("entity TimingCore is\nend;\n")
    (tmp_path / "second.vhd").write_text("entity timingcore is\nend;\n")
    with pytest.raises(ValueError) as exc:
        discover_units(tmp_path)
    assert "first.vhd" in str(exc.value)
    assert "second.vhd" in str(exc.value)


def test_discover_units_missing_dir_names_import_command(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        discover_units(tmp_path / "absent")
    assert IMPORT_HINT in str(exc.value)


def test_discover_units_empty_dir_returns_empty_list(tmp_path):
    assert discover_units(tmp_path) == []


def test_unit_ids_are_the_sorted_union_in_any_discovery_order():
    expected = ["aa", "timinggthwrapper", "zz"]
    assert _collect_unit_ids(lambda: ["zz", "aa"]) == expected
    assert _collect_unit_ids(lambda: ["aa", "zz"]) == expected


def test_unit_ids_for_an_empty_library_is_one_failing_sentinel():
    assert _collect_unit_ids(lambda: []) == [EMPTY_LIBRARY_ID]


def test_unit_ids_for_a_missing_tree_is_one_failing_sentinel():
    def missing():
        raise FileNotFoundError(IMPORT_HINT)

    assert _collect_unit_ids(missing) == [MISSING_TREE_ID]


def test_analyze_raises_when_ghdl_binary_is_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("GHDL_CMD", "no-such-ghdl-binary")
    monkeypatch.setattr(
        ghdl_analysis, "build_vhdl_sources", lambda: {"lcls_timing_core": []}
    )
    with pytest.raises(FileNotFoundError, match="no-such-ghdl-binary"):
        analyze("timingcore", tmp_path / "work")


def test_analyze_raises_when_import_step_fails(monkeypatch, tmp_path):
    missing_source = str(tmp_path / "does_not_exist.vhd")
    monkeypatch.setattr(
        ghdl_analysis,
        "build_vhdl_sources",
        lambda: {"lcls_timing_core": [missing_source]},
    )
    with pytest.raises(subprocess.CalledProcessError):
        analyze("timingcore", tmp_path / "work")
