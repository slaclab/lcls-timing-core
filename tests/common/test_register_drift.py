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
        matching and its hint, array reporting, output ordering, and the
        allowlist verdict and validation rules.
    Stimulus: hand-built RegField lists for the Python, VHDL, and YAML sources
        and hand-built allowlists; no repository file is read.
    Checks: the exact (block, field, kind) keys that compare returns, the
        reasons verdict returns, and the errors validate_allowlist raises. A
        seeded one-bit drift must fail, and so must a stale allowlist entry.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import pytest

from tests.common import register_drift as rd
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
