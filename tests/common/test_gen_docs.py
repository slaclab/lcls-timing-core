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
        of every documentation tree (statuses for all 62 entities and modules), and
        every entry of the sidecars under docs/_data. Small synthetic VHDL strings cover the entity reader and
        the page renderers.
    Stimulus: render_all on the real tree (text parsing only, no simulator),
        a temporary docs directory for the freshness check, and synthetic
        design units for the renderers.
    Checks: the empty and missing header sets equal the header sidecar in
        both directions and each contradicts entry pins the current header
        text, sidecar kinds are known and links are issue URLs or pending,
        the verification status of every entity and module follows the CI
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
        files that declare BsaControl render as distinct rows, the four
        Verilog modules read as declared (non-ANSI and ANSI headers,
        parameters, port ranges) and a port without a direction is rejected,
        the four GT wrappers that share an entity name get distinct titles,
        and the family matrix and the version checks equal a hand-written
        table, including two rows for a family that loads two directories,
        the reset sidecar follows its schema (seeded extra key, lower-case
        value, missing key, unknown block, variant, or word are rejected),
        every sidecar entry cites an assert of an existing function that
        holds its basis and the text reset (seeded literal mismatch, missing
        function, basis outside an assert, undefined name are rejected),
        every sidecar word is a decoded word of its variant, every allowlist
        entry of a documented block is on its page with its issue link, the
        drift of the reviewed tables equals the allowlist, the rows show
        every drift the comparison reports, descriptions are copied from
        the Python source or marked missing, adjacent fields keep their own
        flagged rows, and rows are sorted by byte offset, bit offset, name,
        the constructor reader returns the arguments, defaults, and
        ValueError checks of a class, and the API pages are built without
        importing Rogue, every device class has one page with its gated issues,
        and the YAML map page has one section per file with the parse
        failures, the missing include, and the spliced fields of an including
        map, and every message layout include is generated from its model table:
        the printed ranges equal field_layout, the totals equal the declared
        sizes, and an empty or zero-width table is rejected.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import ast
import copy
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.common import gen_docs, pyrogue_ast, register_drift, register_tables, timing_model, yaml_maps
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
    read_family_matrix,
    read_locks,
    read_verilog_unit,
    read_vhdl_unit,
    render_all,
    rendered_files,
    statuses,
)
from tests.common.ghdl_analysis import KNOWN_GHDL_UNANALYZABLE, NOT_SIMULATED
from tests.common.register_drift import ISSUE_URL_RE
from tests.common.regression_utils import REPO_ROOT
from tests.common.vhdl_registers import read_decode
from tests.common import source_inventory
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


TIME_STAMP_GENERATOR = "LCLS-I/evr/EvrV1TimeStampGenerator.v"


def test_verilog_reader_parses_the_time_stamp_generator():
    unit = read_verilog_unit(REPO_ROOT / TIME_STAMP_GENERATOR)
    assert (unit.kind, unit.name, unit.generics) == ("module", "EvrV1TimeStampGenerator", ())
    assert [tuple(port) for port in unit.ports] == [
        ("Clock", "in", "wire"),
        ("Reset", "in", "wire"),
        ("TimeStamp", "out", "[63:0]"),
    ]
    assert unit.line == 11


def test_verilog_reader_reads_parameters_and_ansi_headers(tmp_path):
    channel = read_verilog_unit(REPO_ROOT / "LCLS-I/evr/EvrV1EventReceiverChannel.v")
    assert [tuple(generic) for generic in channel.generics] == [
        ("delayIdle", "parameter [1:0]", "2'b00"),
        ("delayWait", "parameter [1:0]", "2'b01"),
        ("delayOut", "parameter [1:0]", "2'b10"),
    ]
    assert [port.name for port in channel.ports][:3] == ["Clock", "Reset", "myEvent"]
    assert tuple(channel.ports[-1]) == ("channelDebug", "out", "[102:0]")
    source = tmp_path / "Probe.v"
    source.write_text(
        "// module Fake(a);\n"
        "/* module Fake2(b);\n   input b; */\n"
        "module Probe #(parameter W = 8, parameter [3:0] K = 4'd3) (\n"
        "    input  wire clk,\n"
        "    input  [W-1:0] a, b,\n"
        "    output reg [7:0] q,\n"
        "    inout  z\n"
        ");\n"
        "endmodule\n",
        encoding="utf-8",
    )
    unit = read_verilog_unit(source)
    assert unit.name == "Probe"
    assert unit.line == 4
    assert [tuple(generic) for generic in unit.generics] == [("W", "parameter", "8"), ("K", "parameter [3:0]", "4'd3")]
    assert [tuple(port) for port in unit.ports] == [
        ("clk", "in", "wire"),
        ("a", "in", "[W-1:0]"),
        ("b", "in", "[W-1:0]"),
        ("q", "out", "[7:0]"),
        ("z", "inout", "wire"),
    ]


