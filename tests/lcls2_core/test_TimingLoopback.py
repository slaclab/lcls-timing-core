#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""End-to-end loopback of the LCLS-II timing link through the production RTL.

Test methodology:
    Sweep: none, one compiled simulation of TimingFrameLoopbackWrapper. The
        chain is the production WordSerializer, TimingSerializer, and then
        TimingDeserializer and TimingFrameRx side by side on the serializer
        output.
    Stimulus: txRst is held for 3 txClk cycles, then released. A fiducial is
        pulsed once every 200 txClk together with the 944-bit message on the
        words port. The random run sends 21 seeded random messages; the link
        error run sends 5 and pulses rxDecErr="01" for one cycle on the
        symbol of word 27 of the second frame.
    Checks: the serializer output of every frame equals
        timing_model.message_frame of the sent message, symbol for symbol;
        the deserializer presents the 59 message words of every frame in
        order with offset 0 and last 1, pulses sof and eof once per frame and
        never crcErr; TimingFrameRx delivers frame N at the start of frame
        N + 1, so 21 frames give 20 strobes, each model-equal to the sent
        message with timingMessageValid=1 and no CRC or version flag. After a
        link error the deserializer abandons the interrupted frame (no eof,
        no crcErr) and TimingFrameRx delivers the words that arrived mixed
        with the tail of the previous frame (observed, intent unconfirmed);
        the frames after it are recovered by both receivers. Every checked
        output is resolvable on every sampled cycle.
    Timing: 10 ns txClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        and the combinational advance output are stable; inputs are driven
        at the same instant.
