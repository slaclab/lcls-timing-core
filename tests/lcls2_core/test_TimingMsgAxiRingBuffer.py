#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingMsgAxiRingBuffer test: timing messages recorded and read back over AXI-Lite.

The module turns each timing message into 32 bit words (TimingMsgToAxiStream)
and records every valid word in a surf AxiLiteRingBuffer while the control
register's bufferEnable bit is set. Because TimingMsgToAxiStream never ends its
stream (see test_TimingMsgToAxiStream), the words recorded after a message are
the 30 message chunks, least significant chunk first, followed by zero words
for as long as recording stays enabled. That stream is the model here. The 1024 word wrap case and the clear case
rely on it never ending (checked: they fail when the stream is made to end
after one frame), so they need revisiting when that known issue is fixed.

Ring buffer behavior asserted as observed, intent unconfirmed (it lives in
surf, not in this repository): the status length is one less than the number
of recorded words; AXI-Lite word 1 reads RAM[0], which is never written until
the ring wraps, so the first recorded word is AXI-Lite word 2; the newest
recorded word sits one past the reported length; and in a wrapped ring the
newest word is not reachable at all because word 2**RAM_ADDR_WIDTH_G aliases
the control register.

Test methodology:
    Sweep: RAM_ADDR_WIDTH_G in 4 (16 words, wraps within the message) and 10
        (1024 words, the default), one compiled simulation each. VECTOR_SIZE_G
        is 944. Clocks: timingClk 5.4 ns and axilClk 10 ns, unrelated.
    Stimulus: each entrypoint starts from a fresh 5 cycle reset followed by 40
        idle cycles. Control writes use a cocotbext-axi AxiLiteMaster: bit 31
        is bufferEnable and bit 30 is bufferClear. A one cycle
        timingMessageStrobe carries a model-packed random message (seed
        logged). The enable write is made 20 axilClk cycles before the strobe,
        and the disable write is made a fixed number of axilClk cycles after
        it, so the number of recorded words is measured from the status
        length, not assumed.
    Checks: response codes (OKAY for the control register and RAM window,
        DECERR for a RAM word write), status fields (bit 31 enable, bits 27 to
        20 RAM_ADDR_WIDTH_G, low bits length), the recorded words against the
        model stream, and that every S_AXI output is resolvable after reset
        release. Waits are bounded loops of clock cycles.
    Timing: see the sweep; the recorded count depends on the clock phase, so
        window checks match contiguous model windows instead of fixed counts.
    Propagation sampling: control writes and the strobe change 2 ns after a
        clock edge, past the 1 ns TPD_G register delay.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiResp
import pytest

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingMsgAxiRingBufferWrapper.vhd"

VECTOR_SIZE = 944
CHUNK_BITS = 32
CHUNK_MASK = (1 << CHUNK_BITS) - 1
MESSAGE_CHUNKS = -(-VECTOR_SIZE // CHUNK_BITS)
RESET_CYCLES = 5
IDLE_CYCLES = 40
ENABLE_SETTLE = 20
DISABLE_SETTLE = 20
ENABLE_BIT = 1 << 31
CLEAR_BIT = 1 << 30
RAM_WIDTH_SHIFT = 20
RAM_WIDTH_MASK = 0xFF
OUTPUT_NAMES = (
    "S_AXI_AWREADY", "S_AXI_WREADY", "S_AXI_BRESP", "S_AXI_BVALID",
    "S_AXI_ARREADY", "S_AXI_RDATA", "S_AXI_RRESP", "S_AXI_RVALID",
)


def ram_width(dut):
    """RAM_ADDR_WIDTH_G, read from the width of the address port (AXI address is RAM_ADDR_WIDTH_G + 3 bits)."""
    return len(dut.S_AXI_ARADDR) - 3


def message_chunks(vector):
    return [(vector >> (CHUNK_BITS * index)) & CHUNK_MASK for index in range(MESSAGE_CHUNKS)]


def stream_word(chunks, index):
    """Word ``index`` of the model stream: the message chunks, then zero forever."""
    return chunks[index] if index < len(chunks) else 0


def find_window(chunks, words):
    """First offset k with words[i] == stream word k + i for every i, or None."""
    for offset in range(len(chunks) + len(words)):
        if all(word == stream_word(chunks, offset + index) for index, word in enumerate(words)):
            return offset
    return None


async def start_up(dut):
    """Drive resets and inputs, build the AXI-Lite master, then start the clocks (cocotbext-axi order)."""
    dut.timingRst.value = 1
    dut.axilRst.value = 1
    dut.timingMessageStrobe.value = 0
    dut.timingMessage.value = 0
    master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "S_AXI"), dut.axilClk, dut.axilRst, reset_active_level=True)
    await Timer(1, unit="ns")
    clocks = [
        cocotb.start_soon(Clock(dut.timingClk, 5.4, unit="ns").start(start_high=False)),
        cocotb.start_soon(Clock(dut.axilClk, 10, unit="ns").start(start_high=False)),
    ]
    return master, clocks


