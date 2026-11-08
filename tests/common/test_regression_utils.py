#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Unit tests for the shared simulator runner helpers.

Test methodology:
    Sweep: fake imported-library trees under a temporary directory (the
        libraries zlib, lcls_timing_core, ruckus, surf and unisim, each
        holding unsorted one-entity VHDL files), plus parameter
        dictionaries that are equal, unequal, long, or slash-bearing.
    Stimulus: regression_utils.BUILD_SRC_ROOT is monkeypatched onto the
        temporary tree, then build_vhdl_sources(), merge_vhdl_sources(),
        _sim_build_suffix() and _sim_build_path() are called directly.
        No simulator is launched.
    Checks: library order is surf, ruckus, then the rest alphabetically
        with files sorted inside each library; a missing library raises
        FileNotFoundError naming every absent library and the make import
        command; None and empty extra sources return the base set
        unchanged; a duplicate file or a re-declared primary unit raises
        ValueError naming the files; parameter sets equal after str()
        share one build directory and any difference gives another; long
        or slash-bearing suffixes collapse to params-<sha256>.
    Timing: none, the helpers only manipulate paths and source text.
"""

import re

import pytest

from tests.common import regression_utils

IMPORT_HINT = 'make MODULES="$PWD" import'
LIBRARIES = ("zlib", "lcls_timing_core", "ruckus", "surf", "unisim")


def write_entity(path, name):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"entity {name} is\nend entity {name};\n")
    return path


@pytest.fixture
def build_tree(tmp_path, monkeypatch):
    """Fake build/SRC_VHDL tree with files created in unsorted order."""
    root = tmp_path / "SRC_VHDL"
    for library in LIBRARIES:
        for stem in ("Zeta", "Alpha", "Mid"):
            write_entity(root / library / f"{stem}.vhd", f"{library}_{stem}")
    monkeypatch.setattr(regression_utils, "BUILD_SRC_ROOT", root)
    return root


def test_build_vhdl_sources_orders_surf_ruckus_then_alphabetical(build_tree):
    sources = regression_utils.build_vhdl_sources()

    assert list(sources) == ["surf", "ruckus", "lcls_timing_core", "unisim", "zlib"]


def test_build_vhdl_sources_sorts_files_inside_each_library(build_tree):
    sources = regression_utils.build_vhdl_sources()

    for library, paths in sources.items():
        assert paths == sorted(paths), library
        assert [path.rsplit("/", 1)[1] for path in paths] == [
            "Alpha.vhd", "Mid.vhd", "Zeta.vhd"
        ]


def test_build_vhdl_sources_names_every_missing_library(build_tree):
    for library in ("ruckus", "lcls_timing_core"):
        for path in (build_tree / library).iterdir():
            path.unlink()
        (build_tree / library).rmdir()

    with pytest.raises(FileNotFoundError) as excinfo:
        regression_utils.build_vhdl_sources()

    message = str(excinfo.value)
    assert "ruckus" in message
    assert "lcls_timing_core" in message
    assert "surf" not in message
    assert IMPORT_HINT in message


def test_merge_vhdl_sources_without_extras_returns_base_unchanged(build_tree):
    base = regression_utils.build_vhdl_sources()

    assert regression_utils.merge_vhdl_sources(base, None) is base
    assert regression_utils.merge_vhdl_sources(base, {}) is base


def test_merge_vhdl_sources_rejects_a_duplicate_imported_file(build_tree):
    base = regression_utils.build_vhdl_sources()
    duplicate = base["surf"][0]

    with pytest.raises(ValueError) as excinfo:
        regression_utils.merge_vhdl_sources(base, {"surf": [duplicate]})

    assert duplicate in str(excinfo.value)


def test_merge_vhdl_sources_rejects_a_redeclared_primary_unit(build_tree, tmp_path):
    base = regression_utils.build_vhdl_sources()
    imported = base["lcls_timing_core"][0]
    clash = write_entity(tmp_path / "wrappers" / "Clash.vhd", "lcls_timing_core_Alpha")

    with pytest.raises(ValueError) as excinfo:
        regression_utils.merge_vhdl_sources(base, {"lcls_timing_core": [str(clash)]})

    message = str(excinfo.value)
    assert str(clash) in message
    assert imported in message


def test_merge_vhdl_sources_appends_a_new_library(build_tree, tmp_path):
    base = regression_utils.build_vhdl_sources()
    extra = write_entity(tmp_path / "wrappers" / "Wrapper.vhd", "Wrapper")

    merged = regression_utils.merge_vhdl_sources(base, {"work": [str(extra)]})

    assert list(merged) == list(base) + ["work"]
    assert merged["work"] == [str(extra)]
    assert "work" not in base


def test_sim_build_path_equal_after_str_conversion_shares_a_directory():
    test_file = regression_utils.TESTS_ROOT / "lcls2_core" / "test_Fake.py"

    assert regression_utils._sim_build_path(test_file, {"Width": 4}) == (
        regression_utils._sim_build_path(test_file, {"Width": "4"})
    )


def test_sim_build_path_differing_values_or_keys_get_different_directories():
    test_file = regression_utils.TESTS_ROOT / "lcls2_core" / "test_Fake.py"
    paths = {
        regression_utils._sim_build_path(test_file, {"Width": 4}),
        regression_utils._sim_build_path(test_file, {"Width": 5}),
        regression_utils._sim_build_path(test_file, {"Depth": 4}),
    }

    assert len(paths) == 3


def test_sim_build_path_without_parameters_is_the_bare_directory():
    test_file = regression_utils.TESTS_ROOT / "lcls2_core" / "test_Fake.py"
    expected = regression_utils.TESTS_ROOT / "sim_build" / "lcls2_core" / "test_Fake"

    assert regression_utils._sim_build_path(test_file, None) == str(expected)
    assert regression_utils._sim_build_path(test_file, {}) == str(expected)


def test_sim_build_suffix_joins_parameters_sorted_by_key():
    assert regression_utils._sim_build_suffix({"b": 1, "a": 2}) == "a=2,b=1"


def test_sim_build_suffix_hashes_slashes_and_long_values():
    hashed = re.compile(r"params-[0-9a-f]{64}")

    assert hashed.fullmatch(regression_utils._sim_build_suffix({"Path": "a/b"}))
    assert hashed.fullmatch(regression_utils._sim_build_suffix({"Path": "a\\b"}))
    assert hashed.fullmatch(regression_utils._sim_build_suffix({"Long": "x" * 200}))
    assert not hashed.fullmatch(regression_utils._sim_build_suffix({"Long": "x" * 100}))
