#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2Cache test: each written 192-bit entry is read back as six 32-bit words.

Test methodology:
    Sweep: 8 entries written and read back; 1030 writes (1024 entries and six
        more) read back in full; the empty flag against the read pointer with
        3 entries written; the write and read pointer resets.
    Stimulus: independent clka (10 ns) and clkb (7 ns); entries are
        deterministic 192-bit values; wea is held high for one clka cycle per
        entry and enb for one clkb cycle per word, followed by one idle clkb
        cycle so the RAM output register settles before the next read.
    Checks: the words of an entry come out lowest word first (bits 31 downto
        0 of the entry first); every entry read equals the written value;
        dout and empty are resolvable after the pointers are reset.
        Pointer behavior is asserted as measured and the maintainers have not
        confirmed it as intended: the write pointer stops at entry 1023 and
        later writes keep overwriting it, empty rises only when the read
        pointer reaches entry 1023 whatever the writer did, only word 0 of
        entry 1023 can be read, and rsta and rstb clear their pointers and
        done flags.
    Timing: asynchronous clocks, 10 ns and 7 ns; inputs change 2 ns after a
        rising edge of their own clock.
    Propagation sampling: the RAM output register and the read pointer
        update on the rising edge of clkb, so dout and empty are sampled 2 ns
        after a clkb edge.