def test_verilog_reader_rejects_a_port_without_a_direction(tmp_path):
    source = tmp_path / "Broken.v"
    source.write_text("module Broken(a, b);\n  input a;\nendmodule\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"Broken\.v.*port b"):
        read_verilog_unit(source)
    nothing = tmp_path / "Nothing.v"
    nothing.write_text("// module Commented(a);\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"Nothing\.v"):
        read_verilog_unit(nothing)


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
            if units[path].kind == "package":
                assert path not in found, f"{path}: a package has no status"
                continue
            assert found.get(path) in STATUSES, f"{path}: status {found.get(path)!r} is not one of {STATUSES}"
        if tree.key == "core":
            assert found[DIVIDER] == "simulated"


def test_unknown_documentation_tree_is_rejected():
    with pytest.raises(ValueError, match="nothing"):
        statuses(REPO_ROOT, "nothing")


def _entity_names():
    """Return {path: lowercase unit name} of every entity and module in every documentation tree."""
    return {
        path: unit.name.lower()
        for tree in DOC_TREES
        for path, unit in gen_docs._tree_units(REPO_ROOT, tree).items()
        if unit.kind in ("entity", "module")
    }


def test_statuses_match_the_baselines():
    found = {}
    for tree in DOC_TREES:
        found.update(statuses(REPO_ROOT, tree.key))
    names = _entity_names()
    assert set(found) == set(names)
    assert len(found) == 62
    assert all(status in STATUSES for status in found.values())

    def by_status(status):
        return {path for path, value in found.items() if value == status}

    excluded = by_status("baseline-excluded")
    assert {names[path] for path in excluded} == set(KNOWN_GHDL_UNANALYZABLE) & set(names.values())
    assert {Path(path).name for path in excluded} == {
        "TPGMiniReg.vhd", "TPGMiniCore.vhd", "TimingCore.vhd", "TimingGthWrapper.vhd",
        "EvrV2Module.vhd", "EvrV2_tb.vhd", "EvrV1CoreIsrCtrl.vhd",
    }
    not_simulated = by_status("not simulated")
    assert {names[path] for path in not_simulated} == set(NOT_SIMULATED) & set(names.values())
    assert {Path(path).name for path in not_simulated} == {"EvrV1EventReceiver.vhd", "EvrV1Core.vhd"}
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
    assert "LCLS-II/core/rtl/TPGMiniEdefPkg.vhd" not in found
    assert found["LCLS-II/core/tb/TimingSerialDelay_tb.vhd"] == "simulated"
    assert found["LCLS-II/core/rtl/TPGMiniEdefTb.vhd"] == "simulated"
    assert found["LCLS-II/core/rtl/BsaControlv2.vhd"] == "simulated"
    vivado = by_status("Vivado-only")
    assert vivado == {path for path in found if path.startswith(gen_docs.GT_DIRECTORIES)}
    assert {Path(path).name for path in vivado} == {"TimingGtCoreWrapper.vhd", "TimingGthCoreWrapper.vhd"}
    assert len(vivado) == 5
    simulated = by_status("simulated")
    assert len(simulated) == 62 - 7 - 2 - 4 - 5
    assert found["LCLS-I/evr/EvrV1TimeStampGenerator.v"] == "simulated"
    assert all(found[path] == "simulated" for path in found if path.startswith("LCLS-II/evr/rtl/") and path not in excluded)


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
        files = rendered_files(REPO_ROOT, tree)
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


def test_every_tracked_rtl_file_is_documented():
    documented = {path for tree in DOC_TREES for path in gen_docs.documented_files(REPO_ROOT, tree)}
    assert documented == set(source_inventory.rtl_sources(REPO_ROOT))
    assert len(documented) == 68
    assert not any("wrappers" in Path(path).parts for path in documented)
    assert all(rendered_files(REPO_ROOT, tree) == gen_docs.documented_files(REPO_ROOT, tree) for tree in DOC_TREES)


def test_duplicate_gt_wrappers_get_distinct_titles():
    page = render_all(REPO_ROOT)["reference/entities/gt.rst"]
    shared = [
        "LCLS-II/gtp7/rtl/TimingGtCoreWrapper.vhd",
        "LCLS-II/gtx7/rtl/TimingGtCoreWrapper.vhd",
        "LCLS-II/gthUltraScale/rtl/TimingGtCoreWrapper.vhd",
        "LCLS-II/gtyUltraScale+/rtl/TimingGtCoreWrapper.vhd",
    ]
    titles = re.findall(r"^(TimingGtCoreWrapper \(.*\))$", page, re.MULTILINE)
    assert titles == [f"TimingGtCoreWrapper ({path})" for path in sorted(shared)]
    labels = re.findall(r"^\.\. _(entity-[^:]*timinggtcorewrapper[^:]*):$", page, re.MULTILINE)
    assert len(labels) == len(shared) and len(set(labels)) == len(shared), labels
    assert re.search(r"^TimingGthCoreWrapper$", page, re.MULTILINE)
    assert page.count("Vivado-only") >= 5
    rows = re.findall(r"^   \* - :ref:`(\w+) <entity-[^>]+>`\n     - :repo:`([^`]+)`\n     - Vivado-only$", page, re.MULTILINE)
    assert len(rows) == 5


_GTH_XCI = "LCLS_TIMING_GTH_XCI"
_GTY_XCI = "LCLS_TIMING_GTY_XCI"
_GTH = "TimingGth_extref, TimingGth_fixedlat"
_GTY = "TimingGty_extref, TimingGty_fixedlat"


def _bullets(*lines):
    return "\n".join(f"- {line}" for line in lines)


# Written by hand from LCLS-II/ruckus.tcl and the five GT ruckus.tcl files, not produced by the parser.
_GTH_US_COREGEN = _bullets(
    f"coregen/2025.1 (xci): {_GTH}; Vivado >= 2025.1, {_GTH_XCI} = 1",
    f"coregen/2025.1 (dcp): {_GTH}; Vivado >= 2025.1, {_GTH_XCI} not 1",
    f"coregen/2025.1 (xdc): TimingGth_fixedlat; Vivado >= 2025.1, {_GTH_XCI} not 1",
    f"coregen/2016.4 (xci): {_GTH}; Vivado >= 2016.4 and < 2025.1, {_GTH_XCI} = 1",
    f"coregen/2016.4 (dcp): {_GTH}; Vivado >= 2016.4 and < 2025.1, {_GTH_XCI} not 1",
)
_GTH_US_SELECT = _bullets(f"{_GTH_XCI} = 1: file type xci", f"{_GTH_XCI} not 1: file type dcp, xdc")
_GTH_PLUS_COREGEN = _bullets(
    f"coregen (xci): {_GTH}; Vivado >= 2022.2, {_GTH_XCI} = 1",
    f"coregen (dcp): {_GTH}; Vivado >= 2022.2, {_GTH_XCI} not 1",
)
_GTH_PLUS_SELECT = _bullets(f"{_GTH_XCI} = 1: file type xci", f"{_GTH_XCI} not 1: file type dcp")
_GTY_COREGEN = _bullets(
    f"coregen (xci): {_GTY}, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, {_GTY_XCI} = 1",
    f"coregen (dcp): {_GTY}, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, {_GTY_XCI} not 1",
    f"coregen/smurf (xci): {_GTY}; Vivado >= 2018.2, TIMING_246MHz set and not 0, {_GTY_XCI} = 1",
    f"coregen/smurf (dcp): {_GTY}; Vivado >= 2018.2, TIMING_246MHz set and not 0, {_GTY_XCI} not 1",
)
_GTY_SELECT = _bullets(
    "TIMING_246MHz unset or 0: directory coregen",
    "TIMING_246MHz set and not 0: directory coregen/smurf",
    f"{_GTY_XCI} = 1: file type xci",
    f"{_GTY_XCI} not 1: file type dcp",
)
_US_PLUS_FAMILIES = ("kintexuplus", "virtexuplus", "virtexuplusHBM", "zynquplus", "zynquplusRFSOC", "qzynquplusRFSOC")

EXPECTED_FAMILIES = [
    ("artix7", "gtp7", "TimingGtCoreWrapper", "none", "none", "none"),
    ("kintex7", "gtx7", "TimingGtCoreWrapper", "none", "none", "none"),
    ("kintexu", "gthUltraScale", "TimingGtCoreWrapper", "Vivado >= 2016.4", _GTH_US_COREGEN, _GTH_US_SELECT),
    *[(f, "gtyUltraScale+", "TimingGtCoreWrapper", "none", _GTY_COREGEN, _GTY_SELECT) for f in _US_PLUS_FAMILIES],
    *[
        (f, "gthUltraScale+", "TimingGthCoreWrapper", "Vivado >= 2022.2", _GTH_PLUS_COREGEN, _GTH_PLUS_SELECT)
        for f in _US_PLUS_FAMILIES
    ],
]


def test_family_matrix_matches_the_reviewed_table():
    assert [tuple(row) for row in read_family_matrix(REPO_ROOT)] == EXPECTED_FAMILIES
    assert len(EXPECTED_FAMILIES) == 15


def test_a_family_that_loads_two_directories_gets_two_rows():
    rows = read_family_matrix(REPO_ROOT)
    for family in _US_PLUS_FAMILIES:
        mine = [row for row in rows if row.family == family]
        assert [row.directory for row in mine] == ["gtyUltraScale+", "gthUltraScale+"], family
        assert mine[0].wrapper != mine[1].wrapper
    assert [row.family for row in rows if row.directory == "gthUltraScale"] == ["kintexu"]
    page = render_all(REPO_ROOT)["reference/families.rst"]
    assert page.count("LCLS-II/gtyUltraScale+/ruckus.tcl") == 6
    assert page.count("LCLS-II/gthUltraScale+/ruckus.tcl") == 6
    for name in ("LCLS_TIMING_GTH_XCI", "LCLS_TIMING_GTY_XCI", "TIMING_246MHz"):
        assert name in page


def test_family_parser_rejects_an_unknown_condition(tmp_path):
    (tmp_path / "LCLS-II").mkdir()
    (tmp_path / "LCLS-II" / "ruckus.tcl").write_text(
        "if { $::env(SURPRISE) == 3 } {\n   loadRuckusTcl \"$::DIR_PATH/gtp7\"\n}\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="SURPRISE"):
        read_family_matrix(tmp_path)


def test_locks_are_read_from_every_ruckus_file():
    locks = read_locks(REPO_ROOT)
    assert locks == [
        ("ruckus.tcl", "VersionCheck", "Vivado", "2019.1"),
        ("ruckus.tcl", "SubmoduleCheck", "ruckus", "2.1.2"),
        ("ruckus.tcl", "SubmoduleCheck", "surf", "2.53.0"),
        ("LCLS-II/gtx7/ruckus.tcl", "SubmoduleCheck", "surf", "2.74.0"),
    ]
    tracked = source_inventory.repo_ruckus_files(REPO_ROOT)
    assert len(tracked) == 10
    seen = sum(
        len(re.findall(r"^[^#\n]*\b(?:VersionCheck|SubmoduleCheck)\b", (REPO_ROOT / path).read_text(encoding="utf-8"), re.MULTILINE))
        for path in tracked
    )
    assert seen == len(locks)
    page = render_all(REPO_ROOT)["reference/families.rst"]
    for _, check, name, version in locks:
        assert name in page and version in page and check in page


def test_core_tree_renders_every_documented_file():
    core = next(tree for tree in DOC_TREES if tree.key == "core")
    assert core.only is None
    assert rendered_files(REPO_ROOT, core) == gen_docs.documented_files(REPO_ROOT, core)


# ---------------------------------------------------------------------------
# Register pages
# ---------------------------------------------------------------------------

RESET_WORD_RE = re.compile(r"^0x[0-9A-F]{3}$")
RESET_VALUE_RE = re.compile(r"^0x[0-9A-F]{8}$")
RESET_TEST_RE = re.compile(r"^[\w./-]+\.py::\w+$")
RESET_KEYS = {"value", "test", "basis"}
LITERAL_RE = re.compile(r"0[xX][0-9a-fA-F]+|\d+")


def reset_schema_problems(resets):
    """Return the problems of a reset mapping against the sidecar schema (empty means valid)."""
    problems = []
    if not isinstance(resets, dict):
        return ["the sidecar is not a mapping"]
    for block_name, variants in resets.items():
        block = register_drift.BLOCKS.get(block_name)
        if block is None:
            problems.append(f"unknown block {block_name!r}")
            continue
        known = {variant.id for variant in block.variants}
        for variant_id, words in variants.items():
            if variant_id not in known:
                problems.append(f"{block_name}: unknown variant {variant_id!r}")
                continue
            for word, entry in words.items():
                where = f"{block_name}/{variant_id}/{word}"
                if not isinstance(word, str) or not RESET_WORD_RE.match(word):
                    problems.append(f"{where}: word is not 0x plus three upper-case hex digits")
                if not isinstance(entry, dict) or set(entry) != RESET_KEYS:
                    problems.append(f"{where}: entry keys are not exactly {sorted(RESET_KEYS)}")
                    continue
                if not isinstance(entry["value"], str) or not RESET_VALUE_RE.match(entry["value"]):
                    problems.append(f"{where}: value is not 0x plus eight upper-case hex digits")
                if not isinstance(entry["test"], str) or not RESET_TEST_RE.match(entry["test"]):
                    problems.append(f"{where}: test is not <repo path>::<function>")
                if not isinstance(entry["basis"], str) or not entry["basis"]:
                    problems.append(f"{where}: basis is empty")
    return problems


def defined_names(tree):
    """Return the names a module defines: functions, module-level assignments, and imports."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def assigned_names(functions):
    """Return the names assigned inside the given function nodes (the computation an assert compares with)."""
    return {
        target.id
        for function in functions
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def cite_problems(entry, source):
    """Return why an entry's cited function does not support its value (empty means it does)."""
    tree = ast.parse(source)
    function = entry["test"].split("::", 1)[1]
    found = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function
    ]
    if not found:
        return [f"no function {function} in the cited file"]
    basis = entry["basis"]
    token = re.compile(r"(?<!\w)" + re.escape(basis) + r"(?!\w)")
    segments = [
        ast.get_source_segment(source, node) or ""
        for function_node in found
        for node in ast.walk(function_node)
        if isinstance(node, ast.Assert)
    ]
    if not any(token.search(segment) and "reset" in segment.lower() for segment in segments):
        return [f"no assert in {function} holds the token {basis!r} and the text 'reset'"]
    if LITERAL_RE.fullmatch(basis):
        if int(basis, 0) != int(entry["value"], 16):
            return [f"literal basis {basis} differs from the value {entry['value']}"]
    elif basis not in defined_names(tree) | assigned_names(found):
        return [f"basis {basis!r} is not defined in the cited file or assigned in the cited function"]
    return []


def sidecar_entries(resets):
    for block_name, variants in resets.items():
        for variant_id, words in variants.items():
            for word, entry in words.items():
                yield block_name, variant_id, word, entry


def test_reset_sidecar_schema():
    resets = load_sidecar("register_resets.yaml")
    assert resets
    assert reset_schema_problems(resets) == []
    extra_key = copy.deepcopy(resets)
    first = next(iter(sidecar_entries(extra_key)))
    first[3]["note"] = "a key the schema does not allow"
    assert any("entry keys" in problem for problem in reset_schema_problems(extra_key))
    lower = copy.deepcopy(resets)
    next(iter(sidecar_entries(lower)))[3]["value"] = "0xabcdef01"
    assert any("upper-case" in problem for problem in reset_schema_problems(lower))
    missing = copy.deepcopy(resets)
    del next(iter(sidecar_entries(missing)))[3]["basis"]
    assert any("entry keys" in problem for problem in reset_schema_problems(missing))
    assert any("unknown block" in problem for problem in reset_schema_problems({"NoSuchBlock": {}}))
    assert any(
        "unknown variant" in problem
        for problem in reset_schema_problems({"EvrV2TriggerReg": {"nope": {}}})
    )
    assert any(
        "word is not" in problem
        for problem in reset_schema_problems(
            {"EvrV2TriggerReg": {"default": {"0x0": dict(value="0x00000000", test="a.py::f", basis="x")}}}
        )
    )


def test_reset_entries_cite_an_existing_test():
    resets = load_sidecar("register_resets.yaml")
    for block_name, variant_id, word, entry in sidecar_entries(resets):
        path = REPO_ROOT / entry["test"].split("::", 1)[0]
        assert path.is_file(), f"{block_name}/{variant_id}/{word}: {path} does not exist"
        problems = cite_problems(entry, path.read_text(encoding="utf-8"))
        assert not problems, f"{block_name}/{variant_id}/{word}: {problems}"


CITED = (
    "ZERO = 0\n"
    "def reset_word(word):\n"
    "    return 0\n"
    "async def check(dut):\n"
    "    value = 3\n"
    "    assert value == 0, 'word read after reset'\n"
    "    assert value == reset_word(1), 'after reset'\n"
    "    print(7, 'reset')\n"
    "def other():\n"
    "    assert 5 == 5\n"
)


def test_cite_check_accepts_matching_and_rejects_seeded_entries():
    ok = {"value": "0x00000000", "test": "t.py::check", "basis": "0"}
    assert cite_problems(ok, CITED) == []
    assert cite_problems({**ok, "basis": "reset_word"}, CITED) == []
    assert cite_problems({**ok, "value": "0x00000004"}, CITED), "a literal that differs from the value must fail"
    assert cite_problems({**ok, "test": "t.py::missing"}, CITED), "a missing function must fail"
    assert cite_problems({**ok, "basis": "7"}, CITED), "a basis outside any assert must fail"
    assert cite_problems({**ok, "test": "t.py::other", "basis": "5"}, CITED), "an assert without reset must fail"
    assert cite_problems({**ok, "basis": "ZERO"}, CITED), "a name that is not inside an assert must fail"
    named = {**ok, "basis": "reset_word", "test": "t.py::check"}
    assert cite_problems(named, CITED.replace("def reset_word", "def renamed")), "an undefined name must fail"
    local = "def check():\n    want = compute()\n    assert 1 == want, 'after reset'\ndef other():\n    miss = 2\n"
    assert cite_problems({**ok, "test": "t.py::check", "basis": "want"}, local) == [], "a local computation is valid"
    assert cite_problems({**ok, "test": "t.py::check", "basis": "miss"}, local), "another function's local must fail"


def test_reset_entries_are_decoded_words():
    resets = load_sidecar("register_resets.yaml")
    for block_name, variant_id, word, _ in sidecar_entries(resets):
        block = register_drift.BLOCKS[block_name]
        assert block.vhdl is not None, f"{block_name} has no RTL decode, so no word can be asserted"
        variant = next(v for v in block.variants if v.id == variant_id)
        decode = read_decode(block.vhdl, generics=variant.generics)
        words = set()
        for field in register_drift.from_vhdl(decode, block_name):
            span = ((field.bit_in_word + (field.bit_size or 1)) + 31) // 32
            words.update(field.word_byte + 4 * count for count in range(span))
        assert int(word, 16) in words, f"{block_name}/{variant_id}: {word} is not a decoded word"


def page_cells(text):
    """Return the rows of every list-table in a page as lists of cell texts (continuation lines joined by newline)."""
    rows = []
    row = None
    for line in text.splitlines():
        if line.startswith("   * - "):
            row = [[line[len("   * - "):]]]
            rows.append(row)
        elif line.startswith("     - ") and row is not None:
            row.append([line[len("     - "):]])
        elif line.startswith("       ") and row is not None:
            row[-1].append(line.strip())
    return [["\n".join(cell) for cell in each] for each in rows]


def test_every_allowlist_entry_is_on_its_page():
    pages = render_all(REPO_ROOT)
    for block_name in gen_docs.REGISTER_BLOCKS:
        page = pages[f"reference/registers/{block_name}.rst"]
        assert not entries_missing_from(page, block_name, register_drift.ALLOWLIST)
    checked = {key for key in register_drift.ALLOWLIST if key[0] in gen_docs.REGISTER_BLOCKS}
    assert checked, "no allowlist entry belongs to a documented block"


def entries_missing_from(page, block_name, allowlist):
    """Return the allowlist keys of a block that the page does not show with their issue link."""
    missing = []
    for key, issue in allowlist.items():
        if key[0] != block_name:
            continue
        number = issue.rsplit("/", 1)[1]
        lines = [line for line in page.splitlines() if line.startswith(f"   * ``{key[1]}`` ({key[2]}):")]
        if not any(f":issue:`{number}`" in line for line in lines):
            missing.append(key)
    return missing


def test_allowlist_check_flags_an_entry_missing_from_a_page():
    key = ("EvrV2TriggerReg", "ComplEn", "bitOffset")
    page = render_all(REPO_ROOT)["reference/registers/EvrV2TriggerReg.rst"]
    assert entries_missing_from(page, "EvrV2TriggerReg", {key: register_drift.ALLOWLIST[key]}) == []
    stripped = "\n".join(line for line in page.splitlines() if not line.startswith("   * ``ComplEn`` (bitOffset)"))
    assert entries_missing_from(stripped, "EvrV2TriggerReg", {key: register_drift.ALLOWLIST[key]}) == [key]
    wrong = page.replace(":issue:`214`", ":issue:`999`")
    assert entries_missing_from(wrong, "EvrV2TriggerReg", {key: register_drift.ALLOWLIST[key]}) == [key]


def block_variants(blocks):
    for name in blocks:
        block = register_drift.BLOCKS[name]
        for variant in block.variants:
            yield block, variant


def test_table_drift_matches_the_allowlist():
    drifts = []
    for block, variant in block_variants(gen_docs.REGISTER_BLOCKS):
        drifts.extend(gen_docs.block_comparison(block, variant).drifts)
    reasons = register_drift.verdict(drifts, register_drift.ALLOWLIST, blocks=set(gen_docs.REGISTER_BLOCKS))
    assert reasons == []


KIND_RE = re.compile(r"\b(?:missing-in-\w+|offset|bitOffset|bitSize|mode)\b")


def cell_kinds(cell):
    """Return the drift kinds a cell names on its first line (empty for agrees, not compared, absent)."""
    return set(KIND_RE.findall(cell.split("\n")[0]))


def test_rows_show_every_drift_the_comparison_reports():
    for block, variant in block_variants(gen_docs.REGISTER_BLOCKS):
        sources = gen_docs.block_sources(block, variant)
        reported = {
            (drift.field, drift.kind) for drift in gen_docs.block_comparison(block, variant).drifts
        }
        inside, outside = gen_docs.split_entries(block, sources)
        state = gen_docs.yaml_state(block, variant, sources)
        shown = set()
        for entry in inside:
            for source in ("python", "yaml"):
                cell = gen_docs.rtl_agreement(block.name, entry, source, state if source == "yaml" else "compared")
                shown.update((entry.name, kind) for kind in cell_kinds(cell))
                if cell.startswith("absent"):
                    shown.add((entry.name, f"missing-in-{source}"))
        for entry in outside:
            cell = gen_docs.python_agreement(block.name, entry, state)
            shown.update((entry.name, kind) for kind in cell_kinds(cell))
            if cell.startswith("absent"):
                shown.add((entry.name, "missing-in-yaml"))
        assert shown == {item for item in reported if not item[0].startswith("<")}, (block.name, variant.id)


def description_literals(source):
    """Return ({descriptions}, {variable names without one}) of the register declarations of a class source."""
    described, bare = set(), set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("RemoteVariable", "addRemoteVariables", "RemoteCommand")):
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        name = keywords["name"].value if isinstance(keywords.get("name"), ast.Constant) else None
        text = keywords.get("description")
        if isinstance(text, ast.Constant) and isinstance(text.value, str) and text.value:
            described.add(text.value)
        elif name is not None:
            bare.add(name)
    return described, bare


def description_problems(page, source):
    """Return the rows whose Description cell is neither source text nor the marker, or hides a described variable.

    Both table shapes are read: the RTL-primary table (eight columns, Python agreement in column 6) and the
    Python-view table (six columns, where a YAML-only register is the row that says missing-in-python).
    """
    described, bare = description_literals(source)
    problems = []
    for cells in page_cells(page):
        if len(cells) not in (len(gen_docs.RTL_HEADER), len(gen_docs.PYTHON_HEADER)) or cells[0] == "Offset":
            continue
        if not cells[0].startswith("``0x"):
            continue
        text = cells[-1]
        name = cells[1].split("\n")[0].strip("`").split("[")[0].split(".")[-1]
        python_absent = (
            cells[5].startswith("absent") if len(cells) == len(gen_docs.RTL_HEADER) else "missing-in-python" in cells[4]
        )
        if text == gen_docs.NO_DESCRIPTION:
            if not python_absent and name not in bare:
                problems.append(f"{name}: marked missing but the source describes it")
        elif text not in described:
            problems.append(f"{name}: {text!r} is not a description in the source")
    return problems


CLASS_FILES = {
    "TPG": ("TPG", "TPGControl", "TPGStatus", "TPGSeqState", "TPGSeqJump"),
    "EvrV2CoreTriggers": ("EvrV2CoreTriggers", "EvrV2ChannelReg", "EvrV2TriggerReg"),
}


def class_source(block_name):
    """Return the text of the class file of a block and, for a composite, of its child classes."""
    return "\n".join(
        (REPO_ROOT / "python" / "LclsTimingCore" / f"{name}.py").read_text(encoding="utf-8")
        for name in CLASS_FILES.get(block_name, (block_name,))
    )


def test_descriptions_are_copied_or_marked_missing():
    pages = render_all(REPO_ROOT)
    for block_name in gen_docs.REGISTER_BLOCKS:
        source = class_source(block_name)
        page = pages[f"reference/registers/{block_name}.rst"]
        assert description_problems(page, source) == [], block_name
    page = pages["reference/registers/EvrV2TriggerReg.rst"]
    source = (REPO_ROOT / "python/LclsTimingCore/EvrV2TriggerReg.py").read_text(encoding="utf-8")
    assert "Trigger Enable" in page
    invented = page.replace("Signal polarity", "A description nobody wrote")
    assert description_problems(invented, source)
    hidden = page.replace("Signal polarity", gen_docs.NO_DESCRIPTION)
    assert description_problems(hidden, source)


def test_read_descriptions_returns_the_text_per_base_name():
    source = (
        "import pyrogue as pr\n"
        "class A(pr.Device):\n"
        "    def __init__(self):\n"
        "        self.add(pr.RemoteVariable(name='One', offset=0, description='first'))\n"
        "        self.add(pr.RemoteVariable(name='Two', offset=4))\n"
        "        self.addRemoteVariables(name='Arr', offset=8, number=2, stride=4, description='array')\n"
    )
    variables = pyrogue_ast.parse_remote_variables(source)
    assert [(v.name, v.description) for v in variables] == [
        ("One", "first"), ("Two", None), ("Arr[0]", "array"), ("Arr[1]", "array"),
    ]
    page_source = REPO_ROOT / "python/LclsTimingCore/EvrV2TriggerReg.py"
    described = pyrogue_ast.read_descriptions(page_source)
    assert described["EnableTrig"] == "Trigger Enable"
    assert described["Delay"] == "Delay in ticks"


def test_adjacent_fields_get_their_own_flagged_rows():
    page = render_all(REPO_ROOT)["reference/registers/EvrV2TriggerReg.rst"]
    default_table = page.split("Variant useTap")[0]
    rows = {cells[1].split("\n")[0].strip("`"): cells for cells in page_cells(default_table)}
    assert rows["ComplEn"][2] == "[28]" and rows["ComplAnd"][2] == "[29]"
    for name in ("ComplEn", "ComplAnd"):
        assert "differs: bitOffset :issue:`214`" in rows[name][5]
    assert rows["Source"][5] == "agrees"
    assert page.count(":issue:`214`") >= 3


def test_register_rows_are_sorted_by_offset_then_bit():
    for path, page in render_all(REPO_ROOT).items():
        if not path.startswith("reference/registers/") or path.endswith(("index.rst", "yaml_only.rst")):
            continue
        last = None
        for cells in page_cells(page):
            if cells[0] == "Offset":
                last = None
                continue
            if not cells[0].startswith("``0x"):
                continue
            offset = int(cells[0].split("``")[1], 16)
            bits = cells[2].strip("[]").split(":")
            key = (offset, 0 if bits == ["strobe"] else int(bits[-1]))
            assert last is None or last <= key, f"{path}: row {cells[1]!r} is out of order"
            last = key


def test_register_generation_is_idempotent_and_ascii():
    first = gen_docs.render_registers(REPO_ROOT)
    assert first == gen_docs.render_registers(REPO_ROOT)
    for path, text in first.items():
        text.encode("ascii")
        assert "\u2013" not in text and "\u2014" not in text, path


def test_every_block_and_shape_map_has_a_page():
    pages = render_all(REPO_ROOT)
    assert gen_docs.REGISTER_BLOCKS == tuple(register_drift.BLOCKS)
    for name in register_drift.BLOCKS:
        assert f"reference/registers/{name}.rst" in pages
    shape = {name for name, kind in yaml_maps.YAML_CLASSIFICATION.items() if kind == "shape"}
    assert set(gen_docs.YAML_ONLY_MAPS) == shape
    drift_maps = {name for name, kind in yaml_maps.YAML_CLASSIFICATION.items() if kind == "drift"}
    assert drift_maps == {block.yaml for block in register_drift.BLOCKS.values()}
    only = pages[gen_docs.YAML_ONLY_PAGE]
    for name in shape:
        assert f"\n{name}\n{'-' * len(name)}\n" in only, f"no section for {name}"
    index = pages["reference/registers/index.rst"]
    for name, reason in register_drift.COVERED_BY_LEAVES.items():
        assert name in index and reason in index
    listed = set()
    in_toctree = False
    for line in index.splitlines():
        if line.startswith(".. toctree::"):
            in_toctree = True
        elif in_toctree and line.startswith("   ") and not line.strip().startswith(":"):
            listed.add(line.strip())
        elif in_toctree and line and not line.startswith(" "):
            in_toctree = False
    assert listed == set(register_drift.BLOCKS) | {"yaml_only"}
    registers = {path for path in pages if path.startswith("reference/registers/")}
    assert registers == {"reference/registers/index.rst", gen_docs.YAML_ONLY_PAGE} | {
        f"reference/registers/{name}.rst" for name in register_drift.BLOCKS
    }


def test_no_rtl_pages_say_so():
    pages = render_all(REPO_ROOT)
    without = sorted(name for name, block in register_drift.BLOCKS.items() if block.vhdl is None)
    assert without == sorted(
        ["TPGControl", "LclsTriggerPulse", "EvrV2CoreTriggers", "TPGStatus", "TPGSeqJump", "TPGSeqState", "TPG"]
    )
    for name, block in register_drift.BLOCKS.items():
        page = pages[f"reference/registers/{name}.rst"]
        assert ("No RTL in repo:" in page) == (block.vhdl is None), name
        assert ("     - Reset\n" in page) == (block.vhdl is not None), name


def test_unparseable_maps_show_the_parse_error_and_its_issue():
    pages = render_all(REPO_ROOT)
    for file, (kind, line, fragment) in yaml_maps.KNOWN_YAML_DEFECTS.items():
        page = pages[f"reference/registers/{Path(file).stem}.rst"]
        assert f"``{kind}`` at line {line}" in page and fragment in page
        assert "map does not parse :issue:`218`" in page
        assert "``<yaml>`` (missing-in-yaml)" in page


def test_composite_pages_link_their_children():
    pages = render_all(REPO_ROOT)
    tpg = pages["reference/registers/TPG.rst"]
    for child in ("TPGControl", "TPGStatus", "TPGSeqState", "TPGSeqJump"):
        assert f":ref:`{child} <register-map-{child.lower()}>`" in tpg
        assert f".. _register-map-{child.lower()}:" in pages[f"reference/registers/{child}.rst"]
    triggers = pages["reference/registers/EvrV2CoreTriggers.rst"]
    assert ":ref:`EvrV2ChannelReg <register-map-evrv2channelreg>`" in triggers
    assert "``0x1000``" in triggers and "16" in triggers


def test_arrays_collapse_into_one_row_with_an_offset_note():
    page = render_all(REPO_ROOT)["reference/registers/EvrV2Core.rst"]
    assert "``0x200`` + ``0x10`` * i" in page
    assert "``TriggerChannel[0..11]``" in page
    assert page.count("TriggerChannel[") == 1


def test_yaml_only_page_lists_arrays_without_expanding_them():
    only = render_all(REPO_ROOT)[gen_docs.YAML_ONLY_PAGE]
    assert "``dram[0..536870911]``" in only and "``0x000`` + ``0x8`` * i" in only
    assert "EvrV2Module.yaml has no top-level key 'EvrV2Module'" in only
    assert "``PacketSize``" in only and "BLD max packet size in words" in only
    assert only.count("``TriggerFineDelay[0..11]``") == 2
    rows = gen_docs.yaml_only_rows("BldAxiStream.yaml")
    assert [row.name for row in rows][:3] == ["PacketSize", "Enable", "ChannelMask"]
    with pytest.raises(ValueError, match="no top-level key"):
        gen_docs.yaml_only_rows("EvrV2Module.yaml")


def test_constructor_reader_reads_evr_core_triggers():
    path = REPO_ROOT / "python/LclsTimingCore/EvrV2CoreTriggers.py"
    arguments = dict(pyrogue_ast.read_constructor(path, "EvrV2CoreTriggers"))
    assert arguments["numTrig"] == "1"
    assert arguments["dmaEnable"] == "False"
    assert arguments["tickUnit"] == "'TBD'"
    assert "**kwargs" in arguments and arguments["**kwargs"] is None
    assert [name for name, _ in pyrogue_ast.read_constructor(path, "EvrV2CoreTriggers")][0] == "name"
    ((condition, message),) = pyrogue_ast.read_constructor_checks(path, "EvrV2CoreTriggers")
    assert "numTrig < 1" in condition and "numTrig > 16" in condition
    assert "between 1 to 16" in message
    assert pyrogue_ast.read_constructor_checks(
        REPO_ROOT / "python/LclsTimingCore/EvrV2TriggerReg.py", "EvrV2TriggerReg"
    ) == []


def test_constructor_reader_handles_synthetic_signatures(tmp_path):
    source = tmp_path / "Synthetic.py"
    source.write_text(
        "import pyrogue as pr\n"
        "class Synthetic(pr.Device):\n"
        "    def __init__(self, a, b=2, *rest, c=3, **kwargs):\n"
        "        if a:\n"
        "            raise ValueError('a is set')\n"
        "        if b:\n"
        "            if c:\n"
        "                raise ValueError('c nested', 1)\n"
        "            raise KeyError('not counted')\n"
        "        if rest:\n"
        "            raise TypeError('not counted')\n",
        encoding="utf-8",
    )
    assert pyrogue_ast.read_constructor(source, "Synthetic") == [
        ("a", None), ("b", "2"), ("*rest", None), ("c", "3"), ("**kwargs", None),
    ]
    assert pyrogue_ast.read_constructor_checks(source, "Synthetic") == [
        ("a", "'a is set'"), ("c", "'c nested'"),
    ]
    with pytest.raises(ValueError, match="no class Missing"):
        pyrogue_ast.read_constructor(source, "Missing")


def test_api_pages_import_no_rogue():
    code = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from tests.common import gen_docs\n"
        "pages = gen_docs.render_pyrogue(sys.argv[1])\n"
        "assert any(path.startswith('reference/pyrogue/') for path in pages)\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] in ('rogue', 'pyrogue', 'cocotb', 'LclsTimingCore'))\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(REPO_ROOT)], capture_output=True, text=True, check=False, cwd=REPO_ROOT
    )
    assert result.returncode == 0, result.stderr


