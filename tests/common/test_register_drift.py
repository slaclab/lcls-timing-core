#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Drift comparison and allowlist verdict on synthetic register fields.

Test methodology:
    Sweep: position kinds (offset, bitOffset, bitSize), the access mode
        capability rule, an empty source against an absent one, name-map
        matching and its hint (single names, array elements, and pieces of
        one register), array reporting, output ordering, an RTL window and
        unparsed RTL arms, the block-level YAML finding, the VHDL adapter
        (joined words, repeated targets, strobes), the report text and its
        atomic write, and the allowlist verdict and validation rules.
    Stimulus: hand-built RegField lists and Decode records for the Python,
        VHDL, and YAML sources, hand-built allowlists, and files under
        tmp_path; no repository register file is read.
    Checks: the exact (block, field, kind) keys that compare returns, the
        reasons verdict returns, the errors validate_allowlist raises, and
        that two calls on the same input give the same list and the same
        report file. A seeded one-bit drift must fail, and so must a stale
        allowlist entry.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import pytest

from tests.common import register_drift as rd
from tests.common import vhdl_registers
from tests.common.register_drift import Drift, RegField

BLOCK = "X"


def _field(source, name, byte, bit, size=8, mode="RW", index=None, readable=None, writable=None):
    if readable is None:
        readable = mode in ("RW", "RO")
    if writable is None:
        writable = mode in ("RW", "WO")
    return RegField(BLOCK, name, index, byte, bit, size, mode, source, 1, readable, writable)


def _keys(drifts):
    return [(d.block, d.field, d.kind) for d in drifts]


def test_compare_equal_position_is_no_drift():
    # Byte 0x24 bit 13 and byte 0x25 bit 5 are the same absolute bit.
    python = [_field("python", "Field", 0x24, 13, 18)]
    vhdl = [_field("vhdl", "Field", 0x25, 5, 18)]
    yaml = [_field("yaml", "Field", 0x25, 5, 18)]
    assert rd.compare(BLOCK, python, vhdl, yaml, {}) == []


@pytest.mark.parametrize(
    "kind, python_args, vhdl_args",
    [
        ("offset", (0x00, 4, 8), (0x04, 4, 8)),
        ("bitOffset", (0x00, 4, 8), (0x00, 5, 8)),
        ("bitSize", (0x00, 4, 8), (0x00, 4, 9)),
    ],
)
def test_compare_position_kinds(kind, python_args, vhdl_args):
    python = [_field("python", "Field", *python_args)]
    vhdl = [_field("vhdl", "Field", *vhdl_args)]
    assert _keys(rd.compare(BLOCK, python, vhdl, None, {})) == [(BLOCK, "Field", kind)]


@pytest.mark.parametrize(
    "python_mode, vhdl_readable, vhdl_writable, drifts",
    [
        ("RW", True, True, False),
        ("RW", True, False, True),
        ("RW", False, True, True),
        ("RO", True, False, False),
        ("RO", True, True, True),
        ("WO", False, True, False),
        ("WO", True, True, False),
        ("WO", True, False, True),
    ],
)
def test_compare_mode_capability_rule(python_mode, vhdl_readable, vhdl_writable, drifts):
    python = [_field("python", "Field", 0, 0, mode=python_mode)]
    vhdl = [_field("vhdl", "Field", 0, 0, mode="RW", readable=vhdl_readable, writable=vhdl_writable)]
    result = rd.compare(BLOCK, python, vhdl, None, {})
    assert _keys(result) == ([(BLOCK, "Field", "mode")] if drifts else [])


def test_compare_mode_python_against_yaml_is_equality():
    python = [_field("python", "Field", 0, 0, mode="WO")]
    yaml = [_field("yaml", "Field", 0, 0, mode="RW")]
    assert _keys(rd.compare(BLOCK, python, None, yaml, {})) == [(BLOCK, "Field", "mode")]


def test_compare_empty_source_reports_missing():
    python = [_field("python", "A", 0, 0), _field("python", "B", 4, 0)]
    assert _keys(rd.compare(BLOCK, python, [], None, {})) == [
        (BLOCK, "A", "missing-in-vhdl"),
        (BLOCK, "B", "missing-in-vhdl"),
    ]
    vhdl = [_field("vhdl", "C", 8, 0)]
    assert _keys(rd.compare(BLOCK, [], vhdl, None, {})) == [(BLOCK, "C", "missing-in-python")]


def test_compare_none_source_not_compared():
    python = [_field("python", "A", 0, 0)]
    assert rd.compare(BLOCK, python, None, None, {}) == []
    assert rd.compare(BLOCK, None, None, None, {}) == []


