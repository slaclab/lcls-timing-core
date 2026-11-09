#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Generated reference pages: freshness, the VHDL entity reader, and the authored sidecars.

Test methodology:
    Sweep: every generated page under docs/reference, every documented file
        of every documentation tree (statuses for all 32 core entities), and
        every entry of the sidecars under docs/_data. Small synthetic VHDL strings cover the entity reader and
        the page renderers.
    Stimulus: render_all on the real tree (text parsing only, no simulator),
        a temporary docs directory for the freshness check, and synthetic
        design units for the renderers.
    Checks: the empty and missing header sets equal the header sidecar in
        both directions and each contradicts entry pins the current header
        text, sidecar kinds are known and links are issue URLs or pending,
        the verification status of every core entity follows the CI
        baselines (baseline-excluded, not simulated, and not loaded sets are
        exact), the issues cell orders links by number with pending last,
        an entity without generics or ports renders none, a missing purpose
        or status raises naming the file, the committed pages equal a fresh generation, generation is
        deterministic and carries no host path, list tables reject a row with
        the wrong cell count, the reader returns the generics and ports of
        Divider.vhd in declaration order and rejects a file with no unit,
        the purposes sidecar has exactly the rendered files as keys and no
        purpose repeats a banner header, every purpose is one to three plain
        sentences, every rendered entity has one known status, and the two
        files that declare BsaControl render as distinct rows.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import re
from pathlib import Path

import pytest

from tests.common import gen_docs
from tests.common.gen_docs import (
    DOC_TREES,
    STATUSES,
    DesignUnit,
    Generic,
    Port,
    check_files,
    entity_issues,
    entity_section,
    header_description,
    header_findings,
    issue_cell,
    list_table,
    load_sidecar,
    read_vhdl_unit,
    render_all,
    rendered_files,
    statuses,
)
from tests.common.ghdl_analysis import KNOWN_GHDL_UNANALYZABLE, NOT_SIMULATED
from tests.common.register_drift import ISSUE_URL_RE
from tests.common.regression_utils import REPO_ROOT
from tests.common.source_inventory import UNLOADED_SOURCES

DIVIDER = "LCLS-II/core/rtl/Divider.vhd"


def test_committed_reference_matches_a_fresh_generation():
    problems = gen_docs.check_all(REPO_ROOT)
    assert not problems, (
        "the committed reference pages are stale; run `python -m tests.common.gen_docs` and commit the result:\n"
        + "\n".join(f"{path}: {problem}" for path, problem in problems)
    )


def test_check_reports_stale_missing_and_stray_files(tmp_path):
    expected = {"reference/index.rst": "one\n", "reference/entities/core.rst": "two\n"}
    docs = tmp_path / "docs"
    (docs / "reference" / "entities").mkdir(parents=True)
    (docs / "reference" / "index.rst").write_text("one\n", encoding="utf-8")
    (docs / "reference" / "stray.rst").write_text("x\n", encoding="utf-8")
    (docs / "_generated").mkdir()
    (docs / "_generated" / "other.rst").write_text("x\n", encoding="utf-8")
    (docs / "index.rst").write_text("hand written\n", encoding="utf-8")
    assert check_files(expected, docs) == [
        ("docs/_generated/other.rst", "stray file in a generated directory"),
        ("docs/reference/entities/core.rst", "missing"),
        ("docs/reference/stray.rst", "stray file in a generated directory"),
    ]
    (docs / "reference" / "index.rst").write_text("changed\n", encoding="utf-8")
    assert ("docs/reference/index.rst", "differs from a fresh generation") in check_files(expected, docs)


def test_generation_is_deterministic():
    first = render_all(REPO_ROOT)
    second = render_all(REPO_ROOT)
    assert first == second
    assert list(first) == sorted(first)


def test_generated_text_has_no_host_paths():
    for path, text in render_all(REPO_ROOT).items():
        for forbidden in (str(REPO_ROOT), "/home/", "/sdf/", "/tmp/"):
            assert forbidden not in text, f"{path} contains {forbidden!r}"


def test_list_table_rejects_a_wrong_cell_count():
    with pytest.raises(ValueError, match=r"row 2 has 1 cells, expected 2.*'only'"):
        list_table(["a", "b"], [["1", "2"], ["only"]])
    table = list_table(["a", "b"], [["1", ""], ["line one\nline two", "3"]], widths=[1, 2])
    assert "   :widths: 1 2\n" in table
    assert "     - none\n" in table
    assert "   * - line one\n       line two\n" in table


