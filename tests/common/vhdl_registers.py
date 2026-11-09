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

Local wrapper procedures whose body is one register call are mapped through
that call (arguments substituted, declarations skipped), the classic overloads
that take the AXI-Lite masters and slaves are read, ``muxSlVectorArray(array,
k)`` targets take the width of the array element, and ``a.b'length`` resolves
through the declaration of ``b``.

The hand-written decodes (``case wrPntr is``, ``case rdPntr is`` with an
optional nested ``case regAddr(3 downto 2)`` and an index variable such as
``iseq := conv_integer(regAddr(8 downto 4))``) give one ``VhdlField`` per
assignment from the write data or into the read data. ``bit_offset`` is the
position in the word, ``target_low`` the position in the named signal, and
whole-word assignments are 32 bits wide. A range choice with an index variable
expands to its elements (capped by the declared array length); any other range
choice is a ``VhdlWindow``. Little-endian word slices of one target merge into
one wide field, and a read arm and a write arm of the same target, byte, bit,
and width become one field with both flags. An arm that assigns something but
decodes no data is a strobe. A read or write the parser cannot interpret (a
concatenation, a function of the data) is listed in ``Decode.unresolved`` as
``read 0x4C: concatenation``, so it is pinned rather than skipped. A single
non-range selection after the target name is read as an element index.

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
from typing import Any, Dict, List, NamedTuple, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

PACKAGE_FILES = {
    "EvrV2Pkg": "LCLS-II/evr/rtl/EvrV2Pkg.vhd",
    "TimingPkg": "LCLS-II/core/rtl/TimingPkg.vhd",
    "TPGPkg": "LCLS-II/core/rtl/TPGPkg.vhd",
}