def test_api_page_shows_constructor_variables_and_register_link():
    page = render_all(REPO_ROOT)["reference/pyrogue/EvrV2TriggerReg.rst"]
    assert "``useTap``" in page and "``False``" in page
    assert ":ref:`EvrV2TriggerReg registers <register-map-evrv2triggerreg>`" in page
    assert page.count("DelayTapReadback") == 1


def classes_declared_in_the_package():
    found = set()
    for path in sorted((REPO_ROOT / "python/LclsTimingCore").glob("*.py")):
        if path.name == "__init__.py":
            continue
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef):
                found.add(node.name)
    return found


def test_every_device_class_has_an_api_page():
    pages = render_all(REPO_ROOT)
    classes = classes_declared_in_the_package()
    on_disk = {path.stem for path in (REPO_ROOT / "docs/reference/pyrogue").glob("*.rst")} - {"index"}
    rendered = {path.rsplit("/", 1)[1][:-4] for path in pages if path.startswith("reference/pyrogue/")} - {"index"}
    assert len(classes) == 16
    assert classes == rendered == on_disk
    index = pages["reference/pyrogue/index.rst"]
    for name in classes:
        assert f":ref:`{name} <api-{name.lower()}>`" in index
        assert f".. _api-{name.lower()}:" in pages[f"reference/pyrogue/{name}.rst"]
    rejected = {name for name, block in register_drift.BLOCKS.items() if block.python_source == "ast"}
    assert rejected == {"EvrV1Reg", "TPG", "TPGSeqJump", "TPGSeqState", "TPGStatus"}
    for name in classes:
        page = pages[f"reference/pyrogue/{name}.rst"]
        assert ("rejects this class at ``root.start()``" in page) == (name in rejected), name
    assert "Register table: :ref:`EvrV2ChannelReg registers" in pages["reference/pyrogue/EvrV2CoreChannels.rst"]