def test_compare_name_map_pair_matches():
    python = [_field("python", "Source", 0, 0, 4)]
    vhdl = [_field("vhdl", "channel", 0, 0, 4)]
    yaml = [_field("yaml", "SourceMask", 0, 0, 4)]
    name_map = {"Source": {"vhdl": "channel", "yaml": "SourceMask"}}
    assert rd.compare(BLOCK, python, vhdl, yaml, name_map) == []


def test_compare_same_position_hint():
    python = [_field("python", "Source", 0, 0, 4)]
    vhdl = [_field("vhdl", "channel", 0, 0, 4)]
    drifts = rd.compare(BLOCK, python, vhdl, None, {})
    assert _keys(drifts) == [(BLOCK, "Source", "missing-in-vhdl"), (BLOCK, "channel", "missing-in-python")]
    assert all("add a name-map entry" in d.detail for d in drifts)
    assert "same position as channel" in drifts[0].detail
    elsewhere = [_field("vhdl", "channel", 4, 0, 4)]
    assert all("name-map" not in d.detail for d in rd.compare(BLOCK, python, elsewhere, None, {}))


def test_compare_array_reported_once():
    python = [_field("python", "Arr", 0, 8 * i, 4, index=i) for i in range(4)]
    vhdl = [_field("vhdl", "Arr", 0, 8 * i + 1, 4, index=i) for i in range(4)]
    drifts = rd.compare(BLOCK, python, vhdl, None, {})
    assert _keys(drifts) == [(BLOCK, "Arr", "bitOffset")]
    assert "element 0 of 4" in drifts[0].detail


def test_compare_sorted_and_repeatable():
    python = [_field("python", "Zed", 0, 1), _field("python", "Alpha", 4, 0), _field("python", "Mid", 8, 0, 4)]
    vhdl = [_field("vhdl", "Zed", 0, 2), _field("vhdl", "Alpha", 8, 0), _field("vhdl", "Mid", 8, 0, 5)]
    first = rd.compare(BLOCK, python, vhdl, None, {})
    assert first == rd.compare(BLOCK, python, vhdl, None, {})
    assert _keys(first) == sorted(_keys(first))
    assert _keys(first) == [(BLOCK, "Alpha", "offset"), (BLOCK, "Mid", "bitSize"), (BLOCK, "Zed", "bitOffset")]


def test_verdict_seeded_unlisted_drift():
    python = [_field("python", "Field", 0x00, 4)]
    vhdl = [_field("vhdl", "Field", 0x00, 5)]
    drifts = rd.compare("X", python, vhdl, None, {})
    reasons = rd.verdict(drifts, {})
    assert len(reasons) == 1
    assert reasons[0].startswith("unlisted drift: ('X', 'Field', 'bitOffset')")


def test_verdict_listed_drift_passes_and_stale_entry_fails():
    issue = "https://github.com/slaclab/lcls-timing-core/issues/1"
    drifts = [Drift("X", "Field", "bitOffset", "detail")]
    assert rd.verdict(drifts, {("X", "Field", "bitOffset"): issue}) == []
    reasons = rd.verdict([], {("X", "Field", "bitOffset"): issue})
    assert len(reasons) == 1 and "no longer drifts" in reasons[0]


def test_verdict_stale_entry():
    issue = "https://github.com/slaclab/lcls-timing-core/issues/1"
    allowlist = {("X", "Field", "bitOffset"): issue, ("Y", "Other", "offset"): issue}
    reasons = rd.verdict([], allowlist, blocks={"X"})
    assert len(reasons) == 1 and "('X', 'Field', 'bitOffset')" in reasons[0]
    assert len(rd.verdict([], allowlist)) == 2


@pytest.mark.parametrize(
    "entry",
    [
        {("X", "Field", "bogus"): "https://github.com/slaclab/lcls-timing-core/issues/1"},
        {("X", "", "offset"): "https://github.com/slaclab/lcls-timing-core/issues/1"},
        {("", "Field", "offset"): "https://github.com/slaclab/lcls-timing-core/issues/1"},
        {("X", "Field", "offset"): "https://example.com/issues/1"},
        {("X", "Field", "offset"): "https://github.com/slaclab/rogue/issues/1"},
        {("X", "Field", "offset"): ""},
        {("X", "Field"): "https://github.com/slaclab/lcls-timing-core/issues/1"},
    ],
)
def test_validate_allowlist_rejects_bad_entries(entry):
    with pytest.raises(ValueError):
        rd.validate_allowlist(entry)


