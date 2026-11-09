#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Read PyRogue register declarations from source text without importing Rogue.

``read_remote_variables`` parses a PyRogue device file with the standard
library ``ast`` module and returns one ``RemoteVar`` for every
``pr.RemoteVariable(...)`` call and one per element of every
``self.addRemoteVariables(...)`` call, in source order. Each keyword is read
with ``ast.literal_eval``; a keyword that is not a literal (for example a
``bitSize`` taken from a constructor argument) becomes ``NON_LITERAL``. The
source is never executed, compiled, or imported, and ``pyrogue`` and
``rogue`` are never imported, so the reader runs in any test process and in
parallel workers: the file is opened read-only and no module state is kept.

``overlap_en``, ``base``, and ``enum`` carry the ``overlapEn`` literal (False
when absent), the last attribute name of the ``base`` expression (``pr.Bool``
reads as ``Bool``, absent reads as ``UInt``, a non-attribute expression is
``NON_LITERAL``), and the ``enum`` literal (None when absent).
``description`` is the ``description`` keyword when it is a literal string
(None when absent, ``NON_LITERAL`` when it is not a literal), and
``read_descriptions`` returns it per base variable name for a class file.
``read_child_devices`` lists the ``self.add(<module>.<Class>(...))`` calls of
a composite device, in source order, with the class name, the ``name`` keyword
(the class name when absent), and the ``offset`` literal.
``expected_entries`` turns declarations into the ``Expected`` records that the
table comparisons use.

``condition`` is the unparsed test of the innermost enclosing ``if`` (for
example ``useTap`` or ``dmaEnable``), ``not (<test>)`` inside its ``else``
branch, and None outside any ``if``. A declaration without ``mode`` is
reported as ``"RW"``, the PyRogue default, and a missing ``offset`` or
``bitOffset`` reads as 0.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

NON_LITERAL = "<non-literal>"

REMOTE_VARIABLE = "RemoteVariable"
REMOTE_VARIABLES = "addRemoteVariables"
BITS_PER_BYTE = 8


class RemoteVar(NamedTuple):
    """One register variable as declared in the PyRogue source."""

    name: str
    offset: Any
    bit_offset: Any
    bit_size: Any
    mode: str
    condition: Optional[str]
    line: int
    overlap_en: bool = False
    base: Any = "UInt"
    enum: Any = None
    description: Optional[str] = None


class ChildDevice(NamedTuple):
    """One ``self.add(<module>.<Class>(...))`` call of a composite device."""

    name: str
    cls: str
    offset: Any
    line: int


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return NON_LITERAL


def _base_name(node: Optional[ast.AST]) -> Any:
    if node is None:
        return "UInt"
    if isinstance(node, ast.Attribute):
        return node.attr
    return NON_LITERAL


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


class _Reader(ast.NodeVisitor):
    def __init__(self) -> None:
        self.conditions: List[str] = []
        self.found: List[RemoteVar] = []

    def visit_If(self, node: ast.If) -> None:
        test = ast.unparse(node.test)
        self.visit(node.test)
        self.conditions.append(test)
        for child in node.body:
            self.visit(child)
        self.conditions.pop()
        self.conditions.append(f"not ({test})")
        for child in node.orelse:
            self.visit(child)
        self.conditions.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        if name in (REMOTE_VARIABLE, REMOTE_VARIABLES):
            self._record(node, name)
        self.generic_visit(node)

    def _record(self, node: ast.Call, kind: str) -> None:
        keywords = {kw.arg: _literal(kw.value) for kw in node.keywords if kw.arg is not None}
        raw_base = next((kw.value for kw in node.keywords if kw.arg == "base"), None)
        extra = {
            "overlap_en": keywords.get("overlapEn", False),
            "base": _base_name(raw_base),
            "enum": keywords.get("enum"),
            "description": keywords.get("description"),
        }
        base = keywords.get("name", NON_LITERAL)
        offset = keywords.get("offset", 0)
        bit_offset = keywords.get("bitOffset", 0)
        bit_size = keywords.get("bitSize", NON_LITERAL)
        mode = keywords.get("mode", "RW")
        condition = self.conditions[-1] if self.conditions else None
        number = keywords.get("number")
        stride = keywords.get("stride")
        expandable = (
            kind == REMOTE_VARIABLES
            and isinstance(number, int)
            and isinstance(stride, int)
            and isinstance(offset, int)
        )
        if expandable:
            for index in range(number):
                self.found.append(
                    RemoteVar(
                        f"{base}[{index}]",
                        offset + index * stride,
                        bit_offset,
                        bit_size,
                        mode,
                        condition,
                        node.lineno,
                        **extra,
                    )
                )
        else:
            self.found.append(
                RemoteVar(base, offset, bit_offset, bit_size, mode, condition, node.lineno, **extra)
            )


