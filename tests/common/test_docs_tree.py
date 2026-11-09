#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Stdlib checks of the docs tree, docs/conf.py, docs/requirements.txt, and README.md.

Test methodology:
    Sweep: every .rst file under docs/ outside _build, _data, and _generated,
        plus README.md, docs/conf.py, and docs/requirements.txt.
    Stimulus: the files read as text, docs/conf.py parsed with ast (never
        imported, so Sphinx is not needed), a minimal toctree reader, and one
        git ls-files call for the tracked set.
    Checks: a page reachable from no toctree, a tutorial page or toctree
        entry, a non-ASCII character, a tab, or a line ending in a blank in
        the docs or README, a tests import in docs/conf.py, extlinks roles
        other than repo and issue or with other URL templates, a docs
        requirement that is not an exact pin, a README without the published
        site link and the DOE Code link, a returning legacy doc generator
        file at the repository root, and a :repo: role whose target is not a
        tracked file or a directory holding one each fail one named test.
        Sphinx does not validate extlinks targets, so the last test is the
        only check of them. Each of the 12 explanation pages, the 8 how-to
        pages, and the 7 reference roots (entities, registers, and pyrogue
        indexes, yaml_maps, packages, families, known_issues) must exist and be
        reachable from the root toctree, and a seeded missing or unreachable
        page is reported.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import ast
import fnmatch
import posixpath
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
README = REPO_ROOT / "README.md"
CONF = DOCS / "conf.py"
REQUIREMENTS = DOCS / "requirements.txt"

SKIPPED_DIRS = {"_build", "_data", "_generated"}
SITE = "https://slaclab.github.io/lcls-timing-core/"
DOE_CODE = "https://www.osti.gov/doecode/biblio/75914"
LINK_TEMPLATES = {
    "repo": "https://github.com/slaclab/lcls-timing-core/blob/main/%s",
    "issue": "https://github.com/slaclab/lcls-timing-core/issues/%s",
}
# The script name is split so a repository-wide search for the legacy
# generator finds nothing in this file.
LEGACY_DOC_FILES = ("Doxyfile", "generate" + "DocumentationAndDeploy.sh")

PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[0-9][0-9.]*$")
TOCTREE_RE = re.compile(r"^(\s*)\.\. toctree::\s*$")
TITLE_TARGET_RE = re.compile(r"^.*<([^<>]+)>\s*$")
REPO_ROLE_RE = re.compile(r":repo:`([^`]+)`")


def docs_files():
    """Every file under docs/ outside the build and generated directories."""
    return sorted(p for p in DOCS.rglob("*")
                  if p.is_file()
                  and not SKIPPED_DIRS & set(p.relative_to(DOCS).parts))


def rst_pages():
    """Docs-relative page names without the suffix, for every .rst file."""
    return sorted(p.relative_to(DOCS).with_suffix("").as_posix()
                  for p in docs_files() if p.suffix == ".rst")


def toctree_entries(page):
    """Return the page names a page's toctree blocks list.

    Option lines start with a colon. "Title <target>" reduces to the target.
    Entries resolve relative to the page's directory, and a :glob: block
    expands its patterns against the known pages with fnmatch.
    """
    lines = (DOCS / (page + ".rst")).read_text(encoding="utf-8").splitlines()
    base = posixpath.dirname(page)
    known = rst_pages()
    found = []
    i = 0
    while i < len(lines):
        match = TOCTREE_RE.match(lines[i])
        i += 1
        if not match:
            continue
        indent = len(match.group(1))
        is_glob = False
        entries = []
        while i < len(lines):
            line = lines[i]
            if line.strip() and len(line) - len(line.lstrip()) <= indent:
                break
            i += 1
            text = line.strip()
            if not text:
                continue
            if text.startswith(":"):
                is_glob = is_glob or text.startswith(":glob:")
                continue
            title = TITLE_TARGET_RE.match(text)
            entries.append(title.group(1).strip() if title else text)
        for entry in entries:
            target = posixpath.normpath(posixpath.join(base, entry))
            if is_glob:
                found.extend(n for n in known if fnmatch.fnmatch(n, target))
            else:
                found.append(target)
    return found


def tracked_files():
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files"],
                         check=True, capture_output=True, text=True).stdout
    return set(out.splitlines())


def repo_link_targets(path):
    """Yield (line, target) for every :repo: role in a file.

    Both forms are read: a bare path in backquotes and "Title <path>" in
    backquotes. A #fragment and a trailing slash are removed.
    """
    text = path.read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), 1):
        for match in REPO_ROLE_RE.finditer(line):
            body = match.group(1).strip()
            title = TITLE_TARGET_RE.match(body)
            target = title.group(1).strip() if title else body
            yield number, target.split("#", 1)[0].rstrip("/")


