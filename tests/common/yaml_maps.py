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


def _splice_lines(path, seen, missing, root):
    """Return (owner file name, line number, text) for every line of the spliced map."""
    path = Path(path)
    root = Path(root).resolve()
    out = []
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for number, line in enumerate(text.split("\n"), 1):
        match = INCLUDE_RE.match(line)
        if match is None:
            out.append((path.name, number, line))
            continue
        name = match.group(1)
        target = (path.parent / name).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"{path.name}: include {name!r} resolves outside {root}")
        if name in seen:
            continue
        seen.add(name)
        if target.is_file():
            out.extend(_splice_lines(target, seen, missing, root))
        else:
            missing.append(name)
    return out


def splice(path, seen, missing, *, root=YAML_DIR) -> str:
    """Return the text of path with each include line replaced by its target.

    seen holds the names already included (a name is included at most once, in
    order of first use); missing collects the targets that do not exist; an
    include that resolves outside root raises ValueError.
    """
    return "\n".join(text for _, _, text in _splice_lines(path, seen, missing, root))


def load(name: str, *, root=YAML_DIR) -> YamlLoad:
    """Load root/<name> with its includes; report problems instead of hiding them.

    A YAML tag that safe_load cannot construct (for example a python object
    tag) raises ConstructorError instead of being reported as a parse failure.
    """
    missing: List[str] = []
    text = splice(Path(root) / name, {name}, missing, root=root)
    try:
        return YamlLoad(yaml.safe_load(text), missing, None)
    except yaml.constructor.ConstructorError as error:
        if "could not determine a constructor" in (error.problem or ""):
            raise
        return _failed(error, missing)
    except yaml.YAMLError as error:
        return _failed(error, missing)


def _failed(error, missing) -> YamlLoad:
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

# The issue that records each baseline above, by file. A test compares these
# links with the reasons of the gated tests that reproduce the defects.
KNOWN_YAML_DEFECT_ISSUES = {
    "TPG.yaml": "https://github.com/slaclab/lcls-timing-core/issues/218",
    "TPGControl.yaml": "https://github.com/slaclab/lcls-timing-core/issues/218",
    "TPGSeqState.yaml": "https://github.com/slaclab/lcls-timing-core/issues/218",
}

# Include targets that do not exist in yaml/, by including file.
KNOWN_MISSING_INCLUDES = {"TPG.yaml": ("TPGSeqMem.yaml",)}

KNOWN_MISSING_INCLUDE_ISSUES = {
    "TPG.yaml": "https://github.com/slaclab/lcls-timing-core/issues/219",
}


def load_all(*, root=YAML_DIR):
    """Return {file: YamlLoad} for every yaml/*.yaml, sorted by file name."""
    return {path.name: load(path.name, root=root) for path in sorted(Path(root).glob("*.yaml"))}


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


# Keys the maps use on a node that has a class (IntField, MMIODev, and the
# Enum entries under ``enums``), and inside its ``at`` block, that the loader
# accepts without a finding. A key outside these sets (the
# ``lsbit`` and ``stribe`` typos) is reported, not treated as fatal: CPSW may
# ignore it, in which case the field silently takes its default.
CPSW_NODE_KEYS = frozenset(
    {
        "at",
        "children",
        "class",
        "configPrio",
        "description",
        "enums",
        "hidden",
        "lsBit",
        "metadata",
        "mode",
        "name",
        "sequence",
        "size",
        "sizeBits",
        "value",
    }
)
CPSW_AT_KEYS = frozenset({"nelms", "offset", "stride"})

VALID_MODES = ("RW", "RO")


class _LineDict(dict):
    """A mapping that remembers the line of each key in the spliced text."""

    lines: dict = {}


class _LineLoader(yaml.SafeLoader):
    """SafeLoader that records key lines, after merge keys are resolved."""

    def construct_yaml_map(self, node):
        data = _LineDict()
        yield data
        data.update(self.construct_mapping(node))
        data.lines = {
            str(key.value): key.start_mark.line + 1 for key, _ in node.value if isinstance(key, yaml.ScalarNode)
        }


