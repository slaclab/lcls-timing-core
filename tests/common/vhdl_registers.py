#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Read an AXI-Lite register decode out of a VHDL file without running anything.

The VHDL text is tokenized and evaluated by a restricted integer evaluator and
is never executed: no VHDL tool runs, and no text is ever handed to Python's
built-in expression evaluator or to an interpreter. The module uses only the
standard library, so it runs in a bare checkout.

``parse_decode`` finds every ``axiSlaveRegister``, ``axiSlaveRegisterR``,
``axiWrDetect``, and ``axiRdDetect`` call of the endpoint form
``(endpoint, address, [bit offset,] target[, constant])``, expands the
``for`` loops that enclose them by evaluating the address and bit expressions
at every loop value (never by extrapolating from two values), drops the calls
under a false ``if`` condition, and reports one ``VhdlField`` per register
field and one ``VhdlStrobe`` per detect call.

Generics, constants of the same file, and constants of the packages named in
``PACKAGE_FILES`` feed the evaluator. A field width comes from a declaration
index keyed by the last identifier of the target; two disagreeing
declarations, or none, give width None and the target is listed in
``Decode.unresolved``. A statement that names a register procedure in a form
this module does not handle raises ``UnsupportedStatement`` with the file and
line, so nothing is skipped silently.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

PACKAGE_FILES = {
    "EvrV2Pkg": "LCLS-II/evr/rtl/EvrV2Pkg.vhd",
}

FIELD_CALLS = ("axislaveregister", "axislaveregisterr")
STROBE_CALLS = {"axiwrdetect": "write", "axirddetect": "read"}


class UnsupportedStatement(Exception):
    """A register statement in a form this module does not handle."""


class EvalError(Exception):
    """An expression the restricted evaluator cannot reduce to a value."""


class Token(NamedTuple):
    kind: str
    value: Any
    line: int


class VhdlField(NamedTuple):
    entity: str
    target: str
    index: Optional[int]
    byte_offset: int
    bit_offset: int
    width: Optional[int]
    readable: bool
    writable: bool
    condition: Optional[str]
    line: int


class VhdlStrobe(NamedTuple):
    entity: str
    target: str
    index: Optional[int]
    byte_offset: int
    kind: str
    line: int


class Decode(NamedTuple):
    entity: str
    fields: List[VhdlField]
    strobes: List[VhdlStrobe]
    unresolved: List[str]


# ---------------------------------------------------------------------------
# surf StdRtlPkg integer functions
# ---------------------------------------------------------------------------

def log2(number: int) -> int:
    """surf log2: 1 below 2, else the ceiling of the base 2 logarithm."""
    if number < 2:
        return 1
    return (number - 1).bit_length()


def bit_size(number: int) -> int:
    """surf bitSize: bits needed to hold values 0 to number."""
    if number in (0, 1):
        return 1
    if number & (number - 1) == 0:
        return log2(number) + 1
    return log2(number)


def _first(*args):
    if not args:
        raise EvalError("function called without arguments")
    return args[0]


def _ite(cond, true_value, false_value):
    return true_value if cond else false_value


FUNCTIONS = {
    "ite": _ite,
    "bitsize": bit_size,
    "log2": log2,
    "toslv": _first,
    "conv_unsigned": _first,
    "conv_integer": _first,
    "conv_std_logic_vector": _first,
    "to_unsigned": _first,
    "to_integer": _first,
    "unsigned": _first,
    "std_logic_vector": _first,
    "slv": _first,
    "integer": _first,
    "natural": _first,
    "positive": _first,
}


# ---------------------------------------------------------------------------
# Tokenizer: one linear pass, no nested-quantifier patterns over the file
# ---------------------------------------------------------------------------

_BIT_BASES = {"x": 16, "b": 2, "o": 8, "ux": 16, "ub": 2, "uo": 8, "sx": 16, "sb": 2, "so": 8}
_NUMBER_RE = re.compile(r"(\d[\d_]*)#([0-9a-fA-F_]+)#|\d[\d_]*")
_TWO_CHAR_OPS = frozenset(("<=", ">=", "=>", ":=", "/=", "**", "<>", "<<", ">>"))