"""

from pathlib import Path
from typing import NamedTuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

FRAME_WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingFrameLoopbackWrapper.vhd"

SLOT = 200
LEAD = 20
TAIL = 150
RESET_CYCLES = 3
WORDS = timing_model.TIMING_MESSAGE_WORDS
MESSAGE_MASK = (1 << timing_model.TIMING_MESSAGE_BITS) - 1
STA_CRC = 3
STA_VERSION = 4

# Cycle of the first frame symbol after the fiducial beat, measured on the
# production chain and asserted on every frame.
ALIGN_AFTER_FIDUCIAL = 1
MID_FRAME_SYMBOL = 30  # word 27 of a frame: align, sof, sos, then word 0 at index 3

SAMPLED_OUTPUTS = {
    "data": "txData",
    "data_k": "txDataK",
    "fiducial": "desFiducial",
    "sof": "desSof",
    "eof": "desEof",
    "crc": "desCrcErr",
    "advance": "desAdvance",
    "word": "desStreamData",
    "offset": "desStreamOffset",
    "last": "desStreamLast",
    "message": "timingMessage",
    "strobe": "timingMessageStrobe",
    "valid": "timingMessageValid",
    "sta": "staData",
}


class Beat(NamedTuple):
    """Inputs of one txClk cycle."""

    fiducial: int = 0
    words: int | None = None
    dec_err: int = 0
    rst: int = 0


class Strobe(NamedTuple):
    """One timingMessageStrobe: its cycle, decoded message and flags."""

    cycle: int
    message: dict
    valid: int
    sta: int
    valid_after: int


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


def words_to_int(words):
    return sum(word << (16 * index) for index, word in enumerate(words))


def fiducial_beat(index):
    return LEAD + SLOT * index


def message_beats(messages, errors=None):
    """Beats for ``messages``: a short reset, idle, one fiducial per slot, then a tail."""
    errors = errors or {}
    beats = [Beat(rst=1)] * RESET_CYCLES + [Beat()] * (LEAD - RESET_CYCLES)
    for index, msg in enumerate(messages):
        slot = [Beat()] * SLOT
        slot[0] = Beat(fiducial=1, words=timing_model.pack_message(msg))
        for offset, dec_err in errors.get(index, {}).items():
            slot[offset] = slot[offset]._replace(dec_err=dec_err)
        beats += slot
    return beats + [Beat()] * TAIL


async def start_loopback(dut):
    """Drive defined inputs, start the clock, hold reset, release it."""
    dut.txRst.value = 1
    dut.fiducial.value = 0
    dut.ready.value = 1
    dut.words.value = 0
    dut.rxDecErr.value = 0
    dut.rxDspErr.value = 0
    clock_task = cocotb.start_soon(Clock(dut.txClk, 10, unit="ns").start(start_high=False))
    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.txClk)
    dut.txRst.value = 0
    return clock_task


async def run_beats(dut, beats):
    """Present one beat per cycle and return the outputs sampled on every cycle."""
    samples = []
    for beat in beats:
        await sample_after_tpd(dut.txClk, propagation_time=2)
        samples.append({key: resolved_int(getattr(dut, name)) for key, name in SAMPLED_OUTPUTS.items()})
        dut.fiducial.value = beat.fiducial
        if beat.words is not None:
            dut.words.value = beat.words
        dut.rxDecErr.value = beat.dec_err
        dut.txRst.value = beat.rst
    await sample_after_tpd(dut.txClk, propagation_time=2)
    samples.append({key: resolved_int(getattr(dut, name)) for key, name in SAMPLED_OUTPUTS.items()})
    return samples


def pulses(samples, key):
    return [cycle for cycle, sample in enumerate(samples) if sample[key]]


def sta_cycles(samples, bit):
    return [cycle for cycle, sample in enumerate(samples) if (sample["sta"] >> bit) & 1]


def strobes_of(samples):
    return [
        Strobe(
            cycle,
            timing_model.unpack_message(sample["message"]),
            sample["valid"],
            sample["sta"],
            samples[cycle + 1]["valid"],
        )
        for cycle, sample in enumerate(samples)
        if sample["strobe"]
    ]


def delivered_words(samples):
    """(cycle, word, offset, last) for every advance pulse of the deserializer."""
    return [(cycle, s["word"], s["offset"], s["last"]) for cycle, s in enumerate(samples) if s["advance"]]


def frame_of_cycle(cycle, count):
    """Index of the frame whose slot holds ``cycle``, or None before the first fiducial."""
    index = (cycle - LEAD) // SLOT
    return index if 0 <= index < count else None


def check_serializer_frames(samples, messages):
    """The serializer output of every frame equals the model frame, and idle elsewhere."""
    symbols = [(s["data"], s["data_k"]) for s in samples]
    aligns = [cycle for cycle, symbol in enumerate(symbols) if symbol == timing_model.ALIGN_SYMBOL]
    assert aligns == [fiducial_beat(i) + ALIGN_AFTER_FIDUCIAL for i in range(len(messages))], (
        f"frame starts at {aligns}"
    )
    covered = set()
    for index, (start, msg) in enumerate(zip(aligns, messages)):
        expected = timing_model.message_frame(msg)
        window = symbols[start:start + len(expected)]
        assert window == expected, (
            f"frame {index}: first difference at symbol "
            f"{next((i for i, (a, b) in enumerate(zip(window, expected)) if a != b), len(window))}"
        )
        decoded = timing_model.decode_frame(window)
        assert decoded.crc_ok, f"frame {index}: model decode flags a CRC mismatch on the serializer output"
        covered.update(range(start, start + len(expected)))
    for cycle, symbol in enumerate(symbols):
        if cycle not in covered and cycle > RESET_CYCLES + 1:
            assert symbol == timing_model.IDLE_SYMBOL, f"cycle {cycle}: 0x{symbol[0]:04X}/{symbol[1]:02b} outside a frame"


def check_delivery_offsets(samples, strobes, count):
    """Every strobe sits the same distance after the start of the following frame."""
    aligns = pulses(samples, "fiducial")
    assert len(aligns) >= len(strobes) + 1, f"fiducial pulses at {aligns}"
    offsets = {strobe.cycle - start for strobe, start in zip(strobes, aligns[1:])}
    assert len(offsets) == 1, f"strobe offsets from the next frame start differ: {sorted(offsets)}"
    return offsets.pop()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def loopback_lcls2_random_messages(dut):
    """21 seeded random messages are all recovered by the deserializer and 20 by the receiver.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    count = 21
    messages = [timing_model.random_message(rng) for _ in range(count)]

    clock_task = await start_loopback(dut)
    samples = await run_beats(dut, message_beats(messages))
    clock_task.cancel()

    check_serializer_frames(samples, messages)

    assert len(pulses(samples, "sof")) == count, f"sof pulses at {pulses(samples, 'sof')} (seed {seed})"
    assert pulses(samples, "sof") == pulses(samples, "fiducial"), "sof and fiducial do not pulse together"
    assert len(pulses(samples, "eof")) == count, f"eof pulses at {pulses(samples, 'eof')} (seed {seed})"
    assert pulses(samples, "crc") == [], f"crcErr pulsed at {pulses(samples, 'crc')} (seed {seed})"
    delivered = delivered_words(samples)
    assert len(delivered) == count * WORDS, f"{len(delivered)} words delivered for {count * WORDS} sent"
    for index, msg in enumerate(messages):
        chunk = delivered[index * WORDS:(index + 1) * WORDS]
        assert [(w, o, last) for _, w, o, last in chunk] == [(w, 0, 1) for w in timing_model.message_words(msg)], (
            f"frame {index}: deserializer words differ from the sent message (seed {seed})"
        )
        assert all(frame_of_cycle(cycle, count) == index for cycle, *_ in chunk), (
            f"frame {index}: words delivered outside the frame slot"
        )

    strobes = strobes_of(samples)
    assert len(strobes) == count - 1, f"{len(strobes)} strobes for {count} frames (seed {seed})"
    for index, strobe in enumerate(strobes):
        assert strobe.message == messages[index], f"message {index} differs from the sent message (seed {seed})"
        assert strobe.valid == 1, f"message {index}: timingMessageValid is {strobe.valid} (seed {seed})"
    assert sta_cycles(samples, STA_CRC) == [] and sta_cycles(samples, STA_VERSION) == [], "unexpected error status"
    dut._log.info(f"strobe sits {check_delivery_offsets(samples, strobes, count)} cycles after the next frame start")


