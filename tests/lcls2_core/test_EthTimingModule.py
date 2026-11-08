#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EthTimingModule test: LCLS-I timing stream strobes become Ethernet message frames.

With STREAM_L1_G true each timingStrobe copies the 704 bit timingStream into a
6 beat frame of 16 byte words (88 bytes, the last beat carries tkeep 0x00FF)
that crosses to ethClk through an AxiStreamFifoV2. A strobe is accepted only
when the previous frame has left the shift register and the timeout flag is
clear. The timeout flag starts set after reset and clears when any beat
arrives on the inbound AXI-Stream; it sets again after 2**29 ethClk cycles
without an inbound beat. That re-arm timeout is NOT simulated (about 5e8
cycles), so frames stopping 4.3 s after the last inbound beat is a scope
limit of this test, not a verified behavior. With STREAM_L1_G false the
module only forces the inbound slave ready and never drives the outbound
stream.

Test methodology:
    Sweep: STREAM_L1_G true and false, one compiled simulation each (the
        disabled generic runs only ethtiming_disabled_generic). Clocks:
        ethClk 8 ns and timingClk 5.4 ns, unrelated. The 704 bit stream is
        driven as raw bits, so frames are compared with the vector LSB first.
    Stimulus: a one cycle timingStrobe carrying
        pack_stream(random_stream(rng, allow_code_255=True)) (seed logged).
        Arming is one single-beat inbound frame from an AxiStreamSource.
        Each scenario starts from a fresh 3 cycle reset followed by 40 idle
        cycles. The AxiStreamSink drives M_AXIS_TREADY; its pause control gives
        a periodic 1 in 3 pause and a long stall.
    Checks: every outbound handshake beat is logged on ethClk and grouped
        into frames at tlast: beat count, tdata bytes, tkeep, tuser SOF and
        EOFE bits, tdest. S_AXIS_TREADY is 1 on every sampled cycle. Outputs
        are resolvable after reset release. Waits are bounded loops of
        ethClk cycles.
    Timing: see the sweep; the log samples at each ethClk rising edge.
    Propagation sampling: stimulus changes 2 ns after a clock edge, past the
        1 ns TPD_G register delay.
"""

from dataclasses import dataclass
import itertools
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotbext.axi import AxiStreamBus, AxiStreamSink, AxiStreamSource
import pytest

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/EthTimingModuleWrapper.vhd"

RESET_CYCLES = 3
IDLE_CYCLES = 40
ARM_SETTLE = 20
WORD_BYTES = 16
STREAM_BITS = 704
STREAM_BYTES = STREAM_BITS // 8
FRAME_BEATS = -(-STREAM_BYTES // WORD_BYTES)
FULL_KEEP = 0xFFFF
LAST_KEEP = 0x00FF
SOF_BIT = 1
EOFE_BIT = 0
FRAME_WAIT = 200
PERIODIC_PAUSE = (0, 0, 1)
DISABLED_ENTRYPOINT = "ethtiming_disabled_generic"


@dataclass(frozen=True)
class Beat:
    """One outbound handshake; ``cycle`` counts ethClk edges since the log started."""

    cycle: int
    data: int
    keep: int
    last: int
    user: int
    dest: int


class BeatLog:
    """Logs every M_AXIS handshake and checks S_AXIS_TREADY and tvalid every cycle."""

    def __init__(self, dut):
        self.dut = dut
        self.beats = []
        self.cycle = 0
        self.errors = []
        self.valid_cycles = 0
        self.task = cocotb.start_soon(self._run())

    async def _run(self):
        """Lifetime agent: samples the interfaces at every ethClk edge until cancelled."""
        dut = self.dut
        while True:
            await RisingEdge(dut.ethClk)
            self.cycle += 1
            valid, ready, in_ready = dut.M_AXIS_TVALID.value, dut.M_AXIS_TREADY.value, dut.S_AXIS_TREADY.value
            if not (valid.is_resolvable and ready.is_resolvable and in_ready.is_resolvable):
                self.errors.append(f"cycle {self.cycle}: unresolved tvalid={valid} tready={ready} S_AXIS_TREADY={in_ready}")
                continue
            if int(in_ready) != 1:
                self.errors.append(f"cycle {self.cycle}: S_AXIS_TREADY is {int(in_ready)}")
            if int(valid):
                self.valid_cycles += 1
            if not (int(valid) and int(ready)):
                continue
            fields = (dut.M_AXIS_TDATA, dut.M_AXIS_TKEEP, dut.M_AXIS_TLAST, dut.M_AXIS_TUSER, dut.M_AXIS_TDEST)
            if not all(field.value.is_resolvable for field in fields):
                self.errors.append(f"cycle {self.cycle}: unresolved beat field")
                continue
            self.beats.append(Beat(self.cycle, *(int(field.value) for field in fields)))

    def stop(self):
        self.task.cancel()
        assert not self.errors, f"interface errors: {self.errors[:3]}"

    def frames(self):
        """Complete frames (lists of beats ending at tlast) and the beats of a trailing partial frame."""
        done, current = [], []
        for beat in self.beats:
            current.append(beat)
            if beat.last:
                done.append(current)
                current = []
        return done, current


def frame_bytes(frame):
    """The frame payload: each beat's bytes kept by tkeep, least significant byte first."""
    payload = bytearray()
    for beat in frame:
        for lane in range(WORD_BYTES):
            if beat.keep >> lane & 1:
                payload.append(beat.data >> (8 * lane) & 0xFF)
    return bytes(payload)


