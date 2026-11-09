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

import ast
from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil

import pytest

from tests.common.ghdl_analysis import (
    ENTITY_RE,
    KNOWN_GHDL_UNANALYZABLE,
    NOT_SIMULATED,
    _strip_comments,
)
from tests.common.regression_utils import REPO_ROOT


@dataclass(frozen=True)
class InventoryTree:
    name: str
    root: Path
    ruckus: Path
    wrappers: Path
    expected_vhd: int
    expected_verilog: int
    baseline: frozenset[str] = field(default_factory=frozenset)


TREES = (
    InventoryTree(
        name="core",
        root=Path("LCLS-II/core"),
        ruckus=Path("LCLS-II/core/ruckus.tcl"),
        wrappers=Path("LCLS-II/core/wrappers"),
        expected_vhd=28,
        expected_verilog=0,
        baseline=frozenset({"tpgminireg", "tpgminicore", "timingcore"}),
    ),
    InventoryTree(
        name="evr",
        root=Path("LCLS-II/evr"),
        ruckus=Path("LCLS-II/evr/ruckus.tcl"),
        wrappers=Path("LCLS-II/evr/wrappers"),
        expected_vhd=14,
        expected_verilog=0,
        baseline=frozenset({"evrv2module", "evrv2_tb"}),
    ),
    InventoryTree(
        name="lcls1",
        root=Path("LCLS-I"),
        ruckus=Path("LCLS-I/ruckus.tcl"),
        wrappers=Path("LCLS-I/wrappers"),
        expected_vhd=9,
        expected_verilog=4,
        baseline=frozenset({"evrv1coreisrctrl"}),
    ),
)

VERILOG_LEAVES = frozenset(
    {"evrv1timestampgenerator", "evrv1timeofdayreceiver", "evrv1eventreceiverchannel", "evrv1dbusdecode"}
)

LOAD_RE = re.compile(r'^\s*loadSource\s+-lib\s+lcls_timing_core\s+-path\s+"\$::DIR_PATH/([^"]+\.vhd)"', re.MULTILINE)
DIR_LOAD_RE = re.compile(
    r'^\s*loadSource\s+-lib\s+lcls_timing_core(?:\s+-sim_only)?\s+-dir\s+"\$::DIR_PATH/([^"]+?)/?"',
    re.MULTILINE,
)
MODULE_RE = re.compile(r"^\s*module\s+(\w+)", re.MULTILINE)
COMPONENT_RE = re.compile(r"^\s*component\s+([a-z][a-z0-9_]*)\s+is\b", re.IGNORECASE | re.MULTILINE)
INSTANCE_RE = re.compile(r"\bentity\s+lcls_timing_core\.([a-z][a-z0-9_]*)", re.IGNORECASE)
VHDL_RUNNER = "run_lcls_vhdl_test"
VERILOG_RUNNER = "run_icarus_verilog_test"
SKIPPED_DIRS = {"sim_build", "__pycache__"}


def loaded_files(repo_root, tree):
    """Return (vhdl_files, verilog_files) that the ruckus.tcl of ``tree`` loads, in file order."""
    ruckus = Path(repo_root) / tree.ruckus
    text = ruckus.read_text(encoding="utf-8")
    files = [ruckus.parent / relative for relative in LOAD_RE.findall(text)]
    for directory in DIR_LOAD_RE.findall(text):
        files.extend(sorted((ruckus.parent / directory).glob("*.vhd")))
        files.extend(sorted((ruckus.parent / directory).glob("*.v")))
    return (
        [path for path in files if path.suffix == ".vhd"],
        [path for path in files if path.suffix == ".v"],
    )


def _vhdl_source(path):
    return _strip_comments(Path(path).read_text(encoding="utf-8", errors="replace"))


