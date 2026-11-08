#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Coverage gate: every entity that LCLS-II/core/ruckus.tcl loads has a test.

Test methodology:
    Sweep: every loadSource line of LCLS-II/core/ruckus.tcl, the entities
        declared by those files, the toplevels named by every
        tests/**/test_*.py, the entities instantiated by the wrapper behind
        each wrapper toplevel, and the entities instantiated beneath the
        three baseline units (TPGMiniCore, TPGMiniReg, TimingCore). One
        seeded-gap case runs the same check on a copy of the sources where
        one test file is removed.
    Stimulus: pure Python text parsing of the repository files, no simulator.
        The seeded-gap cases copy LCLS-II/core and tests/ into a tmp_path.
    Checks: every loaded entity is a toplevel, an entity instantiated by a
        wrapper toplevel, or one of the baseline units that
        KNOWN_GHDL_UNANALYZABLE already records (imported, never copied; the
        baseline intersected with the loaded entities is exactly the three
        units); every lcls_timing_core entity instantiated in the three
        baseline files and declared by a loaded file is tested or baselined;
        removing the test of one entity makes the check report that entity by
        name.
    Timing: none, no clock and no simulated time.
"""

import re
import shutil
from pathlib import Path

import pytest

from tests.common.ghdl_analysis import ENTITY_RE, KNOWN_GHDL_UNANALYZABLE, _strip_comments
from tests.common.regression_utils import REPO_ROOT

CORE_DIR = Path("LCLS-II/core")
RUCKUS_REL = CORE_DIR / "ruckus.tcl"
WRAPPERS_REL = CORE_DIR / "wrappers"
RTL_REL = CORE_DIR / "rtl"
BASELINE_UNITS = frozenset({"tpgminireg", "tpgminicore", "timingcore"})
BASELINE_FILES = ("TPGMiniCore.vhd", "TPGMiniReg.vhd", "TimingCore.vhd")
LOADED_EXPECTED = 28

LOAD_RE = re.compile(r'^\s*loadSource\s+-lib\s+lcls_timing_core\s+-path\s+"\$::DIR_PATH/([^"]+\.vhd)"', re.MULTILINE)
TOPLEVEL_RE = re.compile(r'toplevel\s*=\s*"(?:[A-Za-z0-9_]+\.)?([A-Za-z0-9_]+)"')
INSTANCE_RE = re.compile(r"\bentity\s+lcls_timing_core\.([a-z][a-z0-9_]*)", re.IGNORECASE)
SKIPPED_DIRS = {"sim_build", "__pycache__"}


def parse_loaded_files(ruckus_tcl):
    """Return the rtl files named by the loadSource lines of ``ruckus_tcl``, in file order."""
    ruckus_tcl = Path(ruckus_tcl)
    text = ruckus_tcl.read_text(encoding="utf-8")
    return [ruckus_tcl.parent / relative for relative in LOAD_RE.findall(text)]


def _source(path):
    return _strip_comments(Path(path).read_text(encoding="utf-8", errors="replace"))


def core_entities(repo_root):
    """Return the lowercase entities declared by the files that ruckus.tcl loads (packages declare none)."""
    entities = set()
    for path in parse_loaded_files(Path(repo_root) / RUCKUS_REL):
        entities.update(name.lower() for name in ENTITY_RE.findall(_source(path)))
    return entities


def _instances_in(path):
    return {name.lower() for name in INSTANCE_RE.findall(_source(path))}


def _test_files(repo_root):
    return sorted(
        path
        for path in (Path(repo_root) / "tests").rglob("test_*.py")
        if not SKIPPED_DIRS.intersection(path.parts)
    )


def tested_entities(repo_root):
    """Return the lowercase entities that some test simulates.

    A toplevel named by a test is tested. A wrapper toplevel also tests every
    lcls_timing_core entity its file instantiates.
    """
    repo_root = Path(repo_root)
    wrappers = {path.stem.lower(): path for path in (repo_root / WRAPPERS_REL).glob("*.vhd")}
    tested = set()
    for test_file in _test_files(repo_root):
        for toplevel in TOPLEVEL_RE.findall(test_file.read_text(encoding="utf-8")):
            name = toplevel.lower()
            tested.add(name)
            if name in wrappers:
                tested.update(_instances_in(wrappers[name]))
    return tested


# The name starts with "test", so keep pytest from collecting this helper.
tested_entities.__test__ = False


def baseline_children(repo_root):
    """Return the loaded entities instantiated by the three baseline files."""
    repo_root = Path(repo_root)
    loaded = core_entities(repo_root)
    children = set()
    for name in BASELINE_FILES:
        children.update(_instances_in(repo_root / RTL_REL / name))
    return children & loaded


def baseline_units(repo_root):
    """Return the loaded entities that KNOWN_GHDL_UNANALYZABLE exempts."""
    return core_entities(repo_root) & set(KNOWN_GHDL_UNANALYZABLE)


def missing_coverage(repo_root):
    """Return the sorted loaded entities, and children of the baseline units, that nothing tests."""
    covered = tested_entities(repo_root) | baseline_units(repo_root)
    return sorted((core_entities(repo_root) | baseline_children(repo_root)) - covered)


@pytest.fixture(scope="module")
def sources_copy(tmp_path_factory):
    """A copy of LCLS-II/core and tests/ that a test may edit."""
    root = tmp_path_factory.mktemp("core_inventory")
    shutil.copytree(REPO_ROOT / CORE_DIR, root / CORE_DIR)
    shutil.copytree(
        REPO_ROOT / "tests",
        root / "tests",
        ignore=shutil.ignore_patterns(*SKIPPED_DIRS, "*.pyc"),
    )
    return root


def test_every_loaded_core_entity_is_tested_or_baselined():
    loaded = parse_loaded_files(REPO_ROOT / RUCKUS_REL)
    assert len(loaded) == LOADED_EXPECTED, f"ruckus.tcl loads {len(loaded)} files, expected {LOADED_EXPECTED}"
    assert all(path.is_file() for path in loaded), f"a loaded file is missing: {[p for p in loaded if not p.is_file()]}"
    entities = core_entities(REPO_ROOT)
    assert "bsacontrol" in entities, "BsaControlv2.vhd must contribute the entity bsacontrol"
    missing = missing_coverage(REPO_ROOT)
    assert not missing, "loaded core entities without a test: " + ", ".join(missing)


def test_core_baseline_is_exactly_the_three_units():
    assert baseline_units(REPO_ROOT) == BASELINE_UNITS, (
        f"baseline units among the loaded entities: {sorted(baseline_units(REPO_ROOT))}"
    )


def test_children_of_baseline_units_are_tested():
    children = baseline_children(REPO_ROOT)
    assert {"tpgminireg", "tpgmini", "tpgministream", "timingrx", "tpgminicore", "ethtimingmodule"} <= children, (
        f"children found beneath the baseline units: {sorted(children)}"
    )
    covered = tested_entities(REPO_ROOT) | baseline_units(REPO_ROOT)
    untested = sorted(children - covered)
    assert not untested, "entities instantiated beneath the baseline units without a test: " + ", ".join(untested)


@pytest.mark.parametrize(
    ("test_name", "entity"),
    [("test_Divider.py", "divider"), ("test_TPGMiniStream.py", "tpgministream")],
)
def test_seeded_missing_test_is_reported(sources_copy, test_name, entity):
    assert missing_coverage(sources_copy) == [], "the copy must start fully covered"
    removed = next((sources_copy / "tests").rglob(test_name))
    saved = removed.read_text(encoding="utf-8")
    removed.unlink()
    try:
        assert missing_coverage(sources_copy) == [entity], f"removing {test_name} must report exactly {entity}"
    finally:
        removed.write_text(saved, encoding="utf-8")
