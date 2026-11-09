#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Coverage gate: every unit that a ruckus.tcl loads has a dedicated test.

Test methodology:
    Sweep: three trees, LCLS-II/core (the files named by loadSource -path
        lines), LCLS-II/evr (the .vhd files of the rtl/ and sim_only tb/
        directories that loadSource -dir names), and LCLS-I (the evr/
        directory: the .vhd files plus the four Verilog leaves, which ruckus
        GHDL mode imports separately). For each tree: the loaded files, the
        VHDL entities and Verilog modules they declare, the toplevels that
        every tests/**/test_*.py passes to run_lcls_vhdl_test and
        run_icarus_verilog_test, and the units instantiated or declared as
        components beneath each recorded unit. Five seeded-gap cases run the
        same check on a copy of the three trees and tests/ with one defect
        introduced.
    Stimulus: pure Python text parsing and ast of the repository files, no
        simulator. The seeded-gap cases copy the three trees and tests/ into
        a tmp_path and edit the copy.
    Checks: an entity counts as tested only when some test calls
        run_lcls_vhdl_test with a toplevel equal to the entity or to its own
        <entity>wrapper (a wrapper file must exist beside the RTL), and a
        Verilog module only when some test calls run_icarus_verilog_test with
        a toplevel equal to the module. Toplevels are read from real call
        keywords with ast, so a toplevel in a comment, in a docstring, or in
        a test function decorated with skipif does not count, and being
        instantiated by someone else's wrapper does not count either. The only
        units allowed without a dedicated test are the keys of
        KNOWN_GHDL_UNANALYZABLE and NOT_SIMULATED (imported, never copied);
        KNOWN_GHDL_UNANALYZABLE intersected with each tree is exactly the
        tree baseline. Every lcls_timing_core entity and Verilog component
        beneath a recorded unit has a dedicated test or is itself recorded. A
        recorded unit that a test now simulates is reported as stale. Removing
        one test, commenting out one toplevel keyword, or adding a test for a
        recorded unit makes the check report that unit by name.
    Timing: none, no clock and no simulated time.