def assert_frame(frame, vector, label):
    assert len(frame) == FRAME_BEATS, f"{label}: {len(frame)} beats, expected {FRAME_BEATS}"
    assert frame_bytes(frame) == vector.to_bytes(STREAM_BYTES, "little"), f"{label}: payload differs from the stream vector"
    assert [beat.keep for beat in frame] == [FULL_KEEP] * (FRAME_BEATS - 1) + [LAST_KEEP], (
        f"{label}: tkeep {[hex(beat.keep) for beat in frame]}"
    )
    assert [beat.last for beat in frame] == [0] * (FRAME_BEATS - 1) + [1], f"{label}: tlast pattern wrong"
    assert [bool(beat.user >> SOF_BIT & 1) for beat in frame] == [True] + [False] * (FRAME_BEATS - 1), (
        f"{label}: SOF in tuser {[hex(beat.user) for beat in frame]}"
    )
    assert not any(beat.user >> EOFE_BIT & 1 for beat in frame), f"{label}: EOFE set"
    assert all(beat.dest == 0 for beat in frame), f"{label}: nonzero tdest"


async def start_up(dut):
    """Drive resets and inputs, build source and sink, then start the clocks (cocotbext-axi order)."""
    dut.timingRst.value = 1
    dut.ethRst.value = 1
    dut.timingStrobe.value = 0
    dut.timingStream.value = 0
    source = AxiStreamSource(AxiStreamBus.from_prefix(dut, "S_AXIS"), dut.ethClk, dut.ethRst, reset_active_level=True)
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "M_AXIS"), dut.ethClk, dut.ethRst, reset_active_level=True)
    await Timer(1, unit="ns")
    clocks = [
        cocotb.start_soon(Clock(dut.timingClk, 5.4, unit="ns").start(start_high=False)),
        cocotb.start_soon(Clock(dut.ethClk, 8, unit="ns").start(start_high=False)),
    ]
    return source, sink, clocks


async def wait_eth(dut, count):
    for _ in range(count):
        await sample_after_tpd(dut.ethClk, propagation_time=2)


