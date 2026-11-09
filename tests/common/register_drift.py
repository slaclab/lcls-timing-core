#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Compare one register block across its VHDL decode, PyRogue tree, and YAML map.

Every source is reduced to ``RegField`` records. ``compare`` matches fields by
exact name, then through the per-block name map, and reports the differences as
``Drift`` records keyed by (block, field, kind). Positions are compared as the
absolute bit position, byte offset * 8 + bit offset, so Rogue's word alignment
of offsets never shows up as drift: equal positions are no drift, a different
32-bit word is kind ``offset``, and the same word with a different bit is kind
``bitOffset``.

``verdict`` applies the allowlist contract: a drift that is not listed fails,
and a listed entry that no longer drifts fails, so the list shrinks when a
fix lands. Every allowlist value is a link to a filed issue. The module uses
only the standard library, so the engine runs without Rogue.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional, Tuple

BITS_PER_BYTE = 8
WORD_BITS = 32

KINDS = (
    "offset",
    "bitOffset",
    "bitSize",
    "mode",
    "missing-in-vhdl",
    "missing-in-python",
    "missing-in-yaml",
)

SOURCES = ("python", "vhdl", "yaml")

ISSUE_URL_RE = re.compile(r"^https://github\.com/slaclab/lcls-timing-core/issues/\d+$")
PENDING_ISSUE = "pending"
REQUIRE_FILED_ISSUES = False


