#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGMini test: its frames match the model and the production receiver decodes them.

TPGMiniWrapper builds the TPGConfigType input from TPG_CONFIG_INIT_C with the
fields the generator reads replaced by flat ports, and feeds txData and
txDataK of the generator into a TimingFrameRx, so one simulation serves both
the leaf checks and the generator to receiver loopback.

Test methodology:
    Sweep: one compiled simulation with baseDivisor 100, NARRAYSBSA_G 2 and
        FixedRateDivisors 1 to 10 (one divisor per fixed rate bit). Frame
        counts are 8 (model match), 25 (fixed rates, so that divisor 10 fires
        twice), 12 (status and writes) and 12 (loopback).
    Stimulus: txRst is held for 3 txClk cycles, released, and held again for
        3 cycles at a fixed phase after a fiducial, so that the fixed rate
        dividers count from a known frame. pulseIdWrEn and intervalRst stay
        high (their TPG_CONFIG_INIT_C values) while pulseId is loaded with
        0x1000 and are released 30 cycles after the second reset, before the
        first frame; without that release the pulse id never advances.
        Mid-run writes are single cycle pulses of pulseIdWrEn (0x5000) and
        timeStampWrEn (seconds 7, nanoseconds 0x100) placed 20 cycles after
        a chosen fiducial.
    Checks: txData and txDataK carry one frame every 100 clocks, each
        symbol for symbol equal to timing_model.message_frame of its own
        decoded message, with crc_ok true, one segment on stream 0 and idle
        commas in between; the first frame carries pulse id 0x1000 and every
        later frame the previous one plus one; the message fields other than
        pulseId, timeStamp and fixedRates equal a zero message (version 1,
        acTimeSlot 1, mpsClass all zeros); fixedRates bit i is set in frame
        k exactly when k is at least 1 and a multiple of divisor i; the time
        stamp advances 70/13 ns per clock, so frame to frame by 538 or 539
        and by 7000/13 on average; statusNarraysbsa equals NARRAYSBSA_G;
        statusPulseId equals the pulse id of the frame whose fiducial is
        being sampled and statusTimeStamp equals its time stamp 50 cycles
        later; a pulseId write lands in the next frame and the sequence
        continues from it; a timeStamp write lands in the second following
        frame as seconds 7 and 0x100 + 533 ns (99 clocks of the step). The
        receiver strobes with timingMessageValid high, staData bits 3 and 4
        low on every cycle, and delivers the message of the frame sent one
        frame earlier, equal to the model vector, for 5 or more consecutive
        frames. Every checked output is resolvable on every sampled cycle
        after the first reset release.
    Timing: 10 ns txClk, 100 clock base period.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        are stable; stimulus changes are applied right after a sample.