def gated_issue_urls(class_name):
    tree = ast.parse((REPO_ROOT / f"tests/rogue/test_{class_name}.py").read_text(encoding="utf-8"))
    urls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "RUN_KNOWN_ISSUE_TESTS=1" in node.value:
            urls |= set(re.findall(r"https://github\.com/slaclab/lcls-timing-core/issues/(\d+)", node.value))
    return urls


def test_rejected_classes_link_their_gated_issues():
    pages = render_all(REPO_ROOT)
    expected = {
        "EvrV1Reg": {"217"}, "TPG": {"228"}, "TPGSeqJump": {"220"}, "TPGSeqState": {"221"}, "TPGStatus": {"228"},
    }
    for name, numbers in expected.items():
        assert gated_issue_urls(name) == numbers, name
        page = pages[f"reference/pyrogue/{name}.rst"]
        for number in numbers:
            assert f":issue:`{number}`" in page, name
        tests = [issue.test for issue in gen_docs.class_known_issues(name)]
        assert tests == [f"test_{name}_known_issue_overlap"]
        for test in tests:
            assert f"``{test}``" in page
    buildable = pages["reference/pyrogue/TPGMiniCore.rst"]
    assert ":issue:`222`" in buildable and ":issue:`223`" in buildable
    assert "Rogue 6.16.0 rejects" not in buildable