def test_validate_allowlist_pending_issue():
    entry = {("X", "Field", "offset"): rd.PENDING_ISSUE}
    rd.validate_allowlist(entry, require_filed=False)
    with pytest.raises(ValueError):
        rd.validate_allowlist(entry, require_filed=True)


def test_compare_is_idempotent_over_every_option():
    python = [_field("python", "Arr", 0, 8 * i, 4, index=i) for i in range(4)] + [_field("python", "Late", 0x300, 0)]
    vhdl = [_field("vhdl", "arr", 0, 8 * i + 1, 4, index=i) for i in range(4)]
    yaml = [_field("yaml", "Late", 0x304, 0)]
    name_map = {"Arr": {"vhdl": "arr"}}
    first = rd.compare(BLOCK, python, vhdl, yaml, name_map, (0, 0xFF), frozenset({0x40}))
    assert first == rd.compare(BLOCK, python, vhdl, yaml, name_map, (0, 0xFF), frozenset({0x40}))
    assert first != []


def test_compare_window_leaves_outside_fields_to_python_and_yaml():
    python = [_field("python", "In", 0x00, 0), _field("python", "Out", 0x200, 0)]
    vhdl = [_field("vhdl", "In", 0x00, 0)]
    yaml = [_field("yaml", "In", 0x00, 0), _field("yaml", "Out", 0x204, 0)]
    drifts = rd.compare(BLOCK, python, vhdl, yaml, {}, vhdl_window=(0x000, 0x1FF))
    assert _keys(drifts) == [(BLOCK, "Out", "offset")]
    # Without the window the RTL would report the field missing as well.
    unwindowed = rd.compare(BLOCK, python, vhdl, yaml, {})
    assert (BLOCK, "Out", "missing-in-vhdl") in _keys(unwindowed)


def test_compare_skips_words_whose_rtl_arm_is_unparsed():
    python = [_field("python", "Count", 0x4C, 0, 32)]
    vhdl = []
    assert _keys(rd.compare(BLOCK, python, vhdl, None, {})) == [(BLOCK, "Count", "missing-in-vhdl")]
    assert rd.compare(BLOCK, python, vhdl, None, {}, vhdl_skip=frozenset({0x4C})) == []


def test_unresolved_words_reads_the_word_address():
    assert rd.unresolved_words(["read 0x4C: concatenation", "write 0x4F: x"]) == frozenset({0x4C})
    assert rd.unresolved_words([]) == frozenset()
    with pytest.raises(ValueError):
        rd.unresolved_words(["something else"])


def test_compare_block_reports_an_unreadable_yaml_as_one_finding():
    block = rd.Block("X", None, "X.yaml", (rd.Variant("default", {}, {}, True),))
    python = [_field("python", "A", 0, 0), _field("python", "B", 4, 0)]
    result = rd.compare_block(block, block.variants[0], python, None, None, {}, yaml_unreadable=True)
    assert _keys(result.drifts) == [(BLOCK, "<yaml>", "missing-in-yaml")]
    assert result.sources == ("python",) and result.no_rtl == 2


def test_compare_block_counts_fields_without_rtl():
    block = rd.Block("X", "X.vhd", "X.yaml", (rd.Variant("default", {}, {}, True),), vhdl_window=(0, 0xFF))
    python = [_field("python", "A", 0, 0), _field("python", "B", 0x200, 0), _field("python", "C", 0x4C, 0)]
    vhdl = [_field("vhdl", "A", 0, 0)]
    result = rd.compare_block(block, block.variants[0], python, vhdl, None, {}, vhdl_skip=frozenset({0x4C}))
    assert (result.no_rtl, result.unparsed) == (1, 1)
    assert result.sources == ("python", "vhdl")


def test_block_python_sources_are_known():
    assert {block.python_source for block in rd.BLOCKS.values()} <= {"tree", "ast"}
    assert {name for name, block in rd.BLOCKS.items() if block.python_source == "ast"} == {
        "EvrV1Reg", "TPGStatus", "TPGSeqJump", "TPGSeqState", "TPG",
    }


def test_every_python_class_is_compared_or_covered_by_its_leaves():
    from pathlib import Path

    modules = {path.stem for path in (Path(rd.__file__).resolve().parents[2] / "python" / "LclsTimingCore").glob("*.py")}
    modules.discard("__init__")
    assert modules == set(rd.BLOCKS) | set(rd.COVERED_BY_LEAVES)
    assert not set(rd.BLOCKS) & set(rd.COVERED_BY_LEAVES)


