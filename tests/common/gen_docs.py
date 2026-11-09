#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Generated reference pages for the Sphinx site.

Run ``python -m tests.common.gen_docs`` from the repository root to write
every generated page under docs/reference/, and
``python -m tests.common.gen_docs --check`` to compare the committed pages
with a fresh generation. ``--check`` prints one line per page that differs,
is missing, or is a stray file under a generated directory, and exits 1 when
it printed any.

The pages are committed rather than built at documentation time: the strict
Sphinx build then needs nothing but Sphinx, a reviewer sees an RTL change and
its effect on the reference in one diff, and a test in the common leg fails
whenever a committed page is stale.

Nothing is executed or imported from the RTL or PyRogue sources. VHDL is read
with a small lexer and the tokenizer helpers of vhdl_registers, and the
sidecar files under docs/_data are read with yaml.safe_load only. The
simulator-side baselines are imported on first use, so importing this module
needs only the standard library, PyYAML, and the helpers beside it.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import NamedTuple

import yaml

from tests.common import pyrogue_ast, register_tables
from tests.common.register_drift import (
    ALLOWLIST,
    BITS_PER_BYTE,
    BLOCKS,
    COVERED_BY_LEAVES,
    ISSUE_URL_RE,
    NAME_MAPS,
    PENDING_ISSUE,
    WORD_BITS,
    RegField,
    compare_block,
    coverage_split,
    from_vhdl,
    from_yaml,
    group_fields,
    pair_kinds,
    split_index,
    unresolved_words,
)
from tests.common.register_tables import ArgSet
from tests.common.vhdl_registers import read_decode
from tests.common.yaml_maps import INCLUDE_RE, KNOWN_YAML_DEFECTS, YAML_CLASSIFICATION, load, yaml_fields
from tests.common.vhdl_registers import (
    Token,
    _find_top,
    _is_op,
    _matching_paren,
    _split_top,
    _word,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"

# Directories under docs/ that the generator owns completely: anything in them
# that it did not just generate is a stray file.
GENERATED_ROOTS = ("reference", "_generated")

STATUS_SIMULATED = "simulated"
STATUS_BASELINE = "baseline-excluded"
STATUS_VIVADO = "Vivado-only"
STATUS_NOT_SIMULATED = "not simulated"
STATUS_NOT_LOADED = "not simulated: not loaded by any ruckus.tcl"
STATUSES = (STATUS_SIMULATED, STATUS_BASELINE, STATUS_VIVADO, STATUS_NOT_SIMULATED, STATUS_NOT_LOADED)

STATUS_MEANING = (
    (
        STATUS_SIMULATED,
        "A cocotb test runs the entity (or its testbench wrapper) in the regression: in GHDL for a VHDL entity, "
        "in Icarus Verilog for a Verilog module.",
    ),
    (
        STATUS_BASELINE,
        "GHDL cannot analyze the file today. The regression records the exact GHDL message and fails if it "
        "changes or disappears; the issues column links the report.",
    ),
    (
        STATUS_VIVADO,
        "A transceiver wrapper for one device family. It instantiates a vendor primitive, so only Vivado "
        "builds it and the regression does not.",
    ),
    (
        STATUS_NOT_SIMULATED,
        "The file analyzes cleanly but no test simulates the entity; the entity page gives the reason.",
    ),
    (
        STATUS_NOT_LOADED,
        "The file is tracked in the repository but no ruckus.tcl loads it, so no build includes it.",
    ),
)

GT_DIRECTORIES = (
    "LCLS-II/gtp7/",
    "LCLS-II/gtx7/",
    "LCLS-II/gthUltraScale/",
    "LCLS-II/gthUltraScale+/",
    "LCLS-II/gtyUltraScale+/",
)

SIDECAR_PURPOSES = "entity_purposes.yaml"
SIDECAR_HEADER_ISSUES = "header_issues.yaml"
HEADER_KINDS = ("empty", "missing", "contradicts")


class Generic(NamedTuple):
    name: str
    type_text: str
    default_text: str


class Port(NamedTuple):
    name: str
    mode: str
    type_text: str


class DesignUnit(NamedTuple):
    kind: str
    name: str
    generics: tuple
    ports: tuple
    line: int


@dataclass(frozen=True)
class DocTree:
    """One documented source tree.

    ``only``, when not None, is a tuple of repo-relative paths that restricts
    which documented files the tree page renders. ``note`` is an optional
    paragraph that the page shows before its summary table.
    """

    key: str
    title: str
    roots: tuple
    only: tuple | None = None
    note: str = ""

    @property
    def ruckus_files(self):
        """Return the ruckus.tcl files, one per root, that load the tree."""
        return tuple(f"{root}/ruckus.tcl" for root in self.roots)


DOC_TREES = (
    DocTree("core", "LCLS-II core", ("LCLS-II/core",)),
    DocTree("evr", "LCLS-II EVR", ("LCLS-II/evr",)),
    DocTree("lcls1", "LCLS-I EVR", ("LCLS-I",)),
    DocTree(
        "gt",
        "Transceiver wrappers",
        ("LCLS-II/gtp7", "LCLS-II/gtx7", "LCLS-II/gthUltraScale", "LCLS-II/gthUltraScale+", "LCLS-II/gtyUltraScale+"),
        note=(
            "These wrappers instantiate Xilinx GT primitives and IP cores, so only Vivado builds them and the "
            "regression does not simulate them. LCLS-II/ruckus.tcl loads the wrapper directory of the FPGA family "
            "being built; the :doc:`family matrix </reference/families>` lists which."
        ),
    ),
)


# ---------------------------------------------------------------------------
# RST helpers
# ---------------------------------------------------------------------------

def title(text, char):
    """Return ``text`` and an underline of equal length."""
    return f"{text}\n{char * len(text)}\n"


def list_table(header, rows, widths=None):
    """Return a ``.. list-table::`` with a header row.

    Empty cells render as ``none``, and continuation lines of a multi-line cell
    are indented under its bullet. A row whose cell count differs from the
    header raises ValueError naming that row.
    """
    lines = [".. list-table::", "   :header-rows: 1"]
    if widths:
        lines.append("   :widths: " + " ".join(str(width) for width in widths))
    lines.append("")
    for number, row in enumerate([header, *rows]):
        if len(row) != len(header):
            raise ValueError(f"list-table row {number} has {len(row)} cells, expected {len(header)}: {list(row)!r}")
        for index, cell in enumerate(row):
            text = str(cell).strip() or "none"
            first, *rest = text.split("\n")
            lines.append(("   * - " if index == 0 else "     - ") + first)
            lines.extend(("       " + line) if line.strip() else "" for line in rest)
    return "\n".join(lines) + "\n"


def literal(text):
    """Return ``text`` as an inline literal, or an empty string when it is empty."""
    return f"``{text}``" if text else ""


def slug(path):
    """Return the label slug of a repo-relative path."""
    return re.sub(r"[^a-z0-9]+", "-", str(path).lower()).strip("-")


def repo_link(path):
    return f":repo:`{path}`"


# ---------------------------------------------------------------------------
# VHDL entity reader
# ---------------------------------------------------------------------------

_LEX_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<comment>--[^\n]*)
  | (?P<bits>[A-Za-z]{1,2}"[^"\n]*")
  | (?P<str>"(?:[^"\n]|"")*")
  | (?P<char>'[^'\n]')
  | (?P<int>\d[\d_]*(?:\.\d[\d_]*)?(?:\#[0-9A-Fa-f_.]+\#)?(?:[eE][+-]?\d+)?)
  | (?P<id>[A-Za-z_]\w*|\\[^\\\n]+\\)
  | (?P<op><=|>=|=>|:=|/=|\*\*|<>|<<|>>|.)
    """,
    re.VERBOSE,
)

_KEYWORDS = frozenset(
    {"downto", "to", "and", "or", "not", "xor", "nand", "nor", "xnor", "others", "when", "else", "then", "of", "is",
     "in", "out", "inout", "buffer", "mod", "rem", "abs", "range", "all", "open"}
)
_MODES = ("in", "out", "inout", "buffer", "linkage")
_OBJECT_CLASSES = ("signal", "constant", "variable")


def lex(source):
    """Return the tokens of VHDL ``source`` with comments dropped and the original text kept in ``value``."""
    tokens = []
    for match in _LEX_RE.finditer(source):
        kind = match.lastgroup
        if kind in ("ws", "comment"):
            continue
        tokens.append(Token(kind, match.group(), source.count("\n", 0, match.start()) + 1))
    return tokens


def compact(tokens):
    """Join tokens for display: ``std_logic_vector(31 downto 0)``, ``1 ns``, ``(others => '0')``."""
    text = ""
    previous = None
    before = None
    for token in tokens:
        if previous is None:
            text = token.value
        else:
            attach = (
                _is_op(previous, "(")
                or _is_op(previous, ".")
                or _is_op(previous, "'")
                or _is_op(token, ")")
                or _is_op(token, ",")
                or _is_op(token, ".")
                or _is_op(token, "'")
                or (_is_op(token, "(") and previous.kind == "id" and previous.value.lower() not in _KEYWORDS)
                or (
                    previous.kind == "op"
                    and previous.value in ("-", "+")
                    and (before is None or (before.kind == "op" and before.value not in (")",)))
                )
            )
            text += ("" if attach else " ") + token.value
        before, previous = previous, token
    return text


def _clause(body, word, start=0):
    """Return (tokens inside ``word ( ... )``, index after the closing parenthesis) or ([], start)."""
    for index in range(start, len(body) - 1):
        if _word(body[index]) == word and _is_op(body[index + 1], "("):
            close = _matching_paren(body, index + 1)
            if close < 0:
                raise ValueError(f"unbalanced parentheses after {word}")
            return body[index + 2:close], close + 1
    return [], start


def _interface(clause, with_modes):
    """Parse one interface list into (names, mode, type tokens, default tokens) entries."""
    entries = []
    for entry in _split_top(clause, ";"):
        if not entry:
            continue
        colon = _find_top(entry, (":",))
        if colon <= 0:
            raise ValueError(f"interface entry without a colon: {compact(entry)!r}")
        names = [t.value for t in entry[:colon] if t.kind == "id" and _word(t) not in _OBJECT_CLASSES]
        rest = entry[colon + 1:]
        assign = _find_top(rest, (":=",))
        default = rest[assign + 1:] if assign >= 0 else []
        rest = rest[:assign] if assign >= 0 else rest
        mode = "in"
        if rest and _word(rest[0]) in _MODES:
            mode, rest = _word(rest[0]), rest[1:]
        entries.append((names, mode, rest, default))
    return entries


def read_vhdl_unit(path):
    """Return the DesignUnit that VHDL file ``path`` declares (an entity, else a package).

    Raises ValueError naming the file when it declares neither.
    """
    path = Path(path)
    tokens = lex(path.read_text(encoding="utf-8", errors="replace"))
    for kind, extra in (("entity", False), ("package", True)):
        for index in range(len(tokens) - 3):
            if _word(tokens[index]) != kind or tokens[index + 1].kind != "id" or _word(tokens[index + 2]) != "is":
                continue
            if extra and _word(tokens[index + 3]) == "new":
                continue
            name = tokens[index + 1].value
            if kind == "package":
                return DesignUnit(kind, name, (), (), tokens[index].line)
            end = next((n for n in range(index + 3, len(tokens)) if _word(tokens[n]) == "end"), len(tokens))
            body = tokens[index + 3:end]
            generic_tokens, after = _clause(body, "generic")
            port_tokens, _ = _clause(body, "port", after)
            generics = [
                Generic(name, compact(type_tokens), compact(default))
                for names, _, type_tokens, default in _interface(generic_tokens, False)
                for name in names
            ]
            ports = [
                Port(name, mode, compact(type_tokens))
                for names, mode, type_tokens, _ in _interface(port_tokens, True)
                for name in names
            ]
            return DesignUnit(kind, name, tuple(generics), tuple(ports), tokens[index].line)
    raise ValueError(f"{path}: no entity or package declaration found")


# ---------------------------------------------------------------------------
# Verilog module reader
# ---------------------------------------------------------------------------

_VERILOG_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_VERILOG_DIRECTIONS = {"input": "in", "output": "out", "inout": "inout"}
_VERILOG_DECL_RE = re.compile(
    r"(?:(?P<net>reg|wire)\s*)?(?:signed\s*)?(?P<range>\[[^\]]*\])?\s*(?P<names>.*)", re.DOTALL
)
_VERILOG_ANSI_RE = re.compile(
    r"(?:(?P<dir>input|output|inout)\s*)?(?:(?P<net>reg|wire)\s*)?(?:signed\s*)?"
    r"(?P<range>\[[^\]]*\])?\s*(?P<name>\w+)",
    re.DOTALL,
)


def _blank_comments(text):
    """Return ``text`` with every comment replaced by its newlines, so line numbers stay valid."""
    return _VERILOG_COMMENT_RE.sub(lambda match: "\n" * match.group().count("\n"), text)


def _split_commas(text):
    """Split ``text`` at the commas that are outside parentheses, brackets, and braces."""
    parts, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


def _closing_paren(text, start):
    """Return the index of the parenthesis that closes the one at ``text[start]``, or -1."""
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _verilog_parameters(text):
    """Return the Generic entries of one ``parameter [range] name = value, ...`` declaration body."""
    match = re.fullmatch(r"(?:signed\s*)?(?P<range>\[[^\]]*\])?\s*(?P<rest>.*)", text.strip(), re.DOTALL)
    kind = "parameter" + (" " + re.sub(r"\s+", "", match.group("range")) if match.group("range") else "")
    generics = []
    for item in _split_commas(match.group("rest")):
        name, _, value = item.partition("=")
        generics.append(Generic(name.strip(), kind, " ".join(value.split())))
    return generics


def read_verilog_unit(path):
    """Return the DesignUnit (kind ``module``) that Verilog file ``path`` declares.

    Comments are stripped first. Parameters become generics (type text
    ``parameter``, plus its range when it has one, and the default value
    text). Each ``input``, ``output``, or ``inout`` declaration becomes one
    port per name, with the range text (``[63:0]``) or else ``reg`` or ``wire``
    as the type. Both the non-ANSI style (names in the module header,
    directions declared in the body) and the ANSI style (directions in the
    header) are read. Raises ValueError naming the file when it declares no
    module, and naming the file and the port when a header port has no
    direction declaration.
    """
    path = Path(path)
    text = _blank_comments(path.read_text(encoding="utf-8", errors="replace"))
    found = re.search(r"\bmodule\s+(\w+)", text)
    if found is None:
        raise ValueError(f"{path}: no module declaration found")
    name = found.group(1)
    line = text.count("\n", 0, found.start()) + 1
    index = found.end()
    generics = []
    rest = text[index:]
    stripped = rest.lstrip()
    offset = index + (len(rest) - len(stripped))
    if stripped.startswith("#"):
        open_at = text.find("(", offset)
        close_at = _closing_paren(text, open_at)
        if open_at < 0 or close_at < 0:
            raise ValueError(f"{path}: unbalanced parameter list of module {name}")
        for item in _split_commas(text[open_at + 1:close_at]):
            generics.extend(_verilog_parameters(re.sub(r"^parameter\b", "", item.strip())))
        offset = close_at + 1
        stripped = text[offset:].lstrip()
        offset = len(text) - len(stripped)
    header = []
    if stripped.startswith("("):
        close_at = _closing_paren(text, offset)
        if close_at < 0:
            raise ValueError(f"{path}: unbalanced port list of module {name}")
        header = _split_commas(text[offset + 1:close_at])
        offset = close_at + 1
    end = text.find("endmodule", offset)
    body = text[offset:end if end >= 0 else len(text)]
    declared = {}
    for statement in body.split(";"):
        statement = statement.strip()
        word = re.match(r"(input|output|inout|parameter)\b", statement)
        if word is None:
            continue
        remainder = statement[word.end():]
        if word.group(1) == "parameter":
            generics.extend(_verilog_parameters(remainder))
            continue
        decl = _VERILOG_DECL_RE.fullmatch(remainder.strip())
        kind = re.sub(r"\s+", "", decl.group("range")) if decl.group("range") else decl.group("net") or "wire"
        for port in _split_commas(decl.group("names")):
            declared[port] = (_VERILOG_DIRECTIONS[word.group(1)], kind)
    ports = []
    if any(re.match(r"(input|output|inout)\b", item) for item in header):
        current = None
        for item in header:
            entry = _VERILOG_ANSI_RE.fullmatch(item)
            if entry is None:
                raise ValueError(f"{path}: cannot read the port {item!r} of module {name}")
            if entry.group("dir"):
                kind = re.sub(r"\s+", "", entry.group("range")) if entry.group("range") else entry.group("net") or "wire"
                current = (_VERILOG_DIRECTIONS[entry.group("dir")], kind)
            if current is None:
                raise ValueError(f"{path}: port {entry.group('name')} of module {name} has no direction")
            ports.append(Port(entry.group("name"), *current))
    else:
        for port in header:
            if port not in declared:
                raise ValueError(f"{path}: port {port} of module {name} has no input, output, or inout declaration")
            ports.append(Port(port, *declared[port]))
    return DesignUnit("module", name, tuple(generics), tuple(ports), line)


def read_unit(path):
    """Return the DesignUnit of a VHDL or Verilog file, chosen by suffix."""
    return read_verilog_unit(path) if str(path).endswith(".v") else read_vhdl_unit(path)


# ---------------------------------------------------------------------------
# Documented files and sidecars
# ---------------------------------------------------------------------------

def documented_files(repo_root, tree):
    """Return the sorted tracked .vhd and .v files of ``tree`` outside wrappers directories.

    The render filter ``tree.only`` is ignored here: statuses and header checks
    cover every documented file.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", *tree.roots],
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(
        line
        for line in result.stdout.splitlines()
        if line.endswith((".vhd", ".v")) and "wrappers" not in Path(line).parts
    )


def rendered_files(repo_root, tree):
    """Return the documented files that the page of ``tree`` renders."""
    files = documented_files(repo_root, tree)
    if tree.only is None:
        return files
    return [path for path in files if path in tree.only]


def load_sidecar(name, repo_root=REPO_ROOT):
    """Return the mapping in docs/_data/<name> (empty for an empty file), read with yaml.safe_load only."""
    data = yaml.safe_load((Path(repo_root) / "docs" / "_data" / name).read_text(encoding="utf-8"))
    return data or {}


class HeaderDescription(NamedTuple):
    found: bool
    text: str
    first_line: int
    last_line: int


_COMMENT_MARK_RE = re.compile(r"^(?:--|//)")
_BANNER_RE = re.compile(r"[-/=]{5,}")


def header_description(path):
    """Return the Description text of the banner header of ``path``.

    The text runs from after ``Description:`` up to the next banner line of
    five or more ``-``, ``/``, or ``=`` characters, or the first line that is
    not a comment. ``found`` is False when the first 60 lines have no
    ``Description:`` line. The text has its whitespace collapsed.
    """
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    start = next((n for n, line in enumerate(lines[:60]) if "Description:" in line), None)
    if start is None:
        return HeaderDescription(False, "", 0, 0)
    pieces = [lines[start].split("Description:", 1)[1]]
    last = start
    for number in range(start + 1, len(lines)):
        raw = lines[number].strip()
        if not _COMMENT_MARK_RE.match(raw):
            break
        content = _COMMENT_MARK_RE.sub("", raw, count=1).strip()
        if _BANNER_RE.fullmatch(raw) or _BANNER_RE.fullmatch(content):
            break
        pieces.append(content)
        last = number
    text = " ".join(" ".join(pieces).split())
    return HeaderDescription(True, text, start + 1, last + 1)


def header_findings(repo_root, files):
    """Return {path: "empty" or "missing"} for the files of ``files`` whose banner Description has no text.

    ``empty`` is a Description field with no text after it; ``missing`` is a
    file with no Description field in its first 60 lines. Files with text are
    left out. ``contradicts`` is a judgment, so it is never computed.
    """
    findings = {}
    for path in files:
        description = header_description(Path(repo_root) / path)
        if not description.found:
            findings[path] = "missing"
        elif not description.text:
            findings[path] = "empty"
    return findings


# ---------------------------------------------------------------------------
# Verification status
# ---------------------------------------------------------------------------

def _baselines():
    """Import the CI baselines on first use (they live beside the simulator helpers)."""
    from tests.common import ghdl_analysis, source_inventory

    return ghdl_analysis, source_inventory


def _relative(repo_root, path):
    return Path(path).resolve().relative_to(Path(repo_root).resolve()).as_posix()


def verification_status(path, unit, inventory, repo_root=REPO_ROOT):
    """Return the verification status of the entity ``unit`` declared in repo-relative ``path``.

    The first rule that applies wins: baseline-excluded, Vivado-only,
    simulated, not simulated, not loaded.
    """
    ghdl_analysis, source_inventory = _baselines()
    name = unit.name.lower()
    if name in ghdl_analysis.KNOWN_GHDL_UNANALYZABLE:
        return STATUS_BASELINE
    if path.startswith(GT_DIRECTORIES):
        return STATUS_VIVADO
    loaded_by = inventory.entities.get(name)
    this_file_is_loaded = loaded_by is not None and _relative(repo_root, loaded_by) == path
    if inventory.has_dedicated_test(name) and (this_file_is_loaded or loaded_by is None):
        return STATUS_SIMULATED
    if name in ghdl_analysis.NOT_SIMULATED:
        return STATUS_NOT_SIMULATED
    if path in source_inventory.UNLOADED_SOURCES:
        return STATUS_NOT_LOADED
    raise ValueError(f"{path}: no verification status")


def status_detail(status, name, path):
    """Return the text of the ``Status:`` line of an entity section."""
    ghdl_analysis, source_inventory = _baselines()
    key = name.lower()
    if status == STATUS_BASELINE:
        fragment = ghdl_analysis.KNOWN_GHDL_UNANALYZABLE[key]
        return f'{status}; GHDL analysis reports "{fragment}", which the regression records as a known failure'
    if status == STATUS_NOT_SIMULATED:
        return f"{status}; {ghdl_analysis.NOT_SIMULATED[key]}"
    if status == STATUS_NOT_LOADED:
        return f"{status}; {source_inventory.UNLOADED_SOURCES[path]}"
    if status == STATUS_SIMULATED and path.endswith(".v"):
        return f"{status}; a cocotb test runs the module in Icarus Verilog"
    return status


def issue_cell(links):
    """Render issue links: ``:issue:`N``` ordered by number, ``issue pending`` last, ``none`` when empty."""
    filed = []
    pending = 0
    for link in links:
        if link == PENDING_ISSUE:
            pending += 1
        elif ISSUE_URL_RE.match(link):
            filed.append(int(link.rsplit("/", 1)[1]))
        else:
            raise ValueError(f"issue link {link!r} is neither a slaclab/lcls-timing-core issue URL nor {PENDING_ISSUE!r}")
    parts = [f":issue:`{number}`" for number in sorted(set(filed))] + ["issue pending"] * pending
    return ", ".join(parts) if parts else "none"


def _tree_by_key(key):
    for tree in DOC_TREES:
        if tree.key == key:
            return tree
    raise ValueError(f"unknown documentation tree {key!r}")


def _tree_units(repo_root, tree):
    """Return {path: DesignUnit} for every documented VHDL and Verilog file of ``tree``."""
    return {path: read_unit(Path(repo_root) / path) for path in documented_files(repo_root, tree)}


def _entity_statuses(repo_root, units, paths=None):
    """Return {path: status} for the entity files among ``units`` (restricted to ``paths`` when given)."""
    _, source_inventory = _baselines()
    inventory = source_inventory.Inventory(repo_root)
    return {
        path: verification_status(path, unit, inventory, repo_root)
        for path, unit in units.items()
        if unit.kind in ("entity", "module") and (paths is None or path in paths)
    }


def statuses(repo_root=REPO_ROOT, tree="core"):
    """Return {path: status} for every documented file of ``tree`` that declares an entity or module.

    The render filter is ignored; packages have no status.
    """
    return _entity_statuses(repo_root, _tree_units(repo_root, _tree_by_key(tree)))


def entity_issues(path, unit, status, header_issues=None):
    """Return the issue links of one entity row.

    The GHDL issue of a baseline-excluded entity, the unloaded-files issue of
    every file in UNLOADED_SOURCES whatever its status, and the header issue
    of the file when ``header_issues`` (the header sidecar) has an entry.
    """
    ghdl_analysis, source_inventory = _baselines()
    links = []
    if status == STATUS_BASELINE:
        links.append(ghdl_analysis.KNOWN_GHDL_ISSUES[unit.name.lower()])
    if path in source_inventory.UNLOADED_SOURCES:
        links.append(source_inventory.UNLOADED_SOURCES_ISSUE)
    if header_issues and path in header_issues:
        links.append(header_issues[path]["issue"])
    return links


# ---------------------------------------------------------------------------
# Entity pages
# ---------------------------------------------------------------------------

def entity_section(path, unit, purpose, status, detail, issues, qualified):
    """Return the section of one entity: label, title, file, purpose, status, generics, ports, issues."""
    if not purpose:
        raise ValueError(f"{path}: no purpose in docs/_data/{SIDECAR_PURPOSES}")
    if not status:
        raise ValueError(f"{path}: no verification status")
    heading = f"{unit.name} ({path})" if qualified else unit.name
    if unit.generics:
        generics = list_table(
            ["Name", "Type", "Default"],
            [[literal(g.name), literal(g.type_text), literal(g.default_text)] for g in unit.generics],
            widths=[25, 35, 40],
        )
    else:
        generics = "none\n"
    if unit.ports:
        ports = list_table(
            ["Name", "Direction", "Type"],
            [[literal(p.name), p.mode, literal(p.type_text)] for p in unit.ports],
            widths=[25, 15, 60],
        )
    else:
        ports = "none\n"
    return "\n".join(
        [
            f".. _entity-{slug(path)}:",
            "",
            title(heading, "-"),
            f"File: {repo_link(path)}",
            "",
            purpose.strip(),
            "",
            f"Status: {detail}",
            "",
            ".. rubric:: Generics",
            "",
            generics,
            ".. rubric:: Ports",
            "",
            ports,
            f"Issues: {issues}",
            "",
        ]
    )


def render_entity_index():
    rows = [[literal(status), meaning] for status, meaning in STATUS_MEANING]
    lines = [
        title("Entities", "="),
        "The VHDL entities and Verilog modules of the library, with their purpose, generics, ports, and the way the "
        "regression covers it. The pages are generated from the sources by ``python -m tests.common.gen_docs``; "
        "the purposes are authored.",
        "",
        "Each entity or module has one of five verification statuses:",
        "",
        list_table(["Status", "Meaning"], rows, widths=[30, 70]),
        ".. toctree::",
        "   :maxdepth: 1",
        "",
        *[f"   {tree.key}" for tree in DOC_TREES],
        "",
    ]
    return "\n".join(lines)


def render_tree_page(repo_root, tree, purposes, header_issues):
    """Return the page of one tree: the summary table and one section per rendered entity."""
    units = _tree_units(repo_root, tree)
    rendered = rendered_files(repo_root, tree)
    all_statuses = _entity_statuses(repo_root, units, set(rendered))
    names = [unit.name.lower() for unit in units.values() if unit.kind in ("entity", "module")]
    packages = [path for path in rendered if units.get(path) and units[path].kind == "package"]
    entities = sorted(
        (path for path in rendered if path in all_statuses),
        key=lambda path: (path, units[path].name),
    )
    rows = []
    sections = []
    for path in entities:
        unit = units[path]
        status = all_statuses[path]
        issues = issue_cell(entity_issues(path, unit, status, header_issues))
        rows.append([f":ref:`{unit.name} <entity-{slug(path)}>`", repo_link(path), status, issues])
        sections.append(
            entity_section(
                path,
                unit,
                purposes.get(path),
                status,
                status_detail(status, unit.name, path),
                issues,
                names.count(unit.name.lower()) > 1,
            )
        )
    loaders = [repo_link(path) for path in tree.ruckus_files]
    loaded_by = loaders[0] + " loads" if len(loaders) == 1 else ", ".join(loaders[:-1]) + f", and {loaders[-1]} load"
    lines = [
        title(tree.title, "="),
        f"{loaded_by} these sources into the ``lcls_timing_core`` library; a file that is not loaded says so in "
        "the Status column.",
        "",
        *([tree.note, ""] if tree.note else []),
        list_table(["Entity", "File", "Status", "Issues"], rows, widths=[20, 40, 25, 15]),
    ]
    if packages:
        lines += ["Package files in this tree: " + ", ".join(repo_link(path) for path in packages) + ".", ""]
    lines += sections
    return "\n".join(lines)


def render_entities(repo_root=REPO_ROOT):
    """Return {docs-relative path: text} for the entity index and the tree pages."""
    purposes = load_sidecar(SIDECAR_PURPOSES, repo_root)
    header_issues = load_sidecar(SIDECAR_HEADER_ISSUES, repo_root)
    pages = {"reference/entities/index.rst": render_entity_index()}
    for tree in DOC_TREES:
        pages[f"reference/entities/{tree.key}.rst"] = render_tree_page(repo_root, tree, purposes, header_issues)
    return pages


def render_reference_index(pages):
    """Return reference/index.rst: a toctree of the top page of every generated section."""
    entries = sorted(
        match.group(1)
        for path in pages
        if (match := re.fullmatch(r"reference/([^/]+)/index\.rst", path))
    )
    top_pages = [
        match.group(1)
        for path in pages
        if (match := re.fullmatch(r"reference/([^/]+)\.rst", path)) and match.group(1) != "index"
    ]
    return "\n".join(
        [
            title("Reference", "="),
            "Lookup material for the library, generated from the sources by "
            "``python -m tests.common.gen_docs``: entities with their generics and ports, the verification "
            "status of each, the register maps with their reset values and agreement across the RTL, PyRogue, and "
            "YAML sources, and the FPGA family matrix. Do not edit these pages by hand.",
            "",
            ".. toctree::",
            "   :maxdepth: 1",
            "",
            *[f"   {entry}/index" for entry in entries],
            *[f"   {page}" for page in sorted(top_pages)],
            "",
        ]
    )


# ---------------------------------------------------------------------------
# FPGA family matrix
# ---------------------------------------------------------------------------

class FamilyRow(NamedTuple):
    """One row of the family matrix: a family and one GT directory it loads."""

    family: str
    directory: str
    wrapper: str
    vivado_gate: str
    coregen: str
    selection: str


LCLS_II_RUCKUS = "LCLS-II/ruckus.tcl"

_TCL_COMMENT_RE = re.compile(r"^[ \t]*#.*$", re.MULTILINE)
_TCL_IF_RE = re.compile(r"if\s*(?=\{)")
_TCL_ELSE_RE = re.compile(r"\s*else\s*(?=\{)")
_TCL_SET_RE = re.compile(r'set\s+(\w+)\s+"([^"]*)"')
_TCL_LOAD_DIR_RE = re.compile(r'loadSource\s+-lib\s+lcls_timing_core\s+-dir\s+"\$::DIR_PATH/rtl/?"')
_TCL_LOAD_PATH_RE = re.compile(r'loadSource\s+-lib\s+lcls_timing_core\s+-path\s+"([^"]+)"')
_TCL_LOAD_IP_RE = re.compile(r'loadIpCore\s+-path\s+"([^"]+)"')
_TCL_LOAD_XDC_RE = re.compile(r'loadConstraints\s+-path\s+"([^"]+)"')
_TCL_LOAD_RUCKUS_RE = re.compile(r'loadRuckusTcl\s+"\$::DIR_PATH/([^"]+)"')
_TCL_VIVADO_RE = re.compile(r"\$::env\(VIVADO_VERSION\)\s*(>=|<)\s*([0-9.]+)")
_TCL_ENV_EQ_RE = re.compile(r"\[info exists ::env\((\w+)\)\]\s*!=\s*0\s*&&\s*\$::env\(\1\)\s*==\s*1")
_TCL_ENV_UNSET_RE = re.compile(r"\[info exists ::env\((\w+)\)\]\s*!=\s*1\s*\|\|\s*\$::env\(\1\)\s*==\s*0")
_TCL_FAMILY_RE = re.compile(r'\$\{family\}\s*(?:eq|==)\s*(?:\{(\w+)\}|"(\w+)")')
_TCL_LOCK_RE = re.compile(r"\[(?:SubmoduleCheck|VersionCheck)\b[^\]]*\]\s*<\s*0")

_VIVADO_NEGATION = {">=": "<", "<": ">="}
_ENV_NEGATION = {"=1": "not1", "not1": "=1", "unset_or_0": "set_nonzero", "set_nonzero": "unset_or_0"}
_ENV_WORDS = {
    "=1": "{0} = 1",
    "not1": "{0} not 1",
    "unset_or_0": "{0} unset or 0",
    "set_nonzero": "{0} set and not 0",
}


def _tcl_group(text, start):
    """Return (inner text, index after the closing brace) of the brace group that opens at ``text[start]``."""
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:index], index + 1
    raise ValueError("unbalanced braces in TCL text")


def _tcl_nodes(text):
    """Parse TCL ``text`` into [("if", condition, then nodes, else nodes) or ("cmd", line)] without executing it."""
    nodes = []
    position = 0
    while position < len(text):
        rest = text[position:]
        stripped = rest.lstrip()
        if not stripped:
            break
        position += len(rest) - len(stripped)
        keyword = _TCL_IF_RE.match(text, position)
        if keyword:
            condition, position = _tcl_group(text, keyword.end())
            body_at = text.find("{", position)
            if body_at < 0 or text[position:body_at].strip():
                raise ValueError(f"if without a body: {condition.strip()!r}")
            then_text, position = _tcl_group(text, body_at)
            else_text = ""
            other = _TCL_ELSE_RE.match(text, position)
            if other:
                else_text, position = _tcl_group(text, other.end())
            nodes.append(("if", condition.strip(), _tcl_nodes(then_text), _tcl_nodes(else_text)))
            continue
        end = text.find("\n", position)
        end = len(text) if end < 0 else end
        nodes.append(("cmd", text[position:end].strip()))
        position = end + 1
    return nodes


def _tcl_terms(condition):
    """Return (term when true, term when false) of a known TCL condition, or None for a lock check.

    A term is ("vivado", operator, version), ("env", name, kind), or
    ("family", names). Raises ValueError for any other condition, so a new
    kind of test in a ruckus.tcl cannot pass unnoticed.
    """
    if _TCL_LOCK_RE.search(condition):
        return None
    found = _TCL_VIVADO_RE.fullmatch(condition.strip())
    if found:
        op, version = found.groups()
        return ("vivado", op, version), ("vivado", _VIVADO_NEGATION[op], version)
    for pattern, kind in ((_TCL_ENV_EQ_RE, "=1"), (_TCL_ENV_UNSET_RE, "unset_or_0")):
        found = pattern.fullmatch(" ".join(condition.split()))
        if found:
            return ("env", found.group(1), kind), ("env", found.group(1), _ENV_NEGATION[kind])
    names = tuple(first or second for first, second in _TCL_FAMILY_RE.findall(condition))
    if names:
        return ("family", names), ("not-family", names)
    raise ValueError(f"unrecognized TCL condition: {condition!r}")


def _tcl_leaves(text):
    """Return [(terms, command)] for every command of ``text``, each with the terms of the branches it runs under.

    Variables set with ``set name "value"`` are substituted in later
    commands, and a variable set inside a branch applies to the commands that
    follow, under that branch's terms.
    """
    paths = [((), {})]

    def run(nodes, paths):
        leaves = []
        for node in nodes:
            if node[0] == "cmd":
                updated = []
                for terms, env in paths:
                    assign = _TCL_SET_RE.fullmatch(node[1])
                    if assign:
                        env = {**env, assign.group(1): assign.group(2)}
                    else:
                        command = re.sub(r"\$\{(\w+)\}", lambda m, env=env: env.get(m.group(1), m.group(0)), node[1])
                        leaves.append((terms, command))
                    updated.append((terms, env))
                paths = updated
                continue
            _, condition, then_nodes, else_nodes = node
            pair = _tcl_terms(condition)
            if pair is None:
                continue
            merged = []
            for terms, env in paths:
                for branch_terms, body in (((*terms, pair[0]), then_nodes), ((*terms, pair[1]), else_nodes)):
                    if _feasible(branch_terms):
                        inner_leaves, inner_paths = run(body, [(branch_terms, env)])
                        leaves.extend(inner_leaves)
                        merged.extend(inner_paths)
            paths = merged
        return leaves, paths

    leaves, _ = run(_tcl_nodes(_TCL_COMMENT_RE.sub("", text)), paths)
    return leaves


def _version_key(version):
    return tuple(int(part) for part in version.split("."))


def _vivado_bounds(terms):
    """Return (lowest allowed version or None, first excluded version or None) of the Vivado terms of ``terms``."""
    lower = [term[2] for term in terms if term[0] == "vivado" and term[1] == ">="]
    upper = [term[2] for term in terms if term[0] == "vivado" and term[1] == "<"]
    return (max(lower, key=_version_key) if lower else None, min(upper, key=_version_key) if upper else None)


def _feasible(terms):
    """Return False when ``terms`` can never hold together.

    That is an empty Vivado range, opposite settings of one variable, or a
    family that is both required and excluded (a build has one family).
    """
    low, high = _vivado_bounds(terms)
    if low and high and _version_key(low) >= _version_key(high):
        return False
    kinds = {}
    allowed = None
    excluded = set()
    for term in terms:
        if term[0] == "env":
            kinds.setdefault(term[1], set()).add(term[2])
        elif term[0] == "family":
            allowed = set(term[1]) if allowed is None else allowed & set(term[1])
        elif term[0] == "not-family":
            excluded.update(term[1])
    if allowed is not None and not allowed - excluded:
        return False
    return not any(_ENV_NEGATION[kind] in found for found in kinds.values() for kind in found)


def _collapse_vivado(terms):
    """Return the text of the Vivado terms of ``terms``: one range such as ``Vivado >= 2016.4 and < 2025.1``."""
    low, high = _vivado_bounds(terms)
    if low and high:
        return f"Vivado >= {low} and < {high}"
    if low:
        return f"Vivado >= {low}"
    if high:
        return f"Vivado < {high}"
    return ""


def _env_texts(terms):
    return [_ENV_WORDS[kind].format(name) for term in terms if term[0] == "env" for _, name, kind in [term]]


def _condition_text(terms):
    parts = [text for text in [_collapse_vivado(terms), *_env_texts(terms)] if text]
    return ", ".join(parts) if parts else "always"


def _bullets(lines):
    lines = list(lines)
    if not lines:
        return "none"
    return lines[0] if len(lines) == 1 else "\n".join(f"- {line}" for line in lines)


def _gt_directory_facts(repo_root, directory):
    """Return (wrapper entity, RTL Vivado gate, coregen lines, selection lines) of one GT directory."""
    root = Path(repo_root) / "LCLS-II" / directory
    sources = sorted((root / "rtl").glob("*.vhd"))
    if len(sources) != 1:
        raise ValueError(f"LCLS-II/{directory}/rtl: expected one .vhd file, found {len(sources)}")
    wrapper = read_vhdl_unit(sources[0]).name
    rtl_gate = ""
    groups = {}
    for terms, command in _tcl_leaves((root / "ruckus.tcl").read_text(encoding="utf-8")):
        if _TCL_LOAD_DIR_RE.fullmatch(command):
            rtl_gate = _collapse_vivado(terms)
            continue
        for pattern, kind in ((_TCL_LOAD_IP_RE, None), (_TCL_LOAD_PATH_RE, None), (_TCL_LOAD_XDC_RE, "xdc")):
            found = pattern.fullmatch(command)
            if found:
                path = found.group(1).replace("$::DIR_PATH/", "")
                relative, name = path.rsplit("/", 1)
                stem, _, extension = name.rpartition(".")
                groups.setdefault((relative, extension or kind, terms), []).append(stem)
    coregen = []
    selection_sets = {}
    for (relative, extension, terms), stems in groups.items():
        coregen.append(f"{relative} ({extension}): {', '.join(sorted(stems))}; {_condition_text(terms)}")
        for term in terms:
            if term[0] == "env":
                selection_sets.setdefault(term[1], {}).setdefault(term, []).append((relative, extension))
    selection = []
    for name, by_term in selection_sets.items():
        differ_by_directory = len({frozenset(r for r, _ in pairs) for pairs in by_term.values()}) > 1
        for term, pairs in by_term.items():
            values = sorted({relative if differ_by_directory else extension for relative, extension in pairs})
            noun = "directory" if differ_by_directory else "file type"
            selection.append(f"{_ENV_WORDS[term[2]].format(name)}: {noun} {', '.join(values)}")
    return wrapper, rtl_gate or "none", coregen, selection


def read_family_matrix(repo_root=REPO_ROOT):
    """Return the FamilyRow list read from LCLS-II/ruckus.tcl and the GT ruckus.tcl files it loads.

    One row per family and GT directory, in the order of LCLS-II/ruckus.tcl,
    so a family that loads two directories has two rows. The files are only
    parsed (brace matching and regular expressions), never executed.
    """
    repo_root = Path(repo_root)
    text = (repo_root / LCLS_II_RUCKUS).read_text(encoding="utf-8")
    pairs = []
    for terms, command in _tcl_leaves(text):
        families = [term for term in terms if term[0] == "family"]
        loaded = _TCL_LOAD_RUCKUS_RE.fullmatch(command)
        if families and loaded:
            for family in families[-1][1]:
                pairs.append((family, loaded.group(1)))
    facts = {}
    rows = []
    for family, directory in pairs:
        if directory not in facts:
            facts[directory] = _gt_directory_facts(repo_root, directory)
        wrapper, gate, coregen, selection = facts[directory]
        rows.append(FamilyRow(family, directory, wrapper, gate, _bullets(coregen), _bullets(selection)))
    return rows


def read_locks(repo_root=REPO_ROOT):
    """Return (file, check, name, version) for every VersionCheck and SubmoduleCheck in the tracked ruckus.tcl files.

    The root ruckus.tcl comes first, then the others by path; tests/ is skipped.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", "*ruckus.tcl"], check=True, capture_output=True, text=True
    )
    files = sorted((line for line in result.stdout.splitlines() if not line.startswith("tests/")), key=lambda p: (p != "ruckus.tcl", p))
    locks = []
    for path in files:
        text = _TCL_COMMENT_RE.sub("", (Path(repo_root) / path).read_text(encoding="utf-8"))
        for match in re.finditer(r"\b(VersionCheck)\s+([0-9.]+)|\b(SubmoduleCheck)\s+\{(\w+)\}\s+\{([0-9.]+)\}", text):
            if match.group(1):
                locks.append((path, "VersionCheck", "Vivado", match.group(2)))
            else:
                locks.append((path, "SubmoduleCheck", match.group(4), match.group(5)))
    return locks


def render_families(repo_root=REPO_ROOT):
    """Return reference/families.rst: the family matrix and the version checks."""
    rows = [
        [
            family.family,
            repo_link(f"LCLS-II/{family.directory}/ruckus.tcl"),
            family.wrapper,
            family.vivado_gate,
            family.coregen,
            family.selection,
        ]
        for family in read_family_matrix(repo_root)
    ]
    locks = [[repo_link(path), check, name, version] for path, check, name, version in read_locks(repo_root)]
    return "\n".join(
        [
            title("FPGA families, Vivado, and coregen", "="),
            f"{repo_link(LCLS_II_RUCKUS)} asks ruckus for the FPGA family of the build and loads the transceiver "
            "wrapper directories listed here. The table has one row for each family and directory, so a family that "
            "loads two directories has two rows.",
            "",
            list_table(
                ["Family", "Directory", "Wrapper entity", "Vivado gate on the RTL", "Coregen IP loaded", "Selected by"],
                rows,
                widths=[11, 17, 14, 11, 30, 17],
            ),
            "The coregen column lists, for each Vivado version range and environment variable setting, the directory, "
            "the file type, and the IP cores that the directory's ``ruckus.tcl`` loads. Outside the listed ranges the "
            "directory loads no IP and its ``ruckus.tcl`` prints a warning.",
            "",
            "The transceiver wrappers are not simulated in CI, see :doc:`entities/gt`.",
            "",
            title("Version checks and locks", "-"),
            "Every ``VersionCheck`` and ``SubmoduleCheck`` in the repository's ``ruckus.tcl`` files, as found.",
            "",
            list_table(["File", "Check", "Name", "Version"], locks, widths=[40, 20, 20, 20]),
        ]
    )


# ---------------------------------------------------------------------------
# Register maps
# ---------------------------------------------------------------------------

SIDECAR_RESETS = "register_resets.yaml"
NO_DESCRIPTION = "no description in source"
NOT_ASSERTED = "not asserted"
PYTHON_DIR = REPO_ROOT / "python"

# The blocks that have a register page, in page order: every block of the drift comparison.
REGISTER_BLOCKS = tuple(BLOCKS)

# Maps that describe no PyRogue class and no RTL decode here, documented from the YAML on one page.
YAML_ONLY_MAPS = tuple(sorted(name for name, kind in YAML_CLASSIFICATION.items() if kind == "shape"))
YAML_ONLY_PAGE = "reference/registers/yaml_only.rst"

# The reviewed table arguments of each (block, variant id) whose Python source
# is a built tree. The flags are the table `when` conditions that match the
# variant's Python arguments.
VARIANT_ARG_SETS = {
    ("EvrV2TriggerReg", "default"): ArgSet("default", {}),
    ("EvrV2TriggerReg", "useTap"): ArgSet("useTap", {"useTap": True}, ("useTap",)),
    ("EvrV2ChannelReg", "default"): ArgSet("default", {}),
    ("EvrV2ChannelReg", "dmaEnable"): ArgSet("dmaEnable", {"dmaEnable": True}, ("dmaEnable",)),
    ("EvrV2Core", "default"): ArgSet("default", {}),
    ("EvrV1Isr", "default"): ArgSet("default", {}),
    ("GthRxAlignCheck", "default"): ArgSet("default", {}),
    ("TimingFrameRx", "SELECT"): ArgSet("SELECT", {}, ("clkselSelect",)),
    ("TimingFrameRx", "LCLSII"): ArgSet("LCLSII", {"clkselMode": "LCLSII"}, ("clkselFixed",)),
    ("TPGMiniCore", "default"): ArgSet("default", {}),
    ("TPGMiniCore", "narrays1"): ArgSet("narrays1", {"NARRAYSBSA": 1}),
    ("TPGMiniCore", "narrays4"): ArgSet("narrays4", {"NARRAYSBSA": 4}),
    ("TPGControl", "default"): ArgSet("default", {}),
    ("LclsTriggerPulse", "default"): ArgSet("default", {}),
    ("EvrV2CoreTriggers", "default"): ArgSet(
        "default", {"numTrig": 16, "dmaEnable": True, "useTap": True}, ("dmaEnable", "useTap")
    ),
}

RTL_HEADER = ["Offset", "Field", "Bits", "Mode", "Reset", "Python", "YAML", "Description"]
RTL_WIDTHS = [9, 17, 7, 6, 12, 15, 15, 19]


class Sources(NamedTuple):
    """The three views of one block variant, as the drift comparison reads them."""

    python: list
    vhdl: object
    yaml: object
    yaml_unreadable: bool
    skip: frozenset
    decode: object


class Entry(NamedTuple):
    """One register of one array element (or a scalar) with the field each source has for it."""

    name: str
    element: int
    indexed: bool
    fields: dict


def python_view(block, variant):
    """RegFields of the Python class for one variant, from the reviewed tables.

    The tables are the checked copy of what the class builds, so no Rogue
    object is needed. Register variables and commands are kept, link variables
    dropped, and every position is the absolute bit split into a word byte
    address and a bit offset, the way Rogue reports it.
    """
    arg_set = VARIANT_ARG_SETS[(block.name, variant.id)]
    fields = []
    for entry in register_tables.expand(register_tables.load_table(block.name), arg_set).values():
        if entry.kind == "LinkVariable":
            continue
        if entry.abs_bit is None:
            raise ValueError(f"{block.name}: {entry.path} has no offset in its table")
        name, index = split_index(entry.path)
        fields.append(
            RegField(
                block=block.name, name=name, index=index,
                byte_offset=(entry.abs_bit // WORD_BITS) * 4, bit_offset=entry.abs_bit % WORD_BITS,
                bit_size=entry.bit_size, mode=entry.mode, source="python", line=0,
                readable=entry.mode in ("RW", "RO"), writable=entry.mode in ("RW", "WO"),
            )
        )
    return fields


def block_sources(block, variant):
    """Return the Sources of one block variant (the way the Rogue drift test assembles them)."""
    if block.python_source == "ast":
        python = pyrogue_ast.declared_fields(block.name, block.name)
    else:
        python = python_view(block, variant)
    vhdl = None
    decode = None
    skip = frozenset()
    if block.vhdl is not None:
        decode = read_decode(block.vhdl, generics=variant.generics)
        vhdl = from_vhdl(decode, block.name)
        skip = unresolved_words(decode.unresolved)
    yaml_fields_ = None
    unreadable = False
    if block.yaml is not None and variant.compare_yaml:
        if block.yaml in KNOWN_YAML_DEFECTS:
            unreadable = True
        else:
            yaml_fields_ = from_yaml(yaml_fields(block.yaml), block.name)
    return Sources(python, vhdl, yaml_fields_, unreadable, skip, decode)


def block_comparison(block, variant):
    """Compare one variant across the sources it has, as the Rogue drift test does without a tree."""
    sources = block_sources(block, variant)
    return compare_block(
        block, variant, sources.python, sources.vhdl, sources.yaml,
        NAME_MAPS.get(block.name, {}), yaml_unreadable=sources.yaml_unreadable, vhdl_skip=sources.skip,
    )


def _entries(grouped):
    entries = []
    for name, by_source in grouped.items():
        for element in sorted({e for per in by_source.values() for e in per}):
            fields = {s: per[element] for s, per in by_source.items() if element in per}
            python = fields.get("python")
            if python is not None:
                indexed = python.index is not None
            else:
                indexed = any(f.index is not None for f in fields.values())
            entries.append(Entry(name, element, indexed, fields))
    return entries


def split_entries(block, sources):
    """Return (RTL-primary entries, entries no readable RTL covers) for one variant."""
    name_map = NAME_MAPS.get(block.name, {})
    if sources.vhdl is None:
        return [], _entries(group_fields(sources.python, None, sources.yaml, name_map))
    python_in, python_out = coverage_split(sources.python, block.vhdl_window, sources.skip)
    yaml_in, yaml_out = coverage_split(sources.yaml, block.vhdl_window, sources.skip)
    vhdl_in = coverage_split(sources.vhdl, block.vhdl_window, sources.skip)[0]
    inside = _entries(group_fields(python_in, vhdl_in, yaml_in, name_map))
    outside = _entries(group_fields(python_out, None, yaml_out, name_map))
    return inside, outside


def _primary(entry, order):
    for source in order:
        if source in entry.fields:
            return entry.fields[source]
    raise ValueError(f"entry {entry.name} holds no field")


def _issue_text(block, name, kind):
    issue = ALLOWLIST.get((block, name, kind))
    if issue is None:
        return ""
    if issue == PENDING_ISSUE:
        return " (issue pending)"
    return f" :issue:`{issue.rsplit('/', 1)[1]}`"


def state_cell(block, state):
    """Return the cell of a source that is not compared; an unreadable map links its block-level issue."""
    if state == "map does not parse":
        return state + _issue_text(block, "<yaml>", "missing-in-yaml")
    return state


def step_text(step):
    """Return the per-element step of a source as text: bytes when it is whole words, else bits."""
    if not step:
        return ""
    return f", step 0x{step // BITS_PER_BYTE:X}" if step % WORD_BITS == 0 else f", step {step} bits"


def _where(field, step):
    """Return where a source puts a field: the word address, the bits, the mode, and the element step."""
    return f"at 0x{field.word_byte:03X} {bits_cell(field)} {field.mode}{step_text(step)}"


def _differs(block, name, kinds, field, step=0, location=True, python_kinds=()):
    """Return the ``differs`` cell: kinds against the primary source, then kinds against Python only."""
    parts = []
    for label, group in (("differs", kinds), ("differs from Python", python_kinds)):
        if group:
            parts.append(f"{label}: " + ", ".join(f"{kind}{_issue_text(block, name, kind)}" for kind in group))
    text = "; ".join(parts)
    return f"{text}\n{_where(field, step)}" if location else text


def _absent(block, name, source):
    return "absent" + _issue_text(block, name, f"missing-in-{source}")


def rtl_agreement(block, entry, source, state, step=0, location=True):
    """Return the agreement cell of ``source`` (python or yaml) against the RTL field of the entry.

    The YAML cell also reports the kinds in which the YAML field differs from the Python field, because
    two sources that each agree with the RTL can still differ from each other (a write-only strobe the YAML
    map can only call read-write). step is the source's distance in bits between the elements of a collapsed
    run; location False leaves out the line that says where the source puts the field (used to decide
    whether two elements share a row).
    """
    if state != "compared":
        return state_cell(block, state)
    field = entry.fields.get(source)
    rtl = entry.fields.get("vhdl")
    if field is None:
        return _absent(block, entry.name, source)
    python = entry.fields.get("python")
    against_python = pair_kinds(python, field) if source == "yaml" and python is not None else []
    if rtl is None:
        kinds = ["missing-in-vhdl"]
        against_python = [kind for kind in against_python if kind not in kinds]
        rtl_kinds = kinds
    else:
        rtl_kinds = pair_kinds(rtl, field)
        against_python = [kind for kind in against_python if kind not in rtl_kinds]
    if not rtl_kinds and not against_python:
        return "agrees"
    return _differs(block, entry.name, rtl_kinds, field, step, location, against_python)


def python_agreement(block, entry, state, step=0, location=True):
    """Return the YAML cell of an entry that has no RTL, judged against the Python field."""
    if state != "compared":
        return state_cell(block, state)
    python = entry.fields.get("python")
    yaml_field = entry.fields.get("yaml")
    if yaml_field is None:
        return _absent(block, entry.name, "yaml")
    if python is None:
        return _differs(block, entry.name, ["missing-in-python"], yaml_field, step, location)
    kinds = pair_kinds(python, yaml_field)
    return _differs(block, entry.name, kinds, yaml_field, step, location) if kinds else "agrees"


def yaml_state(block, variant, sources):
    """Return ``compared``, ``not compared``, or ``map does not parse`` for the YAML source."""
    if sources.yaml_unreadable:
        return "map does not parse"
    return "compared" if sources.yaml is not None else "not compared"


def variant_resets(resets, block, variant):
    """Return {word byte address: word} of the sidecar entries of one variant."""
    words = resets.get(block.name, {}).get(variant.id, {})
    return {int(address, 16): int(entry["value"], 16) for address, entry in words.items()}


def reset_cell(words, field):
    """Return the slice of the asserted reset words that ``field`` covers, or ``not asserted``."""
    size = field.bit_size
    if size is None:
        return NOT_ASSERTED
    low = field.bit_in_word
    value = 0
    for count in range((low + size + WORD_BITS - 1) // WORD_BITS):
        word = words.get(field.word_byte + 4 * count)
        if word is None:
            return NOT_ASSERTED
        value |= word << (WORD_BITS * count)
    return literal(f"0x{(value >> low) & ((1 << size) - 1):0{(size + 3) // 4}X}")


def bits_cell(field):
    """Return ``[hi:lo]`` (or ``[bit]``) of a field within its word."""
    low = field.bit_in_word
    size = field.bit_size
    if size is None:
        return "strobe"
    return f"[{low}]" if size == 1 else f"[{low + size - 1}:{low}]"


class RegRow(NamedTuple):
    """A table row: one entry, or a run of consecutive array elements that share every cell."""

    name: str
    first: Entry
    count: int
    strides: dict


def shape(entry):
    """Return the width and mode every source gives an entry; elements of a run must share it."""
    return tuple(sorted((source, field.bit_size, field.mode) for source, field in entry.fields.items()))


def collapse(entries, signature):
    """Join consecutive array elements into one RegRow each.

    Elements join when they share the signature (the cells) and each source
    moves by the same number of bits from one element to the next, so the row
    can say ``offset + stride * i``. An irregular array stays in several rows.
    """
    rows = []
    by_name = {}
    for entry in entries:
        by_name.setdefault(entry.name, []).append(entry)
    for name, group in by_name.items():
        group.sort(key=lambda entry: entry.element)
        run = [group[0]]
        strides = {}
        for entry in group[1:]:
            last = run[-1]
            steps = {
                source: field.abs_bit - last.fields[source].abs_bit
                for source, field in entry.fields.items()
                if source in last.fields
            }
            joins = (
                entry.indexed
                and last.indexed
                and entry.element == last.element + 1
                and signature(entry) == signature(last)
                and (not strides or steps == strides)
            )
            if joins:
                strides = steps
                run.append(entry)
            else:
                rows.append(RegRow(name, run[0], len(run), strides))
                run, strides = [entry], {}
        rows.append(RegRow(name, run[0], len(run), strides))
    return rows


def _row_key(row, primary_order):
    field = _primary(row.first, primary_order)
    return (field.word_byte, field.bit_in_word, row.name, row.first.element)


def stride_text(step):
    """Return a per-element step in bits as bytes when it is whole words, else as bits."""
    return f"0x{step // BITS_PER_BYTE:X}" if step % WORD_BITS == 0 else f"{step} bits"


def offset_cell(row, primary_order):
    field = _primary(row.first, primary_order)
    text = literal(f"0x{field.word_byte:03X}")
    if row.count == 1:
        return text
    return f"{text} + {literal(stride_text(row.strides[field.source]))} * i"


def name_cell(row, sources_order):
    """Return the field name, and the names the other sources give the same register."""
    last = row.first.element + row.count - 1
    if row.count > 1:
        shown = f"{row.name}[{row.first.element}..{last}]"
    else:
        shown = f"{row.name}[{row.first.element}]" if row.first.indexed else row.name
    lines = [literal(shown)]
    for source, label in sources_order:
        field = row.first.fields.get(source)
        if field is None or field.name == row.name:
            continue
        other = field.name
        if field.index is not None:
            other += f"[{row.first.element}..{last}]" if row.count > 1 else f"[{field.index}]"
        lines.append(f"{label}: {literal(other)}")
    return "\n".join(lines)


def description_for(entry, descriptions):
    if "python" not in entry.fields:
        return NO_DESCRIPTION
    return descriptions.get(entry.name) or NO_DESCRIPTION


def table_descriptions(class_name):
    """Return {variable name: description} of a class and the children its reviewed table names."""
    found = dict(pyrogue_ast.read_descriptions(PYTHON_DIR / "LclsTimingCore" / f"{class_name}.py"))
    for child in getattr(register_tables.load_table(class_name), "CHILDREN", ()):
        prefix = child.name.split("[")[0] + "."
        for name, text in table_descriptions(child.table).items():
            found.setdefault(prefix + name, text)
    return found


def python_descriptions(block):
    """Return {Python variable name: description} for a block, read from its class files with ast.

    A built-tree block follows the children its reviewed table names, because
    its source adds them in a loop; a source-read block follows the child
    devices written as literals.
    """
    if block.python_source == "ast":
        return pyrogue_ast.declared_descriptions(block.name)
    return table_descriptions(block.name)


def rtl_table(block, entries, state, words, descriptions):
    order = ("vhdl", "python", "yaml")

    def signature(entry):
        field = _primary(entry, order)
        return (
            shape(entry),
            rtl_agreement(block.name, entry, "python", "compared", location=False),
            rtl_agreement(block.name, entry, "yaml", state, location=False),
            reset_cell(words, field),
            description_for(entry, descriptions),
        )

    rows = sorted(collapse(entries, signature), key=lambda row: _row_key(row, order))
    body = []
    for row in rows:
        field = _primary(row.first, order)
        body.append(
            [
                offset_cell(row, order),
                name_cell(row, (("vhdl", "RTL"), ("yaml", "YAML"))),
                bits_cell(field),
                field.mode,
                reset_cell(words, field),
                rtl_agreement(block.name, row.first, "python", "compared", row.strides.get("python", 0)),
                rtl_agreement(block.name, row.first, "yaml", state, row.strides.get("yaml", 0)),
                description_for(row.first, descriptions),
            ]
        )
    return list_table(RTL_HEADER, body, widths=RTL_WIDTHS)


PYTHON_HEADER = ["Offset", "Field", "Bits", "Mode", "YAML", "Description"]
PYTHON_WIDTHS = [10, 22, 8, 7, 23, 30]


def python_table(block, entries, state, descriptions):
    """Return the table of entries that have no readable RTL: the Python view with the YAML agreement."""
    order = ("python", "yaml")

    def signature(entry):
        return (
            shape(entry),
            python_agreement(block.name, entry, state, location=False),
            description_for(entry, descriptions),
        )

    rows = sorted(collapse(entries, signature), key=lambda row: _row_key(row, order))
    body = []
    for row in rows:
        field = _primary(row.first, order)
        body.append(
            [
                offset_cell(row, order),
                name_cell(row, (("yaml", "YAML"),)),
                bits_cell(field),
                field.mode,
                python_agreement(block.name, row.first, state, row.strides.get("yaml", 0)),
                description_for(row.first, descriptions),
            ]
        )
    return list_table(PYTHON_HEADER, body, widths=PYTHON_WIDTHS)


def decode_notes(block, sources):
    """Return the notes on the RTL the page cannot show: the window edge and the words the parser skipped."""
    lines = []
    if block.vhdl_window is not None:
        low, high = block.vhdl_window
        lines += [
            f"The RTL decodes the words from 0x{low:03X} to 0x{high:03X} only; the words above it have no RTL in "
            "this repository, so they are listed in the table of registers without RTL below.",
            "",
        ]
    if sources.decode is not None and sources.decode.unresolved:
        lines += [
            "Not decoded: the parser could not interpret these RTL arms, so the Python and YAML registers of "
            "their words are compared with each other only.",
            "",
            *[f"* {literal(entry)}" for entry in sources.decode.unresolved],
            "",
        ]
    return "\n".join(lines)


def strobe_note(sources, inside):
    """Return the sentence that names the access strobes no register of the table carries."""
    if sources.decode is None:
        return ""
    named = {field.name for entry in inside for field in [entry.fields.get("vhdl")] if field is not None}
    strobes = sorted(
        {
            (strobe.byte_offset, strobe.kind, strobe.target)
            for strobe in sources.decode.strobes
            if f"{strobe.target}!{strobe.kind}" not in named
        }
    )
    if not strobes:
        return ""
    items = ", ".join(f"a {kind} of 0x{offset:03X} pulses {literal(target)}" for offset, kind, target in strobes)
    return f"Access strobes carry no data and are not registers: {items}.\n"


def yaml_defect_table(block):
    """Return the one-row table that names the parse error of an unreadable YAML map and its issue."""
    kind, line, fragment = KNOWN_YAML_DEFECTS[block.yaml]
    lines = (REPO_ROOT / "yaml" / block.yaml).read_text(encoding="utf-8").splitlines()
    spliced = any(INCLUDE_RE.match(text) for text in lines)
    where = f"line {line}" + (" of the text after the includes are spliced in" if spliced else "")
    issue = _issue_text(block.name, "<yaml>", "missing-in-yaml").strip() or "none"
    row = [repo_link(f"yaml/{block.yaml}"), f"{literal(kind)} at {where}: {fragment}", issue]
    return list_table(["YAML map", "Parse error", "Issue"], [row], widths=[30, 55, 15])


def render_variant(block, variant, words, descriptions):
    sources = block_sources(block, variant)
    state = yaml_state(block, variant, sources)
    inside, outside = split_entries(block, sources)
    arguments = ", ".join(literal(f"{key}={value!r}") for key, value in variant.python_args.items()) or "none"
    if block.vhdl is None:
        header = f"Python arguments: {arguments}."
    else:
        generics = (
            ", ".join(f"{literal(key)} = {literal(str(value))}" for key, value in variant.generics.items()) or "none"
        )
        header = f"RTL generics: {generics}. Python arguments: {arguments}."
    lines = [title(f"Variant {variant.id}", "-"), header, ""]
    if state == "map does not parse":
        lines.append(yaml_defect_table(block))
    if inside:
        lines.append(rtl_table(block, inside, state, words, descriptions))
    lines += [note for note in (strobe_note(sources, inside), decode_notes(block, sources)) if note]
    if outside:
        if block.vhdl is not None:
            lines += ["Registers without RTL in the repository (the Python view, with the YAML agreement):", ""]
        lines.append(python_table(block, outside, state, descriptions))
    return "\n".join(lines)


def known_differences(block, details):
    """Return the section that lists every allowlisted drift of the block, or an empty string."""
    keys = sorted(key for key in ALLOWLIST if key[0] == block.name)
    if not keys:
        return ""
    bullets = []
    for key in keys:
        issue = ALLOWLIST[key]
        link = "issue pending" if issue == PENDING_ISSUE else f":issue:`{issue.rsplit('/', 1)[1]}`"
        detail = details.get(key, "no longer reported by the comparison")
        bullets.append(f"   * {literal(key[1])} ({key[2]}): {literal(detail)} {link}")
    return "\n".join(
        [
            title("Known differences", "-"),
            "The comparison of the sources reports these differences, each recorded against an issue.",
            "",
            ".. warning::",
            "",
            "   The sources disagree on the following registers; treat the RTL as the measured behavior.",
            "",
            *bullets,
            "",
        ]
    )


def page_label(name):
    """Return the label of the page of a register block (the target of the child links)."""
    return f"register-map-{slug(name)}"


def child_rows(block):
    """Return [name, class, offset, count, stride] for the child devices of a composite block, or []."""
    if block.python_source == "ast":
        path = PYTHON_DIR / "LclsTimingCore" / f"{block.name}.py"
        return [[child.name, child.cls, child.offset, 1, ""] for child in pyrogue_ast.read_child_devices(path)]
    table = register_tables.load_table(block.name)
    arg_set = VARIANT_ARG_SETS[(block.name, block.variants[0].id)]
    rows = []
    for child in getattr(table, "CHILDREN", ()):
        number = child.number
        count = number if number is None or isinstance(number, int) else arg_set.args.get(number, table.DEFAULTS[number])
        rows.append([child.name.split("[")[0], child.table, child.offset, 1 if count is None else count, child.stride or ""])
    return rows


def child_table(block):
    """Return the table of child devices of a composite block (each class links its own register page), or ''."""
    rows = child_rows(block)
    if not rows:
        return ""
    body = []
    for name, cls, offset, count, stride in rows:
        target = f":ref:`{cls} <{page_label(cls)}>`" if cls in REGISTER_BLOCKS else literal(cls)
        body.append(
            [literal(name), target, literal(f"0x{offset:X}"), str(count), literal(f"0x{stride:X}") if stride != "" else ""]
        )
    return "\n".join(
        [
            "The class adds these child devices; their registers appear below with the child name in front.",
            "",
            list_table(["Child", "Class", "Offset", "Count", "Stride"], body, widths=[25, 30, 15, 10, 20]),
        ]
    )


def render_register_page(block, resets=None):
    """Return the page of one register block: a table per variant, then the known differences."""
    if resets is None:
        resets = load_sidecar(SIDECAR_RESETS)
    descriptions = python_descriptions(block)
    parts = [f".. _{page_label(block.name)}:\n", title(f"{block.name} registers", "=")]
    if block.vhdl is None:
        parts += [
            "No RTL in repo: the firmware that implements this block lives outside this repository, so the "
            "tables show the PyRogue declarations and how the YAML map agrees with them.",
            "",
        ]
    links = []
    if block.vhdl is not None:
        links.append(f"Decode file: {repo_link(block.vhdl)}.")
    links.append(f"Python class: {repo_link(f'python/LclsTimingCore/{block.name}.py')}.")
    if block.yaml is not None:
        links.append(f"YAML map: {repo_link(f'yaml/{block.yaml}')}.")
    parts += [" ".join(links), ""]
    composite = child_table(block)
    if composite:
        parts += [composite]
    details = {}
    for variant in block.variants:
        parts.append(render_variant(block, variant, variant_resets(resets, block, variant), descriptions))
        for drift in block_comparison(block, variant).drifts:
            details.setdefault((drift.block, drift.field, drift.kind), drift.detail)
    parts.append(known_differences(block, details))
    return "\n".join(parts)


def render_register_index():
    rows = [
        ["``agrees``", "the source holds the same position, width, and mode as the RTL field"],
        ["``differs: <kind>``", "the source disagrees; each kind links the issue that records it"],
        ["``differs from Python: <kind>``", "the YAML field differs from the Python variable in that kind"],
        ["``absent``", "the source has no field for this register"],
        ["``not compared``", "the variant does not compare this source (the YAML map describes one variant)"],
        ["``map does not parse``", "the YAML map cannot be read, so none of its fields are compared"],
    ]
    with_rtl = [name for name in REGISTER_BLOCKS if BLOCKS[name].vhdl is not None]
    without = [name for name in REGISTER_BLOCKS if BLOCKS[name].vhdl is None]
    covered = [
        f"* {literal(name)}: {reason}." for name, reason in COVERED_BY_LEAVES.items()
    ]
    return "\n".join(
        [
            title("Register maps", "="),
            "One page per register block. Each table of a block with RTL is read from the RTL address decode, one "
            "table per generic or argument variant. Offset is the byte address of the 32-bit word and Bits the "
            "position inside it. Mode is read-write (RW), read-only (RO), or write-only (WO) as the RTL decodes "
            "it. Reset is the slice of the word that a simulation asserts after reset, or ``not asserted`` "
            "when no test checks it; a word that mixes in a bit the testbench drives from an input is not "
            "listed. The Python and YAML columns compare the PyRogue declaration and the "
            "CPSW map with the RTL field. Description is the ``description`` text of the Python variable. "
            "A block with no RTL here is shown from its Python declarations, and the YAML column compares the "
            "map with them.",
            "",
            list_table(["Agreement", "Meaning"], rows, widths=[30, 70]),
            "Classes that hold no registers of their own are covered by their children:",
            "",
            *covered,
            "",
            ".. toctree::",
            "   :maxdepth: 1",
            "   :caption: Blocks with RTL in this repository",
            "",
            *[f"   {name}" for name in with_rtl],
            "",
            ".. toctree::",
            "   :maxdepth: 1",
            "   :caption: Blocks implemented outside this repository",
            "",
            *[f"   {name}" for name in without],
            "",
            ".. toctree::",
            "   :maxdepth: 1",
            "   :caption: YAML maps with no Python class",
            "",
            "   yaml_only",
            "",
        ]
    )


class YamlRow(NamedTuple):
    name: str
    offset: int
    lsb: int
    size: int
    mode: str
    count: int
    stride: int
    description: str


def yaml_only_rows(name):
    """Return the YamlRow list of a YAML map without expanding its arrays; raises ValueError naming the problem.

    The registers are the IntField children of the top-level key named after the file. A map that is an
    anchored fragment (the registers sit directly under the key, to be merged into another map) is read the
    same way. MMIODev children are entered once per element.
    """
    loaded = load(name)
    if loaded.error is not None:
        raise ValueError(f"{name} does not parse: {loaded.error}")
    stem = Path(name).stem
    node = (loaded.data or {}).get(stem)
    if not isinstance(node, dict):
        raise ValueError(f"{name} has no top-level key {stem!r}")

    def walk(parent, base, prefix):
        children = parent.get("children") or {
            key: value for key, value in parent.items() if isinstance(value, dict) and "class" in value
        }
        for key, child in children.items():
            if not isinstance(child, dict):
                continue
            at = child.get("at") or {}
            offset, count, stride = at.get("offset", 0), at.get("nelms", 1), at.get("stride", 0)
            kind = child.get("class")
            if kind == "IntField":
                yield YamlRow(
                    f"{prefix}{key}", base + offset, child.get("lsBit", 0), child.get("sizeBits", 32),
                    child["mode"], count if "nelms" in at else 1, stride, str(child.get("description") or ""),
                )
            elif kind == "MMIODev":
                for element in range(count):
                    suffix = f"[{element}]" if "nelms" in at else ""
                    yield from walk(child, base + offset + element * stride, f"{prefix}{key}{suffix}.")

    rows = list(walk(node, 0, ""))
    if not rows:
        raise ValueError(f"{name} holds no register under {stem!r}")
    return rows


def yaml_only_section(name):
    stem = Path(name).stem
    lines = [title(f"{stem}.yaml", "-"), f"YAML map: {repo_link(f'yaml/{name}')}.", ""]
    try:
        rows = yaml_only_rows(name)
    except ValueError as error:
        lines += [f"The registers cannot be listed: {literal(str(error))}", ""]
        return "\n".join(lines)
    body = []
    for row in sorted(rows, key=lambda row: (row.offset, row.lsb, row.name)):
        field = RegField("", row.name, None, row.offset, row.lsb, row.size, row.mode, "yaml", 0, True, True)
        offset = literal(f"0x{field.word_byte:03X}")
        shown = row.name
        if row.count > 1:
            offset += f" + {literal(stride_text(row.stride * BITS_PER_BYTE))} * i"
            shown = f"{row.name}[0..{row.count - 1}]"
        body.append([offset, literal(shown), bits_cell(field), row.mode, row.description])
    lines.append(list_table(["Offset", "Field", "Bits", "Mode", "Description"], body, widths=[18, 22, 10, 8, 42]))
    return "\n".join(lines)


def render_yaml_only():
    """Return the page of the YAML maps that describe no PyRogue class and no RTL decode in the repository."""
    return "\n".join(
        [
            title("YAML-only register maps", "="),
            "These CPSW maps describe no PyRogue class and no RTL decode in this repository, so they are listed "
            "as the YAML states them: the byte address of the word, the bits inside it, the mode, and the "
            "description. An array is one row with its element step.",
            "",
            *[yaml_only_section(name) for name in YAML_ONLY_MAPS],
        ]
    )


def render_registers(repo_root=REPO_ROOT):
    """Return {docs-relative path: text} for the register index, the block pages, and the YAML-only page."""
    resets = load_sidecar(SIDECAR_RESETS, repo_root)
    pages = {"reference/registers/index.rst": render_register_index()}
    for name in REGISTER_BLOCKS:
        pages[f"reference/registers/{name}.rst"] = render_register_page(BLOCKS[name], resets)
    pages[YAML_ONLY_PAGE] = render_yaml_only()
    return pages


# ---------------------------------------------------------------------------
# PyRogue API
# ---------------------------------------------------------------------------

API_DIR = "reference/pyrogue"
ROGUE_VERSION = "6.16.0"
LCLS_PACKAGE = PYTHON_DIR / "LclsTimingCore"
ISSUE_IN_TEXT_RE = re.compile(r"https://github\.com/slaclab/lcls-timing-core/issues/(\d+)")
KNOWN_ISSUE_PREFIX = "known issue: "
REPRODUCE_MARKER = "RUN_KNOWN_ISSUE_TESTS=1"
PR_DEVICE_ARGUMENTS = ("name", "description", "**kwargs")


class ApiVar(NamedTuple):
    """One declaration of a class page: a variable, a command, or a run of array elements."""

    name: str
    kind: str
    offset: object
    bit: object
    size: object
    mode: str
    cell: str
    condition: str
    count: int
    indexed: bool
    stride_bits: int
    description: str


class KnownIssue(NamedTuple):
    test: str
    what: str
    issue: str


def api_label(class_name):
    """Return the label of the API page of a class."""
    return f"api-{slug(class_name)}"


def all_device_classes():
    """Return the sorted names of the pr.Device subclasses in python/LclsTimingCore, read with ast."""
    found = []
    for path in sorted(LCLS_PACKAGE.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            is_device = isinstance(node, ast.ClassDef) and any(
                isinstance(base, ast.Attribute) and base.attr == "Device" for base in node.bases
            )
            if is_device:
                found.append(node.name)
    return sorted(found)


def device_classes():
    """Return the class names that get an API page, sorted."""
    return all_device_classes()


def rejected_classes():
    """Return the classes Rogue rejects at root.start(); their variables are read from the source."""
    return sorted(name for name, block in BLOCKS.items() if block.python_source == "ast")


def class_path(class_name):
    return LCLS_PACKAGE / f"{class_name}.py"


def class_known_issues(class_name, rogue_dir=None):
    """Return [KnownIssue] for the gated tests of tests/rogue/test_<class>.py, read with ast.

    A gated test is a function decorated with ``skipif`` whose ``reason`` names
    ``RUN_KNOWN_ISSUE_TESTS=1``. The reason has the form ``known issue: <what>;
    see <issue URL>; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce``; a reason with
    no issue URL (the interim ``pending issue:`` form) reports the issue as
    ``pending``.
    """
    directory = Path(rogue_dir) if rogue_dir is not None else REPO_ROOT / "tests" / "rogue"
    path = directory / f"test_{class_name}.py"
    if not path.is_file():
        return []
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not (isinstance(decorator, ast.Call) and pyrogue_ast._call_name(decorator) == "skipif"):
                continue
            for keyword in decorator.keywords:
                reason = pyrogue_ast._literal(keyword.value) if keyword.arg == "reason" else None
                if isinstance(reason, str) and REPRODUCE_MARKER in reason:
                    what = reason.split("; see ", 1)[0].split("; set ", 1)[0]
                    for prefix in (KNOWN_ISSUE_PREFIX, "pending issue: "):
                        what = what.removeprefix(prefix)
                    match = ISSUE_IN_TEXT_RE.search(reason)
                    link = match.group(0) if match else PENDING_ISSUE
                    found.append(KnownIssue(node.name, what, link))
    return sorted(found, key=lambda issue: issue.test)


def _count_value(number, arg_set, table):
    if number is None or isinstance(number, int):
        return number
    if number in arg_set.args:
        return arg_set.args[number]
    return table.DEFAULTS[number]


def enum_cell(base, enum, depends=()):
    """Return the Base or enum cell: the enum entries, else the base type, else what a link variable follows."""
    if enum:
        return "enum " + ", ".join(f"{key}: {value}" for key, value in enum.items())
    if base is None:
        return "depends on " + ", ".join(depends) if depends else ""
    return str(base)


def table_variables(class_name, arg_set):
    """Return the ApiVar list of a built-tree class under one argument set, from its reviewed table."""
    table = register_tables.load_table(class_name)
    descriptions = pyrogue_ast.read_descriptions(class_path(class_name))
    flags = set(arg_set.flags)
    found = []
    for row in table.ROWS:
        if row.when is not None and row.when not in flags:
            continue
        count = _count_value(row.number, arg_set, table)
        if count == 0:
            continue
        if row.offset is None:
            offset = bit = None
        else:
            position = register_tables.abs_bit(row.offset, row.bit_offset)
            offset, bit = (position // WORD_BITS) * 4, position % WORD_BITS
        enum = row.enum if row.enum is not None else (dict(register_tables.BOOL_ENUM) if row.base == "Bool" else None)
        cell = enum_cell(row.base, None if row.base == "Bool" else enum, row.depends)
        found.append(
            ApiVar(
                row.name, row.kind, offset, bit, row.bit_size, row.mode, cell, row.when or "",
                1 if count is None else count, count is not None,
                (row.stride or 0) * BITS_PER_BYTE, descriptions.get(row.name) or NO_DESCRIPTION,
            )
        )
    return found


def ast_variables(class_name):
    """Return the ApiVar list of a class Rogue rejects, from its own source file read with ast.

    The reader expands every array declaration into elements; elements of one
    declaration are joined back into one ApiVar with the step between the
    first two.
    """
    path = class_path(class_name)
    groups = {}
    for var in pyrogue_ast.read_remote_variables(path):
        for label, value in (("offset", var.offset), ("bit offset", var.bit_offset), ("bit size", var.bit_size)):
            if not isinstance(value, int):
                raise ValueError(f"{path}:{var.line}: {var.name} {label} is not a literal ({value!r})")
        base, index = split_index(var.name)
        groups.setdefault((var.line, base), []).append((index, var))
    found = []
    for (_, base), elements in groups.items():
        _, first = elements[0]
        position = register_tables.abs_bit(first.offset, first.bit_offset)
        step = 0
        if len(elements) > 1:
            second = elements[1][1]
            step = register_tables.abs_bit(second.offset, second.bit_offset) - position
        enum = first.enum if first.enum is not None else (dict(register_tables.BOOL_ENUM) if first.base == "Bool" else None)
        description = first.description if isinstance(first.description, str) and first.description else NO_DESCRIPTION
        found.append(
            ApiVar(
                base, "RemoteVariable", (position // WORD_BITS) * 4, position % WORD_BITS, first.bit_size,
                first.mode, enum_cell(first.base, None if first.base == "Bool" else enum), first.condition or "",
                len(elements), elements[0][0] is not None, step, description,
            )
        )
    return found


def api_bits(var):
    if var.size is None or var.bit is None:
        return ""
    return f"[{var.bit}]" if var.size == 1 else f"[{var.bit + var.size - 1}:{var.bit}]"


def api_offset(var):
    if var.offset is None:
        return ""
    text = literal(f"0x{var.offset:03X}")
    if var.count > 1:
        text += f" + {literal(stride_text(var.stride_bits))} * i"
    return text


API_VARIABLE_HEADER = ["Name", "Kind", "Offset", "Bits", "Mode", "Base or enum", "Condition", "Description"]
API_VARIABLE_WIDTHS = [17, 11, 12, 7, 6, 14, 10, 23]


def variables_table(variables):
    """Return the list-table of ApiVar rows sorted by offset, bit offset, then name, or ``none``."""
    ordered = sorted(
        variables, key=lambda var: (var.offset is None, var.offset or 0, var.bit or 0, var.name)
    )
    body = []
    for var in ordered:
        shown = f"{var.name}[0..{var.count - 1}]" if var.count > 1 else (f"{var.name}[0]" if var.indexed else var.name)
        body.append(
            [
                literal(shown), var.kind, api_offset(var), api_bits(var), var.mode, var.cell,
                literal(var.condition), var.description,
            ]
        )
    if not body:
        return "none\n"
    return list_table(API_VARIABLE_HEADER, body, widths=API_VARIABLE_WIDTHS)


def constructor_section(arguments):
    """Return the Constructor section body for the [(name, default)] list of ``__init__``."""
    if not arguments:
        return "none\n"
    body = [[literal(name), literal(default) if default is not None else ""] for name, default in arguments]
    specific = [name for name, _ in arguments if name not in PR_DEVICE_ARGUMENTS]
    lines = [list_table(["Argument", "Default"], body, widths=[25, 75])]
    if not specific:
        lines += ["Arguments beyond the ``pr.Device`` defaults: none.", ""]
    return "\n".join(lines)


def checks_section(checks):
    """Return the Constructor checks body for [(condition, message)], or ``none``."""
    if not checks:
        return "none\n"
    body = [[literal(condition), literal(message)] for condition, message in checks]
    return "\n".join(
        ["The constructor raises ``ValueError`` when:", "", list_table(["Condition", "Message"], body, widths=[40, 60])]
    )


def api_children(class_name):
    """Return [(name, class, offset, count text, stride)] of the child devices of a class."""
    if class_name in rejected_classes():
        return [(child.name, child.cls, child.offset, "1", "") for child in pyrogue_ast.read_child_devices(class_path(class_name))]
    table = register_tables.load_table(class_name)
    rows = []
    for child in getattr(table, "CHILDREN", ()):
        count = "1" if child.number is None else str(child.number)
        rows.append((child.name.split("[")[0], child.table, child.offset, count, child.stride or ""))
    return rows


def children_section(children):
    if not children:
        return "none\n"
    body = []
    for name, cls, offset, count, stride in children:
        target = f":ref:`{cls} <{api_label(cls)}>`" if cls in all_device_classes() else literal(cls)
        body.append([literal(name), target, literal(f"0x{offset:X}"), count, literal(f"0x{stride:X}") if stride != "" else ""])
    return list_table(["Name", "Class", "Offset", "Count", "Stride"], body, widths=[25, 30, 15, 15, 15])


def register_links(class_name):
    """Return the RST that points a class at its register page, or at its children's pages."""
    if class_name in REGISTER_BLOCKS:
        return f":ref:`{class_name} registers <{page_label(class_name)}>`"
    targets = [cls for _, cls, _, _, _ in api_children(class_name) if cls in REGISTER_BLOCKS]
    if not targets:
        raise ValueError(f"{class_name} has no register page and no child with one")
    return ", ".join(f":ref:`{cls} registers <{page_label(cls)}>`" for cls in dict.fromkeys(targets))


def known_issues_section(class_name):
    issues = class_known_issues(class_name)
    if not issues:
        return "none\n"
    body = [
        [literal(issue.test), issue.what, issue_cell([issue.issue])] for issue in issues
    ]
    return "\n".join(
        [
            f"Each test is skipped unless {literal(REPRODUCE_MARKER)} is set, and fails while the issue stands.",
            "",
            list_table(["Test", "What", "Issue"], body, widths=[35, 45, 20]),
        ]
    )


def variable_sections(class_name):
    """Return the Variables section body: one table per argument set of a built-tree class, one for a source-read class."""
    if class_name in rejected_classes():
        return variables_table(ast_variables(class_name))
    table = register_tables.load_table(class_name)
    tables = [(arg_set, variables_table(table_variables(class_name, arg_set))) for arg_set in table.ARG_SETS]
    if all(text == "none\n" for _, text in tables):
        return "none\n"
    parts = []
    seen = {}
    for arg_set, text in tables:
        arguments = ", ".join(literal(f"{key}={value!r}") for key, value in arg_set.args.items()) or "none"
        parts += [title(f"Arguments {arg_set.id}", "~"), f"Constructor arguments: {arguments}.", ""]
        if text in seen:
            parts += [f"Same variables as arguments {seen[text]}.", ""]
        else:
            seen[text] = arg_set.id
            parts.append(text)
    return "\n".join(parts)


def render_api_page(class_name):
    """Return the page of one device class."""
    path = class_path(class_name)
    rejected = class_name in rejected_classes()
    parts = [
        f".. _{api_label(class_name)}:\n",
        title(class_name, "="),
        f"Source: {repo_link(f'python/LclsTimingCore/{class_name}.py')}. Register table: {register_links(class_name)}.",
        "",
    ]
    if rejected:
        parts += [
            f"Rogue {ROGUE_VERSION} rejects this class at ``root.start()``, so its tree cannot be built. The "
            "variables below are read from the source with ``ast``; the known issues name the declarations "
            "that Rogue refuses.",
            "",
        ]
    parts += [title("Constructor", "-"), constructor_section(pyrogue_ast.read_constructor(path, class_name))]
    parts += [title("Constructor checks", "-"), checks_section(pyrogue_ast.read_constructor_checks(path, class_name))]
    parts += [title("Sub-devices", "-"), children_section(api_children(class_name))]
    parts += [title("Variables", "-"), variable_sections(class_name)]
    parts += [title("Known issues", "-"), known_issues_section(class_name)]
    return "\n".join(parts)


def render_api_index(names):
    rows = []
    rejected = rejected_classes()
    for name in names:
        builds = "no: rejected at ``root.start()``" if name in rejected else "yes"
        rows.append([f":ref:`{name} <{api_label(name)}>`", builds, register_links(name)])
    return "\n".join(
        [
            title("PyRogue API", "="),
            "``import LclsTimingCore`` makes every device class below available: the package ``__init__`` star "
            "imports each module, so ``LclsTimingCore.TPGControl`` and the other classes are one import away. "
            "Each page lists the constructor arguments with their defaults, the checks the constructor makes, "
            "the child devices, and the variables with offset, bits, mode, and description. The variables of a "
            f"class that Rogue {ROGUE_VERSION} builds come from the reviewed table checked against a built tree; "
            f"the {len(rejected_classes())} classes Rogue rejects are read from the source. No page imports Rogue.",
            "",
            list_table(["Class", f"Builds under Rogue {ROGUE_VERSION}", "Register page"], rows, widths=[30, 30, 40]),
            ".. toctree::",
            "   :hidden:",
            "   :maxdepth: 1",
            "",
            *[f"   {name}" for name in names],
            "",
        ]
    )


def render_pyrogue(repo_root=REPO_ROOT):
    """Return {docs-relative path: text} for the PyRogue API index and the page of every device class."""
    names = device_classes()
    pages = {f"{API_DIR}/index.rst": render_api_index(names)}
    for name in names:
        pages[f"{API_DIR}/{name}.rst"] = render_api_page(name)
    return pages


# ---------------------------------------------------------------------------
# Generation and freshness
# ---------------------------------------------------------------------------

def render_all(repo_root=REPO_ROOT):
    """Return {docs-relative path: text} of every generated page, sorted by path."""
    pages = render_entities(repo_root)
    pages.update(render_registers(repo_root))
    pages.update(render_pyrogue(repo_root))
    pages["reference/families.rst"] = render_families(repo_root)
    pages["reference/index.rst"] = render_reference_index(pages)
    for path, text in pages.items():
        try:
            text.encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError(f"generated page {path} is not ASCII: {error}") from error
        if str(repo_root) in text:
            raise ValueError(f"generated page {path} contains the repository path")
    return dict(sorted(pages.items()))


def check_files(expected, docs_dir):
    """Return sorted (path, problem) pairs for differing, missing, and stray generated files."""
    docs_dir = Path(docs_dir)
    problems = []
    for path, text in expected.items():
        target = docs_dir / path
        if not target.is_file():
            problems.append((f"docs/{path}", "missing"))
        elif target.read_text(encoding="utf-8") != text:
            problems.append((f"docs/{path}", "differs from a fresh generation"))
    for root in GENERATED_ROOTS:
        for target in sorted((docs_dir / root).rglob("*")) if (docs_dir / root).is_dir() else []:
            relative = target.relative_to(docs_dir).as_posix()
            if target.is_file() and relative not in expected:
                problems.append((f"docs/{relative}", "stray file in a generated directory"))
    return sorted(problems)


def check_all(repo_root=REPO_ROOT):
    """Return the problems of the committed generated pages against a fresh generation."""
    return check_files(render_all(repo_root), Path(repo_root) / "docs")


def write_all(repo_root=REPO_ROOT):
    """Write every generated page and remove stray files under the generated directories."""
    docs_dir = Path(repo_root) / "docs"
    pages = render_all(repo_root)
    for path, text in pages.items():
        target = docs_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    for path, problem in check_files(pages, docs_dir):
        if problem.startswith("stray"):
            (Path(repo_root) / path).unlink()
    return sorted(pages)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare the committed pages with a fresh generation")
    args = parser.parse_args(argv)
    if args.check:
        problems = check_all()
        for path, problem in problems:
            print(f"{path}: {problem}")
        return 1 if problems else 0
    write_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