@cocotb.test(timeout_time=500, timeout_unit="us")
async def loopback_lcls2_link_error(dut):
    """A decode error mid-frame abandons the frame in the deserializer; the frames after it are recovered.

    The deserializer gives the interrupted frame no eof and no crcErr.
    TimingFrameRx delivers the words that arrived in place of the interrupted
    frame, mixed with the tail of the previous one (observed, intent
    unconfirmed); its verdict follows the version word of that mixed message
    and, as at the receiver level, reaches timingMessageValid on the cycle
    after the strobe. Both receivers decode every frame after the error.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    count = 5
    bad = 1
    messages = [timing_model.random_message(rng) for _ in range(count)]
    errors = {bad: {ALIGN_AFTER_FIDUCIAL + MID_FRAME_SYMBOL: 0b01}}

    clock_task = await start_loopback(dut)
    samples = await run_beats(dut, message_beats(messages, errors))
    clock_task.cancel()

    assert len(pulses(samples, "sof")) == count, f"sof pulses at {pulses(samples, 'sof')} (seed {seed})"
    eofs = pulses(samples, "eof")
    assert [frame_of_cycle(cycle, count) for cycle in eofs] == [i for i in range(count) if i != bad], (
        f"eof landed in frames {[frame_of_cycle(cycle, count) for cycle in eofs]} (seed {seed})"
    )
    assert pulses(samples, "crc") == [], f"crcErr pulsed for an abandoned frame (seed {seed})"

    delivered = delivered_words(samples)
    for index, msg in enumerate(messages):
        chunk = [(w, o, last) for cycle, w, o, last in delivered if frame_of_cycle(cycle, count) == index]
        expected = [(w, 0, 1) for w in timing_model.message_words(msg)]
        if index == bad:
            assert chunk == expected[:len(chunk)] and 0 < len(chunk) < WORDS, (
                f"frame {index}: {len(chunk)} words delivered, not a proper prefix (seed {seed})"
            )
        else:
            assert chunk == expected, f"frame {index}: deserializer words differ from the sent message (seed {seed})"

    words_prev = timing_model.message_words(messages[bad - 1])
    words_bad = timing_model.message_words(messages[bad])
    arrived = MID_FRAME_SYMBOL - 3
    mixed = timing_model.unpack_message(
        ((words_to_int(words_prev) >> (16 * arrived)) | (words_to_int(words_bad[:arrived]) << (16 * (WORDS - arrived))))
        & MESSAGE_MASK
    )
    strobes = strobes_of(samples)
    expected_messages = [messages[0], mixed] + messages[2:count - 1]
    assert [s.message for s in strobes] == expected_messages, (
        f"delivered messages differ after the link error (seed {seed})"
    )
    assert strobes[1].valid_after == int(mixed["version"] == timing_model.TIMING_MESSAGE_VERSION), (
        "the partial frame verdict does not follow its version word"
    )
    assert strobes[2].valid_after == 1 and strobes[3].valid_after == 1, "frames after the error are not valid"
    assert sta_cycles(samples, STA_CRC) == [], "the link error raised a CRC flag"
    check_delivery_offsets(samples, strobes, count)


def test_TimingFrameLoopback():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingframeloopbackwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(FRAME_WRAPPER)]},
        extra_env=cocotb_filtered_env({}, cocotb_test_filter("loopback_lcls2_random_messages", "loopback_lcls2_link_error")),
    )
