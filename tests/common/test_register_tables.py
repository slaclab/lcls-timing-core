#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Table expansion, variable diff, and overlap check on synthetic data.

Test methodology:
    Sweep: the expansion rules (array rows, count arguments, flags, child
        tables, the automatic Bool enum), the variable diff (empty sides,
        ordering, absolute bit comparison), and the overlap check (touching,
        shared, and overlapEn ranges), each on small hand-built tables.
    Stimulus: synthetic Row, Child, and ArgSet values and table objects built
        in the test; no repository file is read except the one smoke case that
        loads the reviewed EvrV2TriggerReg table.
    Checks: exact path sets, absolute bit positions, and sorted messages; an
        empty side never passes.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

from types import SimpleNamespace

import pytest

from tests.common import register_tables as rt
from tests.common.register_tables import ArgSet, Child, Expected, Row


def _table(rows=(), children=(), defaults=None, name="Synthetic"):
    return SimpleNamespace(CLASS=name, ROWS=tuple(rows), CHILDREN=tuple(children), DEFAULTS=defaults or {})


def _entry(path, start, size, overlap_en=False, kind="RemoteVariable", mode="RW"):
    return Expected(path, start, size, mode, "UInt", None, kind, overlap_en, ())


def test_expand_array_rows():
    table = _table([Row("Name", offset=0x10, bit_offset=2, bit_size=8, number=3, stride=4)])
    found = rt.expand(table, ArgSet("default", {}))
    assert sorted(found) == ["Name[0]", "Name[1]", "Name[2]"]
    assert [found[f"Name[{i}]"].abs_bit for i in range(3)] == [
        0x10 * 8 + 2, 0x14 * 8 + 2, 0x18 * 8 + 2,
    ]


def test_expand_single_element_array():
    table = _table([Row("Name", offset=0x10, bit_size=8, number=1, stride=4)])
    assert sorted(rt.expand(table, ArgSet("default", {}))) == ["Name[0]"]


def test_expand_count_argument():
    table = _table([Row("Name", offset=0, bit_size=8, number="N", stride=4)], defaults={"N": 3})
    assert len(rt.expand(table, ArgSet("set", {"N": 2}))) == 2
    assert len(rt.expand(table, ArgSet("default", {}))) == 3
    with pytest.raises(KeyError):
        rt.expand(_table([Row("Name", offset=0, bit_size=8, number="N", stride=4)]), ArgSet("default", {}))


def test_expand_when_flag():
    table = _table([Row("Always", offset=0, bit_size=1), Row("Optional", offset=4, bit_size=1, when="flag")])
    assert sorted(rt.expand(table, ArgSet("default", {}))) == ["Always"]
    assert sorted(rt.expand(table, ArgSet("flag", {}, ("flag",)))) == ["Always", "Optional"]


def _children(monkeypatch, leaf):
    monkeypatch.setattr(rt, "load_table", lambda name: leaf)


def test_expand_child_copies(monkeypatch):
    leaf = _table([Row("Value", offset=0x04, bit_size=8)], name="Leaf")
    _children(monkeypatch, leaf)
    parent = _table(children=[Child("Copy[{i}]", "Leaf", offset=0x1000, number=2, stride=0x100)])
    found = rt.expand(parent, ArgSet("default", {}))
    assert sorted(found) == ["Copy[0].Value", "Copy[1].Value"]
    assert found["Copy[0].Value"].abs_bit == 0x1004 * 8
    assert found["Copy[1].Value"].abs_bit == 0x1104 * 8


def test_expand_child_follows_parent_flag(monkeypatch):
    leaf = _table([Row("Always", offset=0, bit_size=1), Row("Tap", offset=4, bit_size=1, when="useTap")], name="Leaf")
    _children(monkeypatch, leaf)
    parent = _table(children=[Child("Leaf", "Leaf", offset=0x100, args={"useTap": "useTap"})])
    assert sorted(rt.expand(parent, ArgSet("default", {}))) == ["Leaf.Always"]
    assert sorted(rt.expand(parent, ArgSet("tap", {}, ("useTap",)))) == ["Leaf.Always", "Leaf.Tap"]
    unwired = _table(children=[Child("Leaf", "Leaf", offset=0x100)])
    assert sorted(rt.expand(unwired, ArgSet("tap", {}, ("useTap",)))) == ["Leaf.Always"]


