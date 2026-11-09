#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Read literal module constants of a Python file without importing it.

A test module of the regression imports cocotb, so a reader that only needs its
register tables cannot import it. This module parses the file with ``ast`` and
evaluates only an explicit set of node types: constants, tuples, lists, dicts,
names bound earlier in the same module, ``*range(a, b)`` inside a tuple or
list, a unary minus, and calls of helpers named in a ``calls`` map. Anything
else raises ``ValueError`` naming the constant, so a table that stops being a
literal fails loudly instead of being read wrongly. Nothing in the file is
executed.

``calls`` maps a helper name to ``(argument names, defaults)``. A call of the
helper evaluates to a dict from each argument name to the value passed, with
the default filled in where the call omits it. The register walk tables use
this for ``_field(name, lsb, width, mode="RW", condition=None)``.
"""

import ast
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

_MAX_RANGE = 4096

CallSpec = Tuple[Sequence[str], Mapping[str, Any]]


class _Evaluator:
    def __init__(self, assigns: Dict[str, ast.AST], calls: Mapping[str, CallSpec], filename: str):
        self.assigns = assigns
        self.calls = calls
        self.filename = filename
        self.cache: Dict[str, Any] = {}
        self.active: list = []

    def constant(self, name: str) -> Any:
        if name in self.cache:
            return self.cache[name]
        if name not in self.assigns:
            raise ValueError(f"{self.filename}: constant {name} is not assigned at module level")
        if name in self.active:
            raise ValueError(f"{self.filename}: constant {name} refers to itself")
        self.active.append(name)
        try:
            value = self.node(self.assigns[name], name)
        finally:
            self.active.pop()
        self.cache[name] = value
        return value

    def fail(self, name: str, node: ast.AST, why: str):
        raise ValueError(f"{self.filename}: constant {name} line {getattr(node, 'lineno', '?')}: {why}")

    def sequence(self, elements, name):
        values = []
        for element in elements:
            if isinstance(element, ast.Starred):
                values.extend(self.expand(element.value, name))
            else:
                values.append(self.node(element, name))
        return values

    def expand(self, node, name):
        call = node
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "range"
                and not call.keywords and 1 <= len(call.args) <= 3):
            args = [self.node(arg, name) for arg in call.args]
            if not all(isinstance(arg, int) and not isinstance(arg, bool) for arg in args):
                self.fail(name, node, "range bounds are not integers")
            result = range(*args)
            if len(result) > _MAX_RANGE:
                self.fail(name, node, f"range of {len(result)} values is too large")
            return list(result)
        self.fail(name, node, "only *range(...) may be starred")

    def helper(self, node, name):
        spec = self.calls.get(node.func.id)
        if spec is None:
            self.fail(name, node, f"call of {node.func.id} is not allowed")
        names, defaults = spec
        values = dict(defaults)
        if len(node.args) > len(names):
            self.fail(name, node, f"too many arguments for {node.func.id}")
        for argument, value in zip(names, node.args):
            values[argument] = self.node(value, name)
        for keyword in node.keywords:
            if keyword.arg is None or keyword.arg not in names:
                self.fail(name, node, f"unknown keyword for {node.func.id}")
            values[keyword.arg] = self.node(keyword.value, name)
        missing = [argument for argument in names if argument not in values]
        if missing:
            self.fail(name, node, f"{node.func.id} lacks {missing}")
        return {argument: values[argument] for argument in names}

    def node(self, node: ast.AST, name: str) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Tuple):
            return tuple(self.sequence(node.elts, name))
        if isinstance(node, ast.List):
            return self.sequence(node.elts, name)
        if isinstance(node, ast.Dict):
            result = {}
            for key, value in zip(node.keys, node.values):
                if key is None:
                    self.fail(name, node, "dict unpacking is not allowed")
                result[self.node(key, name)] = self.node(value, name)
            return result
        if isinstance(node, ast.Name):
            return self.constant(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value = self.node(node.operand, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                self.fail(name, node, "unary minus needs a number")
            return -value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            return self.helper(node, name)
        return self.fail(name, node, f"{type(node).__name__} is not a literal")


def _assignments(tree: ast.Module) -> Dict[str, ast.AST]:
    assigns: Dict[str, ast.AST] = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 \
                and isinstance(statement.targets[0], ast.Name):
            assigns[statement.targets[0].id] = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) \
                and statement.value is not None:
            assigns[statement.target.id] = statement.value
    return assigns


def read_constants(path, names: Sequence[str], calls: Optional[Mapping[str, CallSpec]] = None) -> Dict[str, Any]:
    """Return ``{name: value}`` for module-level constants of the Python file at path.

    Relative paths resolve from the repository root. A name that is missing or
    whose value is not a literal raises ``ValueError`` naming it.
    """
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    with open(path, "r", encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=str(path))
    evaluator = _Evaluator(_assignments(tree), calls or {}, str(path))
    result = {}
    for name in names:
        try:
            result[name] = evaluator.constant(name)
        except ValueError as error:
            if f"constant {name}" in str(error):
                raise
            raise ValueError(f"constant {name} cannot be read: {error}") from error
    return result