def test_reader_parses_the_divider_declaration():
    unit = read_vhdl_unit(REPO_ROOT / DIVIDER)
    assert unit.kind == "entity"
    assert unit.name == "Divider"
    assert [tuple(generic) for generic in unit.generics] == [("TPD_G", "time", "1 ns"), ("Width", "integer", "4")]
    assert tuple(unit.ports[0]) == ("sysClk", "in", "std_logic")
    assert tuple(unit.ports[-1]) == ("trigO", "out", "std_logic")
    assert [port.name for port in unit.ports] == ["sysClk", "sysReset", "enable", "clear", "divisor", "trigO"]
    assert unit.ports[4].type_text == "std_logic_vector(Width - 1 downto 0)"


def test_reader_handles_name_lists_modes_and_defaults(tmp_path):
    source = tmp_path / "Probe.vhd"
    source.write_text(
        "-- entity Fake is\n"
        "entity Probe is\n"
        "   generic (\n"
        "      A_G, B_G : natural := 2 ** 3;\n"
        "      INIT_G   : slv(7 downto 0) := x\"0F\" );\n"
        "   port (\n"
        "      a, b : in    std_logic;\n"
        "      c    : inout std_logic_vector(A_G - 1 downto 0) := (others => '0');\n"
        "      d    : out   surf.AxiStreamPkg.AxiStreamMasterType );\n"
        "end entity Probe;\n",
        encoding="utf-8",
    )
    unit = read_vhdl_unit(source)
    assert unit.name == "Probe"
    assert [tuple(g) for g in unit.generics] == [
        ("A_G", "natural", "2 ** 3"),
        ("B_G", "natural", "2 ** 3"),
        ("INIT_G", "slv(7 downto 0)", 'x"0F"'),
    ]
    assert [tuple(p) for p in unit.ports] == [
        ("a", "in", "std_logic"),
        ("b", "in", "std_logic"),
        ("c", "inout", "std_logic_vector(A_G - 1 downto 0)"),
        ("d", "out", "surf.AxiStreamPkg.AxiStreamMasterType"),
    ]


def test_reader_returns_a_package_and_skips_package_bodies(tmp_path):
    source = tmp_path / "ProbePkg.vhd"
    source.write_text("package ProbePkg is\n  constant X_C : integer := 1;\nend package ProbePkg;\n"
                      "package body ProbePkg is\nend package body ProbePkg;\n", encoding="utf-8")
    unit = read_vhdl_unit(source)
    assert (unit.kind, unit.name, unit.generics, unit.ports) == ("package", "ProbePkg", (), ())


def test_reader_rejects_a_file_without_a_unit(tmp_path):
    source = tmp_path / "Empty.vhd"
    source.write_text("-- entity Commented is\nlibrary ieee;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty.vhd"):
        read_vhdl_unit(source)


def test_header_description_follows_the_banner_rule(tmp_path):
    with_text = tmp_path / "A.vhd"
    with_text.write_text(
        "-------------------------\n-- Description: first line\n--   second line\n"
        "-------------------------\nlibrary ieee;\n",
        encoding="utf-8",
    )
    assert header_description(with_text) == (True, "first line second line", 2, 3)
    empty = tmp_path / "B.vhd"
    empty.write_text("-- Description:\n-------------------------\nlibrary ieee;\n", encoding="utf-8")
    assert header_description(empty).found is True
    assert header_description(empty).text == ""
    absent = tmp_path / "C.vhd"
    absent.write_text("-- no field here\nlibrary ieee;\n", encoding="utf-8")
    assert header_description(absent).found is False


def _purposes():
    return load_sidecar("entity_purposes.yaml")


def test_purposes_cover_exactly_the_rendered_files():
    rendered = {path for tree in DOC_TREES for path in rendered_files(REPO_ROOT, tree)}
    purposes = set(_purposes())
    extra = sorted(purposes - rendered)
    missing = sorted(rendered - purposes)
    assert not extra, f"purposes for files that are not rendered: {extra}"
    assert not missing, f"rendered files without a purpose: {missing}"


def _normalized(text):
    return " ".join(text.split()).casefold()


def test_purpose_is_not_the_banner_text():
    for path, purpose in _purposes().items():
        header = header_description(REPO_ROOT / path)
        if header.found and header.text:
            assert _normalized(purpose) != _normalized(header.text), f"{path}: purpose repeats the banner header"


def test_purpose_style():
    for path, purpose in _purposes().items():
        text = " ".join(purpose.split())
        assert text.isascii(), f"{path}: purpose is not ASCII"
        assert text.endswith("."), f"{path}: purpose must end with a period"
        assert len(text) <= 600, f"{path}: purpose is {len(text)} characters, the limit is 600"
        sentences = re.findall(r"[.!?](?:\s|$)", text)
        assert 1 <= len(sentences) <= 3, f"{path}: purpose has {len(sentences)} sentences, expected 1 to 3"
        assert not re.search(r"[`*|]|\w_(?!\w)", text), f"{path}: purpose carries RST markup"