_LineLoader.add_constructor("tag:yaml.org,2002:map", _LineLoader.construct_yaml_map)


def _parse_with_lines(name, root):
    spliced = _splice_lines(Path(root) / name, {name}, [], root)
    loader = _LineLoader("\n".join(text for _, _, text in spliced))
    try:
        return loader.get_single_data(), spliced
    finally:
        loader.dispose()


def _locate(origins, node, *keys):
    """Return (file, line) in the owning file for the first of keys present in node."""
    for key in keys:
        if key in node.lines:
            owner, line, _ = origins[node.lines[key] - 1]
            return owner, line
    owner, line, _ = origins[min(node.lines.values()) - 1]
    return owner, line


def _check_mode(node, field, origins, found):
    mode = node.get("mode")
    if mode in VALID_MODES:
        return
    owner, line = _locate(origins, node, "mode", "class", "name")
    detail = f"{field}: mode missing" if mode is None else f"{field}: mode {mode!r} is not RW or RO"
    found.add((owner, line, "mode", detail))


def _scan(node, path, origins, found, visited):
    if isinstance(node, list):
        for index, child in enumerate(node):
            _scan(child, path + (str(index),), origins, found, visited)
        return
    if not isinstance(node, _LineDict) or id(node) in visited:
        return
    visited.add(id(node))
    field = path[-1] if path else ""
    if "class" in node:
        for key in node:
            if key not in CPSW_NODE_KEYS:
                owner, line = _locate(origins, node, key)
                found.add((owner, line, "unknown-key", str(key)))
        at = node.get("at")
        if isinstance(at, _LineDict):
            for key in at:
                if key not in CPSW_AT_KEYS:
                    owner, line = _locate(origins, at, key)
                    found.add((owner, line, "unknown-key", f"at.{key}"))
            nelms = at.get("nelms", 1)
            if isinstance(nelms, int) and nelms > 1 and "stride" not in at:
                owner, line = _locate(origins, at, "nelms")
                found.add((owner, line, "stride", f"{field}: nelms {nelms} without stride"))
        if node.get("class") == "IntField":
            _check_mode(node, field, origins, found)
    items = node.get("IntField")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, _LineDict):
                _check_mode(item, str(item.get("name")), origins, found)
    for key, child in node.items():
        _scan(child, path + (str(key),), origins, found, visited)


def shape_report(results, *, root=YAML_DIR):
    """Return sorted (file, line, kind, detail) findings for the maps that parsed.

    Kinds: ``mode`` (an IntField mode that is missing or not RW or RO),
    ``stride`` (nelms above 1 with no stride), and ``unknown-key`` (a key
    outside CPSW_NODE_KEYS or CPSW_AT_KEYS). The file and line are those of the
    file that owns the text, not of the spliced map.
    """
    found = set()
    for name in sorted(results):
        if results[name].error is not None:
            continue
        data, origins = _parse_with_lines(name, root)
        _scan(data, (), origins, found, set())
    return sorted(found, key=lambda entry: (entry[0], entry[1], entry[2], entry[3]))


def shape_verdict(report, unknown_keys=None, shape_findings=None) -> List[str]:
    """Return sorted reasons where report differs from the two baselines."""
    baseline = set(UNKNOWN_KEYS if unknown_keys is None else unknown_keys)
    baseline |= set(SHAPE_FINDINGS if shape_findings is None else shape_findings)
    reported = set(report)
    reasons = [f"{f}:{line}: new {kind}: {detail}" for f, line, kind, detail in reported - baseline]
    reasons += [
        f"{f}:{line}: {kind} {detail!r} is listed in the baseline but no longer reported; remove the entry"
        for f, line, kind, detail in baseline - reported
    ]
    return sorted(reasons)


