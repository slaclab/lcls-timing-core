#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1Reg register file test over AXI-Lite through a flat-port wrapper.

Test methodology:
    Sweep: the version words and the control register walk; every writable
        word (the words named by the write decode of EvrV1Reg.vhd) with
        USE_WSTRB_G false and true, walked bit by bit; the output map
        words with explicit byte strobes; the interrupt clear word and the
        data-buffer control pulses.
    Stimulus: a cocotbext-axi AxiLiteMaster on the S_AXI port, 10 ns axilClk,
        reset held for three clocks. The build information is fixed by the
        wrapper to the firmware version 0xA1B2C3D4. Reads of EvrV1Reg wait
        for a latch-latency counter, so every blocking master read is
        bounded by the cocotb timeout. Byte strobes the master cannot form
        (0xC on an aligned address) are driven directly on the S_AXI
        channels. The walk reads each writable word, writes 0, then writes
        1 << b for every bit b and reads the word back.
    Checks: the offset tables WRITE_WORDS and READ_WORDS equal the integer
        arms of the write and read decode parsed from EvrV1Reg.vhd, so a new
        arm turns the test red; every writable word resets to 0; the
        read-back mask, and the configuration output bit each written bit
        drives (pulsed outputs included, through a per-cycle watcher), equal
        the table built from the decode as measured under GHDL; every write
        presents its data and decoded address on the event RAM and data
        buffer buses; the version words read the values the read decode
        builds from the firmware version. Every checked output is resolvable
        after reset release.
    Timing: 10 ns axilClk; a register write reaches its configuration output
        after the clock edges that follow the write response.
    Propagation sampling: the registers update after TPD_G (1 ns), so every
        configuration output is sampled 2 ns after a rising edge.
