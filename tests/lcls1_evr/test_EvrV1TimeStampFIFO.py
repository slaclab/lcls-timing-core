#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1TimeStampFIFO leaf test under GHDL.

Test methodology:
    Sweep: 0, 1, 2, 3, 5 and 40 words written for the count and empty
        values; 100 words streamed across the clocks for ordering; a burst
        of 600 writes into the 512 word capacity; exactly 512 writes plus
        one more; a reset with words still stored.
    Stimulus: wr_clk is 10 ns and rd_clk is 13 ns, so the two sides never
        share an edge pattern. rst is held high for 5 cycles of each clock,
        then released, and the test waits for the reset release to cross
        into both domains before it writes. Words are 72 bits and come from
        the seeded generator in timing_model, and the seed is logged. A word
        is consumed by rd_en high at a rd_clk edge, and dout is the word
        that edge consumes.
    Checks: words come out in write order. The counts and empty follow the
        measured table in expected_flags. The FIFO holds 512 words, the
        first 512 written, and a write into the full FIFO drops the word.
        The port named full is driven by the FifoAsync overflow output, so
        it is high for one cycle after each write into a full FIFO and never
        high otherwise. After rst, empty is high, both counts are 0, full is
        low, and the old words are gone. Every checked flag and count is
        resolvable after reset release, and dout is checked only while it
        holds a written word.
    Timing: 10 ns wr_clk, 13 ns rd_clk.
    Propagation sampling: the registers update ``after TPD_G`` (1 ns), so
        every sample is taken 2 ns after the rising edge of the clock of
        the domain the signal belongs to.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.utils import get_sim_time

from tests.common import timing_model
from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd

WR_PERIOD_NS = 10
RD_PERIOD_NS = 13
RESET_CYCLES = 5
SETTLE_CYCLES = 30
WORD_BITS = 72
CAPACITY = 512
BURST_WRITES = 600
ORDER_WORDS = 100
# A word written this long ago is the head of the FIFO whenever every older
# word has been consumed. The measured write-to-head time is 6 rd_clk cycles (78 ns);
# the extra margin only decides when the reader may look.
HEAD_VISIBLE_NS = 300
HEAD_LATENCY_MAX_CYCLES = 12
COUNT_TABLE_WORDS = (0, 1, 2, 3, 5, 40)


def expected_flags(words):
    """Measured (wr_data_count, rd_data_count, empty) after `words` writes settle.

    One word is held ahead of the RAM, so both counts read one less than
    the number written, and empty is already high while two words remain.
    """
    count = max(words - 1, 0)
    return count, count, int(words <= 2)


async def start_clocks(dut):
    dut.rst.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0
    cocotb.start_soon(Clock(dut.wr_clk, WR_PERIOD_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.rd_clk, RD_PERIOD_NS, unit="ns").start())
    await RisingEdge(dut.wr_clk)
    await release_reset(dut)


async def release_reset(dut):
    """Hold rst for a few cycles of each clock, release it, and let it settle.

    Propagation sampling: the waits end 2 ns after an edge, past the 1 ns
    ``after TPD_G`` register delay.
    """
    dut.rst.value = 1
    for _ in range(RESET_CYCLES):
        await sample_after_tpd(dut.wr_clk, propagation_time=2)
    for _ in range(RESET_CYCLES):
        await sample_after_tpd(dut.rd_clk, propagation_time=2)
    dut.rst.value = 0
    await settle(dut)


async def settle(dut, cycles=SETTLE_CYCLES):
    """Wait for writes and the reset release to cross into the read domain.

    Propagation sampling: the waits end 2 ns after an edge, past the 1 ns
    ``after TPD_G`` register delay.
    """
    for _ in range(cycles):
        await sample_after_tpd(dut.rd_clk, propagation_time=2)
    await sample_after_tpd(dut.wr_clk, propagation_time=2)


def level(handle, name):
    assert handle.value.is_resolvable, f"{name} is not resolvable"
    return int(handle.value)


async def write_words(dut, words):
    """Write one word per wr_clk cycle and return the full flag seen after each.

    Propagation sampling: each sample is taken 2 ns after the edge that
    captured the word, past the 1 ns ``after TPD_G`` delay.
    """
    full_trace = []
    for word in words:
        dut.wr_en.value = 1
        dut.din.value = word
        await sample_after_tpd(dut.wr_clk, propagation_time=2)
        full_trace.append(level(dut.full, "full"))
    dut.wr_en.value = 0
    return full_trace


