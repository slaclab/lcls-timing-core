#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed expectation tables for the PyRogue device classes.

A table module under tests/rogue/tables/ holds one row per declaration in the
Python source, with the declared offset and bit offset. ``expand`` turns a
table and an argument set into the variables the class must build, and
``diff_variables`` compares that set with the variables of a built tree.

Rogue normalizes offsets to word alignment, so a declaration written as
offset 0x25 bit 5 builds as word 0x24 bit 13. Tables keep the declared values
(they read like the source) and every comparison uses the absolute bit
position, offset * 8 + bit offset.

Table module contract: module level ``CLASS``, ``ROWS``, ``CHILDREN`` (may be
empty), ``ARG_SETS`` (the first entry has id ``default`` and no arguments),
and an optional ``DEFAULTS`` dict that gives count arguments their default.

The module uses only the standard library, so the common leg can run it
without Rogue.
"""

import importlib
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

BITS_PER_BYTE = 8
BOOL_ENUM = {False: "False", True: "True"}


class Row(NamedTuple):
    name: str
    offset: Optional[int] = None
    bit_offset: int = 0
    bit_size: Optional[int] = None
    mode: str = "RW"
    base: str = "UInt"
    enum: Optional[dict] = None
    number: Any = None
    stride: Optional[int] = None
    when: Optional[str] = None
    kind: str = "RemoteVariable"
    overlap_en: bool = False
    depends: Tuple[str, ...] = ()


class Child(NamedTuple):
    name: str
    table: str
    offset: int
    number: Any = None
    stride: Optional[int] = None
    when: Optional[str] = None
    args: Optional[Dict[str, str]] = None


class ArgSet(NamedTuple):
    id: str
    args: dict
    flags: Tuple[str, ...] = ()


class Expected(NamedTuple):
    path: str
    abs_bit: Optional[int]
    bit_size: Optional[int]
    mode: str
    base: Optional[str]
    enum: Optional[dict]
    kind: str
    overlap_en: bool
    depends: Tuple[str, ...]


COMPARED = ("abs_bit", "bit_size", "mode", "base", "enum", "kind", "overlap_en", "depends")


def abs_bit(offset: int, bit_offset: int) -> int:
    """Absolute bit position of a declaration."""
    return offset * BITS_PER_BYTE + bit_offset


def load_table(class_name: str):
    """Import the table module of a class."""
    return importlib.import_module(f"tests.rogue.tables.{class_name}")


def _count(number, arg_set: ArgSet, table) -> Optional[int]:
    if number is None or isinstance(number, int):
        return number
    if number in arg_set.args:
        return arg_set.args[number]
    defaults = getattr(table, "DEFAULTS", {})
    if number in defaults:
        return defaults[number]
    raise KeyError(f"{table.CLASS}: no value for count argument {number!r}")


def expand(table, arg_set: ArgSet, prefix: str = "", base: int = 0) -> Dict[str, Expected]:
    """Return {path: Expected} for table under arg_set."""
    flags = set(arg_set.flags)
    found: Dict[str, Expected] = {}

    def add(entry: Expected) -> None:
        if entry.path in found:
            raise ValueError(f"{table.CLASS}: duplicate variable {entry.path}")
        found[entry.path] = entry

    for row in table.ROWS:
        if row.when is not None and row.when not in flags:
            continue
        count = _count(row.number, arg_set, table)
        indexes = [None] if count is None else range(count)
        enum = row.enum
        if enum is None and row.base == "Bool":
            enum = dict(BOOL_ENUM)
        for index in indexes:
            if row.offset is None:
                position = None
            else:
                shift = 0 if index is None else index * (row.stride or 0)
                position = abs_bit(base + row.offset + shift, row.bit_offset)
            name = row.name if index is None else f"{row.name}[{index}]"
            add(Expected(prefix + name, position, row.bit_size, row.mode, row.base, enum,
                         row.kind, row.overlap_en, tuple(row.depends)))

    for child in getattr(table, "CHILDREN", ()):
        if child.when is not None and child.when not in flags:
            continue
        count = _count(child.number, arg_set, table)
        indexes = [None] if count is None else range(count)
        child_table = load_table(child.table)
        child_flags = tuple(sorted(
            own for own, parent in (child.args or {}).items() if parent in flags
        ))
        child_set = ArgSet(arg_set.id, {}, child_flags)
        for index in indexes:
            shift = 0 if index is None else index * (child.stride or 0)
            label = child.name.format(i=index)
            for entry in expand(child_table, child_set, f"{prefix}{label}.", base + child.offset + shift).values():
                add(entry)
    return found


def diff_variables(expected: Dict[str, Expected], actual: Dict[str, Expected]) -> List[str]:
    """Return sorted messages for every missing, extra, or differing variable."""
    messages = []
    for path in sorted(expected.keys() - actual.keys()):
        messages.append(f"missing from tree: {path}")
    for path in sorted(actual.keys() - expected.keys()):
        messages.append(f"extra in tree: {path}")
    for path in sorted(expected.keys() & actual.keys()):
        for attribute in COMPARED:
            want, got = getattr(expected[path], attribute), getattr(actual[path], attribute)
            if want != got:
                messages.append(f"{path}: {attribute} expected {want!r}, got {got!r}")
    return sorted(messages)


def find_overlaps(entries: Dict[str, Expected], ignore_flag: bool = False,
                  honored=frozenset()) -> List[Tuple[str, str]]:
    """Return sorted path pairs whose absolute bit ranges share at least one bit.

    A pair is skipped when both variables carry overlap_en, and LinkVariables
    have no bits of their own. With ignore_flag the declared overlap_en is
    ignored, except for the variables named in honored; a class whose array
    variables all carry the flag needs this to see an overlap among them.
    """
    ranges = sorted(
        (entry.abs_bit, entry.abs_bit + entry.bit_size, entry)
        for entry in entries.values()
        if entry.kind != "LinkVariable" and entry.abs_bit is not None and entry.bit_size
    )
    pairs = set()
    for i, (start, end, first) in enumerate(ranges):
        for other_start, _, second in ranges[i + 1:]:
            if other_start >= end:
                break
            flagged = [
                entry.overlap_en and (not ignore_flag or entry.path in honored)
                for entry in (first, second)
            ]
            if all(flagged):
                continue
            pairs.add(tuple(sorted((first.path, second.path))))
    return sorted(pairs)
