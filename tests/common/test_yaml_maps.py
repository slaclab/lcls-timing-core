#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Every YAML register map in yaml/ loads, and its defects are pinned exactly.

Test methodology:
    Sweep: all 20 files of yaml/, each loaded with its includes spliced in;
        the parse failures, the unresolved includes, the register shape of
        every map that parses (mode, stride, key names, element counts), and
        small synthetic maps for the loader rules.
    Stimulus: the repository files themselves and synthetic maps written under
        tmp_path, read with PyYAML safe_load only; no Rogue and no simulator.
    Checks: every file is classified once; the set of files that fail to parse
        equals the recorded baseline with the exact error class, line, and
        message; the only unresolved include is TPGSeqMem.yaml; every IntField
        has mode RW or RO; the keys CPSW does not define and the arrays without
        a stride equal the recorded baselines; an include named twice is
        spliced once, in line order; an include outside the map directory and a
        python object tag are rejected. A new finding fails, and a recorded
        finding that disappears fails until its entry is removed. Two gated
        tests state the intended end state (the include resolves, every map
        parses) and fail while the maps are defective.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import os
import textwrap
from pathlib import Path

import pytest
import yaml

from tests.common import yaml_maps as ym

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

REPO_YAML = Path(__file__).resolve().parents[2] / "yaml"


@pytest.fixture(scope="module")
def loaded():
    return ym.load_all()


def test_every_yaml_file_is_classified():
    on_disk = {path.name for path in REPO_YAML.glob("*.yaml")}
    classified = set(ym.YAML_CLASSIFICATION)
    assert on_disk - classified == set(), f"yaml/ files with no classification: {sorted(on_disk - classified)}"
    assert classified - on_disk == set(), f"classified files missing from yaml/: {sorted(classified - on_disk)}"
    assert set(ym.YAML_CLASSIFICATION.values()) == {"drift", "shape"}
    shape = sorted(name for name, kind in ym.YAML_CLASSIFICATION.items() if kind == "shape")
    assert shape == [
        "AmcCarrierDRAM.yaml",
        "BldAxiStream.yaml",
        "EvrV2Module.yaml",
        "EvrV2PulsegenRegs.yaml",
        "EvrV2TriggerPulse.yaml",
    ]


def test_parse_results_match_baseline(loaded):
    assert list(loaded) == sorted(loaded)
    assert ym.defect_verdict(loaded) == []
    assert sorted(name for name, result in loaded.items() if result.error is not None) == sorted(
        ym.KNOWN_YAML_DEFECTS
    )


def test_only_unresolved_include_is_tpgseqmem(loaded):
    unresolved = {name: tuple(result.missing_includes) for name, result in loaded.items() if result.missing_includes}
    assert unresolved == ym.KNOWN_MISSING_INCLUDES


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPG.yaml includes TPGSeqMem.yaml, which does not exist in yaml/; "
        "see https://github.com/slaclab/lcls-timing-core/issues/219; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_yaml_known_issue_tpgseqmem_include(loaded):
    missing = loaded["TPG.yaml"].missing_includes
    assert not missing, f"TPG.yaml includes {missing}, which does not exist in yaml/"


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPG.yaml, TPGControl.yaml, and TPGSeqState.yaml do not parse; "
        "see https://github.com/slaclab/lcls-timing-core/issues/218; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_yaml_known_issue_every_file_parses(loaded):
    failing = sorted(name for name, result in loaded.items() if result.error is not None)
    assert not failing, f"these maps do not parse: {failing}"


def _write(root, name, text):
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


SHAPE_MAP = """
    m:
      class: MMIODev
      children:
        A:
          at:
            offset: 0x0
            nelms: 4
          class: IntField
          mode: RW
        B:
          at:
            offset: 0x20
            nelms: 1
          class: IntField
          mode: RW
        C:
          at:
            offset: 0x30
          class: IntField
          mode: WO
        D:
          at:
            offset: 0x40
          class: IntField
          lsbit: 3
          stribe: 2
"""


def test_flatten_applies_cpsw_defaults(tmp_path):
    _write(
        tmp_path,
        "m.yaml",
        """
        m:
          class: MMIODev
          children:
            A:
              at:
                offset: 0x10
              class: IntField
              mode: RO
            B:
              at:
                offset: 0x20
                nelms: 2
                stride: 4
              class: IntField
              sizeBits: 8
              lsBit: 3
              mode: RW
        """,
    )
    node = ym.load("m.yaml", root=tmp_path).data["m"]
    assert list(ym.flatten(node)) == [
        ym.YamlField("A", None, 0x10, 0, 32, "RO"),
        ym.YamlField("B", 0, 0x20, 3, 8, "RW"),
        ym.YamlField("B", 1, 0x24, 3, 8, "RW"),
    ]


def test_flatten_empty_children_is_empty(tmp_path):
    _write(tmp_path, "m.yaml", "m:\n  class: MMIODev\n  children: {}\n")
    _write(tmp_path, "n.yaml", "n:\n  class: MMIODev\n  children:\n")
    assert list(ym.flatten(ym.load("m.yaml", root=tmp_path).data["m"])) == []
    assert list(ym.flatten(ym.load("n.yaml", root=tmp_path).data["n"])) == []


def test_shape_report_finds_mode_stride_and_unknown_keys(tmp_path):
    _write(tmp_path, "m.yaml", SHAPE_MAP)
    results = ym.load_all(root=tmp_path)
    assert ym.shape_report(results, root=tmp_path) == [
        ("m.yaml", 7, "stride", "A: nelms 4 without stride"),
        ("m.yaml", 20, "mode", "C: mode 'WO' is not RW or RO"),
        ("m.yaml", 24, "mode", "D: mode missing"),
        ("m.yaml", 25, "unknown-key", "lsbit"),
        ("m.yaml", 26, "unknown-key", "stribe"),
    ]