async def wait_axil(dut, count):
    for _ in range(count):
        await sample_after_tpd(dut.axilClk, propagation_time=2)


async def reset_and_idle(dut):
    """Reset both domains, release, idle, and check every S_AXI output resolves."""
    dut.timingMessageStrobe.value = 0
    dut.timingRst.value = 1
    dut.axilRst.value = 1
    await wait_axil(dut, RESET_CYCLES)
    dut.timingRst.value = 0
    dut.axilRst.value = 0
    await wait_axil(dut, IDLE_CYCLES)
    for _ in range(10):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
        for name in OUTPUT_NAMES:
            value = getattr(dut, name).value
            assert value.is_resolvable, f"{name} is {value} after reset release"


async def send(dut, vector):
    """One timingClk cycle of timingMessageStrobe carrying ``vector``."""
    dut.timingMessage.value = vector
    dut.timingMessageStrobe.value = 1
    await sample_after_tpd(dut.timingClk, propagation_time=2)
    dut.timingMessageStrobe.value = 0
    dut.timingMessage.value = 0


async def write_control(master, value):
    response = await master.write(0, value.to_bytes(4, "little"))
    assert response.resp == AxiResp.OKAY, f"control write response {response.resp!r}"


async def read_word(master, index):
    """AXI-Lite word ``index``: 0 is the control register, 1 and up the RAM window."""
    response = await master.read(4 * index, 4)
    assert response.resp == AxiResp.OKAY, f"word {index} read response {response.resp!r}"
    return int.from_bytes(response.data, "little")


class Status:
    """Fields of the control register read."""

    def __init__(self, raw, width):
        self.raw = raw
        self.enable = raw >> 31 & 1
        self.clear = raw >> 30 & 1
        self.ext_enable = raw >> 29 & 1
        self.ext_clear = raw >> 28 & 1
        self.ram_width = raw >> RAM_WIDTH_SHIFT & RAM_WIDTH_MASK
        self.length = raw & ((1 << width) - 1)


async def read_status(master, width):
    return Status(await read_word(master, 0), width)


async def record_message(dut, master, vector, axil_cycles):
    """Reset, enable, strobe one message, wait, disable; return the status afterwards."""
    width = ram_width(dut)
    await reset_and_idle(dut)
    await write_control(master, ENABLE_BIT)
    await wait_axil(dut, ENABLE_SETTLE)
    await send(dut, vector)
    await wait_axil(dut, axil_cycles)
    await write_control(master, 0)
    await wait_axil(dut, DISABLE_SETTLE)
    return await read_status(master, width)