async def reset_and_idle(dut):
    """Reset both domains for 3 cycles, release, then idle past the FIFO reset recovery."""
    dut.timingStrobe.value = 0
    dut.timingRst.value = 1
    dut.ethRst.value = 1
    await wait_eth(dut, RESET_CYCLES)
    dut.timingRst.value = 0
    dut.ethRst.value = 0
    await wait_eth(dut, IDLE_CYCLES)


async def arm(dut, source):
    """One inbound single-beat frame clears the timeout flag; wait for it to cross to timingClk."""
    await source.send(bytes(WORD_BYTES))
    await source.wait()
    await wait_eth(dut, ARM_SETTLE)


async def strobe_schedule(dut, schedule):
    """Strobes by timingClk cycle offset: {offset: vector}; returns after the last offset."""
    last = max(schedule)
    for offset in range(last + 1):
        if offset in schedule:
            dut.timingStream.value = schedule[offset]
            dut.timingStrobe.value = 1
        await sample_after_tpd(dut.timingClk, propagation_time=2)
        dut.timingStrobe.value = 0
    dut.timingStream.value = 0


async def wait_frames(dut, log, count, limit=FRAME_WAIT):
    for _ in range(limit):
        if len(log.frames()[0]) >= count:
            return
        await sample_after_tpd(dut.ethClk, propagation_time=2)


def random_vectors(rng, count):
    return [timing_model.pack_stream(timing_model.random_stream(rng, allow_code_255=True)) for _ in range(count)]