def count_intfields(data, name) -> int:
    """Count the IntField elements below the top-level key named after the file.

    Counted by arithmetic, not by walking each element: AmcCarrierDRAM.yaml
    declares 0x20000000 elements.
    """
    node = (data or {}).get(Path(name).stem)
    return _count(node) if isinstance(node, dict) else 0


def _count(node) -> int:
    total = 0
    for child in (node.get("children") or {}).values():
        if not isinstance(child, dict):
            continue
        copies = (child.get("at") or {}).get("nelms", 1)
        kind = child.get("class")
        if kind == "IntField":
            total += copies
        elif kind == "MMIODev":
            total += copies * _count(child)
    return total


# Unknown keys on the parseable maps, as (file, line, kind, detail). The
# ``lsbit`` and ``stribe`` spellings differ from CPSW ``lsBit`` and ``stride``,
# so a CPSW that ignores unknown keys places those fields at bit 0 and gives
# CountTrig no stride. ``Commands`` is an empty section header on a device
# node. TPGControl.yaml and TPGSeqState.yaml also use ``lsbit`` but do not
# parse, so they are not scanned until they do.
UNKNOWN_KEYS = (
    ("AmcCarrierDRAM.yaml", 33, "unknown-key", "Commands"),
    ("TPGSeqJump.yaml", 29, "unknown-key", "lsbit"),
    ("TPGSeqJump.yaml", 40, "unknown-key", "lsbit"),
    ("TPGSeqJump.yaml", 51, "unknown-key", "lsbit"),
    ("TPGStatus.yaml", 29, "unknown-key", "lsbit"),
    ("TPGStatus.yaml", 85, "unknown-key", "stribe"),
)

# Arrays (nelms above 1) that declare no stride, so the loader cannot place
# element 1 and later without a CPSW default it has not verified.
SHAPE_FINDINGS = (
    ("EvrV1Reg.yaml", 220, "stride", "Pulse00: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 229, "stride", "Pulse01: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 238, "stride", "Pulse02: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 247, "stride", "Pulse03: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 256, "stride", "Pulse04: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 265, "stride", "Pulse05: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 274, "stride", "Pulse06: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 283, "stride", "Pulse07: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 292, "stride", "Pulse08: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 301, "stride", "Pulse09: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 310, "stride", "Pulse10: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 319, "stride", "Pulse11: nelms 4 without stride"),
    ("EvrV1Reg.yaml", 328, "stride", "OutputMap: nelms 12 without stride"),
    ("EvrV1Reg.yaml", 349, "stride", "MapRam1: nelms 1024 without stride"),
    ("EvrV1Reg.yaml", 358, "stride", "MapRam2: nelms 1024 without stride"),
    ("TPGStatus.yaml", 81, "stride", "CountTrig: nelms 12 without stride"),
)

# IntField elements each parseable map flattens to (see count_intfields). A
# zero is deliberate: those maps declare no IntField below their top-level key,
# and the entry makes that visible.
INTFIELD_COUNTS = {
    "AmcCarrierDRAM.yaml": 536870912,
    "BldAxiStream.yaml": 11,
    "EvrV1Isr.yaml": 1,
    "EvrV1Reg.yaml": 2127,
    "EvrV2ChannelReg.yaml": 9,
    "EvrV2Core.yaml": 188,
    "EvrV2CoreTriggers.yaml": 288,
    "EvrV2Module.yaml": 0,
    "EvrV2PulsegenRegs.yaml": 0,
    "EvrV2TriggerPulse.yaml": 125,
    "EvrV2TriggerReg.yaml": 9,
    "GthRxAlignCheck.yaml": 46,
    "LclsTriggerPulse.yaml": 11,
    "TPGMiniCore.yaml": 68,
    "TPGSeqJump.yaml": 3072,
    "TPGStatus.yaml": 147,
    "TimingFrameRx.yaml": 26,
}