@cocotb.test(timeout_time=300, timeout_unit="us")
async def ringbuffer_disabled_records_nothing(dut):
    """With bufferEnable clear a strobe records nothing: length 0, the RAM window unchanged.

    Propagation sampling: control writes and the strobe change 2 ns after a
    clock edge. After reset the status reads OKAY with the configured RAM
    width in bits 27 to 20 and every other field zero. A message is strobed
    with recording disabled and 200 timing cycles pass; the length is still 0
    and the first RAM words read the same as before the strobe. A write to a
    RAM word is answered DECERR and does not change the status.
    """
    master, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vector = timing_model.pack_message(timing_model.random_message(rng))
    width = ram_width(dut)
    await reset_and_idle(dut)
    status = await read_status(master, width)
    assert status.ram_width == width, f"status reports RAM width {status.ram_width}, expected {width}"
    assert (status.enable, status.clear, status.ext_enable, status.ext_clear, status.length) == (0, 0, 0, 0, 0), (
        f"status after reset is 0x{status.raw:08X}"
    )
    window = min(8, (1 << width) - 1)
    before = [await read_word(master, index) for index in range(1, window + 1)]
    await send(dut, vector)
    await wait_axil(dut, 200)
    status = await read_status(master, width)
    assert status.length == 0, f"length {status.length} with recording disabled"
    after = [await read_word(master, index) for index in range(1, window + 1)]
    assert after == before, "the RAM window changed with recording disabled"
    response = await master.write(4, (0xA5A5A5A5).to_bytes(4, "little"))
    assert response.resp == AxiResp.DECERR, f"RAM word write response {response.resp!r}"
    status = await read_status(master, width)
    assert (status.enable, status.length) == (0, 0), f"status after the RAM write is 0x{status.raw:08X}"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=300, timeout_unit="us")
async def ringbuffer_records_vector(dut):
    """Recording from before the strobe, the RAM holds the model stream from word 2.

    Propagation sampling: control writes and the strobe change 2 ns after a
    clock edge. Observed, intent unconfirmed: recorded count is length + 1, so
    AXI-Lite word j + 2 holds model word j for j below that count, and word 1
    is the unwritten RAM[0]. With the 1024 word ring the 30 message chunks and
    the zero words that follow are all visible; with the 16 word ring only the
    first few chunks fit before recording stops. The enable bit reads back set
    while recording and clear after the disable write.
    """
    master, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vector = timing_model.pack_message(timing_model.random_message(rng))
    chunks = message_chunks(vector)
    width = ram_width(dut)
    capacity = 1 << width
    axil_cycles = 3 if capacity < 2 * MESSAGE_CHUNKS else 30

    await reset_and_idle(dut)
    await write_control(master, ENABLE_BIT)
    assert (await read_status(master, width)).enable == 1, "enable bit does not read back set"
    await write_control(master, 0)
    status = await record_message(dut, master, vector, axil_cycles)
    assert status.enable == 0, f"enable bit set after the disable write, status 0x{status.raw:08X}"
    assert status.ram_width == width
    recorded = status.length + 1
    assert 1 < recorded < capacity - 1, f"{recorded} recorded words in a ring of {capacity}"
    words = [await read_word(master, index) for index in range(2, recorded + 2)]
    expected = [stream_word(chunks, index) for index in range(recorded)]
    assert words == expected, (
        f"recorded words differ from the model stream at {[i for i, (a, b) in enumerate(zip(words, expected)) if a != b]}"
    )
    if recorded > MESSAGE_CHUNKS:
        assert words[:MESSAGE_CHUNKS] == chunks, "message chunks differ"
        assert not any(words[MESSAGE_CHUNKS:]), "nonzero word after the message chunks"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=300, timeout_unit="us")
