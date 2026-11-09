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
        of every documentation tree, and every entry of the sidecars under
        docs/_data. Small synthetic VHDL strings cover the entity reader and
        the page renderers.
    Stimulus: render_all on the real tree (text parsing only, no simulator),
        a temporary docs directory for the freshness check, and synthetic
        design units for the renderers.
    Checks: the committed pages equal a fresh generation, generation is
        deterministic and carries no host path, list tables reject a row with
        the wrong cell count, the reader returns the generics and ports of
        Divider.vhd in declaration order and rejects a file with no unit,
        the purposes sidecar has exactly the rendered files as keys and no
        purpose repeats a banner header, every purpose is one to three plain
        sentences, and every rendered entity has one known status.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import re
import pytest

from tests.common import gen_docs
from tests.common.gen_docs import (
    DOC_TREES,
    STATUSES,
    check_files,
    header_description,
    list_table,
    load_sidecar,
    read_vhdl_unit,
    render_all,
    rendered_files,
    statuses,
)
from tests.common.regression_utils import REPO_ROOT

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
