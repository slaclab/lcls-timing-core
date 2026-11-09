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
from tests.common.yaml_maps import KNOWN_YAML_DEFECTS, yaml_fields
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

# The blocks that have a register page, in page order.
REGISTER_BLOCKS = ("EvrV2TriggerReg",)

# The reviewed table arguments of each (block, variant id) whose Python source
# is a built tree. The flags are the table `when` conditions that match the
# variant's Python arguments.
VARIANT_ARG_SETS = {
    ("EvrV2TriggerReg", "default"): ArgSet("default", {}),
    ("EvrV2TriggerReg", "useTap"): ArgSet("useTap", {"useTap": True}, ("useTap",)),
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
    if block.python_source != "tree":
        raise ValueError(f"{block.name}: no Python view for source {block.python_source!r}")
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


def _where(field):
    """Return where a source puts a field: the word address, the bits, and the mode."""
    return f"at 0x{field.word_byte:03X} {bits_cell(field)} {field.mode}"


def _differs(block, name, kinds, field):
    kinds_text = ", ".join(f"{kind}{_issue_text(block, name, kind)}" for kind in kinds)
    return f"differs: {kinds_text}\n{_where(field)}"


def _absent(block, name, source):
    return "absent" + _issue_text(block, name, f"missing-in-{source}")


def rtl_agreement(block, entry, source, state):
    """Return the agreement cell of ``source`` (python or yaml) against the RTL field of the entry."""
    if state != "compared":
        return state
    field = entry.fields.get(source)
    rtl = entry.fields.get("vhdl")
    if field is None:
        return _absent(block, entry.name, source)
    if rtl is None:
        return _differs(block, entry.name, ["missing-in-vhdl"], field)
    kinds = pair_kinds(rtl, field)
    return _differs(block, entry.name, kinds, field) if kinds else "agrees"


def python_agreement(block, entry, state):
    """Return the YAML cell of an entry that has no RTL, judged against the Python field."""
    if state != "compared":
        return state
    python = entry.fields.get("python")
    yaml_field = entry.fields.get("yaml")
    if yaml_field is None:
        return _absent(block, entry.name, "yaml")
    if python is None:
        return _differs(block, entry.name, ["missing-in-python"], yaml_field)
    kinds = pair_kinds(python, yaml_field)
    return _differs(block, entry.name, kinds, yaml_field) if kinds else "agrees"


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
    stride: int
    cells: tuple


def collapse(entries, signature, primary_order):
    """Join consecutive array elements with equal cells and a constant bit stride into one RegRow each."""
    rows = []
    by_name = {}
    for entry in entries:
        by_name.setdefault(entry.name, []).append(entry)
    for name, group in by_name.items():
        group.sort(key=lambda entry: entry.element)
        run = [group[0]]
        stride = None
        for entry in group[1:]:
            last = run[-1]
            step = _primary(entry, primary_order).abs_bit - _primary(last, primary_order).abs_bit
            joins = (
                entry.indexed
                and last.indexed
                and entry.element == last.element + 1
                and signature(entry) == signature(last)
                and (stride is None or step == stride)
            )
            if joins:
                stride = step
                run.append(entry)
            else:
                rows.append(RegRow(name, run[0], len(run), stride or 0, signature(run[0])))
                run, stride = [entry], None
        rows.append(RegRow(name, run[0], len(run), stride or 0, signature(run[0])))
    return rows


def _row_key(row, primary_order):
    field = _primary(row.first, primary_order)
    return (field.word_byte, field.bit_in_word, row.name, row.first.element)


def offset_cell(row, primary_order):
    field = _primary(row.first, primary_order)
    text = literal(f"0x{field.word_byte:03X}")
    if row.count == 1:
        return text
    step = f"0x{row.stride // BITS_PER_BYTE:X}" if row.stride % WORD_BITS == 0 else f"{row.stride} bits"
    return f"{text} + {literal(step)} * i"


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


def python_descriptions(block):
    """Return {Python variable name: description} for a block, read from its class file with ast."""
    return pyrogue_ast.read_descriptions(PYTHON_DIR / "LclsTimingCore" / f"{block.name}.py")


def rtl_table(block, entries, state, words, descriptions):
    order = ("vhdl", "python", "yaml")

    def signature(entry):
        field = _primary(entry, order)
        return (
            field.bit_size, field.mode, rtl_agreement(block.name, entry, "python", "compared"),
            rtl_agreement(block.name, entry, "yaml", state), reset_cell(words, field),
            description_for(entry, descriptions),
        )

    rows = sorted(collapse(entries, signature, order), key=lambda row: _row_key(row, order))
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
                rtl_agreement(block.name, row.first, "python", "compared"),
                rtl_agreement(block.name, row.first, "yaml", state),
                description_for(row.first, descriptions),
            ]
        )
    return list_table(RTL_HEADER, body, widths=RTL_WIDTHS)


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