def test_validate_allowlist_block_level_entries():
    issue = "https://github.com/slaclab/lcls-timing-core/issues/1"
    rd.validate_allowlist({("X", "<yaml>", "missing-in-yaml"): issue})
    rd.validate_allowlist({("X", "<vhdl>", "missing-in-vhdl"): rd.PENDING_ISSUE}, require_filed=False)
    with pytest.raises(ValueError):
        rd.validate_allowlist({("X", "<yaml>", "offset"): issue})
    with pytest.raises(ValueError):
        rd.validate_allowlist({("X", "<other>", "missing-in-yaml"): issue})


def test_the_reviewed_allowlist_has_no_unreferenced_placeholder_kind():
    # Every value is a filed issue link or the placeholder, and every link
    # names this repository.
    rd.validate_allowlist(rd.ALLOWLIST)
    assert set(rd.ALLOWLIST.values()) <= {rd.PENDING_ISSUE} | {
        f"https://github.com/slaclab/lcls-timing-core/issues/{n}"
        for n in (214, 215, 217, 218, 222, 223, 224, 225, 226, 227, 228)
    }


def test_split_index_handles_arrays_and_groups():
    assert rd.split_index("Name") == ("Name", None)
    assert rd.split_index("Name[3]") == ("Name", 3)
    assert rd.split_index("Group[2].Name") == ("Group.Name", 2)
    assert rd.split_index("Group[2].Name[5]") == ("Group.Name", 2 * rd.INDEX_RADIX + 5)


def test_name_map_pairs_an_array_element_with_a_scalar():
    python = [_field("python", "Sof", 0, 0, 32)]
    vhdl = [_field("vhdl", "cnt", 0, 0, 32, index=0), _field("vhdl", "cnt", 4, 0, 32, index=1)]
    drifts = rd.compare(BLOCK, python, vhdl, None, {"Sof": {"vhdl": "cnt[0]"}})
    assert _keys(drifts) == [(BLOCK, "cnt", "missing-in-python")]
    assert "cnt[1]" in drifts[0].detail


def test_name_map_pairs_elements_with_an_array():
    python = [_field("python", "Pulse", 4 * i, 0, 32, index=i) for i in range(2)]
    vhdl = [_field("vhdl", "ctl", 0, 0, 32, index=0), _field("vhdl", "pre", 4, 0, 32, index=0)]
    name_map = {"Pulse": {"vhdl_elements": ["ctl[0]", "pre[0]"]}}
    assert rd.compare(BLOCK, python, vhdl, None, name_map) == []
    shifted = [_field("vhdl", "ctl", 0, 0, 32, index=0), _field("vhdl", "pre", 8, 0, 32, index=0)]
    assert _keys(rd.compare(BLOCK, python, shifted, None, name_map)) == [(BLOCK, "Pulse", "offset")]


def test_name_map_joins_pieces_of_one_register():
    python = [_field("python", "Word", 0, 0, 32)]
    pieces = [_field("vhdl", "lo", 0, 0, 16, mode="RO"), _field("vhdl", "hi", 0, 16, 16, mode="RW")]
    name_map = {"Word": {"vhdl_pieces": ["lo", "hi"]}}
    assert rd.compare(BLOCK, python, pieces, None, name_map) == []
    wide = [_field("python", "Word", 0, 0, 24)]
    assert _keys(rd.compare(BLOCK, wide, pieces, None, name_map)) == [(BLOCK, "Word", "bitSize")]


def test_name_map_rejects_an_unknown_key():
    python = [_field("python", "A", 0, 0)]
    with pytest.raises(ValueError):
        rd.compare(BLOCK, python, [], None, {"A": {"vhdl_other": ["a"]}})


def test_first_python_name_owns_a_shared_rtl_name():
    python = [_field("python", "Sel", 0, 0, 11), _field("python", "Type", 0, 11, 2)]
    vhdl = [_field("vhdl", "sel", 0, 0, 13)]
    name_map = {"Sel": {"vhdl": "sel"}, "Type": {"vhdl": "sel"}}
    assert _keys(rd.compare(BLOCK, python, vhdl, None, name_map)) == [
        (BLOCK, "Sel", "bitSize"),
        (BLOCK, "Type", "missing-in-vhdl"),
    ]


def test_a_lone_strobe_is_not_a_register():
    vhdl = [_field("vhdl", "reload!write", 0x40, 0, None, mode="WO")]
    assert rd.compare(BLOCK, [], vhdl, None, {}) == []
    python = [_field("python", "Reload", 0x40, 0, 1, mode="WO")]
    assert rd.compare(BLOCK, python, vhdl, None, {"Reload": {"vhdl": "reload!write"}}) == []


def _decode(fields=(), strobes=()):
    return vhdl_registers.Decode("E", list(fields), list(strobes), [])


