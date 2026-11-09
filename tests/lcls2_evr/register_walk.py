#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Walking-one register walks of the EVR V2 AXI-Lite blocks and the PyRogue comparison.

This is a helper module: it holds no cocotb entrypoints. The walk reads each
register word, writes 0, then writes ``1 << b`` for every bit ``b``, reads the
word back, waits for the registered configuration output to settle, and
records which field of the decoded configuration vector changed. The result is
the bit map the RTL actually implements: which bits are read-write, which
configuration field and field bit each one drives, what the word reads after
reset, and what reads back.

The layout tables ``TRIGREG_LAYOUT``, ``CHANREG_LAYOUT`` and ``AXI_LAYOUT``
state that bit map per word. Every walk in the regression asserts that the
observed map equals the table built from them, so the tables are observations
of the simulated RTL, not copies of the PyRogue files.

``compare_with_pyrogue`` then lines the observed map up against the variables
read from a PyRogue file by ``tests.common.pyrogue_ast`` and reports every
disagreement bit for bit.
"""

import re
from typing import Dict, List, NamedTuple, Optional, Tuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiResp

from tests.common import evr_model, pyrogue_ast, timing_model
from tests.common.regression_utils import sample_after_tpd

WORD_BITS = 32
WORD_BYTES = 4
CLOCK_NS = 10
RESET_CLOCKS = 3
SETTLE_CLOCKS = 2
PROPAGATION_NS = 2

TRIGGER_GROUP_TIGHT = 256
TRIGGER_GROUP_CARD = 4096
AXI_CHANNEL_BASE = 0x20
AXI_CHANNEL_STRIDE = 32
AXI_GLOBAL_COUNT = 0x1A8
AXI_DECODE_BITS = 9


class LayoutField(NamedTuple):
    """One field of a register word: ``condition`` names the generic that gates it."""

    name: str
    lsb: int
    width: int
    mode: str
    condition: Optional[str]


class BitInfo(NamedTuple):
    """What one bit of a register word does."""

    group: int
    field: str
    field_bit: int
    mode: str


class WordWalk(NamedTuple):
    """Result of the walking-one walk of one register word."""

    address: int
    reset_value: int
    readback_mask: int
    bit_fields: Dict[int, Tuple[int, str, int]]


class Drift(NamedTuple):
    """One disagreement between the observed RTL map and a PyRogue file."""

    kind: str
    python_name: str
    detail: str
    severity: str


def _field(name, lsb, width, mode="RW", condition=None):
    return LayoutField(name, lsb, width, mode, condition)


TRIGREG_LAYOUT = {
    0x00: (
        _field("channel", 0, 4),
        _field("polarity", 16, 1),
        _field("complEn", 28, 1),
        _field("complAnd", 29, 1),
        _field("enabled", 31, 1),
    ),
    0x04: (_field("delay", 0, 28),),
    0x08: (_field("width", 0, 28),),
    0x0C: (
        _field("delayTap", 0, 6, "RW", "USE_TAP"),
        _field("delay_rd", 16, 6, "RO", "USE_TAP"),
    ),
}

CHANREG_LAYOUT = {
    0x00: (
        _field("enabled", 0, 1),
        _field("bsaEnabled", 1, 1, "RW", "DMA_ENABLE"),
        _field("dmaEnabled", 2, 1, "RW", "DMA_ENABLE"),
    ),
    0x04: (
        _field("rateSel", 0, 13),
        _field("destSel", 13, 19),
    ),
    0x08: (_field("eventCount", 0, 32, "RO"),),
    0x0C: (
        _field("bsaActiveDelay", 0, 20, "RW", "DMA_ENABLE"),
        _field("bsaActiveSetup", 20, 6, "RW", "DMA_ENABLE"),
    ),
    0x10: (_field("bsaActiveWidth", 0, 20, "RW", "DMA_ENABLE"),),
}

# Words that are not part of a channel: the per-channel words of EvrV2Axi
# repeat CHANREG_LAYOUT at AXI_CHANNEL_BASE with a stride of AXI_CHANNEL_STRIDE.
AXI_LAYOUT = {
    0x000: (_field("irqEnable", 0, 1, "RW", "DMA_ENABLE"),),
    0x004: (_field("irqReq", 0, 1, "RO", "DMA_ENABLE"),),
    0x00C: (_field("gtxDebug", 0, 8, "RO", "DMA_ENABLE"),),
    0x010: (_field("countReset", 0, 1),),
    0x014: (_field("trigSel", 0, 1),),
    0x018: (_field("dmaFullThr", 0, 24, "RW", "DMA_ENABLE"),),
    AXI_GLOBAL_COUNT: (_field("globalCount", 0, 32, "RO"),),
}

# Fields of the register block outputs of EvrV2Axi that sit beside channelConfig.
AXI_EXTRA_CONFIG_FIELDS = (
    ("irqEnable", 1, 1),
    ("countReset", 1, 1),
    ("trigSel", 1, 1),
    ("dmaFullThr", 24, 1),
)


def group_size(card):
    """Return the byte stride between trigger or channel register groups."""
    return TRIGGER_GROUP_CARD if card else TRIGGER_GROUP_TIGHT


def layout_bit_map(layout, *, base=0, stride=0, count=1, conditions=()):
    """Return ``{(address, bit): BitInfo}`` for ``count`` groups of ``layout``.

    Fields whose condition is not in ``conditions`` are left out, which is how
    a generic that is false removes its registers.
    """
    result = {}
    for group in range(count):
        for word, fields in layout.items():
            for entry in fields:
                if entry.condition is not None and entry.condition not in conditions:
                    continue
                for bit in range(entry.width):
                    result[(base + group * stride + word, entry.lsb + bit)] = BitInfo(
                        group, entry.name, bit, entry.mode
                    )
    return result


def trigreg_bit_map(triggers, card, tap, *, base=0):
    """Return the expected bit map of EvrV2TrigReg for the generic values."""
    return layout_bit_map(
        TRIGREG_LAYOUT,
        base=base,
        stride=group_size(card),
        count=triggers,
        conditions={"USE_TAP"} if tap else set(),
    )


def chanreg_bit_map(channels, card, dma, *, base=0):
    """Return the expected bit map of EvrV2ChannelReg for the generic values."""
    return layout_bit_map(
        CHANREG_LAYOUT,
        base=base,
        stride=group_size(card),
        count=channels,
        conditions={"DMA_ENABLE"} if dma else set(),
    )


def axi_bit_map(channels, dma):
    """Return the expected bit map of the EvrV2Axi register block."""
    conditions = {"DMA_ENABLE"} if dma else set()
    result = layout_bit_map(AXI_LAYOUT, conditions=conditions)
    result.update(
        layout_bit_map(
            CHANREG_LAYOUT,
            base=AXI_CHANNEL_BASE,
            stride=AXI_CHANNEL_STRIDE,
            count=channels,
            conditions=conditions,
        )
    )
    return result


def word_addresses(layout, *, base=0, stride=0, count=1, conditions=()):
    """Return the sorted addresses of every word that holds at least one enabled field."""
    return sorted({address for address, _ in layout_bit_map(layout, base=base, stride=stride, count=count, conditions=conditions)})


def config_bit_table(fields, element_bits, count, extra=()):
    """Map each bit of a flattened configuration vector to ``(group, field, field_bit)``.

    ``count`` elements of ``fields`` come first, element ``i`` at bit
    ``i * element_bits`` (the order the wrappers flatten them); ``extra``
    fields follow as group 0.
    """
    table = {}
    layout = timing_model.field_layout(fields)
    for group in range(count):
        for name, (offset, width, _) in layout.items():
            for bit in range(width):
                table[group * element_bits + offset + bit] = (group, name, bit)
    start = count * element_bits
    for name, (offset, width, _) in timing_model.field_layout(extra).items():
        for bit in range(width):
            table[start + offset + bit] = (0, name, bit)
    return table


def trigger_config_bits(triggers):
    return config_bit_table(evr_model.TRIGGER_CONFIG_FIELDS, evr_model.TRIGGER_CONFIG_BITS, triggers)


def channel_config_bits(channels, extra=()):
    return config_bit_table(evr_model.CHANNEL_CONFIG_FIELDS, evr_model.CHANNEL_CONFIG_BITS, channels, extra)


def flat_value(handle, label):
    """Return a flat output as an integer after checking that no bit is unresolved."""
    value = handle.value
    assert value.is_resolvable, f"{label} carries unresolved bits: {value}"
    return int(value)


async def start_axi_master(dut):
    """Reset the block, start the clock, release reset, and return ``(master, clock_task)``.

    The order matters on cocotb 2.x: reset is driven and the master built
    (which drives the valids low) before the clock starts.
    """
    dut.axilRst.value = 1
    master = AxiLiteMaster(
        AxiLiteBus.from_prefix(dut, "S_AXI"),
        dut.axilClk,
        dut.axilRst,
        reset_active_level=True,
    )
    await Timer(1, unit="ns")
    clock_task = cocotb.start_soon(Clock(dut.axilClk, CLOCK_NS, unit="ns").start(start_high=False))
    for _ in range(RESET_CLOCKS):
        await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)
    dut.axilRst.value = 0
    for _ in range(RESET_CLOCKS):
        await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)
    return master, clock_task


def make_settle(dut):
    """Return a coroutine function that waits for the registered outputs to settle."""

    async def settle():
        for _ in range(SETTLE_CLOCKS):
            await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)

    return settle


async def read_word(master, address, *, expect=AxiResp.OKAY):
    """Read one 32-bit word, assert the response, and return the value."""
    result = await master.read(address, WORD_BYTES)
    assert result.resp == expect, f"read of 0x{address:03X} answered {result.resp!r}, expected {expect!r}"
    return int.from_bytes(result.data, "little")


async def write_word(master, address, value, *, expect=AxiResp.OKAY):
    """Write one 32-bit word and assert the response."""
    result = await master.write(address, value.to_bytes(WORD_BYTES, "little"))
    assert result.resp == expect, f"write of 0x{address:03X} answered {result.resp!r}, expected {expect!r}"


def _changed_positions(before, after):
    difference = before ^ after
    return [position for position in range(difference.bit_length()) if (difference >> position) & 1]


async def walk_word(master, address, read_config, settle, config_bits, *, ignore=("loadTap",)):
    """Walk one register word and return what it does.

    ``read_config()`` returns the flattened configuration vector, ``settle()``
    waits for it to follow a write, ``config_bits`` maps vector positions to
    ``(group, field, field_bit)``, and ``ignore`` names fields that pulse and
    so cannot be sampled after a fixed wait. The word is left holding 0.

    Raises AssertionError when one written bit moves more than one
    configuration bit or when a write changes any other bit of the read-back.
    """
    reset_value = await read_word(master, address)
    await write_word(master, address, 0)
    await settle()
    zero_config = read_config()
    baseline = await read_word(master, address)
    readback_mask = 0
    bit_fields = {}
    for bit in range(WORD_BITS):
        await write_word(master, address, 1 << bit)
        observed = await read_word(master, address)
        await settle()
        moved = observed ^ baseline
        assert moved & ~(1 << bit) == 0, (
            f"word 0x{address:03X}: writing bit {bit} changed read-back bits 0x{moved & ~(1 << bit):08X} as well"
        )
        if moved >> bit & 1:
            readback_mask |= 1 << bit
        changed = [
            config_bits[position]
            for position in _changed_positions(zero_config, read_config())
            if config_bits[position][1] not in ignore
        ]
        assert len(changed) <= 1, f"word 0x{address:03X}: writing bit {bit} moved {len(changed)} configuration bits: {changed}"
        if changed:
            bit_fields[bit] = changed[0]
    await write_word(master, address, 0)
    return WordWalk(address, reset_value, readback_mask, bit_fields)


async def read_only_mask(master, address, drive, ones):
    """Return the bits of a word that follow a driven status input and ignore writes.

    ``drive(value)`` sets the status input and ``ones`` is the all-ones value
    of that input. The word is written 0 first so that read-write bits read 0.
    Raises AssertionError when a write of all ones changes a bit that follows
    the input.
    """
    await write_word(master, address, 0)
    drive(ones)
    await Timer(1, unit="ns")
    high = await read_word(master, address)
    drive(0)
    await Timer(1, unit="ns")
    low = await read_word(master, address)
    mask = high ^ low
    await write_word(master, address, 0xFFFFFFFF)
    after_write = await read_word(master, address)
    assert after_write & mask == 0, (
        f"word 0x{address:03X}: a write changed read-only bits 0x{after_write & mask:08X}"
    )
    await write_word(master, address, 0)
    return mask


def rtl_bit_map(walks, read_only=()):
    """Return the observed ``{(address, bit): BitInfo}`` of the walks.

    ``read_only`` is an iterable of ``(address, mask, group, field)`` from
    ``read_only_mask``; the field bit counts from the lowest set bit of the
    mask, which must be contiguous.
    """
    result = {}
    for walk in walks:
        for bit, (group, field, field_bit) in walk.bit_fields.items():
            result[(walk.address, bit)] = BitInfo(group, field, field_bit, "RW")
    for address, mask, group, field in read_only:
        bits = [bit for bit in range(WORD_BITS) if mask >> bit & 1]
        if not bits:
            continue
        assert bits == list(range(bits[0], bits[-1] + 1)), f"read-only mask 0x{mask:08X} is not contiguous"
        for field_bit, bit in enumerate(bits):
            result[(address, bit)] = BitInfo(group, field, field_bit, "RO")
    return result


def _ranges(bits):
    ordered = sorted(bits)
    parts = []
    start = previous = ordered[0]
    for bit in ordered[1:]:
        if bit != previous + 1:
            parts.append((start, previous))
            start = bit
        previous = bit
    parts.append((start, previous))
    return ", ".join(f"{low}" if low == high else f"{low}..{high}" for low, high in parts)


def _base_name(name):
    return re.sub(r"\[\d+\]$", "", name)


def compare_with_pyrogue(
    rtl_map,
    variables,
    name_map,
    *,
    base=0,
    enabled_conditions=(),
    window=None,
    severity=None,
):
    """Return the disagreements between the observed RTL map and PyRogue variables.

    ``variables`` come from ``pyrogue_ast.read_remote_variables``; a variable
    whose enclosing condition is not in ``enabled_conditions`` is not
    instantiated by the device and is skipped. ``name_map`` maps the PyRogue
    name (without ``[i]``) to the RTL field name. ``base`` is added to every
    PyRogue offset to give the RTL address, and ``window`` is a
    ``(low, high)`` address range that limits which RTL bits are considered.
    ``severity(kind, python_name)`` returns the tag of an entry, "defect" by
    default. An RTL field no variable maps to is reported as ``(rtl <field>)``.

    Entries of an array variable are merged into one entry per kind. The
    kinds are python_bits_without_rtl (a PyRogue bit no RTL field occupies),
    rtl_bits_without_python (a read-write RTL bit no variable covers),
    field_mismatch (a PyRogue bit sits on a different RTL field than its name
    maps to), width_mismatch (the PyRogue variables of one field instance add
    up to another width than the RTL field), and mode_mismatch.
    """
    tag = severity or (lambda kind, name: "defect")
    rtl = {
        key: info
        for key, info in rtl_map.items()
        if window is None or window[0] <= key[0] < window[1]
    }
    instance_width: Dict[Tuple[int, int, str], int] = {}
    for (address, bit), info in rtl.items():
        key = (address, bit - info.field_bit, info.field)
        instance_width[key] = instance_width.get(key, 0) + 1

    active = [
        var
        for var in variables
        if var.condition is None or var.condition in enabled_conditions
    ]
    notes: Dict[Tuple[str, str], List[str]] = {}
    covered = set()
    owners: Dict[Tuple[int, int, str], List[pyrogue_ast.RemoteVar]] = {}

    def note(kind, name, text):
        notes.setdefault((kind, name), []).append(text)

    for var in active:
        name = _base_name(var.name)
        field = name_map[name]
        missing: Dict[int, List[int]] = {}
        wrong: Dict[Tuple[int, str], List[int]] = {}
        bad_mode: Dict[Tuple[int, str], List[int]] = {}
        for position in pyrogue_ast.absolute_bits(var):
            address = base + (position // WORD_BITS) * WORD_BYTES
            bit = position % WORD_BITS
            covered.add((address, bit))
            info = rtl.get((address, bit))
            if info is None:
                missing.setdefault(address, []).append(bit)
                continue
            if info.field != field:
                wrong.setdefault((address, info.field), []).append(bit)
                continue
            instance = (address, bit - info.field_bit, info.field)
            if var not in owners.setdefault(instance, []):
                owners[instance].append(var)
            if info.mode != var.mode:
                bad_mode.setdefault((address, info.mode), []).append(bit)
        for address, bits in missing.items():
            note(
                "python_bits_without_rtl",
                name,
                f"word 0x{address:03X} bits {_ranges(bits)} have no RTL field",
            )
        for (address, other), bits in wrong.items():
            note(
                "field_mismatch",
                name,
                f"word 0x{address:03X} bits {_ranges(bits)} are RTL field {other}, not {field}",
            )
        for (address, rtl_mode), bits in bad_mode.items():
            note(
                "mode_mismatch",
                name,
                f"word 0x{address:03X} bits {_ranges(bits)} are {rtl_mode} in the RTL and {var.mode} in PyRogue",
            )

    for instance, vars_here in owners.items():
        total = sum(var.bit_size for var in vars_here)
        if total != instance_width[instance]:
            name = _base_name(vars_here[0].name)
            note(
                "width_mismatch",
                name,
                f"word 0x{instance[0]:03X} field {instance[2]}: PyRogue {total} bits against RTL {instance_width[instance]} bits",
            )

    owner_name = {}
    for var in active:
        owner_name.setdefault(name_map[_base_name(var.name)], _base_name(var.name))
    uncovered: Dict[Tuple[int, int, str], List[int]] = {}
    for (address, bit), info in sorted(rtl.items()):
        if info.mode == "RW" and (address, bit) not in covered:
            uncovered.setdefault((address, bit - info.field_bit, info.field), []).append(bit)
    for (address, _, field), bits in uncovered.items():
        note(
            "rtl_bits_without_python",
            owner_name.get(field, f"(rtl {field})"),
            f"RTL field {field} at word 0x{address:03X} bits {_ranges(bits)} has no PyRogue variable",
        )

    drifts = []
    for (kind, name), texts in notes.items():
        detail = texts[0] if len(texts) == 1 else f"{texts[0]} (and {len(texts) - 1} more)"
        drifts.append(Drift(kind, name, detail, tag(kind, name)))
    return drifts