def test_known_issue_reader_reads_filed_and_pending_reasons(tmp_path):
    (tmp_path / "test_Demo.py").write_text(
        "import pytest\n"
        "@pytest.mark.skipif(\n"
        "    SKIP,\n"
        "    reason=(\n"
        "        'known issue: A overlaps B; see https://github.com/slaclab/lcls-timing-core/issues/9; '\n"
        "        'set RUN_KNOWN_ISSUE_TESTS=1 to reproduce'\n"
        "    ),\n"
        ")\n"
        "def test_Demo_known_issue_one():\n"
        "    pass\n"
        "@pytest.mark.skipif(SKIP, reason='pending issue: C is odd; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce')\n"
        "def test_Demo_known_issue_two():\n"
        "    pass\n"
        "@pytest.mark.skipif(SKIP, reason='unrelated reason')\n"
        "def test_Demo_other():\n"
        "    pass\n",
        encoding="utf-8",
    )
    assert gen_docs.class_known_issues("Demo", rogue_dir=tmp_path) == [
        gen_docs.KnownIssue("test_Demo_known_issue_one", "A overlaps B", "https://github.com/slaclab/lcls-timing-core/issues/9"),
        gen_docs.KnownIssue("test_Demo_known_issue_two", "C is odd", "pending"),
    ]
    assert gen_docs.class_known_issues("Absent", rogue_dir=tmp_path) == []


