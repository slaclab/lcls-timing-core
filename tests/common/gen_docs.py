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

from tests.common.register_drift import ISSUE_URL_RE, PENDING_ISSUE
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
        "A cocotb test runs the entity (or its testbench wrapper) in the GHDL leg of the regression.",
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
    which documented files the tree page renders.
    """

    key: str
    title: str
    roots: tuple
    only: tuple | None = None

    @property
    def ruckus(self):
        return f"{self.roots[0]}/ruckus.tcl"


DOC_TREES = (
    DocTree("core", "LCLS-II core", ("LCLS-II/core",), only=("LCLS-II/core/rtl/Divider.vhd",)),
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
    """Return {path: DesignUnit} for every documented VHDL file of ``tree``."""
    return {
        path: read_vhdl_unit(Path(repo_root) / path)
        for path in documented_files(repo_root, tree)
        if path.endswith(".vhd")
    }


def _entity_statuses(repo_root, units, paths=None):
    """Return {path: status} for the entity files among ``units`` (restricted to ``paths`` when given)."""
    _, source_inventory = _baselines()
    inventory = source_inventory.Inventory(repo_root)
    return {
        path: verification_status(path, unit, inventory, repo_root)
        for path, unit in units.items()
        if unit.kind == "entity" and (paths is None or path in paths)
    }


def statuses(repo_root=REPO_ROOT, tree="core"):
    """Return {path: status} for every documented file of ``tree`` that declares an entity.

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
        "The VHDL entities of the library, with their purpose, generics, ports, and the way the "
        "regression covers it. The pages are generated from the sources by ``python -m tests.common.gen_docs``; "
        "the purposes are authored.",
        "",
        "Each entity has one of five verification statuses:",
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
    names = [unit.name.lower() for unit in units.values() if unit.kind == "entity"]
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
    lines = [
        title(tree.title, "="),
        f"{repo_link(tree.ruckus)} loads these sources into the ``lcls_timing_core`` library; a file it does not "
        "load says so in the Status column.",
        "",
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
    return "\n".join(
        [
            title("Reference", "="),
            "Lookup material for the library, generated from the sources by "
            "``python -m tests.common.gen_docs``: entities with their generics and ports, and the verification "
            "status of each. Do not edit these pages by hand.",
            "",
            ".. toctree::",
            "   :maxdepth: 1",
            "",
            *[f"   {entry}/index" for entry in entries],
            "",
        ]
    )


# ---------------------------------------------------------------------------
# Generation and freshness
# ---------------------------------------------------------------------------

def render_all(repo_root=REPO_ROOT):
    """Return {docs-relative path: text} of every generated page, sorted by path."""
    pages = render_entities(repo_root)
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
