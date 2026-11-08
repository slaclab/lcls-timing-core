#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingFrameRx test: model-encoded frames are decoded by the production receiver.

Test methodology:
    Sweep: none, one compiled simulation of TimingFrameRxWrapper. The
        known-issue entrypoint runs in its own simulation and only when
        RUN_KNOWN_ISSUE_TESTS=1.
    Stimulus: rxRst is held for 3 rxClk cycles with idle commas on the flat
        rx ports, then released. A driver presents one model-encoded symbol
        per rxClk. Frames are padded with idle commas to 200 symbols (100
        for the random run). Faults are applied by editing the symbol list
        (flipped CRC or data word, altered version, a segment of 58 or 60
        words, an empty frame) or by pulsing rxRst, rxDecErr or
        messageDelayRst for chosen cycles; messageDelay is stepped through
        0, 50 and 300 with a messageDelayRst pulse after each change.
        Every run starts with a 3 cycle reset so frames left in the delay
        line by an earlier run cannot leak into it.
    Checks: timingMessage is read only on timingMessageStrobe, which
        delivers the frame before the one whose start caused it, so N + 1
        frames are sent to check N. Decoded fields equal the model; a
        corrupted CRC word sets staData bit 3 once and the frame is still
        delivered; a version other than 1 is flagged on staData bit 4 and
        rxVersion and timingMessageValid is low from the cycle after the
        strobe; 58 and 60 word segments pass the CRC and decode with shifted
        alignment; sof, eof and fiducial pulse once per frame; an empty frame
        yields no strobe of its own; the strobe offset from the start of a
        frame changes by exactly the messageDelay difference; a reset in the
        middle of a frame suppresses it, while rxDecErr delivers the partial
        frame mixed with the previous one; 30 seeded random messages are all
        delivered with timingMessageValid=1. Every checked output is
        resolvable on every sampled cycle after reset release; a missing
        strobe fails after a bounded wait.
    Timing: 10 ns rxClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        are stable.
"""

import os
from pathlib import Path
from typing import NamedTuple

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingFrameRxWrapper.vhd"

FRAME_SLOTS = 200
STROBE_WAIT_CYCLES = 600
CHECKED_OUTPUTS = ("timingMessage", "timingMessageStrobe", "timingMessageValid", "staData")


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


def golden_message(pulse_id=0x0123456789ABCDEF):
    msg = timing_model.default_message()
    msg["pulseId"] = pulse_id
    msg["timeStamp"] = 0xFEDCBA9876543210
    msg["beamRequest"] = 0xA5A5A5A5
    msg["bsaDone"] = 0x0F0F0F0F0F0F0F0F
    msg["control"][17] = 0xBEEF
    return msg


def padded(symbols, slots=FRAME_SLOTS):
    return symbols + timing_model.idle_symbols(slots - len(symbols))


async def drive_symbols(dut, symbols):
    """Present one symbol per rxClk edge, then return."""
    for data, data_k in symbols:
        await RisingEdge(dut.rxClk)
        dut.rxData.value = data
        dut.rxDataK.value = data_k


async def start_receiver(dut):
    """Hold reset with idle commas, start the clock, release reset."""
    idle_data, idle_k = timing_model.IDLE_SYMBOL
    dut.rxRst.value = 1
    dut.rxData.value = idle_data
    dut.rxDataK.value = idle_k
    dut.rxDecErr.value = 0
    dut.rxDspErr.value = 0
    dut.messageDelay.value = 0
    dut.messageDelayRst.value = 0
    clock_task = cocotb.start_soon(Clock(dut.rxClk, 10, unit="ns").start(start_high=False))
    for _ in range(3):
        await RisingEdge(dut.rxClk)
    dut.rxRst.value = 0
    return clock_task


@cocotb.test(timeout_time=200, timeout_unit="us")
async def framerx_decodes_model_frames(dut):
    """The first strobe delivers frame A with every field equal to the model.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    msg_a = golden_message()
    msg_b = golden_message(pulse_id=msg_a["pulseId"] + 1)
    symbols = (
        padded(timing_model.message_frame(msg_a))
        + padded(timing_model.message_frame(msg_b))
        + timing_model.idle_symbols(100)
    )

    clock_task = await start_receiver(dut)
    for _ in range(20):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
    driver = cocotb.start_soon(drive_symbols(dut, symbols))

    strobe_seen = False
    for cycle in range(STROBE_WAIT_CYCLES):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
        sampled = {name: resolved_int(getattr(dut, name)) for name in CHECKED_OUTPUTS}
        if sampled["timingMessageStrobe"]:
            strobe_seen = True
            dut._log.info(f"first strobe on cycle {cycle}")
            assert sampled["timingMessageValid"] == 1, "strobe without timingMessageValid"
            assert not (sampled["staData"] >> 3) & 1, f"staData=0x{sampled['staData']:02x} flags a CRC error"
            decoded = timing_model.unpack_message(sampled["timingMessage"])
            assert decoded == msg_a, f"decoded message differs from frame A: {decoded}"
            break

    assert strobe_seen, f"no timingMessageStrobe within {STROBE_WAIT_CYCLES} cycles"

    driver.cancel()
    clock_task.cancel()