def test_classes_that_share_a_variable_name_get_separate_tables():
    pages = render_all(REPO_ROOT)
    owners = {}
    for name in sorted(classes_declared_in_the_package()):
        for row in register_tables.load_table(name).ROWS:
            owners.setdefault(row.name, set()).add(name)
    shared = {variable: classes for variable, classes in owners.items() if len(classes) > 1}
    assert shared, "no two classes declare a variable of the same name"
    for variable, classes in shared.items():
        for name in classes:
            page = pages[f"reference/pyrogue/{name}.rst"]
            assert f"``{variable}``" in page or f"``{variable}[0" in page, (variable, name)
        assert len({pages[f"reference/pyrogue/{name}.rst"] for name in classes}) == len(classes)


def test_empty_constructor_children_and_variables_say_none():
    assert gen_docs.constructor_section([]) == "none\n"
    defaults_only = gen_docs.constructor_section([("name", "'X'"), ("description", "''"), ("**kwargs", None)])
    assert "Arguments beyond the ``pr.Device`` defaults: none." in defaults_only
    assert "Arguments beyond" not in gen_docs.constructor_section([("name", "'X'"), ("numTrig", "1")])
    assert gen_docs.checks_section([]) == "none\n"
    assert gen_docs.children_section([]) == "none\n"
    assert gen_docs.variables_table([]) == "none\n"
    page = render_all(REPO_ROOT)["reference/pyrogue/TPGSeqJump.rst"]
    assert "Constructor checks\n------------------\n\nnone\n" in page
    assert "Sub-devices\n-----------\n\nnone\n" in page
    assert "Arguments beyond the ``pr.Device`` defaults: none." in page