def test_every_rendered_entity_has_one_status():
    for tree in DOC_TREES:
        units = gen_docs._tree_units(REPO_ROOT, tree)
        rendered = rendered_files(REPO_ROOT, tree)
        found = gen_docs._entity_statuses(REPO_ROOT, units, set(rendered))
        for path in rendered:
            assert found.get(path) in STATUSES, f"{path}: status {found.get(path)!r} is not one of {STATUSES}"
    assert found[DIVIDER] == "simulated"


def test_unknown_documentation_tree_is_rejected():
    with pytest.raises(ValueError, match="nothing"):
        statuses(REPO_ROOT, "nothing")


def _core_entity_names():
    return {
        path: read_vhdl_unit(REPO_ROOT / path).name.lower()
        for path in gen_docs.documented_files(REPO_ROOT, DOC_TREES[0])
        if read_vhdl_unit(REPO_ROOT / path).kind == "entity"
    }


def test_statuses_match_the_baselines():
    found = statuses(REPO_ROOT, "core")
    names = _core_entity_names()
    assert set(found) == set(names)
    assert len(found) == 32
    assert all(status in STATUSES for status in found.values())

    def by_status(status):
        return {path for path, value in found.items() if value == status}

    excluded = by_status("baseline-excluded")
    assert {names[path] for path in excluded} == set(KNOWN_GHDL_UNANALYZABLE) & set(names.values())
    assert {Path(path).name for path in excluded} == {
        "TPGMiniReg.vhd", "TPGMiniCore.vhd", "TimingCore.vhd", "TimingGthWrapper.vhd",
    }
    assert {names[path] for path in by_status("not simulated")} == set(NOT_SIMULATED) & set(names.values())
    not_loaded = by_status("not simulated: not loaded by any ruckus.tcl")
    expected_unloaded = {
        path
        for path in UNLOADED_SOURCES
        if path in found and found[path] not in ("simulated", "baseline-excluded")
    }
    assert not_loaded == expected_unloaded
    assert {Path(path).name for path in not_loaded} == {
        "BsaControl.vhd", "ClockTime_186MHz.vhd", "TPFifo.vhd", "TPGNotify.vhd",
    }
    for path in ("LCLS-II/core/rtl/TPGMiniEdefTb.vhd", "LCLS-II/core/tb/TimingSerialDelay_tb.vhd"):
        assert found[path] == "simulated", path
    assert found["LCLS-II/core/rtl/BsaControlv2.vhd"] == "simulated"
    assert not any(value == "Vivado-only" for value in found.values())


def test_entity_issues_link_the_baseline_and_the_unloaded_files():
    units = {path: read_vhdl_unit(REPO_ROOT / path) for path in UNLOADED_SOURCES if path.endswith(".vhd")}
    found = statuses(REPO_ROOT, "core")
    wrapper = "LCLS-II/core/rtl/TimingGthWrapper.vhd"
    assert entity_issues(wrapper, units[wrapper], found[wrapper]) == ["pending", "pending"]
    notify = "LCLS-II/core/rtl/TPGNotify.vhd"
    assert entity_issues(notify, units[notify], found[notify]) == ["pending"]
    divider_unit = read_vhdl_unit(REPO_ROOT / DIVIDER)
    assert entity_issues(DIVIDER, divider_unit, "simulated") == []


def test_issue_cell_orders_and_renders_pending():
    low = "https://github.com/slaclab/lcls-timing-core/issues/12"
    high = "https://github.com/slaclab/lcls-timing-core/issues/207"
    cell = issue_cell([high, "pending", low])
    assert cell == ":issue:`12`, :issue:`207`, issue pending"
    assert "pending`" not in cell
    assert issue_cell([]) == "none"
    assert issue_cell(["pending"]) == "issue pending"
    with pytest.raises(ValueError, match="not-a-link"):
        issue_cell(["not-a-link"])


def _unit(generics=(), ports=()):
    return DesignUnit("entity", "Probe", tuple(generics), tuple(ports), 1)


def test_entity_without_generics_or_ports_renders_none():
    section = entity_section("LCLS-II/core/rtl/Probe.vhd", _unit(), "Does nothing.", "simulated", "simulated", "none", False)
    assert ".. rubric:: Generics\n\nnone\n" in section
    assert ".. rubric:: Ports\n\nnone\n" in section
    assert "list-table" not in section
    full = entity_section(
        "LCLS-II/core/rtl/Probe.vhd",
        _unit([Generic("TPD_G", "time", "1 ns"), Generic("OPEN_G", "natural", "")], [Port("clk", "in", "sl")]),
        "Does nothing.",
        "simulated",
        "simulated",
        "none",
        True,
    )
    assert "Probe (LCLS-II/core/rtl/Probe.vhd)\n" in full
    assert "   * - ``OPEN_G``\n     - ``natural``\n     - none\n" in full