def test_shape_report_flags_unknown_at_key(tmp_path):
    _write(
        tmp_path,
        "m.yaml",
        """
        m:
          class: MMIODev
          children:
            A:
              at:
                offset: 0x0
                strde: 4
              class: IntField
              mode: RW
        """,
    )
    results = ym.load_all(root=tmp_path)
    assert ym.shape_report(results, root=tmp_path) == [("m.yaml", 7, "unknown-key", "at.strde")]


def test_shape_verdict_fails_both_directions():
    report = [("a.yaml", 3, "unknown-key", "lsbit"), ("a.yaml", 9, "stride", "X: nelms 2 without stride")]
    assert ym.shape_verdict(report, unknown_keys=(report[0],), shape_findings=(report[1],)) == []
    new = ym.shape_verdict(report, unknown_keys=(), shape_findings=(report[1],))
    assert len(new) == 1 and "new unknown-key" in new[0] and "lsbit" in new[0]
    stale = ym.shape_verdict([report[1]], unknown_keys=(report[0],), shape_findings=(report[1],))
    assert len(stale) == 1 and "no longer reported" in stale[0] and "remove the entry" in stale[0]


def test_defect_verdict_fails_both_directions():
    bad = ym.YamlLoad(None, [], ("mapping values are not allowed here", 5), "ScannerError")
    good = ym.YamlLoad({}, [], None)
    baseline = {"b.yaml": ("ScannerError", 5, "mapping values")}
    assert ym.defect_verdict({"a.yaml": good, "b.yaml": bad}, baseline) == []
    assert "a.yaml: new parse failure" in ym.defect_verdict({"a.yaml": bad, "b.yaml": bad}, baseline)[0]
    assert "now parses; remove the entry" in ym.defect_verdict({"a.yaml": good, "b.yaml": good}, baseline)[0]
    moved = ym.YamlLoad(None, [], ("mapping values are not allowed here", 6), "ScannerError")
    assert "differs from KNOWN_YAML_DEFECTS" in ym.defect_verdict({"b.yaml": moved}, baseline)[0]


def test_include_named_twice_is_spliced_once_in_line_order(tmp_path):
    _write(tmp_path, "b.yaml", "B: &B\n  y: 2\n")
    _write(tmp_path, "c.yaml", "#include b.yaml\nC:\n  z: 3\n")
    _write(
        tmp_path,
        "a.yaml",
        """
        #include b.yaml
        #include c.yaml
        #include b.yaml
        A:
          <<: *B
          x: 1
        """,
    )
    missing = []
    text = ym.splice(tmp_path / "a.yaml", {"a.yaml"}, missing, root=tmp_path)
    assert missing == []
    assert text.count("B: &B") == 1
    assert text.index("B: &B") < text.index("C:") < text.index("A:")
    assert ym.load("a.yaml", root=tmp_path).data["A"] == {"y": 2, "x": 1}


def test_missing_include_is_recorded_not_skipped(tmp_path):
    _write(tmp_path, "a.yaml", "#include nothing.yaml\nA:\n  x: 1\n")
    result = ym.load("a.yaml", root=tmp_path)
    assert result.missing_includes == ["nothing.yaml"]
    assert result.data == {"A": {"x": 1}}


def test_include_outside_root_is_rejected(tmp_path):
    root = tmp_path / "yaml"
    _write(tmp_path, "outside.yaml", "O:\n  x: 1\n")
    _write(root, "a.yaml", "#include ../outside.yaml\nA:\n  x: 1\n")
    with pytest.raises(ValueError, match="outside"):
        ym.splice(root / "a.yaml", {"a.yaml"}, [], root=root)
    with pytest.raises(ValueError, match="outside"):
        ym.load("a.yaml", root=root)


def test_python_object_tag_is_rejected(tmp_path):
    _write(tmp_path, "a.yaml", "A: !!python/object/apply:os.getcwd []\n")
    with pytest.raises(yaml.constructor.ConstructorError):
        ym.load("a.yaml", root=tmp_path)


PARSEABLE = sorted(set(ym.YAML_CLASSIFICATION) - set(ym.KNOWN_YAML_DEFECTS))


def test_yaml_shape_matches_baseline(loaded):
    report = ym.shape_report(loaded)
    assert ym.shape_verdict(report) == []
    assert all(entry in report for entry in ym.UNKNOWN_KEYS + ym.SHAPE_FINDINGS)
    assert all(entry[2] == "unknown-key" for entry in ym.UNKNOWN_KEYS)
    assert all(entry[2] != "unknown-key" for entry in ym.SHAPE_FINDINGS)


def test_yaml_intfield_counts_cover_every_parseable_file():
    assert sorted(ym.INTFIELD_COUNTS) == PARSEABLE


@pytest.mark.parametrize("name", PARSEABLE)
def test_yaml_intfield_counts(loaded, name):
    count = ym.count_intfields(loaded[name].data, name)
    assert count == ym.INTFIELD_COUNTS[name]
    node = loaded[name].data.get(Path(name).stem)
    if isinstance(node, dict) and count <= 10000:
        assert len(list(ym.flatten(node))) == count


def test_yaml_modes_are_rw_or_ro(loaded):
    assert [entry for entry in ym.shape_report(loaded) if entry[2] == "mode"] == []