async def drain(dut, limit):
    """Hold rd_en high and return the head word before every consuming edge.

    Once the FIFO is empty dout keeps its last word, so the list ends with a
    repeat of the final word. Propagation sampling: each head is read 2 ns
    after the previous edge, past the 1 ns ``after TPD_G`` delay.
    """
    await sample_after_tpd(dut.rd_clk, propagation_time=2)
    heads = [level(dut.dout, "dout")]
    dut.rd_en.value = 1
    for _ in range(limit):
        await sample_after_tpd(dut.rd_clk, propagation_time=2)
        heads.append(level(dut.dout, "dout"))
    dut.rd_en.value = 0
    return heads


def words_before_repeat(heads):
    """Number of distinct consecutive words before dout stops advancing."""
    for index in range(1, len(heads)):
        if heads[index] == heads[index - 1]:
            return index
    return len(heads)


def read_flags(dut):
    return (
        level(dut.wr_data_count, "wr_data_count"),
        level(dut.rd_data_count, "rd_data_count"),
        level(dut.empty, "empty"),
    )


def random_words(rng, count):
    return [rng.getrandbits(WORD_BITS) for _ in range(count)]


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def fifo_order_across_clocks(dut):
    """Words written on wr_clk come out in order on rd_clk while both run.

    A writer streams 100 words, one per wr_clk cycle. The reader consumes a
    word as soon as that word is old enough to be the head, so reads and
    writes overlap. There is no valid output on this wrapper, so age stands
    in for it.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_clocks(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")
    words = random_words(rng, ORDER_WORDS)
    write_times = []

    async def writer():
        for word in words:
            dut.wr_en.value = 1
            dut.din.value = word
            write_times.append(get_sim_time("ns"))
            await sample_after_tpd(dut.wr_clk, propagation_time=2)
            assert level(dut.full, "full") == 0, "full asserted while far below capacity"
        dut.wr_en.value = 0

    writer_task = cocotb.start_soon(writer())
    received = []
    while len(received) < len(words):
        await sample_after_tpd(dut.rd_clk, propagation_time=2)
        index = len(received)
        aged = index < len(write_times) and get_sim_time("ns") - write_times[index] >= HEAD_VISIBLE_NS
        if aged:
            received.append(level(dut.dout, "dout"))
            dut.rd_en.value = 1
        else:
            dut.rd_en.value = 0
    await sample_after_tpd(dut.rd_clk, propagation_time=2)
    dut.rd_en.value = 0
    await writer_task

    assert received == words, "words did not come out in write order"
    await settle(dut)
    assert read_flags(dut) == (0, 0, 1), f"flags {read_flags(dut)} after draining, expected (0, 0, 1)"


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def fifo_counts(dut):
    """The counts and empty after N writes follow the measured table.

    The head word is on dout while empty is still high for one or two
    words, and the first written word reaches dout within a measured
    number of rd_clk cycles. This is observed, intent unconfirmed.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_clocks(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")

    for count in COUNT_TABLE_WORDS:
        await release_reset(dut)
        words = random_words(rng, count)
        await write_words(dut, words)
        await settle(dut)
        flags = read_flags(dut)
        assert flags == expected_flags(count), (
            f"after {count} writes (wr_data_count, rd_data_count, empty) = {flags}, "
            f"expected {expected_flags(count)}"
        )
        assert level(dut.full, "full") == 0, f"full high after {count} writes"
        if count > 0:
            head = level(dut.dout, "dout")
            assert head == words[0], f"head {head:#x} after {count} writes, expected {words[0]:#x}"

        # Consuming every word returns the FIFO to its empty state.
        if count > 0:
            heads = await drain(dut, count + 4)
            assert heads[:count] == words, f"words after {count} writes came out as {heads[:count]}"
            await settle(dut)
            assert read_flags(dut) == (0, 0, 1), f"flags {read_flags(dut)} after consuming {count} words"

    # Write-to-head latency of a single word, in rd_clk cycles.
    await release_reset(dut)
    word = rng.getrandbits(WORD_BITS)
    await write_words(dut, [word])
    arrival = None
    for cycle in range(1, HEAD_LATENCY_MAX_CYCLES + 1):
        await sample_after_tpd(dut.rd_clk, propagation_time=2)
        if dut.dout.value.is_resolvable and int(dut.dout.value) == word:
            arrival = cycle
            break
    dut._log.info(f"first word reached dout after {arrival} rd_clk cycles")
    assert arrival is not None, f"first word not on dout within {HEAD_LATENCY_MAX_CYCLES} rd_clk cycles"
    assert arrival * RD_PERIOD_NS < HEAD_VISIBLE_NS, "write-to-head time exceeds the reader margin"


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def fifo_capacity_and_full_flag(dut):
    """The FIFO holds 512 words and the full port pulses on a write into it.

    This is observed, intent unconfirmed: the port named full carries the
    FifoAsync overflow output, so it is a one cycle strobe after a write
    into a full FIFO and stays low while the FIFO is merely full.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_clocks(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")

    # A burst longer than the capacity: the first 512 words are kept and
    # each of the rest is flagged.
    words = random_words(rng, BURST_WRITES)
    full_trace = await write_words(dut, words)
    flagged = [index for index, flag in enumerate(full_trace) if flag]
    assert flagged == list(range(CAPACITY, BURST_WRITES)), (
        f"full seen after writes {flagged[:3]} ..., expected one per write from {CAPACITY}"
    )
    await settle(dut)
    assert read_flags(dut) == (CAPACITY - 1, CAPACITY - 1, 0), (
        f"flags {read_flags(dut)} with the FIFO full, expected ({CAPACITY - 1}, {CAPACITY - 1}, 0)"
    )
    assert level(dut.full, "full") == 0, "full stays high while the FIFO is merely full"
    heads = await drain(dut, BURST_WRITES + 8)
    stored = words_before_repeat(heads)
    assert stored == CAPACITY, f"{stored} words came out of the burst, expected {CAPACITY}"
    assert heads[:CAPACITY] == words[:CAPACITY], "the kept words are not the first words written"
    await settle(dut)
    assert read_flags(dut) == (0, 0, 1), f"flags {read_flags(dut)} after draining, expected (0, 0, 1)"

    # Exactly 512 words never raise full; one more write raises it for one
    # cycle and is dropped.
    await release_reset(dut)
    words = random_words(rng, CAPACITY + 1)
    full_trace = await write_words(dut, words[:CAPACITY])
    assert not any(full_trace), f"full seen while filling to capacity at writes {full_trace.index(1)}"
    dut.wr_en.value = 1
    dut.din.value = words[CAPACITY]
    await sample_after_tpd(dut.wr_clk, propagation_time=2)
    extra_trace = [level(dut.full, "full")]
    dut.wr_en.value = 0
    for _ in range(4):
        await sample_after_tpd(dut.wr_clk, propagation_time=2)
        extra_trace.append(level(dut.full, "full"))
    assert extra_trace == [1, 0, 0, 0, 0], f"full after one write past capacity: {extra_trace}"
    await settle(dut)
    heads = await drain(dut, CAPACITY + 8)
    assert words_before_repeat(heads) == CAPACITY, "the write past capacity was stored"
    assert heads[:CAPACITY] == words[:CAPACITY], "stored words differ from the words written"


@cocotb.test(timeout_time=1, timeout_unit="ms")
async def fifo_reset_empties(dut):
    """rst empties a FIFO that holds words, and later words are not mixed with old ones.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    await start_clocks(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")

    old_words = random_words(rng, 20)
    await write_words(dut, old_words)
    await settle(dut)
    assert read_flags(dut) == expected_flags(len(old_words)), "FIFO did not hold the old words before reset"

    await release_reset(dut)
    assert read_flags(dut) == (0, 0, 1), f"flags {read_flags(dut)} after reset, expected (0, 0, 1)"
    assert level(dut.full, "full") == 0, "full high after reset"

    new_word = rng.getrandbits(WORD_BITS)
    await write_words(dut, [new_word])
    await settle(dut)
    heads = await drain(dut, 4)
    assert heads[0] == new_word, f"first word after reset is {heads[0]:#x}, expected the new word {new_word:#x}"
    assert words_before_repeat(heads) == 1, "an old word came out after the new one"


def test_EvrV1TimeStampFIFO():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv1timestampfifo",
    )