def reachable_pages(pages):
    """Return the set of pages reachable from the root toctree through toctree entries."""
    seen = set()
    todo = ["index"]
    while todo:
        page = todo.pop()
        if page in seen:
            continue
        seen.add(page)
        todo.extend(t for t in toctree_entries(page) if t in pages)
    return seen


def test_every_page_is_reachable_from_the_root_toctree():
    pages = set(rst_pages())
    assert "index" in pages
    orphans = sorted(pages - reachable_pages(pages))
    assert not orphans, "pages reachable from no toctree: %s" % orphans


REQUIRED_PAGES = (
    *("explanation/" + name for name in (
        "overview", "architecture", "timing_message", "lcls2_frame",
        "lcls1_stream", "clocking_cdc", "gt_families", "extension_package",
        "tpg", "bsa", "evr_v2", "evr_v1")),
    *("how-to/" + name for name in (
        "run_regression", "release_flow", "add_wrapper_test", "use_pyrogue",
        "instantiate_timing_core", "instantiate_evr", "integrate_ruckus",
        "override_timing_extn_pkg")),
    *("reference/" + name for name in (
        "entities/index", "registers/index", "pyrogue/index", "yaml_maps",
        "packages", "families", "known_issues")),
)


def missing_or_unreachable(required, pages, reachable):
    """Return (required pages that do not exist, required pages no toctree reaches)."""
    missing = sorted(p for p in required if p not in pages)
    unreachable = sorted(p for p in required if p in pages and p not in reachable)
    return missing, unreachable


def test_required_pages_exist_and_are_reachable():
    assert len(REQUIRED_PAGES) == 12 + 8 + 7
    assert len(set(REQUIRED_PAGES)) == len(REQUIRED_PAGES)
    pages = set(rst_pages())
    reachable = reachable_pages(pages)
    missing, unreachable = missing_or_unreachable(REQUIRED_PAGES, pages, reachable)
    assert not missing, "required pages that do not exist: %s" % missing
    assert not unreachable, "required pages no toctree reaches: %s" % unreachable
    # A seeded absent page and a seeded orphan are both reported.
    gone = pages - {"reference/known_issues"}
    assert missing_or_unreachable(REQUIRED_PAGES, gone, reachable) == (["reference/known_issues"], [])
    orphaned = reachable - {"reference/known_issues"}
    assert missing_or_unreachable(REQUIRED_PAGES, pages, orphaned) == ([], ["reference/known_issues"])


def test_no_tutorial_section():
    for page in rst_pages():
        parts = page.split("/")
        assert not any(p.lower().startswith("tutorial") for p in parts), page
        for entry in toctree_entries(page):
            assert not any(p.lower().startswith("tutorial")
                           for p in entry.split("/")), (page, entry)
    for path in docs_files():
        parts = path.relative_to(DOCS).parts
        assert not any(p.lower().startswith("tutorial") for p in parts), path


def test_docs_text_is_ascii_without_tabs_or_trailing_blanks():
    for path in [*docs_files(), README]:
        data = path.read_bytes()
        text = data.decode("ascii")
        for number, line in enumerate(text.splitlines(), 1):
            where = "%s:%d" % (path.relative_to(REPO_ROOT), number)
            assert "\t" not in line, where
            assert line == line.rstrip(), where


def test_conf_imports_nothing_from_tests():
    tree = ast.parse(CONF.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue
        for module in modules:
            assert module.split(".")[0] != "tests", module


def test_conf_link_roles():
    tree = ast.parse(CONF.read_text(encoding="utf-8"))
    values = [n.value for n in ast.walk(tree)
              if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "extlinks"
                      for t in n.targets)]
    assert len(values) == 1
    extlinks = ast.literal_eval(values[0])
    assert set(extlinks) == set(LINK_TEMPLATES)
    for role, template in LINK_TEMPLATES.items():
        assert extlinks[role][0] == template, role


def test_requirements_are_exact_pins():
    lines = [x for x in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
             if x.strip()]
    assert lines
    for line in lines:
        assert PIN_RE.match(line), line


def test_readme_links_the_site_and_doe_code():
    text = README.read_text(encoding="utf-8")
    assert SITE in text
    for section in ("how-to", "reference", "explanation"):
        assert SITE + section + "/index.html" in text, section
    assert DOE_CODE in text


def test_legacy_doc_generator_files_are_gone():
    for name in LEGACY_DOC_FILES:
        assert not (REPO_ROOT / name).exists(), name


def test_repo_links_resolve_to_tracked_files():
    tracked = tracked_files()
    bad = []
    for path in docs_files():
        if path.suffix not in (".rst", ".inc"):
            continue
        for line, target in repo_link_targets(path):
            found = target in tracked or any(
                f.startswith(target + "/") for f in tracked)
            if not found:
                bad.append("%s:%d: %s" % (path.relative_to(REPO_ROOT), line,
                                          target))
    assert not bad, "untracked :repo: targets:\n" + "\n".join(bad)
