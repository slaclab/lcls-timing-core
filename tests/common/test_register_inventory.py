#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Coverage gate: every PyRogue class, YAML map, and register decode has its test.

Test methodology:
    Sweep: the class modules of python/LclsTimingCore, the test and table
        modules of tests/rogue, the YAML maps of yaml/, and the VHDL files of
        LCLS-I and LCLS-II that decode AXI-Lite registers. Five seeded-gap
        cases run the same checks on a copy of those trees with one defect
        introduced.
    Stimulus: pure Python text parsing and ast of the repository files, no
        simulator and no Rogue import. The seeded-gap cases copy the trees and
        tests/ into a tmp_path and edit the copy; the real tree is never
        edited.
    Checks: every class module has tests/rogue/test_<Class>.py and
        tests/rogue/tables/<Class>.py, and the CLASS constant of the table
        (read with ast from the checked tree) equals the module name. Every
        test_<X>.py and tables/<X>.py names a class, except
        test_import_smoke.py and test_register_drift.py, which belong to no
        class. Every yaml/*.yaml file is a key of YAML_CLASSIFICATION and
        every key still exists. Every class is a key of BLOCKS (compared by
        the drift check) or of COVERED_BY_LEAVES. The VHDL files under LCLS-I
        and LCLS-II whose comment-stripped text calls axiSlaveWaitTxn,
        axiSlaveWaitWriteTxn, or axiSlaveWaitReadTxn are exactly the keys of
        DECODE_FILES, so a ninth register decode fails until it is parsed and
        paired with a block. A seeded gap is reported by the name of the
        class, file, or path that has it.
    Timing: none, no clock and no simulated time.
"""

import ast
from pathlib import Path
import re
import shutil

import pytest

from tests.common.ghdl_analysis import _strip_comments
from tests.common.regression_utils import REPO_ROOT
from tests.common.register_drift import BLOCKS, COVERED_BY_LEAVES
from tests.common.vhdl_registers import DECODE_FILES
from tests.common.yaml_maps import YAML_CLASSIFICATION

PACKAGE_DIR = Path("python/LclsTimingCore")
YAML_DIR = Path("yaml")
ROGUE_DIR = Path("tests/rogue")
TABLES_DIR = ROGUE_DIR / "tables"
DECODE_TREES = (Path("LCLS-I"), Path("LCLS-II"))
# Test modules that exercise the whole suite and belong to no class.
CLASSLESS_TESTS = frozenset({"test_import_smoke.py", "test_register_drift.py"})
DECODE_CALL_RE = re.compile(r"\baxiSlaveWait(?:Write|Read)?Txn\b", re.IGNORECASE)
SKIPPED_DIRS = {"sim_build", "__pycache__"}
COPIED_TREES = (
    PACKAGE_DIR,
    YAML_DIR,
    Path("LCLS-I"),
    Path("LCLS-II/core"),
    Path("LCLS-II/evr"),
)


def class_names(root):
    """Return the sorted module stems of the PyRogue class modules under ``root``."""
    return sorted(path.stem for path in (Path(root) / PACKAGE_DIR).glob("*.py") if path.stem != "__init__")


def _table_class(path):
    """Return the CLASS string constant that the table module at ``path`` assigns, or None."""
    for node in ast.parse(Path(path).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CLASS" for t in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    return None


def missing_coverage(root):
    """Return the sorted messages that name each class, table, test, or map without its pairing."""
    root = Path(root)
    classes = class_names(root)
    known = set(classes)
    messages = []
    for name in classes:
        test = root / ROGUE_DIR / f"test_{name}.py"
        table = root / TABLES_DIR / f"{name}.py"
        if not test.is_file():
            messages.append(f"class {name}: missing {ROGUE_DIR}/test_{name}.py")
        if not table.is_file():
            messages.append(f"class {name}: missing {TABLES_DIR}/{name}.py")
        elif _table_class(table) != name:
            messages.append(f"class {name}: {TABLES_DIR}/{name}.py has CLASS {_table_class(table)!r}")
        if name not in BLOCKS and name not in COVERED_BY_LEAVES:
            messages.append(f"class {name}: in neither BLOCKS nor COVERED_BY_LEAVES")
    for test in sorted((root / ROGUE_DIR).glob("test_*.py")):
        if test.name not in CLASSLESS_TESTS and test.stem[len("test_"):] not in known:
            messages.append(f"test module {ROGUE_DIR}/{test.name} names no class")
    for table in sorted((root / TABLES_DIR).glob("*.py")):
        if table.stem != "__init__" and table.stem not in known:
            messages.append(f"table module {TABLES_DIR}/{table.name} names no class")
    maps = {path.name for path in (root / YAML_DIR).glob("*.yaml")}
    for name in sorted(maps - set(YAML_CLASSIFICATION)):
        messages.append(f"yaml map {name}: missing from YAML_CLASSIFICATION")
    for name in sorted(set(YAML_CLASSIFICATION) - maps):
        messages.append(f"yaml map {name}: classified but {YAML_DIR}/{name} does not exist")
    return sorted(messages)


def decode_inventory(root):
    """Return the sorted repository-relative VHDL paths that decode AXI-Lite registers."""
    root = Path(root)
    found = []
    for tree in DECODE_TREES:
        for path in (root / tree).rglob("*.vhd"):
            if SKIPPED_DIRS.intersection(path.parts):
                continue
            text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
            if DECODE_CALL_RE.search(text):
                found.append(path.relative_to(root).as_posix())
    return sorted(found)


def decode_gaps(root):
    """Return the sorted messages for decode files that DECODE_FILES lacks or no longer finds."""
    found = set(decode_inventory(root))
    messages = [f"decode file {name}: not in DECODE_FILES" for name in sorted(found - set(DECODE_FILES))]
    messages += [f"decode file {name}: in DECODE_FILES but decodes nothing" for name in sorted(set(DECODE_FILES) - found)]
    return messages


def all_gaps(root):
    """Return every coverage message of ``root``: classes, tables, maps, and decode files."""
    return sorted(missing_coverage(root) + decode_gaps(root))


@pytest.fixture
def register_sources_copy(tmp_path):
    """A copy of the register trees and tests/ that a test may edit."""
    ignore = shutil.ignore_patterns(*SKIPPED_DIRS, "*.pyc")
    for tree in COPIED_TREES:
        shutil.copytree(REPO_ROOT / tree, tmp_path / tree, ignore=ignore)
    shutil.copytree(REPO_ROOT / "tests", tmp_path / "tests", ignore=ignore)
    return tmp_path


def test_register_coverage_is_complete():
    assert class_names(REPO_ROOT), "no class module found under python/LclsTimingCore"
    assert missing_coverage(REPO_ROOT) == []


def test_decode_inventory_is_exact():
    inventory = decode_inventory(REPO_ROOT)
    assert inventory == sorted(DECODE_FILES), f"decode files found: {inventory}"
    assert decode_gaps(REPO_ROOT) == []


def test_decode_inventory_ignores_comments(tmp_path):
    (tmp_path / "LCLS-I").mkdir()
    rtl = tmp_path / "LCLS-II" / "core" / "rtl"
    rtl.mkdir(parents=True)
    (rtl / "Commented.vhd").write_text("-- axiSlaveWaitTxn(ep, regCon, a, b);\nentity Commented is end;\n", encoding="utf-8")
    (rtl / "Decoded.vhd").write_text("axiSlaveWaitReadTxn(ep, regCon, a, b);\n", encoding="utf-8")
    assert decode_inventory(tmp_path) == ["LCLS-II/core/rtl/Decoded.vhd"]


def _remove(relative):
    def edit(root):
        (root / relative).unlink()
    return edit


def _add_file(relative, text):
    def edit(root):
        (root / relative).write_text(text, encoding="utf-8")
    return edit


NEW_DEVICE = "import pyrogue as pr\n\n\nclass NewDevice(pr.Device):\n    pass\n"
NEW_DECODE = "architecture rtl of NewDecode is\nbegin\n   axiSlaveWaitTxn(ep, axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave);\nend rtl;\n"

SEEDED_GAPS = [
    pytest.param(
        _remove("tests/rogue/test_TPGStatus.py"), "tests/rogue/test_TPGStatus.py", id="remove_test_module"
    ),
    pytest.param(
        _remove("tests/rogue/tables/EvrV1Isr.py"), "tests/rogue/tables/EvrV1Isr.py", id="remove_table_module"
    ),
    pytest.param(
        _add_file("python/LclsTimingCore/NewDevice.py", NEW_DEVICE), "class NewDevice", id="add_class_module"
    ),
    pytest.param(_add_file("yaml/NewMap.yaml", "NewMap: {}\n"), "NewMap.yaml", id="add_yaml_map"),
    pytest.param(
        _add_file("LCLS-II/core/rtl/NewDecode.vhd", NEW_DECODE), "LCLS-II/core/rtl/NewDecode.vhd", id="add_decode_file"
    ),
]


@pytest.mark.parametrize(("edit", "named"), SEEDED_GAPS)
def test_seeded_register_gap_is_reported(register_sources_copy, edit, named):
    root = register_sources_copy
    assert root != REPO_ROOT
    assert all_gaps(root) == [], "the copy must start with no gap"
    edit(root)
    gaps = all_gaps(root)
    assert any(named in message for message in gaps), f"{named} is not named in {gaps}"