def tokenize(source: str) -> List[Token]:
    """Return the tokens of source with comments dropped."""
    tokens: List[Token] = []
    i, n, line = 0, len(source), 1
    while i < n:
        c = source[i]
        if c == "\n":
            line += 1
            i += 1
        elif c.isspace():
            i += 1
        elif c == "-" and source.startswith("--", i):
            end = source.find("\n", i)
            i = n if end < 0 else end
        elif c.isalpha() or c == "_":
            j = i + 1
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            if j < n and source[j] == '"' and word.lower() in _BIT_BASES:
                end = source.find('"', j + 1)
                if end < 0:
                    raise ValueError(f"line {line}: unterminated bit string")
                digits = source[j + 1:end].replace("_", "")
                try:
                    value = int(digits, _BIT_BASES[word.lower()]) if digits else 0
                except ValueError:
                    value = None
                tokens.append(Token("bits", value, line))
                i = end + 1
            else:
                tokens.append(Token("id", word, line))
                i = j
        elif c.isdigit():
            match = _NUMBER_RE.match(source, i)
            if match.group(2) is not None:
                value = int(match.group(2).replace("_", ""), int(match.group(1).replace("_", "")))
            else:
                value = int(match.group(0).replace("_", ""))
            tokens.append(Token("int", value, line))
            i = match.end()
        elif c == '"':
            j = i + 1
            text = []
            closed = False
            for _ in range(source.count('"', j) + 1):
                end = source.find('"', j)
                if end < 0:
                    break
                text.append(source[j:end])
                if source.startswith('""', end):
                    text.append('"')
                    j = end + 2
                else:
                    i = end + 1
                    closed = True
                    break
            if not closed:
                raise ValueError(f"line {line}: unterminated string")
            tokens.append(Token("str", "".join(text), line))
        elif c == "'" and i + 2 < n and source[i + 2] == "'":
            tokens.append(Token("char", source[i + 1], line))
            i += 3
        elif source[i:i + 2] in _TWO_CHAR_OPS:
            tokens.append(Token("op", source[i:i + 2], line))
            i += 2
        else:
            tokens.append(Token("op", c, line))
            i += 1
    return tokens


def _word(token: Token) -> str:
    return token.value.lower() if token.kind == "id" else ""


def _is_op(token: Token, value: str) -> bool:
    return token.kind == "op" and token.value == value


def _text(tokens) -> str:
    parts = []
    for token in tokens:
        if token.kind == "str":
            parts.append('"' + token.value + '"')
        elif token.kind == "char":
            parts.append("'" + token.value + "'")
        else:
            parts.append(str(token.value))
    return " ".join(parts)


def _split_top(tokens, separator: str) -> List[List[Token]]:
    """Split tokens on an operator at parenthesis depth zero."""
    parts: List[List[Token]] = [[]]
    depth = 0
    for token in tokens:
        if _is_op(token, "("):
            depth += 1
        elif _is_op(token, ")"):
            depth -= 1
        if depth == 0 and _is_op(token, separator):
            parts.append([])
        else:
            parts[-1].append(token)
    return parts


def _find_top(tokens, words) -> int:
    """Index of the first token at depth zero whose lowercase text is in words."""
    depth = 0
    for index, token in enumerate(tokens):
        if _is_op(token, "("):
            depth += 1
        elif _is_op(token, ")"):
            depth -= 1
        elif depth == 0 and (_word(token) in words or (token.kind == "op" and token.value in words)):
            return index
    return -1


def _matching_paren(tokens, start: int) -> int:
    depth = 0
    for index in range(start, len(tokens)):
        if _is_op(tokens[index], "("):
            depth += 1
        elif _is_op(tokens[index], ")"):
            depth -= 1
            if depth == 0:
                return index
    return -1


# ---------------------------------------------------------------------------
# Restricted evaluator: integers, booleans, and strings only
# ---------------------------------------------------------------------------

_LOGICAL = ("and", "or", "xor", "nand", "nor", "xnor")
_RELATIONAL = ("=", "/=", "<", "<=", ">", ">=")