"""

import os
from pathlib import Path
import re

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiResp
import pytest

from tests.common.regression_utils import (
    REPO_ROOT,
    parameter_case,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-I/wrappers/EvrV1RegWrapper.vhd"
RTL_FILE = REPO_ROOT / "LCLS-I/evr/EvrV1Reg.vhd"
WRITE_CASE = "case wrPntr is"
READ_CASE = "case rdPntr is"

USE_WSTRB = os.getenv("USE_WSTRB_G", "false") == "true"

PULSE_FIRST_WORD = 128
PULSE_WORDS_PER_CHANNEL = 4
PULSE_PORTS = ("configPulseControl", "configPulsePrescale", "configPulseDelay", "configPulseWidth")
OUTPUT_MAP_FIRST_WORD = 272
OUTPUT_MAP_WORDS = 6
FULL_WORD = 0xFFFFFFFF
BUS_WRITE_TIMEOUT_CLOCKS = 64

# Offsets of the decoded words, as the integer arms of the decode in
# EvrV1Reg.vhd; test_offset_tables_match_rtl_case_arms parses them back out.
WRITE_WORDS = (
    1, 2, 3, 4, 5, 8, 19,
    40, 41, 42, 43, 44,
    *range(128, 176),
    *range(272, 278),
)
READ_WORDS = (
    0, 1, 2, 3, 4, 5, 8, 11, 12, 19,
    23, 24, 25, 26, 27, 28, 29, 30,
    40, 41, 42, 43, 44,
    *range(128, 176),
    *range(272, 278),
)
READ_RANGES = ((512, 1023), (4096, 5119), (5120, 6143))

CLOCK_NS = 10
RESET_CLOCKS = 3
SETTLE_CLOCKS = 4
PROPAGATION_NS = 2
WORD_BITS = 32
WORD_BYTES = 4

FW_VERSION = 0xA1B2C3D4
# Word 11 is the fixed prefix 0001 1111 above the low 24 bits of the firmware
# version; word 12 is the firmware version with its bytes reversed.
VERSION_WORD = 0x1F000000 | (FW_VERSION & 0xFFFFFF)
VERSION_SWAPPED_WORD = int.from_bytes(FW_VERSION.to_bytes(4, "big"), "little")

IRQ_FLAG_WORD = 2
DBUS_WORD = 8
# Measured under GHDL: clocks the clear and data buffer outputs stay high.
IRQ_CLEAR_CYCLES = 2
DBENA_CYCLES = 4
DBDIS_CYCLES = 3

CONTROL_WORD = 1
CONTROL_LATCH_BIT = 10
CONTROL_MAP_PAGE_BIT = 8
CONTROL_ENABLE_BIT = 31

# Flat configuration outputs of the wrapper and the width of each.
CONFIG_PORTS = (
    ("configLatchTs", 1),
    ("configPulseControl", 384),
    ("configPulsePrescale", 384),
    ("configPulseDelay", 384),
    ("configPulseWidth", 384),
    ("configTsFifoRdEna", 1),
    ("configEventRamData", 32),
    ("configEventRamCs", 8),
    ("configEventRamAddr", 8),
    ("configEventRamWe", 8),
    ("configMapRamPage", 1),
    ("configEvrEnable", 1),
    ("configOutputMap", 192),
    ("configUSecDivider", 32),
    ("configIntControl", 32),
    ("configDbena", 1),
    ("configDbdis", 1),
    ("configDben", 1),
    ("configDbRdAddr", 9),
    ("configIrqClr", 32),
    ("configIntEventEn", 1),
    ("configExtEventEn", 1),
    ("configIntEventCode", 8),
    ("configExtEventCode", 8),
    ("configIntEventCount", 32),
)


def snapshot(dut):
    """Return every flat configuration output as an integer after checking it is resolvable."""
    result = {}
    for name, _ in OBSERVED_PORTS:
        value = getattr(dut, name).value
        assert value.is_resolvable, f"{name} carries unresolved bits: {value}"
        result[name] = int(value)
    return result


# Output ports that are not part of the configuration record.
IRQ_PORTS = (
    ("irqEnable", 1),
    ("irqReq", 1),
)
OBSERVED_PORTS = CONFIG_PORTS + IRQ_PORTS

# Every write presents its data and the decoded address bits on these outputs
# whatever word it targets, so they are left out of the per-register field maps.
BUS_PORTS = (
    "configEventRamData",
    "configEventRamAddr",
    "configEventRamCs",
    "configEventRamWe",
    "configDbRdAddr",
)


def changed_ports(before, after, *, ignore=BUS_PORTS):
    """Return the names of the configuration outputs that differ between two snapshots."""
    return sorted(name for name in before if name not in ignore and before[name] != after[name])


async def start_axi_master(dut):
    """Reset the block, start the clock, release reset, and return ``(master, clock_task)``.

    The order matters on cocotb 2.x: reset is driven and the master built
    (which drives the valids low) before the clock starts.
    """
    dut.axilRst.value = 1
    for name in ("S_AXI_AWADDR", "S_AXI_ARADDR", "S_AXI_WDATA", "S_AXI_WSTRB", "S_AXI_AWPROT", "S_AXI_ARPROT"):
        getattr(dut, name).value = 0
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
    return master, clock_task


async def watch_config(dut, history):
    """Lifetime agent: append the configuration outputs after every clock edge until cancelled.

    Propagation sampling: each snapshot is taken 2 ns after the edge.
    """
    while True:
        await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)
        history.append(snapshot(dut))


def moved_ports(baseline, history):
    """Return the configuration outputs that left ``baseline`` in any recorded cycle."""
    seen = set()
    for entry in history:
        seen.update(changed_ports(baseline, entry))
    return sorted(seen)


async def settle(dut, clocks=SETTLE_CLOCKS):
    """Wait for the registered outputs to follow a write."""
    for _ in range(clocks):
        await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)


async def read_word(master, word, *, expect=AxiResp.OKAY):
    """Read one 32-bit word by index, assert the response, and return the value."""
    result = await master.read(word * WORD_BYTES, WORD_BYTES)
    assert result.resp == expect, f"read of word {word} answered {result.resp!r}, expected {expect!r}"
    return int.from_bytes(result.data, "little")


async def write_word(master, word, value, *, expect=AxiResp.OKAY):
    """Write one 32-bit word by index and assert the response."""
    result = await master.write(word * WORD_BYTES, value.to_bytes(WORD_BYTES, "little"))
    assert result.resp == expect, f"write of word {word} answered {result.resp!r}, expected {expect!r}"


def case_arms(header):
    """Return the integer ``when`` labels and ranges of the case statement opened by ``header``.

    The case statement is read out of EvrV1Reg.vhd as text: nested case
    statements are skipped by tracking the nesting depth, and ``when others``
    carries no integer, so it is not returned.
    """
    lines = RTL_FILE.read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if header in line)
    depth = 1
    words = []
    ranges = []
    for line in lines[start + 1:]:
        text = line.strip()
        if re.match(r"case\b.*\bis$", text):
            depth += 1
        elif re.match(r"end case\b", text):
            depth -= 1
            if depth == 0:
                break
        elif depth == 1:
            match = re.match(r"when\s+(\d+)(?:\s+to\s+(\d+))?\s*=>", text)
            if match is None:
                continue
            if match.group(2) is None:
                words.append(int(match.group(1)))
            else:
                ranges.append((int(match.group(1)), int(match.group(2))))
    return tuple(words), tuple(ranges)


def identity_bits(port, width=WORD_BITS, *, base=0):
    """Map written bit ``b`` to bit ``base + b`` of ``port``."""
    return {bit: (port, base + bit) for bit in range(width)}


def expected_word(word):
    """Return ``(read-back mask, {written bit: (port, port bit)})`` of one writable word, as measured."""
    control_readback = FULL_WORD & ~(1 << CONTROL_LATCH_BIT)
    fixed = {
        1: (
            control_readback,
            {
                CONTROL_MAP_PAGE_BIT: ("configMapRamPage", 0),
                CONTROL_LATCH_BIT: ("configLatchTs", 0),
                CONTROL_ENABLE_BIT: ("configEvrEnable", 0),
            },
        ),
        # Word 2 reads the interrupt flags, so nothing written reads back.
        2: (0, identity_bits("configIrqClr")),
        3: (FULL_WORD, identity_bits("configIntControl")),
        4: (FULL_WORD, {}),
        # Bit 1 of word 5 reads irqActive, not the written bit.
        5: (FULL_WORD & ~0b10, {0: ("irqEnable", 0)}),
        8: (1 << 12, {15: ("configDbena", 0), 14: ("configDbdis", 0), 12: ("configDben", 0)}),
        19: (FULL_WORD, identity_bits("configUSecDivider")),
        40: (0x1, {0: ("configIntEventEn", 0)}),
        41: (FULL_WORD, identity_bits("configIntEventCount")),
        42: (0xFF, identity_bits("configIntEventCode", 8)),
        43: (0x1, {0: ("configExtEventEn", 0)}),
        44: (0xFF, identity_bits("configExtEventCode", 8)),
    }
    if word in fixed:
        return fixed[word]
    if word >= OUTPUT_MAP_FIRST_WORD:
        if USE_WSTRB:
            # Observed, intent unconfirmed: a full-word write has the strobe 0xF,
            # which neither half accepts when USE_WSTRB_G is true.
            return 0, {}
        pair = word - OUTPUT_MAP_FIRST_WORD
        bits = {}
        for bit in range(16):
            bits[bit] = ("configOutputMap", 16 * (2 * pair + 1) + bit)
            bits[bit + 16] = ("configOutputMap", 16 * (2 * pair) + bit)
        return FULL_WORD, bits
    channel, kind = divmod(word - PULSE_FIRST_WORD, PULSE_WORDS_PER_CHANNEL)
    return FULL_WORD, identity_bits(PULSE_PORTS[kind], base=WORD_BITS * channel)


def moved_bits(baseline, history):
    """Return the sorted ``(port, bit)`` pairs that left ``baseline`` in any recorded cycle."""
    seen = set()
    for entry in history:
        for name in changed_ports(baseline, entry):
            difference = baseline[name] ^ entry[name]
            seen.update((name, bit) for bit in range(difference.bit_length()) if difference >> bit & 1)
    return sorted(seen)


def check_buses(snap, word, value):
    """Assert the event RAM and data buffer buses carry a write's data and decoded address."""
    address = word * WORD_BYTES
    assert snap["configEventRamData"] == value, f"word {word}: event RAM data 0x{snap['configEventRamData']:08X}"
    assert snap["configEventRamAddr"] == (address >> 4) & 0xFF, f"word {word}: event RAM address {snap['configEventRamAddr']}"
    assert snap["configDbRdAddr"] == (address >> 2) & 0x1FF, f"word {word}: data buffer address {snap['configDbRdAddr']}"
    assert snap["configEventRamCs"] == 0, f"word {word}: event RAM select {snap['configEventRamCs']}"
    assert snap["configEventRamWe"] == 0, f"word {word}: event RAM write enable {snap['configEventRamWe']}"