def _vfield(target, byte, bit, width, index=None, readable=True, writable=False, target_low=0):
    return vhdl_registers.VhdlField("E", target, index, byte, bit, width, readable, writable, None, 1, target_low)


def test_from_vhdl_joins_back_to_back_words_of_one_target():
    decode = _decode([_vfield("pid", 0x08, 0, 32), _vfield("pid", 0x0C, 0, 32)])
    (field,) = rd.from_vhdl(decode, BLOCK)
    assert (field.name, field.byte_offset, field.bit_size) == ("pid", 0x08, 64)


def test_from_vhdl_keeps_words_apart_that_do_not_join():
    # Seconds first and counter second (descending target bits), different
    # access, or a gap between the words are separate registers.
    descending = _decode([_vfield("ts", 0x60, 0, 32, target_low=32), _vfield("ts", 0x64, 0, 32)])
    assert sorted(f.name for f in rd.from_vhdl(descending, BLOCK)) == ["ts@0x60", "ts@0x64"]
    gap = _decode([_vfield("pid", 0x08, 0, 32), _vfield("pid", 0x10, 0, 32)])
    assert sorted(f.name for f in rd.from_vhdl(gap, BLOCK)) == ["pid@0x10", "pid@0x8"]
    access = _decode([_vfield("pid", 0x08, 0, 32), _vfield("pid", 0x0C, 0, 32, readable=False, writable=True)])
    assert len(rd.from_vhdl(access, BLOCK)) == 2


def test_from_vhdl_names_repeated_targets_by_address_and_bit():
    decode = _decode([_vfield("v", 0x30, 0, 8), _vfield("v", 0x30, 8, 8), _vfield("v", 0x34, 0, 8)])
    assert sorted(f.name for f in rd.from_vhdl(decode, BLOCK)) == ["v@0x30.0", "v@0x30.8", "v@0x34"]


def test_from_vhdl_keeps_loop_indices_only_for_repeated_targets():
    one = rd.from_vhdl(_decode([_vfield("t", 0, 0, 1, index=0)]), BLOCK)
    assert one[0].index is None
    many = rd.from_vhdl(_decode([_vfield("t", 0, 0, 1, index=0), _vfield("t", 4, 0, 1, index=1)]), BLOCK)
    assert [f.index for f in many] == [0, 1]


def test_from_vhdl_adds_strobes_without_a_width():
    strobe = vhdl_registers.VhdlStrobe("E", "go", None, 0x40, "write", 3)
    (field,) = rd.from_vhdl(_decode(strobes=[strobe]), BLOCK)
    assert (field.name, field.mode, field.bit_size, field.byte_offset) == ("go!write", "WO", None, 0x40)


def test_format_report_is_deterministic_and_names_links_and_gaps():
    issue = "https://github.com/slaclab/lcls-timing-core/issues/214"
    block = rd.Block("X", None, "X.yaml", (rd.Variant("default", {}, {}, True),))
    results = [
        rd.BlockResult("X", "default", [Drift("X", "A", "bitOffset", "a detail"), Drift("X", "B", "offset", "b detail")],
                       ("python", "yaml"), 3, 2),
        rd.BlockResult("Y", "default", [], ("python",), 0),
    ]
    allowlist = {("X", "A", "bitOffset"): issue, ("X", "Gone", "offset"): issue, ("Z", "Other", "offset"): issue}
    text = rd.format_report(results, allowlist)
    assert text == rd.format_report(list(reversed(results)), allowlist)
    assert f"drift X default A bitOffset {issue}: a detail" in text
    assert "drift X default B offset unlisted: b detail" in text
    assert "block X variant default: compared python, yaml; 3 fields: no RTL in repo; 2 fields: RTL arm not parsed" in text
    assert "block Y variant default: compared python\n" in text
    assert "stale ('X', 'Gone', 'offset')" in text and "('Z'" not in text
    assert block.name == "X"


def test_write_report_replaces_the_file_and_leaves_no_temporary(tmp_path):
    path = tmp_path / "report.txt"
    rd.write_report(path, "first\n")
    rd.write_report(path, "second\n")
    rd.write_report(path, "second\n")
    assert path.read_text(encoding="utf-8") == "second\n"
    assert [p.name for p in tmp_path.iterdir()] == ["report.txt"]


def test_write_report_keeps_the_old_file_when_the_write_fails(tmp_path):
    path = tmp_path / "report.txt"
    rd.write_report(path, "old\n")
    with pytest.raises(TypeError):
        rd.write_report(path, 12345)
    assert path.read_text(encoding="utf-8") == "old\n"
    assert [p.name for p in tmp_path.iterdir()] == ["report.txt"]