@cocotb.test(timeout_time=200, timeout_unit="us")
async def ethtiming_disabled_generic(dut):
    """STREAM_L1_G false: the outbound stream stays idle and the inbound slave is always ready.

    Propagation sampling: stimulus changes 2 ns after a clock edge. Three
    strobes, then an arming beat and three more strobes, produce no outbound
    tvalid over at least 300 ethClk cycles, and S_AXIS_TREADY stays 1 throughout,
    including while the source drives a beat.
    """
    source, sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vectors = random_vectors(rng, 3)
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await strobe_schedule(dut, {0: vectors[0], 6: vectors[1], 12: vectors[2]})
    await arm(dut, source)
    await strobe_schedule(dut, {0: vectors[0], 6: vectors[1], 12: vectors[2]})
    await wait_eth(dut, 300)
    log.stop()
    assert log.valid_cycles == 0, f"tvalid was high on {log.valid_cycles} cycles with STREAM_L1_G false"
    assert not log.beats and sink.count() == 0
    assert log.cycle >= 300, "the log did not cover the window"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def ethtiming_unarmed(dut):
    """STREAM_L1_G true: nothing is sent until an inbound beat arrives.

    Propagation sampling: stimulus changes 2 ns after a clock edge. After a
    reset the timeout flag is set, so three strobes produce no outbound beat in
    300 ethClk cycles; after one inbound beat the next strobe produces a frame.
    """
    source, sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vectors = random_vectors(rng, 4)
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await strobe_schedule(dut, {0: vectors[0], 8: vectors[1], 16: vectors[2]})
    await wait_eth(dut, 300)
    assert log.valid_cycles == 0, f"{log.valid_cycles} tvalid cycles before any inbound beat"
    await arm(dut, source)
    await strobe_schedule(dut, {0: vectors[3]})
    await wait_frames(dut, log, 1)
    log.stop()
    frames, partial = log.frames()
    assert len(frames) == 1 and not partial, f"{len(frames)} frames after arming, expected 1"
    assert_frame(frames[0], vectors[3], "armed frame")
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def ethtiming_frame_content(dut):
    """Each strobe after arming is one 6 beat frame equal to the stream vector, LSB first.

    Propagation sampling: stimulus changes 2 ns after a clock edge. Five
    random streams, 30 timingClk cycles apart, each produce one frame: 16 byte
    words 1 to 5 with tkeep 0xFFFF and the 6th with tkeep 0x00FF and tlast, SOF
    in tuser on the first beat only, tdest 0, and the 88 payload bytes equal to
    the vector. The number of frames equals the number of strobes.
    """
    source, sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vectors = random_vectors(rng, 4) + [(1 << STREAM_BITS) - 1]
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await arm(dut, source)
    await strobe_schedule(dut, {30 * index: vector for index, vector in enumerate(vectors)})
    await wait_frames(dut, log, len(vectors))
    await wait_eth(dut, 50)
    log.stop()
    frames, partial = log.frames()
    assert not partial, f"{len(partial)} beats of an unfinished frame"
    assert len(frames) == len(vectors), f"{len(frames)} frames for {len(vectors)} strobes"
    for index, (frame, vector) in enumerate(zip(frames, vectors)):
        assert_frame(frame, vector, f"frame {index}")
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def ethtiming_strobe_during_frame(dut):
    """A strobe while a frame is still being shifted out is ignored, with no frame for it.

    Propagation sampling: stimulus changes 2 ns after a clock edge. Stream A
    is strobed, then B and C one and three timingClk cycles later (inside the
    6 cycle shift); only A is sent. D, strobed after the frame has finished,
    is sent as its own frame, so the module is not stuck.
    """
    source, sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    stream_a, stream_b, stream_c, stream_d = random_vectors(rng, 4)
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await arm(dut, source)
    await strobe_schedule(dut, {0: stream_a, 1: stream_b, 3: stream_c, 40: stream_d})
    await wait_frames(dut, log, 2)
    await wait_eth(dut, 50)
    log.stop()
    frames, partial = log.frames()
    assert not partial and len(frames) == 2, f"{len(frames)} frames, expected A and D only"
    assert_frame(frames[0], stream_a, "frame A")
    assert_frame(frames[1], stream_d, "frame D")
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def ethtiming_backpressure(dut):
    """Sink backpressure delays a frame without losing or reordering it.

    Propagation sampling: stimulus changes 2 ns after a clock edge. With the
    sink paused one cycle in three, three frames arrive complete and in order
    (and tvalid was held off for at least one cycle). With the sink stalled
    for 150 ethClk cycles after one strobe, no beat appears during the stall and
    the frame arrives complete after it ends.
    """
    source, sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vectors = random_vectors(rng, 4)

    sink.set_pause_generator(itertools.cycle(PERIODIC_PAUSE))
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await arm(dut, source)
    await strobe_schedule(dut, {40 * index: vector for index, vector in enumerate(vectors[:3])})
    await wait_frames(dut, log, 3)
    log.stop()
    frames, partial = log.frames()
    assert not partial and len(frames) == 3, f"{len(frames)} frames under the periodic pause"
    for index, frame in enumerate(frames):
        assert_frame(frame, vectors[index], f"paused frame {index}")
    sink.clear_pause_generator()

    sink.pause = True
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await arm(dut, source)
    await strobe_schedule(dut, {0: vectors[3]})
    await wait_eth(dut, 150)
    assert not log.beats, "a beat was delivered during the stall"
    assert log.valid_cycles > 0, "the frame was not waiting at the output during the stall"
    sink.pause = False
    await wait_frames(dut, log, 1)
    log.stop()
    frames, partial = log.frames()
    assert not partial and len(frames) == 1, f"{len(frames)} frames after the stall"
    assert_frame(frames[0], vectors[3], "stalled frame")
    for clock in clocks:
        clock.cancel()


CASES = [
    pytest.param("true", id="stream_l1_true"),
    pytest.param("false", id="stream_l1_false"),
]


@pytest.mark.parametrize("stream_l1", CASES)
def test_EthTimingModule(stream_l1):
    test_filter = cocotb_test_filter(DISABLED_ENTRYPOINT) if stream_l1 == "false" else cocotb_test_filter_excluding(DISABLED_ENTRYPOINT)
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.ethtimingmodulewrapper",
        parameters={"STREAM_L1_G": stream_l1},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({"STREAM_L1_G": stream_l1}, test_filter),
    )