async def raw_write(dut, word, value, strb):
    """Write one word with an explicit byte strobe by driving the S_AXI channels directly.

    The cocotbext-axi master derives the strobe from the address offset and
    the data length, so it cannot present 0xC on an aligned address. Returns
    the write response.
    """
    clock = dut.axilClk
    dut.S_AXI_AWADDR.value = word * WORD_BYTES
    dut.S_AXI_AWPROT.value = 0
    dut.S_AXI_AWVALID.value = 1
    dut.S_AXI_WDATA.value = value
    dut.S_AXI_WSTRB.value = strb
    dut.S_AXI_WVALID.value = 1
    dut.S_AXI_BREADY.value = 1
    address_pending = True
    data_pending = True
    for _ in range(BUS_WRITE_TIMEOUT_CLOCKS):
        await RisingEdge(clock)
        if address_pending and int(dut.S_AXI_AWREADY.value) == 1:
            address_pending = False
            dut.S_AXI_AWVALID.value = 0
        if data_pending and int(dut.S_AXI_WREADY.value) == 1:
            data_pending = False
            dut.S_AXI_WVALID.value = 0
        if not (address_pending or data_pending) and int(dut.S_AXI_BVALID.value) == 1:
            response = AxiResp(int(dut.S_AXI_BRESP.value))
            dut.S_AXI_BREADY.value = 0
            return response
    raise AssertionError(f"write of word {word} with strobe 0x{strb:X} did not complete in {BUS_WRITE_TIMEOUT_CLOCKS} clocks")