"""

from pathlib import Path
from typing import NamedTuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    env_int,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TPGMiniWrapper.vhd"

BASE_DIVISOR = 100
FIXED_DIVISORS = tuple(range(1, 11))
LOADED_PULSE_ID = 0x1000
WRITTEN_PULSE_ID = 0x5000
WRITTEN_TIME = (7 << 32) | 0x100
STEP_NS_PER_FRAME = 7000 / 13
NS_AFTER_LOAD = 533
FRAME_SYMBOLS = len(timing_model.message_frame(timing_model.default_message()))
RESET_CYCLES = 3
RESET_AFTER_FIDUCIAL = 20
RELEASE_AFTER_RESET = 30
STATUS_TIME_OFFSET = 50
FIRST_FIDUCIAL_WAIT = 2 * BASE_DIVISOR


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


class Cycle(NamedTuple):
    """Outputs of one txClk cycle."""

    symbol: tuple
    fiducial: int
    status_pulse_id: int
    status_time_stamp: int
    strobe: int
    valid: int
    sta: int
    message: int | None


class Frame(NamedTuple):
    """One captured frame: the cycle of its alignment comma and its decoded message."""

    start: int
    message: dict
    vector: int


class Event(NamedTuple):
    """Port writes applied ``offset`` cycles after the fiducial of frame ``frame``."""

    frame: int
    offset: int
    values: dict


def pack_divisors(divisors):
    return sum(divisor << (20 * index) for index, divisor in enumerate(divisors))


def words_to_int(words):
    return sum(word << (16 * index) for index, word in enumerate(words))


def zero_message():
    """The message TPGMini leaves unchanged: version 1, time slot 1, no MPS class."""
    msg = timing_model.default_message()
    msg["mpsClass"] = [0] * len(msg["mpsClass"])
    msg["acTimeSlot"] = 1
    return msg


def expected_fixed_rates(frame, divisors=FIXED_DIVISORS):
    """Fixed rate bit i is set from frame divisor i on, then every divisor i frames."""
    return sum(1 << bit for bit, divisor in enumerate(divisors) if frame >= 1 and frame % divisor == 0)


async def sample(dut):
    """Wait one cycle and return its outputs."""
    await sample_after_tpd(dut.txClk, propagation_time=2)
    strobe = resolved_int(dut.timingMessageStrobe)
    return Cycle(
        (resolved_int(dut.txData), resolved_int(dut.txDataK)),
        resolved_int(dut.fiducial),
        resolved_int(dut.statusPulseId),
        resolved_int(dut.statusTimeStamp),
        strobe,
        resolved_int(dut.timingMessageValid),
        resolved_int(dut.staData),
        resolved_int(dut.timingMessage) if strobe else None,
    )


async def start_generator(dut, divisors=FIXED_DIVISORS):
    """Reset twice, load the pulse id, and release the load before the first frame.

    The second reset comes RESET_AFTER_FIDUCIAL cycles after a fiducial, so
    the next fiducial is the first one the fixed rate dividers count.
    """
    dut.txRst.value = 1
    dut.txRdy.value = 1
    dut.cfgBaseDivisor.value = BASE_DIVISOR
    dut.cfgFixedRateDivisors.value = pack_divisors(divisors)
    dut.cfgPulseId.value = LOADED_PULSE_ID
    dut.cfgPulseIdWrEn.value = 1
    dut.cfgTimeStamp.value = 0
    dut.cfgTimeStampWrEn.value = 0
    dut.cfgInterval.value = 0x488B
    dut.cfgIntervalRst.value = 1
    clock_task = cocotb.start_soon(Clock(dut.txClk, 10, unit="ns").start(start_high=False))
    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.txClk)
    dut.txRst.value = 0
    for _ in range(FIRST_FIDUCIAL_WAIT):
        if (await sample(dut)).fiducial:
            break
    else:
        raise AssertionError(f"no fiducial within {FIRST_FIDUCIAL_WAIT} cycles of the first reset release")
    for _ in range(RESET_AFTER_FIDUCIAL):
        await sample(dut)
    dut.txRst.value = 1
    for _ in range(RESET_CYCLES):
        await RisingEdge(dut.txClk)
    dut.txRst.value = 0
    for _ in range(RELEASE_AFTER_RESET):
        await sample(dut)
    dut.cfgPulseIdWrEn.value = 0
    dut.cfgIntervalRst.value = 0
    return clock_task


async def record(dut, frames, events=()):
    """Return the cycles of ``frames`` frame periods after the release, applying ``events``."""
    cycles = []
    pending = list(events)
    fiducials = []
    for _ in range(frames * BASE_DIVISOR + 10):
        cycle = await sample(dut)
        index = len(cycles)
        cycles.append(cycle)
        if cycle.fiducial:
            fiducials.append(index)
        for event in list(pending):
            if event.frame < len(fiducials) and index == fiducials[event.frame] + event.offset:
                for name, value in event.values.items():
                    getattr(dut, name).value = value
                pending.remove(event)
    assert not pending, f"events never applied: {pending}"
    return cycles


def fiducial_cycles(cycles):
    return [index for index, cycle in enumerate(cycles) if cycle.fiducial]


def split_frames(cycles):
    """Decode every complete frame, checking the wire encoding of each one.

    A frame runs from one alignment comma to the next. Each must equal the
    model encoding of its own decoded message, pass the CRC, hold one
    segment on stream 0 and be followed by idle commas only.
    """
    starts = [index for index, cycle in enumerate(cycles) if cycle.symbol == timing_model.ALIGN_SYMBOL]
    assert len(starts) >= 3, f"only {len(starts)} frames captured"
    frames = []
    for start, following in zip(starts, starts[1:]):
        assert following - start == BASE_DIVISOR, f"frame at cycle {start} is followed after {following - start} cycles"
        symbols = [cycle.symbol for cycle in cycles[start:following]]
        decoded = timing_model.decode_frame(symbols)
        assert decoded.crc_ok, f"frame at cycle {start} fails the model CRC check"
        assert len(decoded.segments) == 1, f"frame at cycle {start} has {len(decoded.segments)} segments"
        segment = decoded.segments[0]
        assert (segment.stream_id, segment.offset, segment.last) == (0, 0, 1), f"segment header {segment[:1]}"
        assert len(segment.words) == timing_model.TIMING_MESSAGE_WORDS
        vector = words_to_int(segment.words)
        message = timing_model.unpack_message(vector)
        assert symbols[:FRAME_SYMBOLS] == timing_model.message_frame(message), (
            f"frame at cycle {start} differs from the model encoding of its message"
        )
        assert all(symbol == timing_model.IDLE_SYMBOL for symbol in symbols[FRAME_SYMBOLS:]), (
            f"non-idle symbol between frames after cycle {start}"
        )
        frames.append(Frame(start, message, vector))
    return frames


def check_static_fields(frames):
    expected = zero_message()
    for index, frame in enumerate(frames):
        for name, value in expected.items():
            if name in ("pulseId", "timeStamp", "fixedRates"):
                continue
            assert frame.message[name] == value, f"frame {index}: {name} is {frame.message[name]}, expected {value}"


def check_time_stamps(frames, skip=()):
    """The time stamp advances 70/13 ns per clock: 538 or 539 per frame, with no drift."""
    stamps = [frame.message["timeStamp"] for frame in frames]
    for index in range(1, len(stamps)):
        if index not in skip:
            step = stamps[index] - stamps[index - 1]
            assert step in (538, 539), f"time stamp stepped by {step} ns into frame {index}"
    if not skip:
        drift = abs(stamps[-1] - stamps[0] - (len(stamps) - 1) * STEP_NS_PER_FRAME)
        assert drift < 1, f"time stamp drifted by {drift} ns over {len(stamps) - 1} frames"


@cocotb.test(timeout_time=500, timeout_unit="us")
async def tpgmini_frames_match_model(dut):
    """Every frame on txData equals the model encoding and the pulse id counts up from 0x1000.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_generator(dut)
    cycles = await record(dut, 8)
    frames = split_frames(cycles)
    assert len(frames) >= 7, f"only {len(frames)} complete frames"
    fiducials = fiducial_cycles(cycles)
    assert all(b - a == BASE_DIVISOR for a, b in zip(fiducials, fiducials[1:])), f"fiducial spacing {fiducials}"
    assert [frame.start for frame in frames] == [cycle + 2 for cycle in fiducials[: len(frames)]], (
        "a frame does not start two cycles after its fiducial"
    )
    pulse_ids = [frame.message["pulseId"] for frame in frames]
    assert pulse_ids == [LOADED_PULSE_ID + index for index in range(len(frames))], f"pulse ids {pulse_ids}"
    check_static_fields(frames)
    check_time_stamps(frames)
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def tpgmini_fixed_rates(dut):
    """Fixed rate bit i is set every divisor i frames, starting at frame divisor i.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_generator(dut)
    cycles = await record(dut, 25)
    frames = split_frames(cycles)
    assert len(frames) >= 24, f"only {len(frames)} complete frames"
    for index, frame in enumerate(frames):
        assert frame.message["fixedRates"] == expected_fixed_rates(index), (
            f"frame {index}: fixedRates {frame.message['fixedRates']:010b}, expected {expected_fixed_rates(index):010b}"
        )
    seen = [sum((frame.message["fixedRates"] >> bit) & 1 for frame in frames) for bit in range(len(FIXED_DIVISORS))]
    assert seen[0] == len(frames) - 1, "divisor 1 does not fire in every frame after the first"
    assert min(seen[1:]) >= 2, f"a fixed rate bit fired fewer than twice in {len(frames)} frames: {seen}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def tpgmini_status(dut):
    """The status outputs follow the frames and the pulse id and time stamp writes land in later frames.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_generator(dut)
    assert resolved_int(dut.statusNarraysbsa) == env_int("NARRAYSBSA_G", default=2), "statusNarraysbsa differs from NARRAYSBSA_G"
    events = [
        Event(2, 20, {"cfgPulseId": WRITTEN_PULSE_ID, "cfgPulseIdWrEn": 1}),
        Event(2, 21, {"cfgPulseIdWrEn": 0}),
        Event(5, 20, {"cfgTimeStamp": WRITTEN_TIME, "cfgTimeStampWrEn": 1}),
        Event(5, 21, {"cfgTimeStampWrEn": 0}),
    ]
    cycles = await record(dut, 12, events)
    frames = split_frames(cycles)
    assert len(frames) >= 10, f"only {len(frames)} complete frames"
    fiducials = fiducial_cycles(cycles)
    for index, frame in enumerate(frames):
        assert cycles[fiducials[index]].status_pulse_id == frame.message["pulseId"], (
            f"frame {index}: statusPulseId 0x{cycles[fiducials[index]].status_pulse_id:X} at its fiducial, "
            f"frame carries 0x{frame.message['pulseId']:X}"
        )
        if index >= 1:
            sampled = cycles[fiducials[index] + STATUS_TIME_OFFSET].status_time_stamp
            assert sampled == frame.message["timeStamp"], (
                f"frame {index}: statusTimeStamp 0x{sampled:X}, frame carries 0x{frame.message['timeStamp']:X}"
            )

    expected_ids = [LOADED_PULSE_ID, LOADED_PULSE_ID + 1, LOADED_PULSE_ID + 2] + [
        WRITTEN_PULSE_ID + index for index in range(len(frames) - 3)
    ]
    assert [frame.message["pulseId"] for frame in frames] == expected_ids, "pulse ids do not continue from the written value"

    stamps = [frame.message["timeStamp"] for frame in frames]
    assert stamps[6] - stamps[5] in (538, 539), "the frame before the time stamp load is not on the normal step"
    assert stamps[7] == WRITTEN_TIME + NS_AFTER_LOAD, (
        f"frame 7 time stamp 0x{stamps[7]:X}, expected 0x{WRITTEN_TIME + NS_AFTER_LOAD:X}"
    )
    check_time_stamps(frames, skip=(7,))
    check_static_fields(frames)
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def tpgmini_loopback_framerx(dut):
    """TimingFrameRx fed by the generator strobes with valid set and delivers each frame one frame late.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_generator(dut)
    cycles = await record(dut, 12)
    frames = split_frames(cycles)
    strobes = [index for index, cycle in enumerate(cycles) if cycle.strobe]
    assert len(strobes) >= 5, f"only {len(strobes)} strobes in {len(cycles)} cycles"
    assert all(not (cycle.sta >> 3) & 0b11 for cycle in cycles), "staData flags a CRC or version error on a generator frame"

    delivered = []
    for strobe in strobes:
        sent = [index for index, frame in enumerate(frames) if frame.start + BASE_DIVISOR <= strobe]
        assert sent, f"strobe at cycle {strobe} precedes the end of the first frame"
        frame_index = sent[-1]
        cycle = cycles[strobe]
        assert cycle.valid == 1, f"timingMessageValid is low on the strobe at cycle {strobe}"
        assert cycle.message == frames[frame_index].vector, (
            f"strobe at cycle {strobe} delivers a message that differs from the model decode of frame {frame_index}"
        )
        delivered.append(frame_index)
    assert delivered == list(range(delivered[0], delivered[0] + len(delivered))), f"frames delivered out of order: {delivered}"
    assert delivered[0] == 0, "the first strobe does not deliver the first frame"
    clock_task.cancel()


def test_TPGMini():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.tpgminiwrapper",
        parameters={"NARRAYSBSA_G": 2},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
