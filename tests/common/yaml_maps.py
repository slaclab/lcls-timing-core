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
    error_class: Optional[str] = None


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
        line = mark.line + 1 if mark else None
        return YamlLoad(None, missing, (problem, line), type(error).__name__)


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


# Every yaml/*.yaml is either compared against the Python and RTL sides by the
# drift check ("drift") or only checked for shape ("shape"): the five shape
# maps describe no register block that Python or the RTL decode mirrors one to
# one.
YAML_CLASSIFICATION = {
    "AmcCarrierDRAM.yaml": "shape",
    "BldAxiStream.yaml": "shape",
    "EvrV1Isr.yaml": "drift",
    "EvrV1Reg.yaml": "drift",
    "EvrV2ChannelReg.yaml": "drift",
    "EvrV2Core.yaml": "drift",
    "EvrV2CoreTriggers.yaml": "drift",
    "EvrV2Module.yaml": "shape",
    "EvrV2PulsegenRegs.yaml": "shape",
    "EvrV2TriggerPulse.yaml": "shape",
    "EvrV2TriggerReg.yaml": "drift",
    "GthRxAlignCheck.yaml": "drift",
    "LclsTriggerPulse.yaml": "drift",
    "TPG.yaml": "drift",
    "TPGControl.yaml": "drift",
    "TPGMiniCore.yaml": "drift",
    "TPGSeqJump.yaml": "drift",
    "TPGSeqState.yaml": "drift",
    "TPGStatus.yaml": "drift",
    "TimingFrameRx.yaml": "drift",
}

# Maps that do not parse after include splicing: (error class, line, message
# fragment). TPGControl.yaml and TPGSeqState.yaml fail on their own text, so
# their lines are file lines. TPG.yaml fails because it splices both; its line
# counts the spliced text (TPGControl.yaml line 58 after the 11 lines that
# precede the first include of TPG.yaml).
KNOWN_YAML_DEFECTS = {
    "TPG.yaml": ("ScannerError", 69, "mapping values are not allowed here"),
    "TPGControl.yaml": ("ScannerError", 58, "mapping values are not allowed here"),
    "TPGSeqState.yaml": ("ScannerError", 27, "mapping values are not allowed here"),
}

# Include targets that do not exist in yaml/, by including file.
KNOWN_MISSING_INCLUDES = {"TPG.yaml": ("TPGSeqMem.yaml",)}


def load_all():
    """Return {file: YamlLoad} for every yaml/*.yaml, sorted by file name."""
    return {path.name: load(path.name) for path in sorted(YAML_DIR.glob("*.yaml"))}


def defect_verdict(results, baseline=None) -> List[str]:
    """Return sorted reasons where results differ from the parse-failure baseline.

    A parse failure that is not listed fails, a listed file that now parses
    fails until its entry is removed, and a listed file that fails differently
    (class, line, or message) fails.
    """
    baseline = KNOWN_YAML_DEFECTS if baseline is None else baseline
    reasons = []
    for name in sorted(set(results) | set(baseline)):
        expected = baseline.get(name)
        result = results.get(name)
        if result is None:
            reasons.append(f"{name}: listed in KNOWN_YAML_DEFECTS but no such file was loaded; remove the entry")
        elif result.error is None:
            if expected is not None:
                reasons.append(f"{name}: listed in KNOWN_YAML_DEFECTS but now parses; remove the entry")
        else:
            problem, line = result.error
            if expected is None:
                reasons.append(f"{name}: new parse failure: {result.error_class}: {problem} (line {line})")
                continue
            kind, want_line, fragment = expected
            if result.error_class != kind or (want_line is not None and line != want_line) or fragment not in problem:
                reasons.append(
                    f"{name}: parse failure differs from KNOWN_YAML_DEFECTS "
                    f"(expected {kind} at line {want_line} containing {fragment!r}; "
                    f"got {result.error_class} at line {line}: {problem})"
                )
    return sorted(reasons)