async def walk_word(dut, master, word):
    """Walk one writable word; return its reset value, zero read-back, read-back mask and bit map.

    The bit map is ``{written bit: (port, port bit)}`` for the one output bit
    each written bit moves (pulsed outputs included); the word is left at 0.
    Raises AssertionError when a written bit changes another read-back bit or
    moves more than one output bit.
    """
    reset_value = await read_word(master, word)
    await write_word(master, word, 0)
    await settle(dut)
    baseline = snapshot(dut)
    zero_readback = await read_word(master, word)
    readback_mask = 0
    bits = {}
    for bit in range(WORD_BITS):
        history = []
        watcher = cocotb.start_soon(watch_config(dut, history))
        await write_word(master, word, 1 << bit)
        await settle(dut)
        watcher.cancel()
        check_buses(history[-1], word, 1 << bit)
        observed = await read_word(master, word)
        moved = observed ^ zero_readback
        assert moved & ~(1 << bit) == 0, f"word {word}: writing bit {bit} changed read-back bits 0x{moved & ~(1 << bit):08X} as well"
        if moved >> bit & 1:
            readback_mask |= 1 << bit
        changed = moved_bits(baseline, history)
        assert len(changed) <= 1, f"word {word}: writing bit {bit} moved {changed}"
        if changed:
            bits[bit] = changed[0]
        await write_word(master, word, 0)
        await settle(dut)
    return reset_value, zero_readback, readback_mask, bits


async def write_and_watch(dut, master, word, value):
    """Write one word while recording the outputs every cycle; return the history."""
    history = []
    watcher = cocotb.start_soon(watch_config(dut, history))
    await write_word(master, word, value)
    await settle(dut)
    watcher.cancel()
    return history


def high_cycles(history, port):
    """Return the indices of the recorded cycles in which ``port`` is non-zero."""
    return [index for index, entry in enumerate(history) if entry[port] != 0]