PARTIAL_STREAM = 2
PARTIAL_WORDS = 20
FULL_STREAMS = (1, 15)


def extension_slice(dut, stream_id):
    return (resolved_int(dut.extensionData) >> ((stream_id - 1) * 512)) & ((1 << 512) - 1)


@cocotb.test(timeout_time=200, timeout_unit="us")
async def framerx_extension_segments(dut):
    """Extension segments appear in their extensionData slice at the modeled placement.

    A 32-word segment fills its 512-bit slice with word 0 in the lowest
    bits. A 20-word segment is shifted in last and lands at the top of the
    slice, so its word 0 sits at word index 12; this placement was measured
    on the production receiver before the model encoded it.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    msg = golden_message()
    full = {stream_id: rng.getrandbits(512) for stream_id in FULL_STREAMS}
    partial_words = [rng.getrandbits(16) or 1 for _ in range(PARTIAL_WORDS)]
    segments = [
        timing_model.Segment(0, tuple(timing_model.message_words(msg))),
        *(timing_model.extension_segment(stream_id, full[stream_id]) for stream_id in FULL_STREAMS),
        timing_model.Segment(PARTIAL_STREAM, tuple(partial_words)),
    ]
    symbols = padded(timing_model.encode_frame(segments)) * 2 + timing_model.idle_symbols(100)

    clock_task = await start_receiver(dut)
    for _ in range(20):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
    driver = cocotb.start_soon(drive_symbols(dut, symbols))

    strobe_seen = False
    for _ in range(STROBE_WAIT_CYCLES):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
        if resolved_int(dut.timingMessageStrobe):
            strobe_seen = True
            break
    assert strobe_seen, f"no timingMessageStrobe within {STROBE_WAIT_CYCLES} cycles"

    # extensionValid is registered one cycle after the strobe.
    await sample_after_tpd(dut.rxClk, propagation_time=2)
    valid = resolved_int(dut.extensionValid)
    expected_valid = sum(1 << (stream_id - 1) for stream_id in (*FULL_STREAMS, PARTIAL_STREAM))
    assert valid == expected_valid, f"extensionValid=0x{valid:04x}, expected 0x{expected_valid:04x}"
    for stream_id in FULL_STREAMS:
        value = extension_slice(dut, stream_id)
        assert value == timing_model.extension_data(timing_model.extension_segment(stream_id, full[stream_id]).words)
        assert value == full[stream_id], f"stream {stream_id} slice differs from the sent 512 bits"
    value = extension_slice(dut, PARTIAL_STREAM)
    assert value == timing_model.extension_data(partial_words), (
        f"stream {PARTIAL_STREAM} slice 0x{value:0128x} differs from the modeled top-aligned placement"
    )
    assert (value >> (16 * 12)) & 0xFFFF == partial_words[0], "word 0 of a 20-word segment is not at word index 12"
    assert value & ((1 << (16 * 12)) - 1) == 0, "the low 12 words of a 20-word segment are not zero after reset"
    for stream_id in range(1, 16):
        if stream_id not in (*FULL_STREAMS, PARTIAL_STREAM):
            assert extension_slice(dut, stream_id) == 0, f"idle stream {stream_id} slice is not zero"

    driver.cancel()
    clock_task.cancel()




# Error, status, delay and random-traffic cases. These drive and sample from
# one loop so that every strobe has an exact cycle number.

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
KNOWN_ISSUE_ENTRYPOINT = "framerx_valid_qualifies_strobe"

RESET_CYCLES = 3
LEAD_CYCLES = 20
TAIL_CYCLES = 30
MESSAGE_WORDS = timing_model.TIMING_MESSAGE_WORDS
MESSAGE_MASK = (1 << timing_model.TIMING_MESSAGE_BITS) - 1
SAMPLED_OUTPUTS = {
    "message": "timingMessage",
    "strobe": "timingMessageStrobe",
    "valid": "timingMessageValid",
    "sta": "staData",
    "version": "rxVersion",
}
STA_SOF, STA_EOF, STA_FIDUCIAL, STA_CRC, STA_VERSION = range(5)


class Beat(NamedTuple):
    """Inputs of one rxClk cycle."""

    data: int
    data_k: int
    dec_err: int = 0
    rst: int = 0
    delay: int | None = None
    delay_rst: int = 0


class Strobe(NamedTuple):
    """One timingMessageStrobe: its cycle, decoded message, and the flags around it."""

    cycle: int
    message: dict
    valid: int
    sta: int
    valid_after: int
    sta_after: int
    version_after: int


IDLE_BEAT = Beat(*timing_model.IDLE_SYMBOL)


def frame_beats(symbols, slots):
    return [Beat(data, data_k) for data, data_k in padded(symbols, slots)]


def sequence(frames, slots=FRAME_SLOTS):
    """Beats for ``frames``: a short reset, idle, each frame padded to ``slots``, then idle."""
    beats = [IDLE_BEAT._replace(rst=1)] * RESET_CYCLES + [IDLE_BEAT] * (LEAD_CYCLES - RESET_CYCLES)
    for frame in frames:
        beats += frame_beats(frame, slots)
    return beats + [IDLE_BEAT] * TAIL_CYCLES


def frame_cycle(index, slots=FRAME_SLOTS):
    """Beat number of the first symbol (the alignment comma) of frame ``index``."""
    return LEAD_CYCLES + slots * index


def in_frame(cycle, index, slots=FRAME_SLOTS):
    return frame_cycle(index, slots) <= cycle < frame_cycle(index + 1, slots)


def words_to_int(words):
    return sum(word << (16 * index) for index, word in enumerate(words))


def message_of(msg):
    return timing_model.message_frame(msg)


def frame_of_words(words):
    return timing_model.encode_frame([timing_model.Segment(0, tuple(words))])


def with_version(msg, version):
    changed = dict(msg)
    changed["version"] = version
    return changed


def sent_messages(count=4):
    first = golden_message()
    return [golden_message(first["pulseId"] + index) for index in range(count)]


async def run_beats(dut, beats):
    """Present one beat per cycle and return the outputs sampled on every cycle."""
    samples = []
    for beat in beats:
        await sample_after_tpd(dut.rxClk, propagation_time=2)
        samples.append({key: resolved_int(getattr(dut, name)) for key, name in SAMPLED_OUTPUTS.items()})
        dut.rxData.value = beat.data
        dut.rxDataK.value = beat.data_k
        dut.rxDecErr.value = beat.dec_err
        dut.rxRst.value = beat.rst
        if beat.delay is not None:
            dut.messageDelay.value = beat.delay
        dut.messageDelayRst.value = beat.delay_rst
    return samples


def strobes_of(samples):
    records = []
    for cycle, sample in enumerate(samples):
        if sample["strobe"]:
            after = samples[cycle + 1]
            records.append(
                Strobe(
                    cycle,
                    timing_model.unpack_message(sample["message"]),
                    sample["valid"],
                    sample["sta"],
                    after["valid"],
                    after["sta"],
                    after["version"],
                )
            )
    return records


def sta_cycles(samples, bit):
    return [cycle for cycle, sample in enumerate(samples) if (sample["sta"] >> bit) & 1]


def decode_of_vector(vector):
    return timing_model.unpack_message(vector & MESSAGE_MASK)


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_crc_error_still_delivered(dut):
    """A frame with a bad CRC sets staData(3) and is still delivered (observed, intent unconfirmed).

    A flipped CRC low word sets staData bit 3 once and the frame is delivered
    with timingMessageValid=1 and the sent fields. A flipped data word sets
    the same bit and the corrupted payload is delivered with
    timingMessageValid=1.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    msg_a, msg_b, msg_c, _ = sent_messages()

    bad_crc = message_of(msg_a)
    bad_crc[-2] = (bad_crc[-2][0] ^ 0x0001, 0b00)
    samples = await run_beats(dut, sequence([message_of(msg_a), bad_crc, message_of(msg_b), message_of(msg_c)]))
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == [msg_a, msg_a, msg_b], "delivered messages differ with a flipped CRC low word"
    assert all(s.valid == 1 for s in strobes), f"timingMessageValid at the strobes: {[s.valid for s in strobes]}"
    crc_pulses = sta_cycles(samples, STA_CRC)
    assert len(crc_pulses) == 1 and in_frame(crc_pulses[0], 1), f"staData(3) pulses at {crc_pulses}"

    words = timing_model.message_words(msg_a)
    corrupted_words = list(words)
    corrupted_words[1] ^= 0x0010
    corrupted = decode_of_vector(words_to_int(corrupted_words))
    bad_data = frame_of_words(corrupted_words)
    bad_data[-2:] = message_of(msg_a)[-2:]
    samples = await run_beats(dut, sequence([message_of(msg_a), bad_data, message_of(msg_b), message_of(msg_c)]))
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == [msg_a, corrupted, msg_b], "delivered messages differ with a flipped data word"
    assert all(s.valid == 1 for s in strobes), f"timingMessageValid at the strobes: {[s.valid for s in strobes]}"
    crc_pulses = sta_cycles(samples, STA_CRC)
    assert len(crc_pulses) == 1 and in_frame(crc_pulses[0], 1), f"staData(3) pulses at {crc_pulses}"
    assert corrupted["pulseId"] == msg_a["pulseId"] ^ 0x0010, "corrupted payload is not the flipped pulse id bit"


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_version_mismatch(dut):
    """A version other than 1 is flagged on staData(4) and rxVersion until a version 1 frame arrives.

    The flag and timingMessageValid change on the cycle after the strobe, not
    on the strobe cycle itself; the gated entrypoint framerx_valid_qualifies_strobe
    holds the strobe-cycle expectation.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    msg_a, msg_b, msg_c, msg_d = sent_messages()
    sent = [msg_a, with_version(msg_b, 0x0000), msg_c, with_version(msg_d, 0x0002), msg_a]
    samples = await run_beats(dut, sequence([message_of(msg) for msg in sent] + [message_of(msg_b)]))
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == sent, "delivered messages differ from the sent frames"
    for index, strobe in enumerate(strobes):
        bad = strobe.message["version"] != timing_model.TIMING_MESSAGE_VERSION
        label = f"strobe {index} (version 0x{strobe.message['version']:04X})"
        assert strobe.valid_after == int(not bad), f"{label}: timingMessageValid on the next cycle is {strobe.valid_after}"
        assert (strobe.sta_after >> STA_VERSION) & 1 == int(bad), f"{label}: staData=0x{strobe.sta_after:02X} on the next cycle"
        assert strobe.version_after == strobe.message["version"], f"{label}: rxVersion 0x{strobe.version_after:08X}"
        if index + 1 < len(strobes):
            held = range(strobe.cycle + 1, strobes[index + 1].cycle + 1)
            levels = {(samples[cycle]["sta"] >> STA_VERSION) & 1 for cycle in held}
            assert levels == {int(bad)}, f"{label}: staData(4) does not hold until the next strobe"
    dut._log.info(f"rxVersion after each strobe: {[hex(s.version_after) for s in strobes]}")


@cocotb.test(
    timeout_time=400,
    timeout_unit="us",
    skip=KNOWN_ISSUE_SKIP,
)
async def framerx_valid_qualifies_strobe(dut):
    """timingMessageValid and staData(4) on the strobe cycle describe that strobe's message.

    Known issue: the version verdict is registered at the strobe, so on the
    strobe cycle itself timingMessageValid and staData(4) still show the
    previous frame's verdict. Run with RUN_KNOWN_ISSUE_TESTS=1.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    msg_a, msg_b, msg_c, msg_d = sent_messages()
    sent = [msg_a, with_version(msg_b, 0x0000), msg_c, with_version(msg_d, 0x0002), msg_a]
    samples = await run_beats(dut, sequence([message_of(msg) for msg in sent] + [message_of(msg_b)]))
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == sent, "delivered messages differ from the sent frames"
    for index, strobe in enumerate(strobes):
        bad = strobe.message["version"] != timing_model.TIMING_MESSAGE_VERSION
        label = f"strobe {index} (version 0x{strobe.message['version']:04X})"
        assert strobe.valid == int(not bad), f"{label}: timingMessageValid on the strobe cycle is {strobe.valid}"
        assert (strobe.sta >> STA_VERSION) & 1 == int(bad), f"{label}: staData=0x{strobe.sta:02X} on the strobe cycle"


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_length_mismatch(dut):
    """A 58 or 60 word segment passes the CRC and decodes with shifted alignment (observed, intent unconfirmed).

    The receiver has no length check. The 59 word shift register keeps the
    last 59 words it was given, so a segment one word short leaves the
    previous frame's last word at index 0 and every field is shifted up by
    one word, and a segment one word long loses its first word.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    msg_a, msg_b, msg_c, _ = sent_messages()
    words_a = timing_model.message_words(msg_a)
    words_b = timing_model.message_words(msg_b)
    short = words_b[:MESSAGE_WORDS - 1]
    long = words_b + [0x1234]
    expected_short = decode_of_vector((words_to_int(short) << 16) | words_a[-1])
    expected_long = decode_of_vector(words_to_int(long) >> 16)
    frames = [message_of(msg_a), frame_of_words(short), message_of(msg_c), frame_of_words(long), message_of(msg_a)]
    samples = await run_beats(dut, sequence(frames + [message_of(msg_b)]))
    strobes = strobes_of(samples)
    assert sta_cycles(samples, STA_CRC) == [], f"staData(3) pulsed at {sta_cycles(samples, STA_CRC)}"
    assert [s.message for s in strobes] == [msg_a, expected_short, msg_c, expected_long, msg_a], (
        "delivered messages differ from the shifted-alignment prediction"
    )
    # The shifted version word is not 1, so the verdict flags the frame by chance.
    assert strobes[1].valid_after == 0 and strobes[3].valid_after == 0, "shifted frames were not flagged by version"
    dut._log.info(
        f"shifted version words: short 0x{expected_short['version']:04X}, long 0x{expected_long['version']:04X}"
    )


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_status_bits(dut):
    """staData sof, eof and fiducial pulse once per frame and the strobe count is frames minus one.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    messages = sent_messages(5)
    frames = [message_of(msg) for msg in messages]
    samples = await run_beats(dut, sequence(frames))
    for name, bit in (("sof", STA_SOF), ("eof", STA_EOF), ("fiducial", STA_FIDUCIAL)):
        pulses = sta_cycles(samples, bit)
        assert len(pulses) == len(frames), f"staData {name} pulses at {pulses}"
        assert [index for index in range(len(frames)) if in_frame(pulses[index], index)] == list(range(len(frames))), (
            f"staData {name} does not pulse once inside each frame: {pulses}"
        )
    assert sta_cycles(samples, STA_SOF) == sta_cycles(samples, STA_FIDUCIAL), "sof and fiducial do not pulse together"
    assert sta_cycles(samples, STA_CRC) == [] and sta_cycles(samples, STA_VERSION) == [], "unexpected error status"
    strobes = strobes_of(samples)
    assert len(strobes) == len(frames) - 1, f"{len(strobes)} strobes for {len(frames)} frames"
    assert [s.message for s in strobes] == messages[:-1], "delivered messages differ from the sent frames"


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_empty_frame(dut):
    """An empty frame yields no strobe of its own and later frames decode correctly (observed, intent unconfirmed).

    In the sequence good, empty, good, good, good the strobe that the frame
    after the empty one would normally cause does not occur, and the empty
    frame is never delivered. The following frames are delivered with the
    correct content. The empty-frame handling of the delay line is the
    subject of the known-issue test in the TimingSerialDelay module.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    msg_a, msg_b, msg_c, msg_d = sent_messages()
    frames = [message_of(msg_a), timing_model.encode_frame([]), message_of(msg_b), message_of(msg_c), message_of(msg_d)]
    samples = await run_beats(dut, sequence(frames))
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == [msg_a, msg_b, msg_c], "delivered messages differ from the non-empty frames"
    assert all(s.valid == 1 for s in strobes), f"timingMessageValid at the strobes: {[s.valid for s in strobes]}"
    assert [index for index in range(len(frames)) if any(in_frame(s.cycle, index) for s in strobes)] == [1, 3, 4], (
        f"strobes landed at {[s.cycle for s in strobes]}"
    )
    for name, bit in (("sof", STA_SOF), ("eof", STA_EOF), ("fiducial", STA_FIDUCIAL)):
        assert len(sta_cycles(samples, bit)) == len(frames), f"staData {name} pulses at {sta_cycles(samples, bit)}"
    assert sta_cycles(samples, STA_CRC) == [], "the empty frame raised a CRC error"


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_message_delay(dut):
    """The strobe moves by exactly the messageDelay difference in rxClk cycles.

    messageDelay is stepped 0, 50, 300 and each change is followed by one
    messageDelayRst pulse; without the pulse a lowered delay would stall the
    delay line for 2^20 cycles. Each step sends frame A then frame B and
    measures the strobe that delivers A from the SOF symbol of B.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    msg_a, msg_b, _, _ = sent_messages()
    delays = (0, 50, 300)
    beats = [IDLE_BEAT._replace(rst=1)] * RESET_CYCLES + [IDLE_BEAT] * (LEAD_CYCLES - RESET_CYCLES)
    sof_cycles = []
    for delay in delays:
        beats += [IDLE_BEAT._replace(delay=delay), IDLE_BEAT._replace(delay_rst=1)] + [IDLE_BEAT] * 4
        beats += frame_beats(message_of(msg_a), FRAME_SLOTS)
        sof_cycles.append(len(beats) + 1)
        beats += frame_beats(message_of(msg_b), FRAME_SLOTS)
        beats += [IDLE_BEAT] * (delay + 100)
    samples = await run_beats(dut, beats)
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == [msg_a] * len(delays), "each step must deliver frame A once"
    assert all(s.valid == 1 for s in strobes), f"timingMessageValid at the strobes: {[s.valid for s in strobes]}"
    offsets = [strobe.cycle - sof for strobe, sof in zip(strobes, sof_cycles)]
    dut._log.info(f"strobe offsets from the SOF symbol for delays {delays}: {offsets}")
    for delay, offset in zip(delays, offsets):
        assert offset - offsets[0] == delay - delays[0], f"delay {delay}: offset {offset}, base offset {offsets[0]}"


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_reset_and_link_error(dut):
    """A reset suppresses the frame it interrupts; rxDecErr delivers the partial frame (observed, intent unconfirmed).

    rxRst for 2 cycles in the middle of frame B removes B and the next frames
    decode. rxDecErr for one cycle at the same point abandons B in the
    deserializer, but the delay line still receives the words sent before the
    error plus a stop token, so the strobe that would deliver B carries the
    previous frame's last words below the 27 words of B that arrived. The
    frames after it decode.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    await start_receiver(dut)
    msg_a, msg_b, msg_c, msg_d = sent_messages()
    frames = [message_of(msg) for msg in (msg_a, msg_b, msg_c, msg_d, msg_a)]
    interrupt = frame_cycle(1) + 30  # the symbol of word 27 of frame B

    beats = sequence(frames)
    for offset in (0, 1):
        beats[interrupt + offset] = beats[interrupt + offset]._replace(rst=1)
    samples = await run_beats(dut, beats)
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == [msg_a, msg_c, msg_d], "a reset in the middle of B did not suppress B"
    assert not any(in_frame(s.cycle, 2) for s in strobes), "a strobe followed the interrupted frame"
    assert len(sta_cycles(samples, STA_EOF)) == len(frames) - 1, "the interrupted frame reached its end of frame"

    words_a = timing_model.message_words(msg_a)
    words_b = timing_model.message_words(msg_b)
    arrived = 27
    mixed = decode_of_vector((words_to_int(words_a) >> (16 * arrived)) | (words_to_int(words_b[:arrived]) << (16 * (MESSAGE_WORDS - arrived))))
    beats = sequence(frames)
    beats[interrupt] = beats[interrupt]._replace(dec_err=0b01)
    samples = await run_beats(dut, beats)
    strobes = strobes_of(samples)
    assert [s.message for s in strobes] == [msg_a, mixed, msg_c, msg_d], "rxDecErr delivered an unexpected message"
    assert sta_cycles(samples, STA_CRC) == [], "rxDecErr raised a CRC error"
    assert len(sta_cycles(samples, STA_EOF)) == len(frames) - 1, "the interrupted frame reached its end of frame"
    assert strobes[1].valid_after == int(mixed["version"] == timing_model.TIMING_MESSAGE_VERSION), (
        "the partial frame verdict does not follow its version word"
    )
    assert strobes[2].valid_after == 1 and strobes[3].valid_after == 1, "frames after the error are not valid"


@cocotb.test(timeout_time=400, timeout_unit="us")
async def framerx_random_messages(dut):
    """30 seeded random messages are all delivered with the sent fields and timingMessageValid=1.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    await start_receiver(dut)
    count = 30
    messages = [timing_model.random_message(rng) for _ in range(count + 1)]
    samples = await run_beats(dut, sequence([message_of(msg) for msg in messages], slots=100))
    strobes = strobes_of(samples)
    assert len(strobes) == count, f"{len(strobes)} strobes for {count + 1} frames"
    for index, strobe in enumerate(strobes):
        assert strobe.message == messages[index], f"message {index} differs from the sent message (seed {seed})"
        assert strobe.valid == 1, f"message {index}: timingMessageValid is {strobe.valid} (seed {seed})"
    assert sta_cycles(samples, STA_CRC) == [] and sta_cycles(samples, STA_VERSION) == [], "unexpected error status"


def test_TimingFrameRx():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingframerxwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({}, cocotb_test_filter_excluding(KNOWN_ISSUE_ENTRYPOINT)),
    )


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "open question: TimingFrameRx timingMessageValid and staData(4) lag the strobe by one cycle; "
        "see https://github.com/slaclab/lcls-timing-core/issues/211; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_TimingFrameRx_known_issue_valid_on_strobe():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingframerxwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({}, cocotb_test_filter(KNOWN_ISSUE_ENTRYPOINT)),
    )
