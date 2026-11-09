#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Inventory helpers shared by the coverage gate and the reference generator.

The helpers read the ruckus.tcl files, the RTL sources, and the test modules as
text and with ast. Nothing is imported or executed from those files.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess

from tests.common.ghdl_analysis import (
    ENTITY_RE,
    KNOWN_GHDL_UNANALYZABLE,
    NOT_SIMULATED,
    _strip_comments,
)


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

LOAD_RE = re.compile(
    r'^\s*loadSource\s+-lib\s+lcls_timing_core\s+-path\s+"\$::DIR_PATH/([^"]+\.(?:vhd|v))"', re.MULTILINE
)
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


# RTL files that no ruckus.tcl loads, each with the reason measured from the
# sources. A new or a vanished entry fails tests/common/test_unloaded_sources.py.
UNLOADED_SOURCES: dict[str, str] = {
    "LCLS-II/core/rtl/BsaControl.vhd": (
        "declares entity BsaControl, which the loaded BsaControlv2.vhd also declares; "
        "TPGMini.vhd instantiates the loaded one"
    ),
    "LCLS-II/core/rtl/ClockTime_186MHz.vhd": "no file in the repository instantiates ClockTime_186MHz",
    "LCLS-II/core/rtl/TPFifo.vhd": "no file in the repository instantiates TPFifo",
    "LCLS-II/core/rtl/TPGMiniEdefTb.vhd": (
        "testbench entity in an rtl directory; LCLS-II/core/ruckus.tcl does not list it"
    ),
    "LCLS-II/core/rtl/TPGNotify.vhd": "no file in the repository instantiates TPGNotify",
    "LCLS-II/core/rtl/TimingGthWrapper.vhd": "no file in the repository instantiates TimingGthWrapper",
    "LCLS-II/core/rtl/default/TimingExtnPkg.vhd": (
        "default TimingExtnPkg; LCLS-II/core/ruckus.tcl lists no file from rtl/default, and only the "
        "test wrapper TimingExtnPkgWrapper.vhd uses the package"
    ),
    "LCLS-II/core/tb/TimingSerialDelay_tb.vhd": "testbench; LCLS-II/core/ruckus.tcl loads no tb directory",
}

# One issue covers all of the files above; the value becomes its URL once filed.
UNLOADED_SOURCES_ISSUE = "pending"


def repo_ruckus_files(repo_root):
    """Return the tracked ruckus.tcl files outside tests/, as sorted repo-relative paths."""
    return sorted(
        line
        for line in _tracked(repo_root, "*ruckus.tcl")
        if not line.startswith("tests/")
    )


def repo_loaded_sources(repo_root):
    """Return the repo-relative paths of the .vhd and .v files that some ruckus.tcl loads.

    Both ``loadSource -path`` files and the files of ``loadSource -dir``
    directories count; the directories are not searched recursively.
    """
    root = Path(repo_root)
    loaded = set()
    for ruckus in repo_ruckus_files(root):
        parent = (root / ruckus).parent
        text = (root / ruckus).read_text(encoding="utf-8")
        found = [parent / relative for relative in LOAD_RE.findall(text)]
        for directory in DIR_LOAD_RE.findall(text):
            found.extend(sorted((parent / directory).glob("*.vhd")))
            found.extend(sorted((parent / directory).glob("*.v")))
        loaded.update(path.relative_to(root).as_posix() for path in found)
    return loaded


def rtl_sources(repo_root):
    """Return the tracked .vhd and .v files under LCLS-I/ and LCLS-II/ outside wrappers directories."""
    return sorted(
        line
        for line in _tracked(repo_root, "LCLS-I", "LCLS-II")
        if line.endswith((".vhd", ".v")) and "wrappers" not in Path(line).parts
    )


def unloaded_sources(repo_root):
    """Return the RTL files that no ruckus.tcl loads, as a set of repo-relative paths."""
    return set(rtl_sources(repo_root)) - repo_loaded_sources(repo_root)


def _tracked(repo_root, *pathspecs):
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", *pathspecs],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()