class _Evaluator:
    def __init__(self, tokens, env: Dict[str, Any]):
        self.tokens = list(tokens)
        self.env = env
        self.pos = 0

    def _peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _take(self) -> Token:
        token = self._peek()
        if token is None:
            raise EvalError("unexpected end of expression")
        self.pos += 1
        return token

    def _accept_op(self, *values) -> Optional[str]:
        token = self._peek()
        if token is not None and token.kind == "op" and token.value in values:
            self.pos += 1
            return token.value
        return None

    def _accept_word(self, *words) -> Optional[str]:
        token = self._peek()
        if token is not None and _word(token) in words:
            self.pos += 1
            return _word(token)
        return None

    def run(self):
        value = self.logical()
        if self._peek() is not None:
            raise EvalError(f"unexpected token {self._peek().value!r}")
        return value

    def logical(self):
        value = self.relation()
        for _ in range(len(self.tokens)):
            word = self._accept_word(*_LOGICAL)
            if word is None:
                break
            other = self.relation()
            if word == "and":
                value = bool(value) and bool(other)
            elif word == "or":
                value = bool(value) or bool(other)
            elif word == "xor":
                value = bool(value) != bool(other)
            elif word == "nand":
                value = not (bool(value) and bool(other))
            elif word == "nor":
                value = not (bool(value) or bool(other))
            else:
                value = bool(value) == bool(other)
        return value

    def relation(self):
        value = self.adding()
        op = self._accept_op(*_RELATIONAL)
        if op is None:
            return value
        other = self.adding()
        if op == "=":
            return value == other
        if op == "/=":
            return value != other
        if not (_is_int(value) and _is_int(other)):
            raise EvalError("ordering needs integers")
        return {"<": value < other, "<=": value <= other, ">": value > other, ">=": value >= other}[op]

    def adding(self):
        value = self.term()
        for _ in range(len(self.tokens)):
            op = self._accept_op("+", "-")
            if op is None:
                break
            other = self.term()
            if not (_is_int(value) and _is_int(other)):
                raise EvalError("arithmetic needs integers")
            value = value + other if op == "+" else value - other
        return value

    def term(self):
        value = self.factor()
        for _ in range(len(self.tokens)):
            op = self._accept_op("*", "/")
            word = None if op else self._accept_word("mod", "rem")
            if op is None and word is None:
                break
            other = self.factor()
            if not (_is_int(value) and _is_int(other)):
                raise EvalError("arithmetic needs integers")
            if op == "*":
                value = value * other
            else:
                if other == 0:
                    raise EvalError("division by zero")
                if op == "/":
                    quotient = abs(value) // abs(other)
                    value = quotient if (value >= 0) == (other >= 0) else -quotient
                elif word == "mod":
                    value = value % other
                else:
                    value = value - other * (abs(value) // abs(other)) * (1 if (value >= 0) == (other >= 0) else -1)
        return value

    def factor(self):
        if self._accept_word("not"):
            return not self.factor()
        if self._accept_word("abs"):
            value = self.factor()
            if not _is_int(value):
                raise EvalError("abs needs an integer")
            return abs(value)
        sign = self._accept_op("+", "-")
        if sign is not None:
            value = self.factor()
            if not _is_int(value):
                raise EvalError("sign needs an integer")
            return -value if sign == "-" else value
        value = self.primary()
        if self._accept_op("**"):
            exponent = self.primary()
            if not (_is_int(value) and _is_int(exponent)) or exponent < 0 or exponent > 64:
                raise EvalError("unsupported exponent")
            return value ** exponent
        return value

    def primary(self):
        token = self._take()
        if token.kind == "int":
            return token.value
        if token.kind == "bits":
            if token.value is None:
                raise EvalError("bit string with undefined digits")
            return token.value
        if token.kind == "str":
            return token.value
        if token.kind == "char":
            raise EvalError("character literal")
        if token.kind == "op" and token.value == "(":
            value = self.logical()
            if not self._accept_op(")"):
                raise EvalError("missing closing parenthesis")
            return value
        if token.kind == "id":
            name = token.value.lower()
            if self._accept_op("("):
                args = []
                closed = self._accept_op(")")
                for _ in range(len(self.tokens)):
                    if closed:
                        break
                    args.append(self.logical())
                    closed = self._accept_op(")")
                    if not closed and not self._accept_op(","):
                        raise EvalError("malformed argument list")
                if not closed:
                    raise EvalError("malformed argument list")
                function = FUNCTIONS.get(name)
                if function is None:
                    raise EvalError(f"function {token.value} is not supported")
                try:
                    return function(*args)
                except TypeError as error:
                    raise EvalError(f"bad call of {token.value}: {error}")
            if name == "true":
                return True
            if name == "false":
                return False
            if name in self.env:
                return self.env[name]
            raise EvalError(f"unknown name {token.value}")
        raise EvalError(f"unexpected token {token.value!r}")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def evaluate(tokens, env: Dict[str, Any]):
    """Reduce tokens to an int, bool, or str, or raise EvalError."""
    return _Evaluator(tokens, env).run()


# ---------------------------------------------------------------------------
# Declarations: constants, entity generics, and the width index
# ---------------------------------------------------------------------------

_MODE_WORDS = ("in", "out", "inout", "buffer", "signal", "variable", "constant", "file", "shared")
_ARRAY_RE = re.compile(r"^slv(\d+)array$")


def _range_width(tokens, env) -> Optional[int]:
    parts = None
    for word in ("downto", "to"):
        index = _find_top(tokens, (word,))
        if index >= 0:
            parts = [tokens[:index], tokens[index + 1:]]
            break
    if parts is None:
        return None
    try:
        high, low = evaluate(parts[0], env), evaluate(parts[1], env)
    except EvalError:
        return None
    if not (_is_int(high) and _is_int(low)):
        return None
    return abs(high - low) + 1


def _split_words(tokens, word: str):
    index = _find_top(tokens, (word,))
    return (tokens[:index], tokens[index + 1:]) if index >= 0 else None


def _type_width(tokens, env) -> Optional[int]:
    if not tokens:
        return None
    head = _word(tokens[0])
    paren = tokens[1:]
    inner = None
    if paren and _is_op(paren[0], "(") and _matching_paren(paren, 0) == len(paren) - 1:
        inner = paren[1:-1]
    if head in ("sl", "std_logic", "std_ulogic") and len(tokens) == 1:
        return 1
    if head in ("slv", "std_logic_vector", "unsigned", "signed") and inner is not None:
        return _range_width(inner, env)
    match = _ARRAY_RE.match(head)
    if match and inner is not None:
        return int(match.group(1))
    if head == "slvectorarray" and inner is not None:
        ranges = _split_top(inner, ",")
        if len(ranges) == 2:
            return _range_width(ranges[1], env)
    return None


def _collect_widths(tokens, env, index: Dict[str, set]) -> None:
    """Add every ``names : type`` declaration of tokens to the width index."""
    for position, token in enumerate(tokens):
        if not _is_op(token, ":") or position == 0:
            continue
        names = []
        j = position - 1
        while j >= 0 and tokens[j].kind == "id":
            names.append(tokens[j].value.lower())
            if j >= 2 and _is_op(tokens[j - 1], ",") and tokens[j - 2].kind == "id":
                j -= 2
            else:
                break
        if not names:
            continue
        k = position + 1
        while k < len(tokens) and _word(tokens[k]) in _MODE_WORDS:
            k += 1
        start, depth = k, 0
        while k < len(tokens):
            current = tokens[k]
            if _is_op(current, "("):
                depth += 1
            elif _is_op(current, ")"):
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and (_is_op(current, ":=") or _is_op(current, ";")):
                break
            k += 1
        width = _type_width(tokens[start:k], env)
        for name in names:
            index.setdefault(name, set()).add(width)


def _collect_constants(tokens, env: Dict[str, Any]) -> None:
    """Evaluate ``constant name : type := expression;`` in order of appearance."""
    position = 0
    while position < len(tokens):
        if _word(tokens[position]) != "constant":
            position += 1
            continue
        end = position + 1
        depth = 0
        while end < len(tokens) and not (depth == 0 and _is_op(tokens[end], ";")):
            if _is_op(tokens[end], "("):
                depth += 1
            elif _is_op(tokens[end], ")"):
                depth -= 1
            end += 1
        statement = tokens[position + 1:end]
        position = end + 1
        colon = _find_top(statement, (":",))
        assign = _find_top(statement, (":=",))
        if colon <= 0 or assign < 0:
            continue
        names = [t.value.lower() for t in statement[:colon] if t.kind == "id"]
        try:
            value = evaluate(statement[assign + 1:], env)
        except EvalError:
            continue
        for name in names:
            env[name] = value


def _entity_header(tokens, env: Dict[str, Any]):
    """Return the entity name and evaluate its generic defaults into env."""
    for position in range(len(tokens) - 2):
        if _word(tokens[position]) == "entity" and tokens[position + 1].kind == "id" \
                and _word(tokens[position + 2]) == "is":
            name = tokens[position + 1].value
            after = position + 3
            if after < len(tokens) and _word(tokens[after]) == "generic" and _is_op(tokens[after + 1], "("):
                close = _matching_paren(tokens, after + 1)
                body = tokens[after + 2:close]
                defaults: Dict[str, Any] = {}
                for entry in _split_top(body, ";"):
                    colon = _find_top(entry, (":",))
                    assign = _find_top(entry, (":=",))
                    if colon <= 0 or assign < 0:
                        continue
                    try:
                        value = evaluate(entry[assign + 1:], {**env, **defaults})
                    except EvalError:
                        continue
                    for token in entry[:colon]:
                        if token.kind == "id":
                            defaults[token.value.lower()] = value
                return name, defaults
            return name, {}
    raise UnsupportedStatement("no entity declaration found")


def _used_packages(tokens) -> List[str]:
    found = []
    for position in range(len(tokens) - 5):
        if (_word(tokens[position]) == "use" and tokens[position + 1].kind == "id"
                and _is_op(tokens[position + 2], ".") and tokens[position + 3].kind == "id"
                and _is_op(tokens[position + 4], ".") and _word(tokens[position + 5]) == "all"):
            found.append(tokens[position + 3].value)
    return found


# ---------------------------------------------------------------------------
# Statement structure: a nesting stack over ';' separated chunks
# ---------------------------------------------------------------------------

class _Stmt:
    def __init__(self, tokens, line):
        self.tokens = tokens
        self.line = line


class _For:
    def __init__(self, var, low, high, descending, line):
        self.var, self.low, self.high, self.descending, self.line = var, low, high, descending, line
        self.body: list = []


class _If:
    def __init__(self, cond, line):
        self.line = line
        self.branches: list = [[cond, [], line]]


def _chunks(tokens):
    chunk, depth = [], 0
    for token in tokens:
        if _is_op(token, "("):
            depth += 1
        elif _is_op(token, ")"):
            depth -= 1
        if depth == 0 and _is_op(token, ";"):
            if chunk:
                yield chunk
            chunk = []
        else:
            chunk.append(token)
    if chunk:
        yield chunk


_BLOCK_END_WORDS = ("if", "loop", "case", "process", "generate", "record", "block")
_OPENERS = ("process", "for", "if", "case", "block", "loop", "while")


def _build(tokens, filename):
    root: list = []
    frames: list = []
    skipping = False

    def body():
        for kind, node in reversed(frames):
            if kind == "for":
                return node.body
            if kind == "if":
                return node.branches[-1][1]
        return root

    def pop(*kinds):
        for index in range(len(frames) - 1, -1, -1):
            if frames[index][0] in kinds:
                del frames[index:]
                return

    for chunk in _chunks(tokens):
        if skipping:
            if _word(chunk[0]) == "end" and (len(chunk) == 1 or _word(chunk[1]) not in _BLOCK_END_WORDS):
                skipping = False
            continue
        toks = list(chunk)
        while toks:
            head = _word(toks[0])
            if (len(toks) > 2 and toks[0].kind == "id" and _is_op(toks[1], ":")
                    and _word(toks[2]) in _OPENERS):
                toks = toks[2:]
                continue
            if head in ("procedure", "function", "pure", "impure"):
                if _find_top(toks, ("is",)) >= 0:
                    skipping = True
                toks = []
            elif head == "architecture":
                index = _find_top(toks, ("is",))
                toks = toks[index + 1:] if index >= 0 else []
            elif head == "begin":
                toks = toks[1:]
            elif head == "process":
                toks = toks[1:]
                if toks and _is_op(toks[0], "("):
                    toks = toks[_matching_paren(toks, 0) + 1:]
                if toks and _word(toks[0]) == "is":
                    toks = toks[1:]
                frames.append(("process", None))
            elif head == "case":
                index = _find_top(toks, ("is",))
                toks = toks[index + 1:] if index >= 0 else []
                frames.append(("case", None))
            elif head == "when" and _find_top(toks, ("=>",)) >= 0:
                toks = toks[_find_top(toks, ("=>",)) + 1:]
            elif head == "for" and _find_top(toks, ("loop", "generate")) >= 0:
                index = _find_top(toks, ("loop", "generate"))
                header = toks[1:index]
                parts = _split_words(header, "in")
                if parts is None or len(parts[0]) != 1:
                    raise UnsupportedStatement(f"{filename}:{toks[0].line}: unsupported loop header {_text(header)}")
                descending = _find_top(parts[1], ("downto",)) >= 0
                bounds = _split_words(parts[1], "downto" if descending else "to")
                if bounds is None:
                    raise UnsupportedStatement(f"{filename}:{toks[0].line}: unsupported loop range {_text(parts[1])}")
                node = _For(parts[0][0].value.lower(), bounds[0], bounds[1], descending, toks[0].line)
                body().append(node)
                frames.append(("for", node))
                toks = toks[index + 1:]
            elif head == "if" and _find_top(toks, ("then", "generate")) >= 0:
                index = _find_top(toks, ("then", "generate"))
                node = _If(toks[1:index], toks[0].line)
                body().append(node)
                frames.append(("if", node))
                toks = toks[index + 1:]
            elif head == "elsif" and frames and frames[-1][0] == "if":
                index = _find_top(toks, ("then", "generate"))
                frames[-1][1].branches.append([toks[1:index], [], toks[0].line])
                toks = toks[index + 1:]
            elif head == "else" and frames and frames[-1][0] == "if":
                frames[-1][1].branches.append([None, [], toks[0].line])
                toks = toks[1:]
                if toks and _word(toks[0]) == "generate":
                    toks = toks[1:]
            elif head == "end":
                kind = _word(toks[1]) if len(toks) > 1 else ""
                if kind == "if":
                    pop("if")
                elif kind == "loop":
                    pop("for")
                elif kind == "generate":
                    pop("for", "if")
                elif kind == "case":
                    pop("case")
                elif kind == "process":
                    pop("process")
                toks = []
            else:
                body().append(_Stmt(toks, toks[0].line))
                toks = []
    return root


def _has_register_call(nodes) -> bool:
    for node in nodes:
        if isinstance(node, _Stmt):
            if _call_name(node.tokens):
                return True
        elif isinstance(node, _For):
            if _has_register_call(node.body):
                return True
        elif any(_has_register_call(branch[1]) for branch in node.branches):
            return True
    return False


def _call_name(tokens) -> str:
    """Lowercase register procedure name when a statement starts with one."""
    name = _word(tokens[0])
    if name in FIELD_CALLS or name in STROBE_CALLS:
        return name
    if name.startswith(("axislaveregister", "axilslaveregister")):
        return name
    return ""


# ---------------------------------------------------------------------------
# Executing the structure
# ---------------------------------------------------------------------------

class _Run:
    def __init__(self, entity, filename, env, widths):
        self.entity, self.filename, self.env, self.widths = entity, filename, env, widths
        self.fields: List[VhdlField] = []
        self.strobes: List[VhdlStrobe] = []
        self.unresolved: set = set()

    def fail(self, line, message):
        raise UnsupportedStatement(f"{self.filename}:{line}: {message}")

    def value(self, tokens, env, line, what):
        try:
            result = evaluate(tokens, env)
        except EvalError as error:
            self.fail(line, f"cannot evaluate {what} {_text(tokens)!r}: {error}")
        if not _is_int(result):
            self.fail(line, f"{what} {_text(tokens)!r} is not an integer")
        return result

    def run(self, nodes, env, conds, index):
        for node in nodes:
            if isinstance(node, _Stmt):
                self.statement(node, env, conds, index)
            elif isinstance(node, _For):
                self.loop(node, env, conds)
            else:
                self.branch(node, env, conds, index)

    def loop(self, node, env, conds):
        low = self.value(node.low, env, node.line, "loop bound")
        high = self.value(node.high, env, node.line, "loop bound")
        values = range(low, high - 1, -1) if node.descending else range(low, high + 1)
        for current in values:
            self.run(node.body, {**env, node.var: current}, conds, current)

    def branch(self, node, env, conds, index):
        taken, earlier = None, []
        for cond, nodes, line in node.branches:
            if cond is None:
                taken = (nodes, "not (" + " or ".join(earlier) + ")" if earlier else None)
                break
            try:
                result = evaluate(cond, env)
            except EvalError as error:
                if any(_has_register_call(branch[1]) for branch in node.branches):
                    self.fail(line, f"cannot evaluate condition {_text(cond)!r}: {error}")
                return
            if result:
                taken = (nodes, _text(cond))
                break
            earlier.append(_text(cond))
        if taken is not None:
            extra = [taken[1]] if taken[1] else []
            self.run(taken[0], env, conds + extra, index)

    def target(self, tokens):
        depth, name, slice_tokens = 0, None, None
        for position, token in enumerate(tokens):
            if _is_op(token, "("):
                depth += 1
                if depth == 1 and name is not None and slice_tokens is None:
                    close = _matching_paren(tokens, position)
                    if close > 0:
                        inner = tokens[position + 1:close]
                        if _find_top(inner, ("downto", "to")) >= 0:
                            slice_tokens = inner
                        else:
                            slice_tokens = None
            elif _is_op(token, ")"):
                depth -= 1
            elif depth == 0 and token.kind == "id":
                name, slice_tokens = token.value, None
        return name, slice_tokens

    def statement(self, node, env, conds, index):
        tokens, line = node.tokens, node.line
        name = _call_name(tokens)
        if not name:
            return
        if len(tokens) < 3 or not _is_op(tokens[1], "(") or _matching_paren(tokens, 1) != len(tokens) - 1:
            self.fail(line, f"unsupported form of {tokens[0].value}")
        args = _split_top(tokens[2:-1], ",")
        condition = " and ".join(conds) if conds else None
        if name in STROBE_CALLS:
            if len(args) != 3:
                self.fail(line, f"unsupported form of {tokens[0].value} with {len(args)} arguments")
            address = self.value(args[1], env, line, "address")
            target, _ = self.target(args[2])
            self.strobes.append(VhdlStrobe(self.entity, target, index, address, STROBE_CALLS[name], line))
            return
        if name not in FIELD_CALLS or len(args) not in (4, 5) or (name == "axislaveregisterr" and len(args) != 4):
            self.fail(line, f"unsupported form of {tokens[0].value} with {len(args)} arguments")
        address = self.value(args[1], env, line, "address")
        offset = self.value(args[2], env, line, "bit offset")
        target, slice_tokens = self.target(args[3])
        if target is None:
            self.fail(line, f"no target identifier in {_text(args[3])!r}")
        width = _range_width(slice_tokens, env) if slice_tokens else self.widths.get(target.lower())
        if width is None:
            self.unresolved.add(target)
        self.fields.append(
            VhdlField(self.entity, target, index, address, offset, width, True, name == "axislaveregister", condition, line)
        )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def parse_decode(source: str, filename: str = "<source>", generics: Optional[Dict[str, Any]] = None) -> Decode:
    """Return the register decode found in source (text is parsed, never run)."""
    tokens = tokenize(source)
    env: Dict[str, Any] = {}
    index: Dict[str, set] = {}
    for package in _used_packages(tokens):
        path = PACKAGE_FILES.get(package)
        if path is None:
            continue
        package_tokens = tokenize(read_text(path))
        _collect_constants(package_tokens, env)
        _collect_widths(package_tokens, env, index)
    entity, defaults = _entity_header(tokens, env)
    env.update(defaults)
    env.update({key.lower(): value for key, value in (generics or {}).items()})
    _collect_constants(tokens, env)
    _collect_widths(tokens, env, index)
    widths = {name: next(iter(found)) for name, found in index.items() if len(found) == 1}
    run = _Run(entity, filename, env, widths)
    run.run(_build(tokens, filename), env, [], None)
    return Decode(entity, run.fields, run.strobes, sorted(run.unresolved))


def read_text(path) -> str:
    """Read a repository file as utf-8; relative paths resolve from the repository root."""
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def read_decode(path, generics: Optional[Dict[str, Any]] = None) -> Decode:
    """Return the register decode of the VHDL file at path."""
    return parse_decode(read_text(path), str(path), generics)