@dataclass(frozen=True)
class RegField:
    block: str
    name: str
    index: Optional[int]
    byte_offset: int
    bit_offset: int
    bit_size: Optional[int]
    mode: str
    source: str
    line: int
    readable: bool
    writable: bool

    @property
    def abs_bit(self) -> int:
        return self.byte_offset * BITS_PER_BYTE + self.bit_offset

    @property
    def word_byte(self) -> int:
        return (self.abs_bit // WORD_BITS) * 4

    @property
    def bit_in_word(self) -> int:
        return self.abs_bit % WORD_BITS


class Drift(NamedTuple):
    block: str
    field: str
    kind: str
    detail: str


@dataclass(frozen=True)
class Variant:
    id: str
    python_args: dict
    generics: dict
    compare_yaml: bool


@dataclass(frozen=True)
class Block:
    name: str
    vhdl: Optional[str]
    yaml: Optional[str]
    variants: Tuple[Variant, ...]
    vhdl_window: Optional[Tuple[int, int]] = None
    python_source: str = "tree"


BLOCKS = {
    "EvrV2TriggerReg": Block(
        "EvrV2TriggerReg",
        "LCLS-II/evr/rtl/EvrV2TrigReg.vhd",
        "EvrV2TriggerReg.yaml",
        (
            Variant("default", {}, {"TRIGGERS_C": 1, "USE_TAP_C": False, "EVR_CARD_G": False}, False),
            Variant("useTap", {"useTap": True}, {"TRIGGERS_C": 1, "USE_TAP_C": True, "EVR_CARD_G": False}, True),
        ),
    ),
}

# python name -> {"vhdl": name, "yaml": name}; a missing source key means the
# name is the same in that source.
NAME_MAPS: Dict[str, Dict[str, Dict[str, str]]] = {
    "EvrV2TriggerReg": {
        # The RTL record names the trigger enable "enabled" and the source
        # select "channel"; the CPSW map calls the trigger enable "Enable".
        "EnableTrig": {"vhdl": "enabled", "yaml": "Enable"},
        "Source": {"vhdl": "channel"},
        "Polarity": {"vhdl": "polarity"},
        "ComplEn": {"vhdl": "complEn"},
        "ComplAnd": {"vhdl": "complAnd"},
        "Delay": {"vhdl": "delay"},
        "Width": {"vhdl": "width"},
        "DelayTap": {"vhdl": "delayTap"},
        "DelayTapReadback": {"vhdl": "delay_rd"},
    },
}

# (block, field, kind) -> filed issue link. field has the [i] index stripped.
ALLOWLIST: Dict[Tuple[str, str, str], str] = {
    # The Python variables sit one bit above the RTL decode and the YAML map.
    ("EvrV2TriggerReg", "ComplEn", "bitOffset"): "https://github.com/slaclab/lcls-timing-core/issues/214",
    ("EvrV2TriggerReg", "ComplAnd", "bitOffset"): "https://github.com/slaclab/lcls-timing-core/issues/214",
}


def _mode(readable: bool, writable: bool) -> str:
    if readable and writable:
        return "RW"
    return "RO" if readable else "WO"


def from_vhdl(decode, block: str) -> List[RegField]:
    """Adapt a vhdl_registers.Decode into RegFields.

    A loop index is kept as the element index only when the same target is
    decoded more than once, so a one-trigger decode lines up with scalar
    Python variables and a many-element decode lines up with Name[i].
    """
    counts: Dict[str, int] = {}
    for field in decode.fields:
        counts[field.target] = counts.get(field.target, 0) + 1
    return [
        RegField(
            block=block,
            name=field.target,
            index=field.index if counts[field.target] > 1 else None,
            byte_offset=field.byte_offset,
            bit_offset=field.bit_offset,
            bit_size=field.width,
            mode=_mode(field.readable, field.writable),
            source="vhdl",
            line=field.line,
            readable=field.readable,
            writable=field.writable,
        )
        for field in decode.fields
    ]


def from_yaml(fields, block: str) -> List[RegField]:
    """Adapt yaml_maps.YamlField records into RegFields."""
    return [
        RegField(
            block=block,
            name=field.name,
            index=field.index,
            byte_offset=field.byte_offset,
            bit_offset=field.bit_offset,
            bit_size=field.bit_size,
            mode=field.mode,
            source="yaml",
            line=0,
            readable=True,
            writable=field.mode == "RW",
        )
        for field in fields
    ]


def mode_agrees(declared: RegField, vhdl: RegField) -> bool:
    """Capability rule between a declared access mode and the RTL decode.

    RW needs the RTL readable and writable, RO needs it readable and not
    writable, and WO needs it writable. Two non-RTL sources (Python against
    YAML) compare by plain equality.
    """
    if declared.source != "vhdl" and vhdl.source != "vhdl":
        return declared.mode == vhdl.mode
    if declared.source == "vhdl":
        declared, vhdl = vhdl, declared
    if declared.mode == "RW":
        return vhdl.readable and vhdl.writable
    if declared.mode == "RO":
        return vhdl.readable and not vhdl.writable
    return vhdl.writable


def _label(field: RegField) -> str:
    return field.name if field.index is None else f"{field.name}[{field.index}]"


def _element(field: RegField) -> int:
    return field.index or 0


def _canonical(source: str, name: str, python_names, reverse) -> str:
    if source == "python" or name in python_names:
        return name
    return reverse.get(source, {}).get(name, name)


def _position_kind(a: RegField, b: RegField) -> Optional[str]:
    if a.abs_bit == b.abs_bit:
        return None
    return "offset" if a.word_byte != b.word_byte else "bitOffset"


def compare(block: str, python, vhdl, yaml, name_map: Dict[str, Dict[str, str]]) -> List[Drift]:
    """Return the drifts between the sources that are present.

    None means the source is not compared; an empty list means it is compared
    and holds nothing, so every field of the other sources is missing there.
    """
    sources = {"python": python, "vhdl": vhdl, "yaml": yaml}
    present = [s for s in SOURCES if sources[s] is not None]
    python_names = {f.name for f in (python or [])}
    reverse: Dict[str, Dict[str, str]] = {"vhdl": {}, "yaml": {}}
    for python_name, names in name_map.items():
        for source, other in names.items():
            reverse[source][other] = python_name

    grouped: Dict[str, Dict[str, Dict[int, RegField]]] = {}
    for source in present:
        for field in sources[source]:
            canonical = _canonical(source, field.name, python_names, reverse)
            grouped.setdefault(canonical, {}).setdefault(source, {})[_element(field)] = field

    # Fields that exist in one source only, used to hint at an unmapped rename.
    lonely: Dict[str, List[RegField]] = {s: [] for s in present}
    for canonical, by_source in grouped.items():
        if len(by_source) == 1:
            source = next(iter(by_source))
            lonely[source].extend(by_source[source].values())

    found: Dict[Tuple[str, str], List[Tuple[int, str, str]]] = {}

    def record(field: str, kind: str, element: int, detail: str, total: int) -> None:
        found.setdefault((field, kind), []).append((element, detail, total))

    for canonical, by_source in grouped.items():
        elements = sorted({e for per in by_source.values() for e in per})
        for element in elements:
            have = {s: by_source[s][element] for s in present if s in by_source and element in by_source[s]}
            for source in present:
                if source in have:
                    continue
                other = next(iter(have.values()))
                hint = ""
                for candidate in lonely[source]:
                    if (candidate.abs_bit == other.abs_bit and candidate.bit_size == other.bit_size
                            and candidate.source != other.source):
                        hint = (
                            f"; same position as {_label(candidate)}: add a name-map entry "
                            "if this is the same register"
                        )
                        break
                record(
                    canonical,
                    f"missing-in-{source}",
                    element,
                    f"{_label(other)} is in {other.source} at bit {other.abs_bit} "
                    f"(width {other.bit_size}) but not in {source}{hint}",
                    len(elements),
                )
            names = sorted(have)
            for i, first in enumerate(names):
                for second in names[i + 1:]:
                    a, b = have[first], have[second]
                    kind = _position_kind(a, b)
                    if kind is not None:
                        record(canonical, kind, element,
                               f"{_label(a)} {first} bit {a.abs_bit} (word {a.word_byte:#x} bit {a.bit_in_word}) "
                               f"vs {second} bit {b.abs_bit} (word {b.word_byte:#x} bit {b.bit_in_word})",
                               len(elements))
                    if a.bit_size is not None and b.bit_size is not None and a.bit_size != b.bit_size:
                        record(canonical, "bitSize", element,
                               f"{_label(a)} {first} width {a.bit_size} vs {second} width {b.bit_size}",
                               len(elements))
                    if not mode_agrees(a, b):
                        record(canonical, "mode", element,
                               f"{_label(a)} {first} mode {a.mode} vs {second} mode {b.mode}",
                               len(elements))

    drifts = []
    for (field, kind), entries in found.items():
        element, detail, total = sorted(entries)[0]
        differing = len({e for e, _, _ in entries})
        suffix = f" (first differing element {element} of {total}, {differing} differ)" if total > 1 else ""
        drifts.append(Drift(block, field, kind, detail + suffix))
    return sorted(drifts, key=lambda d: (d.block, d.field, d.kind))


def validate_allowlist(allowlist, require_filed: bool = REQUIRE_FILED_ISSUES) -> None:
    """Reject entries that could not prove a specific, linked drift."""
    for key, value in allowlist.items():
        if not (isinstance(key, tuple) and len(key) == 3 and all(isinstance(k, str) for k in key)):
            raise ValueError(f"allowlist key {key!r} must be (block, field, kind)")
        block, field, kind = key
        if not block or not field:
            raise ValueError(f"allowlist key {key!r} needs a block and a field")
        if kind not in KINDS:
            raise ValueError(f"allowlist key {key!r} has kind {kind!r}, expected one of {KINDS}")
        if value == PENDING_ISSUE:
            if require_filed:
                raise ValueError(f"allowlist entry {key!r} is still {PENDING_ISSUE}; link a filed issue")
            continue
        if not isinstance(value, str) or not ISSUE_URL_RE.match(value):
            raise ValueError(f"allowlist entry {key!r} must link a slaclab/lcls-timing-core issue, got {value!r}")


def verdict(drifts, allowlist, blocks=None) -> List[str]:
    """Return the reasons the drifts fail the allowlist; empty means pass.

    The stale direction is judged only over blocks (all blocks of the
    allowlist when None), so a per-block run never reports another block's
    entry as stale.
    """
    reasons = []
    seen = set()
    for drift in drifts:
        key = (drift.block, drift.field, drift.kind)
        seen.add(key)
        if key not in allowlist:
            reasons.append(f"unlisted drift: {key}: {drift.detail}")
    for key in sorted(allowlist):
        if blocks is not None and key[0] not in blocks:
            continue
        if key not in seen:
            reasons.append(f"listed in ALLOWLIST but no longer drifts; remove the entry: {key}")
    return reasons
