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

``condition`` is the unparsed test of the innermost enclosing ``if`` (for
example ``useTap`` or ``dmaEnable``), ``not (<test>)`` inside its ``else``
branch, and None outside any ``if``. A declaration without ``mode`` is
reported as ``"RW"``, the PyRogue default, and a missing ``offset`` or
``bitOffset`` reads as 0.
"""

import ast
from pathlib import Path
from typing import Any, List, NamedTuple, Optional

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


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
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
                    )
                )
        else:
            self.found.append(RemoteVar(base, offset, bit_offset, bit_size, mode, condition, node.lineno))


def parse_remote_variables(source: str, filename: str = "<source>") -> List[RemoteVar]:
    """Return the declarations found in ``source`` (text is parsed, never run)."""
    reader = _Reader()
    reader.visit(ast.parse(source, filename=filename))
    return reader.found


def read_remote_variables(path) -> List[RemoteVar]:
    """Return the declarations of the PyRogue file at ``path``, in source order."""
    with open(Path(path), "r", encoding="utf-8") as handle:
        return parse_remote_variables(handle.read(), str(path))


def absolute_bits(var: RemoteVar) -> range:
    """Return the absolute bit positions a variable covers, counted from byte offset 0."""
    for label, value in (("offset", var.offset), ("bit_offset", var.bit_offset), ("bit_size", var.bit_size)):
        if not isinstance(value, int):
            raise ValueError(f"{var.name}: {label} is not a literal ({value!r})")
    start = var.offset * BITS_PER_BYTE + var.bit_offset
    return range(start, start + var.bit_size)