def test_missing_purpose_or_status_raises():
    path = "LCLS-II/core/rtl/Probe.vhd"
    with pytest.raises(ValueError, match=path):
        entity_section(path, _unit(), None, "simulated", "simulated", "none", False)
    with pytest.raises(ValueError, match=path):
        entity_section(path, _unit(), "Does nothing.", None, "", "none", False)


def _header_sidecar():
    return load_sidecar("header_issues.yaml")


def test_header_issues_match_the_headers():
    sidecar = _header_sidecar()
    for tree in DOC_TREES:
        files = gen_docs.documented_files(REPO_ROOT, tree)
        computed = header_findings(REPO_ROOT, files)
        for kind in ("empty", "missing"):
            expected = {path for path, entry in sidecar.items() if path in files and entry["kind"] == kind}
            found = {path for path, value in computed.items() if value == kind}
            assert not found - expected, f"{kind} headers with no entry in docs/_data/header_issues.yaml: {sorted(found - expected)}"
            assert not expected - found, (
                f"entries whose header is no longer {kind}; remove them from docs/_data/header_issues.yaml: "
                f"{sorted(expected - found)}"
            )
    for path, entry in sidecar.items():
        if entry["kind"] != "contradicts":
            continue
        current = header_description(REPO_ROOT / path)
        assert current.found and current.text == entry["header"], (
            f"{path}: the header changed; if it was fixed, remove the entry from docs/_data/header_issues.yaml"
        )


def test_header_issue_links_are_urls_or_pending():
    for path, entry in _header_sidecar().items():
        assert entry["issue"] == "pending" or ISSUE_URL_RE.match(entry["issue"]), f"{path}: bad issue link {entry['issue']!r}"
        assert (REPO_ROOT / path).is_file(), f"{path}: no such file"


def test_header_issue_kinds_are_known():
    for path, entry in _header_sidecar().items():
        assert set(entry) <= {"kind", "issue", "header"}, f"{path}: unknown keys {sorted(entry)}"
        assert entry["kind"] in gen_docs.HEADER_KINDS, f"{path}: unknown kind {entry['kind']!r}"
        if entry["kind"] == "contradicts":
            assert entry.get("header"), f"{path}: a contradicts entry needs the pinned header text"
        else:
            assert "header" not in entry, f"{path}: only a contradicts entry carries a header"


def test_header_issue_joins_the_issues_cell():
    unit = read_vhdl_unit(REPO_ROOT / DIVIDER)
    sidecar = {DIVIDER: {"kind": "empty", "issue": "https://github.com/slaclab/lcls-timing-core/issues/300"}}
    assert entity_issues(DIVIDER, unit, "simulated", sidecar) == ["https://github.com/slaclab/lcls-timing-core/issues/300"]
    assert entity_issues(DIVIDER, unit, "simulated", {}) == []


def test_header_findings_report_empty_and_missing(tmp_path):
    (tmp_path / "A.vhd").write_text("-- Description:\n----------\nlibrary ieee;\n", encoding="utf-8")
    (tmp_path / "B.vhd").write_text("library ieee;\n", encoding="utf-8")
    (tmp_path / "C.vhd").write_text("-- Description: text\n----------\nlibrary ieee;\n", encoding="utf-8")
    assert header_findings(tmp_path, ["A.vhd", "B.vhd", "C.vhd"]) == {"A.vhd": "empty", "B.vhd": "missing"}


def test_duplicate_entity_names_get_distinct_rows():
    pages = render_all(REPO_ROOT)
    core = pages["reference/entities/core.rst"]
    loaded = "LCLS-II/core/rtl/BsaControlv2.vhd"
    unloaded = "LCLS-II/core/rtl/BsaControl.vhd"
    titles = re.findall(r"^(BsaControl \(.*\))$", core, re.MULTILINE)
    assert titles == [f"BsaControl ({unloaded})", f"BsaControl ({loaded})"]
    labels = re.findall(r"^\.\. _(entity-[^:]*bsacontrol[^:]*):$", core, re.MULTILINE)
    assert len(labels) == 2 and len(set(labels)) == 2, labels
    rows = {}
    for match in re.finditer(r"^   \* - :ref:`BsaControl <(entity-[^>]+)>`\n     - :repo:`([^`]+)`\n     - (.+)$", core, re.MULTILINE):
        rows[match.group(2)] = (match.group(1), match.group(3))
    assert set(rows) == {loaded, unloaded}
    assert rows[unloaded][1] == "not simulated: not loaded by any ruckus.tcl"
    assert rows[loaded][1] == "simulated"
    assert rows[unloaded][0] != rows[loaded][0]
    assert {label for label, _ in rows.values()} == set(labels)