def test_api_pages_and_variables_are_sorted():
    pages = render_all(REPO_ROOT)
    index = pages["reference/pyrogue/index.rst"]
    listed = [cells[0].split("<")[0].split("`")[-1].strip() for cells in page_cells(index)][1:]
    assert listed == sorted(listed) and len(listed) == 16
    checked = 0
    for path, page in pages.items():
        if not path.startswith("reference/pyrogue/") or path.endswith("index.rst"):
            continue
        for chunk in page.split("Name\n     - Kind")[1:]:
            last = None
            for cells in page_cells(chunk):
                if len(cells) != 8 or not cells[2].startswith("``0x"):
                    continue
                bits = cells[3].strip("[]").split(":")
                key = (int(cells[2].split("``")[1], 16), int(bits[-1]))
                assert last is None or last <= key, f"{path}: {cells[0]} is out of order"
                last = key
                checked += 1
    assert checked > 200


def yaml_section(page, name):
    """Return the text of the section of one YAML map in the generated YAML page."""
    marker = f"\n{name}\n{'-' * len(name)}\n"
    assert marker in page, f"no section for {name}"
    return page.split(marker, 1)[1].split("\n.. _yaml-map-", 1)[0]


def test_yaml_page_documents_every_map_in_file_order():
    pages = render_all(REPO_ROOT)
    page = pages[gen_docs.YAML_MAPS_PAGE]
    on_disk = sorted(path.name for path in (REPO_ROOT / "yaml").glob("*.yaml"))
    assert len(on_disk) == 20
    assert on_disk == sorted(yaml_maps.YAML_CLASSIFICATION)
    positions = [page.index(f"\n{name}\n{'-' * len(name)}\n") for name in on_disk]
    assert positions == sorted(positions)
    assert "yaml_maps" in pages["reference/index.rst"]
    for name in on_disk:
        section = yaml_section(page, name)
        assert f"Classification: ``{yaml_maps.YAML_CLASSIFICATION[name]}``" in section
        assert "Parse status:" in section and "Includes" in section
    summary = page_cells(page.split(f"\n{on_disk[0]}\n")[0])
    assert [cells[0] for cells in summary][1:] == [f":ref:`{name} <yaml-map-{Path(name).stem.lower()}>`" for name in on_disk]


def test_yaml_page_links_the_parse_failures_and_the_missing_include():
    page = render_all(REPO_ROOT)[gen_docs.YAML_MAPS_PAGE]
    assert page.count(":issue:`218`") >= 3 and page.count(":issue:`219`") >= 1
    for name, (kind, line, fragment) in yaml_maps.KNOWN_YAML_DEFECTS.items():
        section = yaml_section(page, name)
        assert f"``{kind}`` at line {line}" in section and fragment in section
        assert ":issue:`218`" in section
        assert "The fields cannot be listed: the map does not parse." in section
    tpg = yaml_section(page, "TPG.yaml")
    assert "``TPGSeqMem.yaml`` (not found beside the map, :issue:`219`)" in tpg
    assert "after the includes are spliced in" in tpg
    assert "after the includes" not in yaml_section(page, "TPGControl.yaml")
    assert "Parse status: parses." in yaml_section(page, "EvrV2TriggerReg.yaml")
    assert ":ref:`EvrV2TriggerReg registers <register-map-evrv2triggerreg>`" in yaml_section(page, "EvrV2TriggerReg.yaml")


def write_yaml(root, name, text):
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(text, encoding="utf-8")


def test_including_map_names_the_included_file_and_lists_the_spliced_fields(tmp_path):
    write_yaml(tmp_path, "inc.yaml", "Shared: &Shared\n  class: IntField\n  mode: RO\n  sizeBits: 8\n")
    write_yaml(
        tmp_path,
        "a.yaml",
        "#include inc.yaml\n"
        "a:\n  class: MMIODev\n  children:\n"
        "    Own:\n      class: IntField\n      mode: RW\n      at:\n        offset: 0x0\n"
        "    Spliced:\n      <<: *Shared\n      at:\n        offset: 0x10\n",
    )
    section = gen_docs.yaml_map_section("a.yaml", root=tmp_path)
    assert "* ``inc.yaml``" in section
    assert "spliced in from ``inc.yaml``" in section
    cells = {row[0]: row for row in page_cells(section)}
    assert cells["``Own``"][1:] == ["``0x000``", "[31:0]", "RW"]
    assert cells["``Spliced``"][1:] == ["``0x010``", "[7:0]", "RO"]
    real = yaml_section(render_all(REPO_ROOT)[gen_docs.YAML_MAPS_PAGE], "EvrV2CoreTriggers.yaml")
    assert "``EvrV2ChannelReg.yaml``" in real and "``EvrV2TriggerReg.yaml``" in real
    assert "``EvrV2TriggerReg[0..15].Delay``" in real