LENGTH_SUFFIX = "'length"
WORD_BITS = 32
# The register decode files, each with the PyRogue block it describes.
DECODE_FILES = {
    "LCLS-I/evr/EvrV1CoreIsrCtrl.vhd": "EvrV1Isr",
    "LCLS-I/evr/EvrV1Reg.vhd": "EvrV1Reg",
    "LCLS-II/core/rtl/GthRxAlignCheck.vhd": "GthRxAlignCheck",
    "LCLS-II/core/rtl/TimingRx.vhd": "TimingFrameRx",
    "LCLS-II/core/rtl/TPGMiniReg.vhd": "TPGMiniCore",
    "LCLS-II/evr/rtl/EvrV2Axi.vhd": "EvrV2Core",
    "LCLS-II/evr/rtl/EvrV2ChannelReg.vhd": "EvrV2ChannelReg",
    "LCLS-II/evr/rtl/EvrV2TrigReg.vhd": "EvrV2TriggerReg",
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
    target_low: int = 0


class VhdlStrobe(NamedTuple):
    entity: str
    target: str
    index: Optional[int]
    byte_offset: int
    kind: str
    line: int


class VhdlWindow(NamedTuple):
    """A range of byte addresses decoded as one block (a memory or a buffer)."""

    entity: str
    target: Optional[str]
    first_byte: int
    last_byte: int
    readable: bool
    writable: bool
    line: int


class Decode(NamedTuple):
    entity: str
    fields: List[VhdlField]
    strobes: List[VhdlStrobe]
    unresolved: List[str]
    windows: Sequence[VhdlWindow] = ()


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
            attribute = self._length_attribute(name)
            if attribute is not None:
                return attribute
            if name in self.env:
                return self.env[name]
            raise EvalError(f"unknown name {token.value}")
        raise EvalError(f"unexpected token {token.value!r}")

    def _length_attribute(self, name):
        """Value of ``a.b'length`` (the last name of the selection) when it follows, else None."""
        position = self.pos
        for _ in range(len(self.tokens)):
            after = self.tokens[position:position + 2]
            if len(after) == 2 and _is_op(after[0], ".") and after[1].kind == "id":
                name = after[1].value.lower()
                position += 2
            else:
                break
        after = self.tokens[position:position + 2]
        if len(after) == 2 and _is_op(after[0], "'") and _word(after[1]) == "length":
            key = name + LENGTH_SUFFIX
            if key not in self.env:
                raise EvalError(f"length of {name} is not declared")
            self.pos = position + 2
            return self.env[key]
        return None


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


def _type_length(tokens, env) -> Optional[int]:
    """Element count of an array declaration, None for a scalar or an unresolved range."""
    if not tokens:
        return None
    head = _word(tokens[0])
    paren = tokens[1:]
    if not (paren and _is_op(paren[0], "(") and _matching_paren(paren, 0) == len(paren) - 1):
        return None
    inner = paren[1:-1]
    if _ARRAY_RE.match(head) or head in ("slv", "std_logic_vector", "unsigned", "signed"):
        return _range_width(inner, env)
    if head == "slvectorarray":
        ranges = _split_top(inner, ",")
        return _range_width(ranges[0], env) if len(ranges) == 2 else None
    return None


def _collect_widths(tokens, env, index: Dict[str, set]) -> None:
    """Add every ``names : type`` declaration of tokens to the width index.

    The same index holds ``name'length`` entries for the declared arrays, so a
    loop bound such as ``r.sample'length`` resolves through the declaration.
    """
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
        length = _type_length(tokens[start:k], env)
        for name in names:
            index.setdefault(name, set()).add(width)
            if length is not None:
                index.setdefault(name + LENGTH_SUFFIX, set()).add(length)


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


class _Case:
    def __init__(self, selector, line):
        self.selector, self.line = selector, line
        self.arms: list = []


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


class _Proc:
    """A user procedure whose body is one register call: formal names and the call tokens."""

    def __init__(self, params, call):
        self.params, self.call = params, call


def _param_names(header) -> List[str]:
    """Formal parameter names of a procedure header ``name ( a, b : in slv; c : in sl )``."""
    if len(header) < 2 or not _is_op(header[1], "("):
        return []
    close = _matching_paren(header, 1)
    names: List[str] = []
    for entry in _split_top(header[2:close], ";"):
        colon = _find_top(entry, (":",))
        names.extend(t.value.lower() for t in entry[:colon] if t.kind == "id")
    return names


def _read_ack_call(statements, params):
    """The read-only register call a read-with-acknowledge procedure body stands for, or None.

    The body matches the address with ``std_match(..., addr)`` and copies
    ``reg`` into ``rdata(reg'range)``; it decodes one read-only register at
    offset 0, the same as the two argument wrapper.
    """
    address = register = None
    for chunk in statements:
        for position, token in enumerate(chunk):
            if _word(token) == "std_match" and position + 1 < len(chunk) and _is_op(chunk[position + 1], "("):
                close = _matching_paren(chunk, position + 1)
                last = _split_top(chunk[position + 2:close], ",")[-1]
                if len(last) == 1 and last[0].kind == "id" and last[0].value.lower() in params:
                    address = last[0].value
            if _word(token) == "rdata" and _find_top(chunk, (":=",)) > position:
                value = chunk[_find_top(chunk, (":=",)) + 1:]
                if len(value) == 1 and value[0].kind == "id" and value[0].value.lower() in params:
                    register = value[0].value
    if address is None or register is None:
        return None
    return tokenize(f"axiSlaveRegister(axiReadMaster, axiReadSlave, axiStatus, {address}, 0, {register})")


def _procedure(header, chunks) -> Optional[_Proc]:
    """Build a _Proc from a declaration ``header`` (tokens before ``is``) and its body chunks."""
    params = _param_names(header)
    statements = []
    begun = False
    for chunk in chunks:
        if not chunk:
            continue
        if not begun:
            if _word(chunk[0]) != "begin":
                continue
            begun = True
            chunk = chunk[1:]
        if chunk:
            statements.append(chunk)
    if len(statements) == 1 and _call_name(statements[0], {}):
        return _Proc(params, statements[0])
    call = _read_ack_call(statements, params) if begun else None
    return _Proc(params, call) if call else None


def _build(tokens, filename):
    root: list = []
    frames: list = []
    procs: Dict[str, Dict[int, Optional[_Proc]]] = {}
    skipping = False
    declaration: Optional[list] = None

    def body():
        for kind, node in reversed(frames):
            if kind == "for":
                return node.body
            if kind == "if":
                return node.branches[-1][1]
            if kind == "case":
                return node.arms[-1][1] if node.arms else []
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
                if declaration is not None:
                    header = declaration[0]
                    procs.setdefault(header[0].value.lower(), {})[len(_param_names(header))] = _procedure(
                        header, declaration[1:]
                    )
            elif declaration is not None:
                declaration.append(chunk)
            continue
        toks = list(chunk)
        while toks:
            head = _word(toks[0])
            if (len(toks) > 2 and toks[0].kind == "id" and _is_op(toks[1], ":")
                    and _word(toks[2]) in _OPENERS):
                toks = toks[2:]
                continue
            if head in ("procedure", "function", "pure", "impure"):
                index = _find_top(toks, ("is",))
                if index >= 0:
                    skipping = True
                    declaration = None
                    if head == "procedure" and len(toks) > 1 and toks[1].kind == "id":
                        declaration = [toks[1:index], toks[index + 1:]]
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
                node = _Case(toks[1:index] if index >= 0 else [], toks[0].line)
                body().append(node)
                frames.append(("case", node))
                toks = toks[index + 1:] if index >= 0 else []
            elif head == "when" and _find_top(toks, ("=>",)) >= 0:
                index = _find_top(toks, ("=>",))
                if frames and frames[-1][0] == "case":
                    frames[-1][1].arms.append([toks[1:index], [], toks[0].line])
                toks = toks[index + 1:]
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
    return root, procs


def _has_register_call(nodes, procs) -> bool:
    for node in nodes:
        if isinstance(node, _Stmt):
            if _call_name(node.tokens, procs):
                return True
        elif isinstance(node, _For):
            if _has_register_call(node.body, procs):
                return True
        elif isinstance(node, _Case):
            if any(_has_register_call(arm[1], procs) for arm in node.arms):
                return True
        elif any(_has_register_call(branch[1], procs) for branch in node.branches):
            return True
    return False


def _has_case(nodes) -> bool:
    for node in nodes:
        if isinstance(node, _Case):
            return True
        if isinstance(node, _For) and _has_case(node.body):
            return True
        if isinstance(node, _If) and any(_has_case(branch[1]) for branch in node.branches):
            return True
    return False


def _call_name(tokens, procs) -> str:
    """Lowercase register procedure name when a statement starts with one.

    A name counts when it is a surf register procedure, starts like a local
    wrapper of one, or is a procedure declared in the file whose body is a
    register call.
    """
    name = _word(tokens[0])
    if name in FIELD_CALLS or name in STROBE_CALLS:
        return name
    if name.startswith(("axislaveregister", "axilslaveregister")):
        return name
    if any(proc is not None for proc in procs.get(name, {}).values()):
        return name
    return ""


def _substitute(tokens, mapping):
    """Replace formal parameter names in tokens by the actual argument tokens."""
    result = []
    for position, token in enumerate(tokens):
        after_dot = position > 0 and _is_op(tokens[position - 1], ".")
        if token.kind == "id" and token.value.lower() in mapping and not after_dot:
            result.extend(mapping[token.value.lower()])
        else:
            result.append(token)
    return result


# ---------------------------------------------------------------------------
# Name expressions of the hand-written decodes
# ---------------------------------------------------------------------------

class _Chain(NamedTuple):
    """A selected name ``a.b(i).c(h downto l)``: the last name and its parenthesis groups."""

    name: str
    groups: list
    inner: list
    dotted: bool


def _chain(tokens) -> Optional[_Chain]:
    """Parse tokens as ``name { . name } { ( ... ) }`` or return None for anything else."""
    name, groups, inner, dotted = None, [], [], False
    position, expect_name = 0, True
    while position < len(tokens):
        token = tokens[position]
        if expect_name:
            if token.kind != "id":
                return None
            if groups:
                inner.extend(groups)
            name, groups, expect_name = token.value, [], False
            position += 1
        elif _is_op(token, "."):
            expect_name, dotted = True, True
            position += 1
        elif _is_op(token, "("):
            close = _matching_paren(tokens, position)
            if close < 0:
                return None
            groups.append(tokens[position + 1:close])
            position = close + 1
        else:
            return None
    if expect_name:
        return None
    return _Chain(name, groups, inner, dotted)


def _is_range(tokens) -> bool:
    return _find_top(tokens, ("downto", "to")) >= 0


def _index_pattern(tokens):
    """Match ``name := conv_integer(addr(h downto l))``: the name, the address chain, and the range."""
    colon = _find_top(tokens, (":=",))
    if colon != 1 or tokens[0].kind != "id":
        return None
    value = tokens[colon + 1:]
    if len(value) < 4 or _word(value[0]) not in ("conv_integer", "to_integer") or not _is_op(value[1], "("):
        return None
    if _matching_paren(value, 1) != len(value) - 1:
        return None
    selected = _chain(value[2:-1])
    if selected is None or len(selected.groups) != 1 or not _is_range(selected.groups[0]):
        return None
    return tokens[0].value.lower(), selected.name.lower(), selected.groups[0]


_WRITE_DATA = ("wdata", "regwrdata")
_READ_DATA = ("rdata", "tmprddata")
_ADDRESS_WORDS = ("awaddr", "araddr")


def _statements(nodes):
    """Every plain statement of a node tree, in order."""
    for node in nodes:
        if isinstance(node, _Stmt):
            yield node
        elif isinstance(node, _For):
            yield from _statements(node.body)
        elif isinstance(node, _Case):
            for arm in node.arms:
                yield from _statements(arm[1])
        else:
            for branch in node.branches:
                yield from _statements(branch[1])


def _address_variables(root):
    """Pointers (``wrPntr := conv_integer(...awaddr(14 downto 2))``) and address copies of the file.

    A pointer maps to its direction and the address bit its value starts at;
    the set holds the names whose bits are address bits.
    """
    pointers: Dict[str, Any] = {}
    addresses = set(_ADDRESS_WORDS)
    for node in _statements(root):
        chunk = node.tokens
        if len(chunk) < 3 or chunk[0].kind != "id" or not _is_op(chunk[1], ":="):
            continue
        words = {_word(token) for token in chunk[2:]}
        direction = "write" if "awaddr" in words else "read" if "araddr" in words else None
        if direction is None:
            continue
        match = _index_pattern(chunk)
        if match is None:
            addresses.add(chunk[0].value.lower())
        else:
            pointers[match[0]] = (direction, match[2])
    return pointers, addresses


class _Arm:
    """Where a case arm sits: the byte of its word, the access direction, and what it decodes."""

    def __init__(self, byte, direction, window=None):
        self.byte, self.direction, self.window = byte, direction, window
        self.assigned: list = []

    def at(self, byte):
        return _Arm(byte, self.direction, self.window)


# ---------------------------------------------------------------------------
# Executing the structure
# ---------------------------------------------------------------------------

_MAX_PROCEDURE_DEPTH = 8


class _Run:
    def __init__(self, entity, filename, env, widths, procs, pointers=None, addresses=()):
        self.entity, self.filename, self.env, self.widths = entity, filename, env, widths
        self.procs = procs
        self.pointers = pointers or {}
        self.addresses = set(addresses)
        self.fields: List[VhdlField] = []
        self.strobes: List[VhdlStrobe] = []
        self.unresolved: set = set()
        self.arm_fields: List[VhdlField] = []
        self.arm_strobes: List[VhdlStrobe] = []
        self.windows: List[VhdlWindow] = []
        self.events = 0

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
            elif isinstance(node, _Case):
                self.case(node, env, conds, index, None)
            else:
                self.branch(node, env, conds, index)

    def loop(self, node, env, conds):
        low = self.value(node.low, env, node.line, "loop bound")
        high = self.value(node.high, env, node.line, "loop bound")
        values = range(low, high - 1, -1) if node.descending else range(low, high + 1)
        for current in values:
            self.run(node.body, {**env, node.var: current}, conds, current)

    def selected(self, node, env, every_unknown):
        """The ``(nodes, condition text)`` pairs of an ``if`` that apply.

        A condition that cannot be evaluated is a run time condition: every
        branch from there on applies when the statement holds a decode case or
        ``every_unknown`` is set, and none does otherwise.
        """
        earlier = []
        for position, (cond, nodes, line) in enumerate(node.branches):
            if cond is None:
                return [(nodes, "not (" + " or ".join(earlier) + ")" if earlier else None)]
            try:
                result = evaluate(cond, env)
            except EvalError as error:
                if any(_has_register_call(branch[1], self.procs) for branch in node.branches):
                    self.fail(line, f"cannot evaluate condition {_text(cond)!r}: {error}")
                if every_unknown or any(_has_case(branch[1]) for branch in node.branches):
                    return [(branch[1], None) for branch in node.branches[position:]]
                return []
            if result:
                return [(nodes, _text(cond))]
            earlier.append(_text(cond))
        return []

    def branch(self, node, env, conds, index):
        for nodes, text in self.selected(node, env, False):
            self.run(nodes, env, conds + ([text] if text else []), index)

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

    # -- hand-written decodes -------------------------------------------------

    def bounds(self, group, env, line):
        """Low bit and width of a ``(h downto l)`` or ``(l to h)`` group."""
        descending = _find_top(group, ("downto",)) >= 0
        parts = _split_words(group, "downto" if descending else "to")
        first = self.value(parts[0], env, line, "range bound")
        second = self.value(parts[1], env, line, "range bound")
        high, low = (first, second) if descending else (second, first)
        return low, high - low + 1

    def choices(self, tokens, env, line):
        """Alternatives of a case choice as ``(first, last)`` pairs; ``others`` is dropped."""
        result = []
        for alt in _split_top(tokens, "|"):
            if len(alt) == 1 and _word(alt[0]) == "others":
                continue
            if len(alt) == 1 and alt[0].kind == "str":
                bits = alt[0].value
                if not bits or set(bits) - {"0", "1"}:
                    self.fail(line, f"unsupported case choice {_text(alt)!r}")
                result.append((int(bits, 2), int(bits, 2)))
                continue
            bounds = _split_words(alt, "to")
            if bounds is not None:
                result.append((self.value(bounds[0], env, line, "case choice"),
                               self.value(bounds[1], env, line, "case choice")))
            else:
                value = self.value(alt, env, line, "case choice")
                result.append((value, value))
        return result

    def case(self, node, env, conds, index, arm):
        """Run a case: a decode of the address when its selector is one, else every arm as it stands."""
        chain = _chain(node.selector)
        name = chain.name.lower() if chain is not None else ""
        if arm is None and chain is not None and not chain.groups and not chain.dotted and name in self.pointers:
            direction, group = self.pointers[name]
            shift, _ = self.bounds(group, env, node.line)
            self.decode(node, env, conds, direction, shift)
        elif (arm is not None and chain is not None and name in self.addresses and len(chain.groups) == 1
              and _is_range(chain.groups[0])):
            low, _ = self.bounds(chain.groups[0], env, node.line)
            for choice, body, line in node.arms:
                for first, last in self.choices(choice, env, line):
                    for value in range(first, last + 1):
                        self.leaf(body, env, conds, arm.at(arm.byte + (value << low)))
        else:
            for _, body, _ in node.arms:
                if arm is None:
                    self.run(body, env, conds, index)
                else:
                    self.arm_nodes(body, env, conds, arm)

    def index_variable(self, body, env, line):
        """The ``(name, low bit)`` of ``name := conv_integer(addr(h downto l))`` at the top of an arm body."""
        for node in body:
            if isinstance(node, _Stmt):
                match = _index_pattern(node.tokens)
                if match is not None and match[1] in self.addresses:
                    return match[0], self.bounds(match[2], env, node.line)[0]
        return None

    def decode(self, node, env, conds, direction, shift):
        for choice, body, line in node.arms:
            for first, last in self.choices(choice, env, line):
                if first == last:
                    self.leaf(body, env, conds, _Arm(first << shift, direction))
                    continue
                span = (last - first + 1) << shift
                variable = self.index_variable(body, env, line)
                if variable is not None:
                    name, low = variable
                    for element in range(-(-span // (1 << low))):
                        self.leaf(body, {**env, name: element}, conds,
                                  _Arm((first << shift) + (element << low), direction))
                    continue
                arm = _Arm(first << shift, direction, window=[])
                self.arm_nodes(body, env, conds, arm)
                self.windows.append(VhdlWindow(
                    self.entity, arm.window[0] if arm.window else None, first << shift,
                    (last << shift) + (1 << shift) - 1, direction == "read", direction == "write", line,
                ))

    def leaf(self, body, env, conds, arm):
        """Run one arm body; an arm that decodes no data but assigns something is a strobe."""
        before = self.events
        self.arm_nodes(body, env, conds, arm)
        if self.events == before and arm.assigned:
            name, line = arm.assigned[0]
            self.arm_strobes.append(VhdlStrobe(self.entity, name, None, arm.byte, arm.direction, line))

    def arm_nodes(self, nodes, env, conds, arm):
        for node in nodes:
            if isinstance(node, _Stmt):
                self.assign(node, env, conds, arm)
            elif isinstance(node, _For):
                low = self.value(node.low, env, node.line, "loop bound")
                high = self.value(node.high, env, node.line, "loop bound")
                values = range(low, high - 1, -1) if node.descending else range(low, high + 1)
                for current in values:
                    self.arm_nodes(node.body, {**env, node.var: current}, conds, arm)
            elif isinstance(node, _Case):
                self.case(node, env, conds, None, arm)
            else:
                for nodes_taken, text in self.selected(node, env, True):
                    self.arm_nodes(nodes_taken, env, conds + ([text] if text else []), arm)

    def data_selection(self, chain, env, line):
        """Low bit and width of the selected bits of the data word, width None for the whole word."""
        if not chain.groups:
            return 0, None
        if len(chain.groups) > 1:
            self.fail(line, "unsupported selection of the data word")
        if _is_range(chain.groups[0]):
            return self.bounds(chain.groups[0], env, line)
        return self.value(chain.groups[0], env, line, "data bit"), 1

    def unresolved_arm(self, kind, arm, reason):
        self.unresolved.add(f"{kind} 0x{arm.byte:X}: {reason}")
        self.events += 1

    def assign(self, node, env, conds, arm):
        tokens, line = node.tokens, node.line
        colon = _find_top(tokens, (":=",))
        if colon <= 0 or _index_pattern(tokens) is not None:
            return
        left, value = _chain(tokens[:colon]), tokens[colon + 1:]
        if left is None:
            return
        words = {_word(token) for token in value}
        if left.name.lower() in _READ_DATA:
            if not [t for t in value if t.kind == "id" and t.value.lower() != "others"]:
                return
            if arm.window is not None:
                source = _chain(value)
                if source is not None and not arm.window:
                    arm.window.append(source.name)
                return
            if _find_top(value, ("&",)) >= 0:
                return self.unresolved_arm("read", arm, "concatenation")
            source = _chain(value)
            if source is None:
                return self.unresolved_arm("read", arm, "expression")
            if not source.dotted and source.groups and (
                    source.name.lower() in FUNCTIONS or source.name.lower() == "fromslv"
                    or source.name.lower() not in self.widths):
                return self.unresolved_arm("read", arm, "function call")
            low, width = self.data_selection(left, env, line)
            return self.emit(source, low, width, env, conds, arm, line, True)
        if set(_WRITE_DATA) & words:
            source = _chain(value)
            if source is None or source.name.lower() not in _WRITE_DATA or (
                    source.groups and not source.dotted and len(source.groups) > 1):
                return self.unresolved_arm("write", arm, "expression of the write data")
            if arm.window is not None:
                return
            low, width = self.data_selection(source, env, line)
            return self.emit(left, low, width, env, conds, arm, line, False)
        arm.assigned.append((left.name, line))

    def emit(self, target, data_low, data_width, env, conds, arm, line, read):
        """Record one decoded field: ``target`` is the name side of the assignment."""
        target_low, target_width, element = 0, None, None
        if target.groups:
            if _is_range(target.groups[0]):
                target_low, target_width = self.bounds(target.groups[0], env, line)
            else:
                element = self.value(target.groups[0], env, line, "element index")
        if target.inner and not _is_range(target.inner[0]):
            element = self.value(target.inner[0], env, line, "element index")
        length = self.widths.get(target.name.lower() + LENGTH_SUFFIX)
        if element is not None and length is not None and not 0 <= element < length:
            return
        width = data_width or target_width or WORD_BITS
        condition = " and ".join(conds) if conds else None
        self.arm_fields.append(VhdlField(
            self.entity, target.name, element, arm.byte, data_low, width, read, not read, condition, line, target_low
        ))
        self.events += 1

    def mux_target(self, tokens, env, line):
        """Target name, element index, and width of ``muxSlVectorArray(array, k)``, else None."""
        if not (len(tokens) > 3 and _word(tokens[0]) == "muxslvectorarray" and _is_op(tokens[1], "(")
                and _matching_paren(tokens, 1) == len(tokens) - 1):
            return None
        parts = _split_top(tokens[2:-1], ",")
        if len(parts) != 2:
            self.fail(line, f"unsupported form of {tokens[0].value} with {len(parts)} arguments")
        name, _ = self.target(parts[0])
        if name is None:
            self.fail(line, f"no array identifier in {_text(parts[0])!r}")
        return name, self.value(parts[1], env, line, "mux index"), self.widths.get(name.lower())

    def register_arguments(self, name, count, line, first):
        """Argument positions (address, bit offset, register) and write access of a register call."""
        if name == "axislaveregister" and count in (4, 5):
            return 1, 2, 3, True
        if name == "axislaveregister" and count == 6:
            return 3, 4, 5, False
        if name == "axislaveregister" and count in (8, 9, 10):
            return 5, 6, 7, True
        if name == "axislaveregisterr" and count == 4:
            return 1, 2, 3, False
        self.fail(line, f"unsupported form of {first.value} with {count} arguments")

    def statement(self, node, env, conds, index, depth=0):
        tokens, line = node.tokens, node.line
        name = _call_name(tokens, self.procs)
        if not name:
            return
        if len(tokens) < 3 or not _is_op(tokens[1], "(") or _matching_paren(tokens, 1) != len(tokens) - 1:
            self.fail(line, f"unsupported form of {tokens[0].value}")
        args = _split_top(tokens[2:-1], ",")
        if name in self.procs:
            proc = self.procs[name].get(len(args))
            if proc is None or depth >= _MAX_PROCEDURE_DEPTH:
                self.fail(line, f"unsupported form of {tokens[0].value} with {len(args)} arguments")
            mapping = {param: arg for param, arg in zip(proc.params, args)}
            self.statement(_Stmt(_substitute(proc.call, mapping), line), env, conds, index, depth + 1)
            return
        condition = " and ".join(conds) if conds else None
        if name in STROBE_CALLS:
            if len(args) != 3:
                self.fail(line, f"unsupported form of {tokens[0].value} with {len(args)} arguments")
            address = self.value(args[1], env, line, "address")
            target, _ = self.target(args[2])
            self.strobes.append(VhdlStrobe(self.entity, target, index, address, STROBE_CALLS[name], line))
            return
        address_at, offset_at, register_at, writable = self.register_arguments(name, len(args), line, tokens[0])
        address = self.value(args[address_at], env, line, "address")
        offset = self.value(args[offset_at], env, line, "bit offset")
        mux = self.mux_target(args[register_at], env, line)
        if mux is not None:
            target, index, width = mux
        else:
            target, slice_tokens = self.target(args[register_at])
            if target is None:
                self.fail(line, f"no target identifier in {_text(args[register_at])!r}")
            width = _range_width(slice_tokens, env) if slice_tokens else self.widths.get(target.lower())
        if width is None:
            self.unresolved.add(target)
        self.fields.append(VhdlField(self.entity, target, index, address, offset, width, True, writable, condition, line))


# ---------------------------------------------------------------------------
# Joining the words of the hand-written decodes
# ---------------------------------------------------------------------------

def _merge_words(fields: List[VhdlField]) -> List[VhdlField]:
    """Join little-endian word slices of one target into one wide field.

    A word that holds bits 31 to 0 of a target followed, at the next word, by
    bits 63 to 32 (and so on) is one 64 bit field. The reverse order is two
    fields, told apart by ``target_low``.
    """
    ordered = sorted(
        fields,
        key=lambda f: (f.target.lower(), -1 if f.index is None else f.index, f.readable, f.condition or "", f.byte_offset),
    )
    result: List[VhdlField] = []
    for field in ordered:
        if result:
            last = result[-1]
            same = (last.target.lower(), last.index, last.readable, last.condition) == (
                field.target.lower(), field.index, field.readable, field.condition)
            adjacent = (last.bit_offset == 0 and field.bit_offset == 0 and last.width % WORD_BITS == 0
                        and field.byte_offset == last.byte_offset + last.width // 8
                        and field.target_low == last.target_low + last.width)
            if same and adjacent:
                result[-1] = last._replace(width=last.width + field.width)
                continue
        result.append(field)
    return result


def _merge_directions(fields: List[VhdlField]) -> List[VhdlField]:
    """One field per target, byte, bit, width, and target bit; a read and a write arm set both flags."""
    merged: Dict[tuple, VhdlField] = {}
    for field in fields:
        key = (field.target.lower(), field.index, field.byte_offset, field.bit_offset, field.width, field.target_low)
        if key in merged:
            old = merged[key]
            merged[key] = old._replace(readable=old.readable or field.readable, writable=old.writable or field.writable)
        else:
            merged[key] = field
    return sorted(merged.values(), key=lambda f: (f.byte_offset, f.bit_offset, f.target.lower(), -1 if f.index is None else f.index))


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
    env.update({name: value for name, value in widths.items() if name.endswith(LENGTH_SUFFIX)})
    root, procs = _build(tokens, filename)
    pointers, addresses = _address_variables(root)
    run = _Run(entity, filename, env, widths, procs, pointers, addresses)
    run.run(root, env, [], None)
    arm_fields = _merge_directions(_merge_words(run.arm_fields))
    return Decode(
        entity, run.fields + arm_fields, run.strobes + run.arm_strobes, sorted(run.unresolved), tuple(run.windows)
    )


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


def read_all(generics_by_file: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Decode]:
    """Return the decode of every file in DECODE_FILES, keyed by path.

    ``generics_by_file`` maps a path to the generics to override for that file.
    """
    generics_by_file = generics_by_file or {}
    return {path: read_decode(path, generics_by_file.get(path)) for path in DECODE_FILES}