async def ringbuffer_wraps(dut):
    """Once the ring is full the length saturates and the window is a contiguous model slice.

    Propagation sampling: control writes and the strobe change 2 ns after a
    clock edge. Recording continues past the ring size. Observed, intent
    unconfirmed: the length saturates at the ring size minus one, AXI-Lite
    words 1 to ring size minus one hold consecutive model words (the oldest
    first, the newest recorded word is not reachable), and word ring size
    aliases the control register. In the 16 word ring the slice still
    contains message chunks but starts after chunk 0, which was overwritten.
    In the 1024 word ring the zero words that follow the message have pushed
    the whole message out, so the window reads zero.
    """
    master, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vector = timing_model.pack_message(timing_model.random_message(rng))
    chunks = message_chunks(vector)
    width = ram_width(dut)
    capacity = 1 << width
    axil_cycles = 10 if capacity < 2 * MESSAGE_CHUNKS else 700
    status = await record_message(dut, master, vector, axil_cycles)
    assert status.length == capacity - 1, f"length {status.length}, expected {capacity - 1} after wrapping"
    if capacity < 2 * MESSAGE_CHUNKS:
        read_indexes = list(range(1, capacity))
    else:
        read_indexes = list(range(1, 65)) + list(range(capacity - 16, capacity))
    words = [await read_word(master, index) for index in read_indexes]
    if capacity < 2 * MESSAGE_CHUNKS:
        offset = find_window(chunks, words)
        assert offset is not None, f"window {[hex(word) for word in words]} is not a contiguous model slice"
        assert 0 < offset < MESSAGE_CHUNKS, f"slice starts at model word {offset}, expected a slice of the message"
        dut._log.info("wrapped window starts at model word %d", offset)
    else:
        assert not any(words), "nonzero word in the wrapped 1024 word ring, expected the zero stream"
    alias = await read_word(master, capacity)
    final = await read_status(master, width)
    assert alias == final.raw, f"word {capacity} is 0x{alias:08X}, expected the control register 0x{final.raw:08X}"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=300, timeout_unit="us")
async def ringbuffer_clear(dut):
    """bufferClear empties the ring and keeps it empty until recording is enabled again.

    Propagation sampling: control writes and the strobe change 2 ns after a
    clock edge. After a message the length is nonzero. Writing the clear bit
    with the enable bit low makes the length 0 and the enable bit reads 0;
    the clear bit reads back 0 once the pulse has passed. With recording still
    disabled the length stays 0 after another message. Enabling again starts
    from empty: after a short enabled interval the length is nonzero and
    below the earlier length (the 16 word ring is enabled for only the two
    control writes, because it saturates within a few cycles).
    """
    master, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    first = timing_model.pack_message(timing_model.random_message(rng))
    second = timing_model.pack_message(timing_model.random_message(rng))
    width = ram_width(dut)
    capacity = 1 << width
    status = await record_message(dut, master, first, 30)
    earlier = status.length
    assert earlier > 0, "nothing was recorded before the clear"

    await write_control(master, CLEAR_BIT)
    await wait_axil(dut, DISABLE_SETTLE)
    status = await read_status(master, width)
    assert status.length == 0, f"length {status.length} after the clear write"
    assert (status.enable, status.clear) == (0, 0), f"status after the clear is 0x{status.raw:08X}"

    await send(dut, second)
    await wait_axil(dut, 30)
    status = await read_status(master, width)
    assert status.length == 0, f"length {status.length} with recording disabled after the clear"

    await write_control(master, ENABLE_BIT)
    await wait_axil(dut, 0 if capacity < 2 * MESSAGE_CHUNKS else 5)
    await write_control(master, 0)
    await wait_axil(dut, DISABLE_SETTLE)
    status = await read_status(master, width)
    assert 0 < status.length < earlier, f"length {status.length} after re-enabling, earlier length {earlier}"
    for clock in clocks:
        clock.cancel()


@pytest.mark.parametrize("ram_addr_width", [4, 10])
def test_TimingMsgAxiRingBuffer(ram_addr_width):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingmsgaxiringbufferwrapper",
        parameters={"RAM_ADDR_WIDTH_G": ram_addr_width, "VECTOR_SIZE_G": VECTOR_SIZE},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