def test_yaml_map_that_does_not_parse_is_shown_with_its_error(tmp_path):
    write_yaml(tmp_path, "bad.yaml", "a: b: c\n")
    section = gen_docs.yaml_map_section("bad.yaml", root=tmp_path)
    assert "``ScannerError`` at line 1" in section and "mapping values are not allowed here" in section
    assert "The fields cannot be listed: the map does not parse." in section
    assert ":issue:" not in section
    page = gen_docs.render_yaml_maps(root=tmp_path)
    assert "no: ``ScannerError``" in page and "\nbad.yaml\n--------\n" in page


def test_collapse_yaml_elements_joins_only_regular_device_arrays():
    def row(name, offset, count=1):
        return gen_docs.YamlRow(name, offset, 0, 32, "RW", count, 4 if count > 1 else 0, "")

    regular = [row(f"d[{i}].x", 0x10 * i) for i in range(4)]
    (joined, shown), = gen_docs.collapse_yaml_elements(regular)
    assert shown == "d[0..3].x" and joined.count == 4 and joined.stride == 0x10 and joined.offset == 0
    irregular = [row("d[0].x", 0), row("d[1].x", 0x10), row("d[2].x", 0x30)]
    assert [shown for _, shown in gen_docs.collapse_yaml_elements(irregular)] == [None, None, None]
    inner = [row("d[0].x", 0, count=2), row("d[1].x", 0x10, count=2)]
    assert [shown for _, shown in gen_docs.collapse_yaml_elements(inner)] == [None, None]
    single = [row("d[0].x", 0)]
    assert [shown for _, shown in gen_docs.collapse_yaml_elements(single)] == [None]


LAYOUT_ROW_RE = re.compile(r"^   \[(\d+):(\d+)\]\s+(\d+(?: x \d+)?)\s+(\S+)$")


def parsed_layout(text):
    """Return [(field, low, high, width text)] read back from a generated layout include."""
    rows = []
    for line in text.splitlines():
        match = LAYOUT_ROW_RE.match(line)
        if match:
            high, low, width, field = match.groups()
            rows.append((field.split("[")[0], int(low), int(high), width))
    return rows


def test_layout_ranges_equal_the_model():
    pages = gen_docs.render_layouts()
    assert sorted(pages) == sorted(f"_generated/{name}.inc" for name, *_ in gen_docs.LAYOUTS)
    for name, _, table, _ in gen_docs.LAYOUTS:
        text = pages[f"_generated/{name}.inc"]
        expected = [
            (field, offset, offset + width * count - 1, str(width) if count == 1 else f"{count} x {width}")
            for field, (offset, width, count) in timing_model.field_layout(table).items()
        ]
        assert parsed_layout(text) == expected, name
        assert "code-block:: text" in text


def test_layout_totals_equal_the_declared_sizes():
    for name, _, table, total in gen_docs.LAYOUTS:
        text = gen_docs.render_layouts()[f"_generated/{name}.inc"]
        rows = parsed_layout(text)
        assert rows[0][1] == 0 and rows[-1][2] == total - 1, name
        for (_, _, high, _), (_, low, _, _) in zip(rows, rows[1:]):
            assert low == high + 1, f"{name}: gap or overlap at bit {low}"
        assert f"{total} bits, packed least significant bit first" in text
        assert f"   total: {total} bits" in text


def test_layout_rejects_an_empty_or_zero_width_table():
    with pytest.raises(ValueError, match="layout table Empty is empty"):
        gen_docs.render_layout("Empty", (), 0)
    with pytest.raises(ValueError, match="layout table Narrow field a has width 0"):
        gen_docs.render_layout("Narrow", (("a", 0, 1), ("b", 8, 1)), 8)
    with pytest.raises(ValueError, match="layout table Sparse field a has width 4 and count 0"):
        gen_docs.render_layout("Sparse", (("a", 4, 0), ("b", 8, 1)), 8)
    with pytest.raises(ValueError, match="layout table Short holds 8 bits, expected 9"):
        gen_docs.render_layout("Short", (("a", 8, 1),), 9)


FRAME_ROW_RE = re.compile(r"^   (\d+)\s{2,}(\S.*?)\s{2,}")


def frame_rows(text):
    """Return [(symbol count, sequence)] of the run rows of a generated frame include."""
    return [(int(match.group(1)), match.group(2)) for match in map(FRAME_ROW_RE.match, text.splitlines()) if match]


def test_frame_diagrams_follow_the_model_encoders():
    pages = gen_docs.render_frames()
    assert sorted(pages) == ["_generated/lcls1_frame.inc", "_generated/lcls2_frame.inc"]

    frame2 = timing_model.message_frame(timing_model.default_message())
    text2 = pages["_generated/lcls2_frame.inc"]
    rows2 = frame_rows(text2)
    assert sum(count for count, _ in rows2) == len(frame2)
    assert [row for row in rows2 if row[1] == "data words"] == [(timing_model.TIMING_MESSAGE_WORDS, "data words")]
    assert [name for _, name in rows2] == [
        "alignment comma", "SOF", "SOS", "data words", "EOS", "EOF", "CRC low word", "CRC high word",
    ]
    assert f"0x{timing_model.SOF_SYMBOL[0]:04X}" in text2 and f"total: {len(frame2)} symbols" in text2
    low, high = frame2[-2][0], frame2[-1][0]
    assert f"0x{low:04X}" in text2 and f"0x{high:04X}" in text2

    databuff = {name: 0 for name, _, _ in timing_model.DATABUFF_FIELDS}
    frame1 = timing_model.encode_lcls1_frame(0, 0, databuff)
    text1 = pages["_generated/lcls1_frame.inc"]
    rows1 = frame_rows(text1)
    assert sum(count for count, _ in rows1) == len(frame1) == timing_model.LCLS1_CODE_INDEX + 512
    assert (2 * timing_model.LCLS1_DATABUFF_BYTES, f"{timing_model.LCLS1_DATABUFF_BYTES} x (comma, data buffer byte)") in rows1
    assert (64, "32 x (pulse id bit, comma)") in rows1
    assert (512, "256 x (comma, unset code slot)") in rows1
    assert f"0x{timing_model.LCLS1_START_SYMBOL[0]:04X}" in text1 and f"total: {len(frame1)} symbols" in text1


def test_symbol_runs_collapse_equal_symbols_and_fold_alternating_pairs():
    comma = (0x00BC, 0b01)
    data = (0x0000, 0b00)
    labels = [("comma", "0x00BC"), ("byte", "data")] * 3 + [("comma", "0x00BC")] * 2 + [("end", "0x1")]
    rows = gen_docs.symbol_runs([comma, data] * 3 + [comma] * 2 + [(1, 0b11)], labels)
    assert rows == [
        ("6", "3 x (comma, byte)", "0x00BC, data", "01, 00"),
        ("2", "comma", "0x00BC", "01"),
        ("1", "end", "0x1", "11"),
    ]
    assert gen_docs.symbol_runs([comma, data], labels[:2])[0] == ("1", "comma", "0x00BC", "01")
    with pytest.raises(ValueError, match="at least one symbol"):
        gen_docs.symbol_runs([], [])
    with pytest.raises(ValueError, match="1 symbols but 2 labels"):
        gen_docs.symbol_runs([comma], labels[:2])