def output_map_halves(dut):
    """Return the twelve 16-bit output map entries from the flat output."""
    value = snapshot(dut)["configOutputMap"]
    return [(value >> (16 * index)) & 0xFFFF for index in range(OUTPUT_MAP_WORDS * 2)]


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def evrv1reg_reset_version_and_control(dut):
    """Version words, control register reset, and the control bit walk.

    Propagation sampling: configuration outputs are sampled 2 ns after the
    clock edges that follow each write.
    """
    master, clock_task = await start_axi_master(dut)

    assert await read_word(master, 11) == VERSION_WORD, "word 11 does not hold the fixed prefix and the low 24 version bits"
    assert await read_word(master, 12) == VERSION_SWAPPED_WORD, "word 12 does not hold the byte-reversed version"

    assert await read_word(master, CONTROL_WORD) == 0, "control register does not reset to 0"
    await settle(dut)
    baseline = snapshot(dut)

    expected_outputs = {
        CONTROL_MAP_PAGE_BIT: ["configMapRamPage"],
        CONTROL_LATCH_BIT: ["configLatchTs"],
        CONTROL_ENABLE_BIT: ["configEvrEnable"],
    }
    for bit in range(WORD_BITS):
        await write_word(master, CONTROL_WORD, 0)
        await settle(dut)
        history = []
        watcher = cocotb.start_soon(watch_config(dut, history))
        await write_word(master, CONTROL_WORD, 1 << bit)
        await settle(dut)
        watcher.cancel()
        seen = moved_ports(baseline, history)
        readback = await read_word(master, CONTROL_WORD)
        expected_readback = 0 if bit == CONTROL_LATCH_BIT else 1 << bit
        assert readback == expected_readback, f"control bit {bit} read back 0x{readback:08X}"
        assert seen == expected_outputs.get(bit, []), f"control bit {bit} moved {seen}"
        if bit == CONTROL_LATCH_BIT:
            pulse = sum(entry["configLatchTs"] for entry in history)
            assert pulse == 1, f"latch output was high for {pulse} cycles, expected 1"
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def evrv1reg_walk_writable_words(dut):
    """Every writable word resets to 0, reads back as measured, and drives its output bit.

    Propagation sampling: configuration outputs are sampled 2 ns after the
    clock edges that follow each write.
    """
    master, clock_task = await start_axi_master(dut)
    for word in WRITE_WORDS:
        assert await read_word(master, word) == 0, f"word {word} does not read 0 after reset"
    for word in WRITE_WORDS:
        _, zero_readback, readback_mask, bits = await walk_word(dut, master, word)
        expected_mask, expected_bits = expected_word(word)
        assert zero_readback == 0, f"word {word} reads 0x{zero_readback:08X} after a write of 0"
        assert readback_mask == expected_mask, (
            f"word {word}: read-back mask 0x{readback_mask:08X}, expected 0x{expected_mask:08X}"
        )
        assert bits == expected_bits, f"word {word}: output bits differ from the decode table: {bits}"
    clock_task.cancel()


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def evrv1reg_irq_clear_word(dut):
    """Word 2 pulses the written bits on the clear output, except for 0xFFFFFFFF.

    Observed, intent unconfirmed: a write of 0xFFFFFFFF clears nothing while
    any other value clears its set bits, and word 2 is both the read of the
    interrupt flags and the write of the clear mask.

    Propagation sampling: the clear output is sampled 2 ns after each edge.
    """
    master, clock_task = await start_axi_master(dut)
    history = await write_and_watch(dut, master, IRQ_FLAG_WORD, FULL_WORD)
    assert high_cycles(history, "configIrqClr") == [], "a write of 0xFFFFFFFF reached the clear output"
    for value in (0x0000A5A5, 0x80000001, 0xFFFFFFFE):
        history = await write_and_watch(dut, master, IRQ_FLAG_WORD, value)
        cycles = high_cycles(history, "configIrqClr")
        assert len(cycles) == IRQ_CLEAR_CYCLES, f"clear output was high for {len(cycles)} cycles after 0x{value:08X}"
        assert cycles == list(range(cycles[0], cycles[0] + IRQ_CLEAR_CYCLES)), "clear cycles are not consecutive"
        assert all(history[index]["configIrqClr"] == value for index in cycles), f"clear output differs from 0x{value:08X}"
    assert await read_word(master, IRQ_FLAG_WORD) == 0, "word 2 does not read the interrupt flags"
    clock_task.cancel()


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def evrv1reg_dbus_control_pulses(dut):
    """Word 8 bits 15 and 14 pulse dbena and dbdis, bit 12 is a level.

    Propagation sampling: the outputs are sampled 2 ns after each edge.
    """
    master, clock_task = await start_axi_master(dut)
    history = await write_and_watch(dut, master, DBUS_WORD, 1 << 15)
    enable = high_cycles(history, "configDbena")
    assert len(enable) == DBENA_CYCLES and enable == list(range(enable[0], enable[0] + DBENA_CYCLES)), f"dbena cycles {enable}"
    assert high_cycles(history, "configDbdis") == [], "dbena write moved dbdis"
    history = await write_and_watch(dut, master, DBUS_WORD, 1 << 14)
    disable = high_cycles(history, "configDbdis")
    assert len(disable) == DBDIS_CYCLES and disable == list(range(disable[0], disable[0] + DBDIS_CYCLES)), f"dbdis cycles {disable}"
    assert high_cycles(history, "configDbena") == [], "dbdis write moved dbena"
    history = await write_and_watch(dut, master, DBUS_WORD, (1 << 15) | (1 << 14))
    both_enable = high_cycles(history, "configDbena")
    both_disable = high_cycles(history, "configDbdis")
    assert len(both_enable) == DBENA_CYCLES and both_enable == list(
        range(both_enable[0], both_enable[0] + DBENA_CYCLES)
    ), f"dbena cycles {both_enable}"
    assert both_disable == [], f"dbdis is not held off while dbena is active: {both_disable}"
    history = await write_and_watch(dut, master, DBUS_WORD, 1 << 12)
    assert history[-1]["configDben"] == 1, "dben did not stay high"
    assert await read_word(master, DBUS_WORD) == 1 << 12, "word 8 does not read dben back"
    history = await write_and_watch(dut, master, DBUS_WORD, 0)
    assert history[-1]["configDben"] == 0, "dben did not clear"
    clock_task.cancel()


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def evrv1reg_output_map_strobes(dut):
    """Output map words 272 to 277 follow the byte strobe only when USE_WSTRB_G is true.

    Observed, intent unconfirmed: with USE_WSTRB_G true a full-word write
    (strobe 0xF) changes neither half; with it false every write sets both.

    Propagation sampling: the output map is sampled 2 ns after each edge.
    """
    master, clock_task = await start_axi_master(dut)
    halves = [0] * (OUTPUT_MAP_WORDS * 2)

    async def strobed(pair, value, strobe):
        word = OUTPUT_MAP_FIRST_WORD + pair
        assert await raw_write(dut, word, value, strobe) == AxiResp.OKAY, f"write of word {word} strobe 0x{strobe:X}"
        await settle(dut)

    for pair in range(OUTPUT_MAP_WORDS):
        word = OUTPUT_MAP_FIRST_WORD + pair
        first = 0xA5C30000 + 0x1111 * pair + 0x0101
        second = 0x5A3C0000 + 0x2222 * pair + 0x0303
        upper, lower = 2 * pair, 2 * pair + 1
        if USE_WSTRB:
            # Each half is written by its own strobe and the other half is kept.
            await strobed(pair, first, 0xC)
            halves[upper] = first >> 16
            assert output_map_halves(dut) == halves, f"word {word}: strobe 0xC"
            await strobed(pair, second, 0x3)
            halves[lower] = second & 0xFFFF
            assert output_map_halves(dut) == halves, f"word {word}: strobe 0x3"
            for strobe in (0xF, 0x8, 0x1, 0x0):
                await strobed(pair, FULL_WORD, strobe)
                assert output_map_halves(dut) == halves, f"word {word}: strobe 0x{strobe:X} changed the map"
            await write_word(master, word, FULL_WORD)
            await settle(dut)
            assert output_map_halves(dut) == halves, f"word {word}: a full master write changed the map"
        else:
            for strobe, value in ((0xF, first), (0xC, second), (0x3, first), (0x1, second)):
                await strobed(pair, value, strobe)
                halves[upper] = value >> 16
                halves[lower] = value & 0xFFFF
                assert output_map_halves(dut) == halves, f"word {word}: strobe 0x{strobe:X}"
        expected_read = (halves[upper] << 16) | halves[lower]
        assert await read_word(master, word) == expected_read, f"word {word} reads back 0x{expected_read:08X}"
    clock_task.cancel()


def test_offset_tables_match_rtl_case_arms():
    assert case_arms(WRITE_CASE) == (WRITE_WORDS, ()), "WRITE_WORDS differ from the write decode"
    assert case_arms(READ_CASE) == (READ_WORDS, READ_RANGES), "READ_WORDS differ from the read decode"


@pytest.mark.parametrize(
    "params",
    [
        parameter_case("false", USE_WSTRB_G="false"),
        parameter_case("true", USE_WSTRB_G="true"),
    ],
)
def test_EvrV1Reg(params):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv1regwrapper",
        parameters=params,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
