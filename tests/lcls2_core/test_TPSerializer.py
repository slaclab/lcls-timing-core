#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPSerializer test: a latched 944-bit message leaves as 59 stream words.

Test methodology:
    Sweep: ID_G in 0 and 15, one compiled simulation each. The message goes
        through the production toSlv and toTimingMessageType in the wrapper,
        so the model words equal the stream words only when the conversion
        is lossless for the message.
    Stimulus: txRst is held for 3 txClk cycles. A one cycle fiducial latches
        the message on the msg port; one advance pulse per cycle follows,
        one per word. Cases are the golden message, 5 seeded random messages
        sent back to back, a fiducial that arrives in the same cycle as an
        advance in the middle of a frame, and a reset in the middle of a
        frame.
    Checks: the fiducial presents word 0 (the version word 0x0001) with
        streamReady high; each of the next 58 advances presents the next
        word of timing_model.message_words with streamReady high, and the
        59th advance drops streamReady; streamOffset is 0 and streamLast is
        1 on every cycle, and streamId equals ID_G; without an advance the
        presented word is held; a reset returns streamReady and the word to
        zero on the next cycle and the next frame is serialized in full; a
        fiducial and an advance together restart the frame at word 0 of the
        new message (observed, intent unconfirmed). Every checked output is
        resolvable on every sampled cycle after reset release.
    Timing: 10 ns txClk.
    Propagation sampling: inputs are driven 2 ns past the rising edge and
        outputs are read 2 ns past the next one, so the registered outputs,
        which settle TPD_G = 1 ns after the edge, reflect the stimulus of the
        previous cycle.