"""

import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common.regression_utils import (
    run_lcls_vhdl_test,
    sample_after_tpd,
)

CLKA_NS = 10
CLKB_NS = 7
ENTRIES = 1024
WORDS = 6
WORD_MASK = 0xFFFFFFFF


def entry_value(index):
    """Return the deterministic 192-bit entry written as number ``index``."""
    return random.Random(0xCAC4E + index).getrandbits(192)


def entry_words(value):
    return [(value >> (32 * k)) & WORD_MASK for k in range(WORDS)]


async def start_clocks(dut):
    tasks = [
        cocotb.start_soon(Clock(dut.clka, CLKA_NS, unit="ns").start(start_high=False)),
        cocotb.start_soon(Clock(dut.clkb, CLKB_NS, unit="ns").start(start_high=False)),
    ]
    dut.wea.value = 0
    dut.din.value = 0
    dut.enb.value = 0
    dut.rsta.value = 0
    dut.rstb.value = 0
    return tasks


def stop(tasks):
    for task in tasks:
        task.cancel()


async def reset_pointers(dut, writer=True, reader=True):
    """Pulse rsta and rstb for three cycles of their own clock."""
    if writer:
        dut.rsta.value = 1
    if reader:
        dut.rstb.value = 1
    for _ in range(3):
        await sample_after_tpd(dut.clka, propagation_time=2)
    for _ in range(3):
        await sample_after_tpd(dut.clkb, propagation_time=2)
    dut.rsta.value = 0
    dut.rstb.value = 0
    await sample_after_tpd(dut.clkb, propagation_time=2)


async def write_entries(dut, first, count):
    """Write entries ``first`` to ``first + count - 1`` back to back, one per clka cycle."""
    await sample_after_tpd(dut.clka, propagation_time=2)
    for index in range(first, first + count):
        dut.wea.value = 1
        dut.din.value = entry_value(index)
        await sample_after_tpd(dut.clka, propagation_time=2)
    dut.wea.value = 0
    await sample_after_tpd(dut.clka, propagation_time=2)


async def read_word(dut):
    """Return (dout, empty) as sampled, then advance the reader by one word."""
    await sample_after_tpd(dut.clkb, propagation_time=2)
    assert dut.dout.value.is_resolvable, f"dout carries unresolved bits: {dut.dout.value}"
    assert dut.empty.value.is_resolvable, f"empty carries unresolved bits: {dut.empty.value}"
    seen = (int(dut.dout.value), int(dut.empty.value))
    dut.enb.value = 1
    await sample_after_tpd(dut.clkb, propagation_time=2)
    dut.enb.value = 0
    return seen


async def read_entries(dut, count):
    """Return the words read for ``count`` consecutive entries as a list of 6-word lists."""
    entries = []
    for _ in range(count):
        entries.append([(await read_word(dut))[0] for _ in range(WORDS)])
    return entries


@cocotb.test(timeout_time=500, timeout_unit="us")
async def cache_round_trip(dut):
    """Eight written entries read back as six words each, lowest word first.

    Propagation sampling: dout and empty are sampled 2 ns after a clkb edge.
    """
    tasks = await start_clocks(dut)
    await reset_pointers(dut)
    await write_entries(dut, 0, 8)
    got = await read_entries(dut, 8)
    for index, words in enumerate(got):
        assert words == entry_words(entry_value(index)), (
            f"entry {index}: read {[hex(w) for w in words]}, "
            f"expected {[hex(w) for w in entry_words(entry_value(index))]}"
        )
    stop(tasks)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def cache_full_overwrites_last_entry(dut):
    """Writes past entry 1023 keep overwriting entry 1023 (observed, intent unconfirmed).

    After 1030 back to back writes entries 0 to 1022 hold writes 0 to 1022
    and entry 1023 holds the last write, number 1029. Once the read pointer
    reaches entry 1023 the word select no longer advances, so only word 0 of
    that entry can be read (observed, intent unconfirmed).

    Propagation sampling: dout and empty are sampled 2 ns after a clkb edge.
    """
    tasks = await start_clocks(dut)
    await reset_pointers(dut)
    await write_entries(dut, 0, ENTRIES + 6)
    got = await read_entries(dut, ENTRIES)
    for index in range(ENTRIES - 1):
        assert got[index] == entry_words(entry_value(index)), f"entry {index} does not hold write {index}"
    last = entry_words(entry_value(ENTRIES + 5))
    assert got[ENTRIES - 1] == [last[0]] * WORDS, (
        f"entry 1023 reads {[hex(w) for w in got[ENTRIES - 1]]}, expected word 0 of write 1029 six times"
    )
    stop(tasks)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def cache_empty_flag(dut):
    """empty rises when the read pointer reaches entry 1023, not when the reader catches the writer.

    Asserted as observed, intent unconfirmed: with 3 entries written the flag stays low
    while the reader consumes them and the stale entries after them, and
    rises after exactly 1023 entries of 6 words have been consumed.

    Propagation sampling: dout and empty are sampled 2 ns after a clkb edge.
    """
    tasks = await start_clocks(dut)
    await reset_pointers(dut)
    await write_entries(dut, 0, 3)
    flags = []
    for word_number in range((ENTRIES - 1) * WORDS + 2):
        flags.append((await read_word(dut))[1])
    low = flags.index(1) if 1 in flags else None
    assert low is not None, "empty never rose while 1023 entries were consumed"
    assert all(flag == 0 for flag in flags[:low]) and all(flag == 1 for flag in flags[low:]), (
        f"empty is not monotonic around word {low}: {flags[low - 2:low + 3]}"
    )
    assert low == (ENTRIES - 1) * WORDS, f"empty rose after {low} words, expected {(ENTRIES - 1) * WORDS}"
    stop(tasks)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def cache_reset_pointers(dut):
    """rstb restarts reading at entry 0 and rsta restarts writing there, clearing done.

    Propagation sampling: dout and empty are sampled 2 ns after a clkb edge.
    """
    tasks = await start_clocks(dut)
    await reset_pointers(dut)
    await write_entries(dut, 0, 4)
    await read_entries(dut, 2)
    await reset_pointers(dut, writer=False)
    again = await read_entries(dut, 4)
    assert again == [entry_words(entry_value(k)) for k in range(4)], "rstb did not restart the reader at entry 0"
    # Fill the cache so the write side is done, then clear it with rsta.
    await write_entries(dut, 0, ENTRIES + 2)
    await reset_pointers(dut)
    await write_entries(dut, 5000, 2)
    final = await read_entries(dut, 2)
    assert final == [entry_words(entry_value(5000 + k)) for k in range(2)], "rsta did not restart the writer at entry 0"
    assert (await read_word(dut))[1] == 0, "empty is high after both pointers were reset"
    stop(tasks)


def test_EvrV2Cache():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2cache",
    )