"""

from __future__ import annotations

import shutil

import pytest

from tests.common.ghdl_analysis import KNOWN_GHDL_UNANALYZABLE, NOT_SIMULATED
from tests.common.regression_utils import REPO_ROOT
from tests.common.source_inventory import (
    SKIPPED_DIRS,
    TREES,
    VERILOG_LEAVES,
    Inventory,
    loaded_files,
    missing_coverage,
    recorded_children,
    stale_recorded,
    tree_units,
)


@pytest.fixture
def sources_copy(tmp_path):
    """A copy of the three trees and tests/ that a test may edit."""
    for tree in TREES:
        shutil.copytree(REPO_ROOT / tree.root, tmp_path / tree.root)
    shutil.copytree(
        REPO_ROOT / "tests",
        tmp_path / "tests",
        ignore=shutil.ignore_patterns(*SKIPPED_DIRS, "*.pyc"),
    )
    return tmp_path


@pytest.mark.parametrize("tree", TREES, ids=[tree.name for tree in TREES])
def test_every_loaded_unit_is_tested_or_recorded(tree):
    vhdl, verilog = loaded_files(REPO_ROOT, tree)
    assert len(vhdl) == tree.expected_vhd, f"{tree.name} loads {len(vhdl)} VHDL files, expected {tree.expected_vhd}"
    assert len(verilog) == tree.expected_verilog, (
        f"{tree.name} loads {len(verilog)} Verilog files, expected {tree.expected_verilog}"
    )
    missing_files = [path for path in vhdl + verilog if not path.is_file()]
    assert not missing_files, f"a loaded file is missing: {missing_files}"
    entities, modules = tree_units(REPO_ROOT, tree)
    assert entities, f"{tree.name} declares no entity"
    if tree.name == "core":
        assert "bsacontrol" in entities, "BsaControlv2.vhd must contribute the entity bsacontrol"
    if tree.name == "lcls1":
        assert set(modules) == VERILOG_LEAVES, f"Verilog modules found: {sorted(modules)}"
    missing = missing_coverage(REPO_ROOT, (tree,))
    assert not missing, f"loaded {tree.name} units without a dedicated test: " + ", ".join(missing)


@pytest.mark.parametrize("tree", TREES, ids=[tree.name for tree in TREES])
def test_baseline_per_tree_is_exact(tree):
    entities, _ = tree_units(REPO_ROOT, tree)
    baseline = set(entities) & set(KNOWN_GHDL_UNANALYZABLE)
    assert baseline == tree.baseline, f"{tree.name} baseline units among the loaded entities: {sorted(baseline)}"


def test_not_simulated_is_exact_and_disjoint():
    assert set(NOT_SIMULATED) == {"evrv1eventreceiver", "evrv1core"}, f"NOT_SIMULATED keys: {sorted(NOT_SIMULATED)}"
    assert all(reason.strip() for reason in NOT_SIMULATED.values()), "every NOT_SIMULATED unit needs a reason"
    overlap = set(NOT_SIMULATED) & set(KNOWN_GHDL_UNANALYZABLE)
    assert not overlap, f"units that analyze cleanly must not be in the analysis baseline: {sorted(overlap)}"
    declared = Inventory(REPO_ROOT)
    assert set(NOT_SIMULATED) <= set(declared.entities), "a NOT_SIMULATED unit is not declared by any tree"
    assert stale_recorded(REPO_ROOT) == [], "a recorded unit now has a dedicated test"


def test_children_of_recorded_units_are_tested():
    children = recorded_children(REPO_ROOT)
    assert {
        # core baseline units
        "tpgminireg", "tpgmini", "tpgministream", "timingrx", "tpgminicore", "ethtimingmodule",
        # evr baseline units
        "evrv2eventselect", "evrv2fromv1", "evrv2trigger", "evrv2axi", "evrv2trigreg",
        # not simulated and baseline LCLS-I units
        "evrv1reg", "evrv1eventreceiver", "evrv1timestampfifo", "evrv1eventram256x32", "evrv1heartbeat",
        "evrv1eventreceiverchannel", "evrv1timeofdayreceiver", "evrv1timestampgenerator", "evrv1dbusdecode",
    } <= children, f"children found beneath the recorded units: {sorted(children)}"
    inventory = Inventory(REPO_ROOT)
    untested = sorted(
        unit for unit in children if unit not in inventory.recorded and not inventory.has_dedicated_test(unit)
    )
    assert not untested, "units beneath the recorded units without a dedicated test: " + ", ".join(untested)


def _remove_test(name):
    def edit(root):
        next((root / "tests").rglob(name)).unlink()
    return edit


def _comment_out(name, line):
    def edit(root):
        path = next((root / "tests").rglob(name))
        text = path.read_text(encoding="utf-8")
        assert line in text, f"{name} does not contain {line!r}"
        path.write_text(text.replace(line, "# " + line), encoding="utf-8")
    return edit


def _add_dedicated_test(relative, toplevel):
    def edit(root):
        (root / relative).write_text(
            "from pathlib import Path\n"
            "\n"
            "from tests.common.regression_utils import run_lcls_vhdl_test\n"
            "\n"
            "\n"
            "def test_added():\n"
            f"    run_lcls_vhdl_test(test_file=Path(__file__), toplevel={toplevel!r})\n",
            encoding="utf-8",
        )
    return edit


SEEDED_GAPS = [
    pytest.param(_remove_test("test_Divider.py"), ["divider"], [], id="missing_core_test"),
    pytest.param(_remove_test("test_EvrV2Trigger.py"), ["evrv2trigger"], [], id="wrapper_instance_only"),
    pytest.param(
        _comment_out("test_EvrV1HeartBeat.py", 'toplevel="lcls_timing_core.evrv1heartbeat",'),
        ["evrv1heartbeat"],
        [],
        id="toplevel_in_comment",
    ),
    pytest.param(
        _remove_test("test_EvrV1TimeofDayReceiver.py"), ["evrv1timeofdayreceiver"], [], id="missing_verilog_test"
    ),
    pytest.param(
        _add_dedicated_test("tests/lcls1_evr/test_EvrV1Core.py", "lcls_timing_core.evrv1core"),
        [],
        ["evrv1core"],
        id="stale_not_simulated",
    ),
]


@pytest.mark.parametrize(("edit", "missing", "stale"), SEEDED_GAPS)
def test_seeded_gap_is_reported(sources_copy, edit, missing, stale):
    assert missing_coverage(sources_copy) == [], "the copy must start fully covered"
    assert stale_recorded(sources_copy) == [], "the copy must start with no stale record"
    edit(sources_copy)
    assert missing_coverage(sources_copy) == missing
    assert stale_recorded(sources_copy) == stale