"""

from pathlib import Path
from typing import NamedTuple

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    env_int,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TPSerializerWrapper.vhd"

RESET_CYCLES = 3
IDLE_CYCLES = 3
WORDS = timing_model.TIMING_MESSAGE_WORDS
RANDOM_MESSAGES = 5


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


class Sample(NamedTuple):
    """Stream outputs after one clock cycle."""

    ready: int
    last: int
    data: int
    offset: int
    stream_id: int


def golden_message():
    msg = timing_model.default_message()
    msg["pulseId"] = 0x0123456789ABCDEF
    msg["timeStamp"] = 0xFEDCBA9876543210
    msg["beamRequest"] = 0xA5A5A5A5
    msg["bsaDone"] = 0x0F0F0F0F0F0F0F0F
    msg["control"][17] = 0xBEEF
    return msg


async def step(dut, *, fiducial=0, advance=0, rst=0, msg=None):
    """Apply one cycle of stimulus and return the outputs after the next edge."""
    if msg is not None:
        dut.msg.value = timing_model.pack_message(msg)
    dut.fiducial.value = fiducial
    dut.advance.value = advance
    dut.txRst.value = rst
    await sample_after_tpd(dut.txClk, propagation_time=2)
    return Sample(
        resolved_int(dut.streamReady),
        resolved_int(dut.streamLast),
        resolved_int(dut.streamData),
        resolved_int(dut.streamOffset),
        resolved_int(dut.streamId),
    )


async def start_serializer(dut):
    """Drive defined inputs, start the clock, hold reset 3 cycles, release it and idle."""
    dut.txRst.value = 1
    dut.fiducial.value = 0
    dut.advance.value = 0
    dut.msg.value = timing_model.pack_message(timing_model.default_message())
    clock_task = cocotb.start_soon(Clock(dut.txClk, 10, unit="ns").start(start_high=False))
    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.txClk)
    dut.txRst.value = 0
    for _ in range(IDLE_CYCLES):
        idle = await step(dut)
        assert idle.ready == 0, "streamReady is high before any fiducial"
    return clock_task


def check_static(sample, ident):
    assert sample.offset == 0, f"streamOffset is {sample.offset}"
    assert sample.last == 1, f"streamLast is {sample.last}"
    assert sample.stream_id == ident, f"streamId is {sample.stream_id}, expected {ident}"


async def serialize(dut, msg, ident):
    """Latch ``msg`` and advance through its words, checking every presented word.

    The final advance, which drops streamReady, is applied and checked too.
    """
    words = timing_model.message_words(msg)
    assert len(words) == WORDS
    first = await step(dut, fiducial=1, msg=msg)
    check_static(first, ident)
    assert first.ready == 1, "streamReady is low after the fiducial"
    assert first.data == words[0], f"word 0 is 0x{first.data:04X}, expected 0x{words[0]:04X}"
    for index in range(1, WORDS):
        sample = await step(dut, advance=1)
        check_static(sample, ident)
        assert sample.ready == 1, f"streamReady dropped at word {index}"
        assert sample.data == words[index], f"word {index} is 0x{sample.data:04X}, expected 0x{words[index]:04X}"
    final = await step(dut, advance=1)
    check_static(final, ident)
    assert final.ready == 0, "streamReady is still high after the last advance"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def tpserializer_golden(dut):
    """The golden message is presented word by word and the last advance drops streamReady.

    Propagation sampling: inputs are driven 2 ns after the edge and outputs
    are read 2 ns after the next one.
    """
    ident = env_int("ID_G", default=0)
    clock_task = await start_serializer(dut)
    msg = golden_message()
    words = timing_model.message_words(msg)
    assert words[0] == timing_model.TIMING_MESSAGE_VERSION, "model word 0 is not the version word"

    first = await step(dut, fiducial=1, msg=msg)
    assert (first.ready, first.data) == (1, 0x0001), f"fiducial presented {first}"
    for _ in range(4):
        held = await step(dut)
        assert held == first, "the presented word moved without an advance"
    for index in range(1, WORDS):
        sample = await step(dut, advance=1)
        check_static(sample, ident)
        assert (sample.ready, sample.data) == (1, words[index]), f"word {index}: {sample}"
    final = await step(dut, advance=1)
    assert final.ready == 0, "streamReady is still high after word 58 was advanced"
    parked = await step(dut)
    assert parked.ready == 0, "streamReady came back without a fiducial"
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def tpserializer_random_messages(dut):
    """Seeded random messages follow each other and every word sequence equals the model.

    Propagation sampling: inputs are driven 2 ns after the edge and outputs
    are read 2 ns after the next one.
    """
    ident = env_int("ID_G", default=0)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_serializer(dut)
    for _ in range(RANDOM_MESSAGES):
        await serialize(dut, timing_model.random_message(rng), ident)
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def tpserializer_reset(dut):
    """A fiducial restarts the frame, also together with an advance, and a reset clears it.

    A fiducial in the same cycle as an advance wins: the stream shows word 0
    of the new message and the following advance shows its word 1 (observed,
    intent unconfirmed).

    Propagation sampling: inputs are driven 2 ns after the edge and outputs
    are read 2 ns after the next one.
    """
    ident = env_int("ID_G", default=0)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_serializer(dut)
    first, second, third = (timing_model.random_message(rng) for _ in range(3))
    second_words = timing_model.message_words(second)

    await step(dut, fiducial=1, msg=first)
    for _ in range(10):
        await step(dut, advance=1)
    restarted = await step(dut, fiducial=1, advance=1, msg=second)
    assert (restarted.ready, restarted.data) == (1, second_words[0]), f"fiducial with advance gave {restarted}"
    nxt = await step(dut, advance=1)
    assert (nxt.ready, nxt.data) == (1, second_words[1]), f"advance after the restart gave {nxt}"

    await step(dut, advance=1)
    cleared = await step(dut, rst=1)
    check_static(cleared, ident)
    assert (cleared.ready, cleared.data) == (0, 0), f"reset left ready={cleared.ready} data=0x{cleared.data:04X}"
    after = await step(dut)
    assert after.ready == 0, "streamReady is high after the reset without a fiducial"

    await serialize(dut, third, ident)
    clock_task.cancel()


@pytest.mark.parametrize("ident", [0, 15])
def test_TPSerializer(ident):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.tpserializerwrapper",
        parameters={"ID_G": ident},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
