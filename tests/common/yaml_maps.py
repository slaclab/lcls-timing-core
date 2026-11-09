#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Load the CPSW register maps in yaml/ and flatten them to register fields.

The maps are not standalone YAML: a line ``#include <name>`` pulls in another
map, a line ``#once <name>`` is a comment, and anchors and merge keys refer
across the included text. ``splice`` therefore replaces each include line with
the text of the named file (at most once per name) before ``yaml.safe_load``
parses the result. A missing include target is recorded, never skipped
silently, and a target that resolves outside yaml/ raises ``ValueError``.

Only ``yaml.safe_load`` is used, so loading a map can never construct an
object or run code. ``flatten`` applies the CPSW defaults (``at.offset`` 0,
``nelms`` 1, ``stride`` 0, ``lsBit`` 0, ``sizeBits`` 32) and descends into
``MMIODev`` children. The module imports no Rogue.
"""

import re
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
YAML_DIR = REPO_ROOT / "yaml"

INCLUDE_RE = re.compile(r"^#include[ \t]+(\S+)[ \t]*$")

DEFAULT_SIZE_BITS = 32


class YamlLoad(NamedTuple):
    data: Optional[dict]
    missing_includes: List[str]
    error: Optional[Tuple[str, Optional[int]]]


class YamlField(NamedTuple):
    name: str
    index: Optional[int]
    byte_offset: int
    bit_offset: int
    bit_size: int
    mode: str


def splice(path, seen, missing) -> str:
    """Return the text of path with each include line replaced by its target.

    seen holds the names already included (a name is included at most once, in
    order of first use); missing collects the targets that do not exist.
    """
    path = Path(path)
    root = YAML_DIR.resolve()
    out = []
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for line in text.split("\n"):
        match = INCLUDE_RE.match(line)
        if match is None:
            out.append(line)
            continue
        name = match.group(1)
        target = (path.parent / name).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"{path.name}: include {name!r} resolves outside {YAML_DIR}")
        if name in seen:
            continue
        seen.add(name)
        if target.is_file():
            out.append(splice(target, seen, missing))
        else:
            missing.append(name)
    return "\n".join(out)


def load(name: str) -> YamlLoad:
    """Load yaml/<name> with its includes; report problems instead of hiding them."""
    missing: List[str] = []
    text = splice(YAML_DIR / name, {name}, missing)
    try:
        return YamlLoad(yaml.safe_load(text), missing, None)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        problem = getattr(error, "problem", None) or str(error)
        return YamlLoad(None, missing, (problem, mark.line + 1 if mark else None))


def flatten(node, base: int = 0, prefix: str = ""):
    """Yield a YamlField for every IntField element below node."""
    for key, child in (node.get("children") or {}).items():
        if not isinstance(child, dict):
            continue
        at = child.get("at") or {}
        offset = at.get("offset", 0)
        count = at.get("nelms", 1)
        stride = at.get("stride", 0)
        kind = child.get("class")
        for element in range(count):
            address = base + offset + element * stride
            index = element if "nelms" in at else None
            label = f"{prefix}{key}"
            if kind == "IntField":
                yield YamlField(
                    name=label,
                    index=index,
                    byte_offset=address,
                    bit_offset=child.get("lsBit", 0),
                    bit_size=child.get("sizeBits", DEFAULT_SIZE_BITS),
                    mode=child["mode"],
                )
            elif kind == "MMIODev":
                suffix = f"[{index}]" if index is not None else ""
                yield from flatten(child, address, f"{label}{suffix}.")


def yaml_fields(name: str) -> List[YamlField]:
    """Return the flattened fields of the top-level key named after the file stem."""
    loaded = load(name)
    if loaded.error is not None:
        raise ValueError(f"{name} does not parse: {loaded.error}")
    stem = Path(name).stem
    node = (loaded.data or {}).get(stem)
    if not isinstance(node, dict):
        raise ValueError(f"{name} has no top-level key {stem!r}")
    return list(flatten(node))