def _verilog_source(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _entities_of(files):
    """Return {lowercase entity: declaring file} for VHDL ``files`` (packages declare none)."""
    declared = {}
    for path in files:
        for name in ENTITY_RE.findall(_vhdl_source(path)):
            declared[name.lower()] = path
    return declared


def tree_units(repo_root, tree):
    """Return ({entity: file}, {module: file}) declared by the files that ``tree`` loads."""
    vhdl, verilog = loaded_files(repo_root, tree)
    modules = {}
    for path in verilog:
        for name in MODULE_RE.findall(_verilog_source(path)):
            modules[name.lower()] = path
    return _entities_of(vhdl), modules


def wrapper_entities(repo_root):
    """Return the lowercase entities declared in the wrappers directory of every tree."""
    names = set()
    for tree in TREES:
        names.update(_entities_of(sorted((Path(repo_root) / tree.wrappers).glob("*.vhd"))))
    return names


def _is_skipif(decorator):
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return isinstance(target, ast.Attribute) and target.attr == "skipif"


def _called_name(call):
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _collect_toplevels(node, found):
    decorated = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    if decorated and any(_is_skipif(decorator) for decorator in node.decorator_list):
        return
    if isinstance(node, ast.Call) and _called_name(node) in found:
        for keyword in node.keywords:
            value = keyword.value
            if keyword.arg == "toplevel" and isinstance(value, ast.Constant) and isinstance(value.value, str):
                found[_called_name(node)].add(value.value.rsplit(".", 1)[-1].lower())
    for child in ast.iter_child_nodes(node):
        _collect_toplevels(child, found)


def _test_files(repo_root):
    return sorted(
        path
        for path in (Path(repo_root) / "tests").rglob("test_*.py")
        if not SKIPPED_DIRS.intersection(path.parts)
    )


def tested_toplevels(repo_root):
    """Return (vhdl, verilog): the lowercase toplevels that some test runs.

    Only string-constant ``toplevel`` keywords of real run_lcls_vhdl_test and
    run_icarus_verilog_test calls count, outside functions or classes that are
    decorated with skipif.
    """
    found = {VHDL_RUNNER: set(), VERILOG_RUNNER: set()}
    for test_file in _test_files(repo_root):
        _collect_toplevels(ast.parse(test_file.read_text(encoding="utf-8")), found)
    return found[VHDL_RUNNER], found[VERILOG_RUNNER]


# The name starts with "test", so keep pytest from collecting this helper.
tested_toplevels.__test__ = False


class Inventory:
    """The declared units, toplevels, and recorded units of a repository copy."""

    def __init__(self, repo_root, trees=TREES):
        self.repo_root = Path(repo_root)
        self.trees = trees
        self.vhdl_toplevels, self.verilog_toplevels = tested_toplevels(self.repo_root)
        self.wrappers = wrapper_entities(self.repo_root)
        self.recorded = set(KNOWN_GHDL_UNANALYZABLE) | set(NOT_SIMULATED)
        self.entities = {}
        self.modules = {}
        self.own = set()
        for tree in TREES:
            entities, modules = tree_units(self.repo_root, tree)
            self.entities.update(entities)
            self.modules.update(modules)
            if tree in trees:
                self.own.update(entities)
                self.own.update(modules)

    def has_dedicated_test(self, unit):
        if unit in self.modules:
            return unit in self.verilog_toplevels
        wrapper = unit + "wrapper"
        return unit in self.vhdl_toplevels or (wrapper in self.vhdl_toplevels and wrapper in self.wrappers)

    def children(self):
        """Return the declared units instantiated or declared as components beneath the recorded units."""
        declared = set(self.entities) | set(self.modules)
        children = set()
        for unit in sorted(self.recorded & self.own & set(self.entities)):
            source = _vhdl_source(self.entities[unit])
            names = INSTANCE_RE.findall(source) + COMPONENT_RE.findall(source)
            children.update(name.lower() for name in names)
        return children & declared

    def missing(self):
        return sorted(
            unit for unit in self.own | self.children() if unit not in self.recorded and not self.has_dedicated_test(unit)
        )

    def stale(self):
        return sorted(unit for unit in self.own & self.recorded if self.has_dedicated_test(unit))


def missing_coverage(repo_root, trees=TREES):
    """Return the sorted loaded units, and children of recorded units, that nothing tests."""
    return Inventory(repo_root, trees).missing()


def stale_recorded(repo_root, trees=TREES):
    """Return the sorted recorded units that a test now simulates."""
    return Inventory(repo_root, trees).stale()


def recorded_children(repo_root, trees=TREES):
    """Return the declared units beneath the recorded units of ``trees``."""
    return Inventory(repo_root, trees).children()


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