def parse_remote_variables(source: str, filename: str = "<source>") -> List[RemoteVar]:
    """Return the declarations found in ``source`` (text is parsed, never run)."""
    reader = _Reader()
    reader.visit(ast.parse(source, filename=filename))
    return reader.found


def read_remote_variables(path) -> List[RemoteVar]:
    """Return the declarations of the PyRogue file at ``path``, in source order."""
    with open(Path(path), "r", encoding="utf-8") as handle:
        return parse_remote_variables(handle.read(), str(path))


def read_descriptions(path) -> Dict[str, Optional[str]]:
    """Return {base variable name: description} for the PyRogue file at ``path``.

    The base name is the declared ``name`` without an element index, so every
    element of an array declaration shares one entry. The description is the
    literal ``description`` keyword, None when the declaration has none. A
    name declared twice (in both branches of an ``if``) keeps its first
    description that is not None.
    """
    found: Dict[str, Optional[str]] = {}
    for var in read_remote_variables(path):
        name = var.name.split("[", 1)[0]
        if found.get(name) is None:
            found[name] = var.description
    return found


def absolute_bits(var: RemoteVar) -> range:
    """Return the absolute bit positions a variable covers, counted from byte offset 0."""
    for label, value in (("offset", var.offset), ("bit_offset", var.bit_offset), ("bit_size", var.bit_size)):
        if not isinstance(value, int):
            raise ValueError(f"{var.name}: {label} is not a literal ({value!r})")
    start = var.offset * BITS_PER_BYTE + var.bit_offset
    return range(start, start + var.bit_size)


def expected_entries(variables: List[RemoteVar]) -> Dict[str, Any]:
    """Return {name: Expected} for declarations read from source.

    The absolute bit position comes from the declared offset and bit offset
    (None when either is not a literal), a Bool variable gets Rogue's
    automatic ``False``/``True`` enum, and every entry is a RemoteVariable
    with no dependencies. Names must be unique, as they are for the classes
    this is used on.
    """
    from tests.common import register_tables

    found: Dict[str, Any] = {}
    for var in variables:
        if var.name in found:
            raise ValueError(f"duplicate declaration {var.name}")
        if isinstance(var.offset, int) and isinstance(var.bit_offset, int):
            position = register_tables.abs_bit(var.offset, var.bit_offset)
        else:
            position = None
        enum = var.enum
        if enum is None and var.base == "Bool":
            enum = dict(register_tables.BOOL_ENUM)
        found[var.name] = register_tables.Expected(
            var.name, position, var.bit_size, var.mode, var.base, enum,
            "RemoteVariable", var.overlap_en, (),
        )
    return found


class _ChildReader(ast.NodeVisitor):
    def __init__(self) -> None:
        self.rogue_aliases = set()
        self.found: List[ChildDevice] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "pyrogue":
                self.rogue_aliases.add(alias.asname or alias.name)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "add"
            and isinstance(func.value, ast.Name)
            and func.value.id == "self"
            and node.args
            and isinstance(node.args[0], ast.Call)
        ):
            inner = node.args[0]
            target = inner.func
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id not in self.rogue_aliases
            ):
                keywords = {kw.arg: _literal(kw.value) for kw in inner.keywords if kw.arg is not None}
                self.found.append(
                    ChildDevice(
                        keywords.get("name", target.attr),
                        target.attr,
                        keywords.get("offset", 0),
                        node.lineno,
                    )
                )
        self.generic_visit(node)


def read_child_devices(path) -> List[ChildDevice]:
    """Return the child devices a composite PyRogue file adds, in source order.

    Only ``self.add(<module>.<Class>(...))`` calls count, and a call through
    the alias that ``import pyrogue as <alias>`` binds (``pr.RemoteVariable``,
    ``pr.LinkVariable``) is never a child device. The file is parsed, never
    run.
    """
    with open(Path(path), "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=str(path))
    reader = _ChildReader()
    reader.visit(tree)
    return reader.found