def test_expand_bool_enum():
    table = _table([Row("Flag", offset=0, bit_size=1, base="Bool"),
                    Row("Named", offset=0, bit_offset=1, bit_size=1, enum={0: "Off", 1: "On"})])
    found = rt.expand(table, ArgSet("default", {}))
    assert found["Flag"].enum == {False: "False", True: "True"}
    assert found["Named"].enum == {0: "Off", 1: "On"}


def test_diff_empty_actual_reports_missing():
    expected = rt.expand(_table([Row("A", offset=0, bit_size=1), Row("B", offset=4, bit_size=1)]), ArgSet("d", {}))
    assert rt.diff_variables(expected, {}) == ["missing from tree: A", "missing from tree: B"]


def test_diff_empty_expected_reports_extra():
    actual = {"X": _entry("X", 0, 1), "Y": _entry("Y", 8, 1)}
    assert rt.diff_variables({}, actual) == ["extra in tree: X", "extra in tree: Y"]


def test_diff_messages_sorted():
    expected = {"B": _entry("B", 0, 1), "A": _entry("A", 8, 1), "C": _entry("C", 16, 1)}
    actual = {"Z": _entry("Z", 0, 1), "C": _entry("C", 17, 2), "A": _entry("A", 8, 1)}
    messages = rt.diff_variables(expected, actual)
    assert messages == sorted(messages)
    assert "missing from tree: B" in messages
    assert "extra in tree: Z" in messages
    assert "C: abs_bit expected 16, got 17" in messages
    assert "C: bit_size expected 1, got 2" in messages


def test_diff_uses_absolute_bit():
    declared = rt.expand(_table([Row("Wide", offset=0x25, bit_offset=5, bit_size=18)]), ArgSet("d", {}))
    built = {"Wide": _entry("Wide", 0x24 * 8 + 13, 18)}
    assert declared["Wide"].abs_bit == 0x25 * 8 + 5
    assert rt.diff_variables(declared, built) == []


def test_overlap_touching_ranges_not_reported():
    entries = {"A": _entry("A", 0, 4), "B": _entry("B", 4, 4)}
    assert rt.find_overlaps(entries) == []


def test_overlap_shared_bit_reported_once():
    entries = {"B": _entry("B", 3, 2), "A": _entry("A", 0, 4)}
    assert rt.find_overlaps(entries) == [("A", "B")]


def test_overlap_en_on_both_suppresses():
    entries = {"A": _entry("A", 0, 4, overlap_en=True), "B": _entry("B", 2, 4, overlap_en=True)}
    assert rt.find_overlaps(entries) == []


def test_overlap_en_on_one_reports():
    entries = {"A": _entry("A", 0, 4, overlap_en=True), "B": _entry("B", 2, 4)}
    assert rt.find_overlaps(entries) == [("A", "B")]


def test_overlap_skips_link_variables():
    link = Expected("L", None, None, "RO", None, None, "LinkVariable", False, ("A",))
    assert rt.find_overlaps({"A": _entry("A", 0, 4), "L": link}) == []


def test_load_table_evrv2triggerreg():
    table = rt.load_table("EvrV2TriggerReg")
    assert table.CLASS == "EvrV2TriggerReg"
    assert table.ARG_SETS[0].id == "default" and table.ARG_SETS[0].args == {}


def test_find_overlaps_can_ignore_the_declared_flag():
    def entry(path, start, flagged):
        return rt.Expected(path, start, 8, "RW", "UInt", None, "RemoteVariable", flagged, ())

    # A covers bits 0 to 7, B bits 4 to 11, C bits 6 to 13; only A and B carry the flag.
    entries = {"A": entry("A", 0, True), "B": entry("B", 4, True), "C": entry("C", 6, False)}
    assert rt.find_overlaps(entries) == [("A", "C"), ("B", "C")]
    assert rt.find_overlaps(entries, ignore_flag=True) == [("A", "B"), ("A", "C"), ("B", "C")]
    assert rt.find_overlaps(entries, ignore_flag=True, honored={"A", "B"}) == [("A", "C"), ("B", "C")]