def render_variant(block, variant, words, descriptions):
    sources = block_sources(block, variant)
    state = yaml_state(block, variant, sources)
    inside, _ = split_entries(block, sources)
    generics = ", ".join(f"{literal(key)} = {literal(str(value))}" for key, value in variant.generics.items()) or "none"
    arguments = ", ".join(literal(f"{key}={value!r}") for key, value in variant.python_args.items()) or "none"
    lines = [
        title(f"Variant {variant.id}", "-"),
        f"RTL generics: {generics}. Python arguments: {arguments}.",
        "",
    ]
    if inside:
        lines.append(rtl_table(block, inside, state, words, descriptions))
    lines.append(strobe_note(sources, inside))
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


def render_register_page(block, resets=None):
    """Return the page of one register block: a table per variant, then the known differences."""
    if resets is None:
        resets = load_sidecar(SIDECAR_RESETS)
    descriptions = python_descriptions(block)
    parts = [title(f"{block.name} registers", "=")]
    links = []
    if block.vhdl is not None:
        links.append(f"Decode file: {repo_link(block.vhdl)}.")
    links.append(f"Python class: {repo_link(f'python/LclsTimingCore/{block.name}.py')}.")
    if block.yaml is not None:
        links.append(f"YAML map: {repo_link(f'yaml/{block.yaml}')}.")
    parts += [" ".join(links), ""]
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
        ["``absent``", "the source has no field for this register"],
        ["``not compared``", "the variant does not compare this source (the YAML map describes one variant)"],
        ["``map does not parse``", "the YAML map cannot be read, so none of its fields are compared"],
    ]
    return "\n".join(
        [
            title("Register maps", "="),
            "One page per register block. Each table is read from the RTL address decode, one table per "
            "generic or argument variant. Offset is the byte address of the 32-bit word and Bits the "
            "position inside it. Mode is read-write (RW), read-only (RO), or write-only (WO) as the RTL decodes "
            "it. Reset is the slice of the word that a simulation asserts after reset, or ``not asserted`` "
            "when no test checks it. The Python and YAML columns compare the PyRogue declaration and the "
            "CPSW map with the RTL field. Description is the ``description`` text of the Python variable.",
            "",
            list_table(["Agreement", "Meaning"], rows, widths=[30, 70]),
            ".. toctree::",
            "   :maxdepth: 1",
            "",
            *[f"   {name}" for name in REGISTER_BLOCKS],
            "",
        ]
    )


def render_registers(repo_root=REPO_ROOT):
    """Return {docs-relative path: text} for the register index and the block pages."""
    resets = load_sidecar(SIDECAR_RESETS, repo_root)
    pages = {"reference/registers/index.rst": render_register_index()}
    for name in REGISTER_BLOCKS:
        pages[f"reference/registers/{name}.rst"] = render_register_page(BLOCKS[name], resets)
    return pages


# ---------------------------------------------------------------------------
# Generation and freshness
# ---------------------------------------------------------------------------

def render_all(repo_root=REPO_ROOT):
    """Return {docs-relative path: text} of every generated page, sorted by path."""
    pages = render_entities(repo_root)
    pages.update(render_registers(repo_root))
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
