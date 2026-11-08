#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingMsgToAxiStream test: a strobed timing message leaves as AXI-Stream beats.

The module copies a timing message vector on timingMessageStrobe and shifts it
out SHIFT_SIZE_G bits at a time, least significant bits first, through an
AxiStreamFifoV2 that converts to the 8 byte output width. Its frame counter is
cleared every cycle, so the end-of-frame comparison never matches and the
stream never ends: after the message it keeps sending zero beats. The default
run asserts what the RTL does (observed, intent unconfirmed for the missing
tLast); the frame the shifter code was written to produce is a gated test.

Test methodology:
    Sweep: (VECTOR_SIZE_G, SHIFT_SIZE_G, COMMON_CLOCK_G) = (944, 32, true) with
        one shared 10 ns clock, and (944, 128, false) with timingClk 5.4 ns and
        axisClk 6.4 ns (unrelated). The generics are passed to the cocotb
        module through the environment because a test filter is set.
    Stimulus: a one cycle timingMessageStrobe carrying a model-packed random
        message (seed logged), an all-ones vector (shows the zero padding up
        to the shift width), and a second message sent while the output is
        stalled. Each scenario starts from a fresh 3 cycle reset followed by
        40 idle cycles, because the internal FIFO drops writes right after
        reset release. The AxiStreamSink drives M_AXIS_TREADY; its pause
        control gives a periodic 1 in 3 pause and a long stall.
    Checks: every handshake beat is logged cycle by cycle, because the stream
        has no tLast and a frame based sink would wait forever. Beats are
        compared with the vector as 64 bit words, tdata bytes, tkeep and
        tuser SOF; tvalid is resolvable on every sampled cycle after reset
        release and every beat field is resolvable. Waits are bounded loops of
        axisClk cycles.
    Timing: see the sweep; the log samples at each axisClk rising edge, which
        is the value the sink handshakes on.
    Propagation sampling: stimulus changes 2 ns after the clock edge, past
        the 1 ns TPD_G register delay.
"""

from dataclasses import dataclass
import itertools
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotbext.axi import AxiStreamBus, AxiStreamSink
import pytest

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    env_flag,
    env_int,
    hdl_parameters_from,
    parameter_case,
    run_lcls_vhdl_test,
    sample_after_tpd,
    start_lockstep_clocks,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingMsgToAxiStreamWrapper.vhd"
KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
KNOWN_ISSUE_ENTRYPOINT = "msgtoaxis_framing_intended"

COMMON_CLOCK = env_flag("COMMON_CLOCK_G", default=True)
SHIFT_SIZE = env_int("SHIFT_SIZE_G", default=32)
VECTOR_SIZE = env_int("VECTOR_SIZE_G", default=944)

RESET_CYCLES = 3
IDLE_CYCLES = 40
OUT_BYTES = 8
OUT_BITS = 8 * OUT_BYTES
WORD_MASK = (1 << OUT_BITS) - 1
# 64 bit output words that hold message bits, the padding up to a whole word is zero
DATA_WORDS = -(-VECTOR_SIZE // OUT_BITS)
# beats the shifter was written to send: eof is compared with VECTOR/SHIFT
INTENDED_BEATS = VECTOR_SIZE // SHIFT_SIZE + 1
INTENDED_BYTES = INTENDED_BEATS * SHIFT_SIZE // 8
SOF_BIT = 1
OBSERVE_CYCLES = 400
PERIODIC_PAUSE = (0, 0, 1)
STALL_CYCLES = 150


@dataclass(frozen=True)
class Beat:
    """One AXI-Stream handshake: ``cycle`` counts axisClk edges since the log started."""

    cycle: int
    data: int
    keep: int
    last: int
    user: int
    dest: int


class BeatLog:
    """Logs every tvalid and tready handshake on M_AXIS until stopped."""

    def __init__(self, dut):
        self.dut = dut
        self.beats = []
        self.cycle = 0
        self.unresolved = []
        self.stalled = 0
        self.task = cocotb.start_soon(self._run())

    async def _run(self):
        """Lifetime agent: samples the handshake at every axisClk edge until cancelled."""
        dut = self.dut
        while True:
            await RisingEdge(dut.axisClk)
            self.cycle += 1
            valid, ready = dut.M_AXIS_TVALID.value, dut.M_AXIS_TREADY.value
            if not (valid.is_resolvable and ready.is_resolvable):
                self.unresolved.append(f"cycle {self.cycle}: tvalid={valid} tready={ready}")
                continue
            if int(valid) and not int(ready):
                self.stalled += 1
            if not (int(valid) and int(ready)):
                continue
            fields = (dut.M_AXIS_TDATA, dut.M_AXIS_TKEEP, dut.M_AXIS_TLAST, dut.M_AXIS_TUSER, dut.M_AXIS_TDEST)
            if not all(field.value.is_resolvable for field in fields):
                self.unresolved.append(f"cycle {self.cycle}: unresolved beat field")
                continue
            self.beats.append(Beat(self.cycle, *(int(field.value) for field in fields)))

    def stop(self):
        self.task.cancel()
        assert not self.unresolved, f"unresolved outputs after reset release: {self.unresolved[:3]}"

    def beats_from(self, cycle):
        return [beat for beat in self.beats if beat.cycle >= cycle]


def message_words(vector):
    """The vector as the 64 bit words the output carries, least significant first."""
    return [(vector >> (OUT_BITS * index)) & WORD_MASK for index in range(DATA_WORDS)]


async def start_up(dut):
    """Drive resets and inputs, build the sink, then start the clocks (cocotbext-axi order)."""
    dut.timingRst.value = 1
    dut.axisRst.value = 1
    dut.timingMessageStrobe.value = 0
    dut.timingMessage.value = 0
    sink = AxiStreamSink(AxiStreamBus.from_prefix(dut, "M_AXIS"), dut.axisClk, dut.axisRst, reset_active_level=True)
    await Timer(1, unit="ns")
    if COMMON_CLOCK:
        clocks = [start_lockstep_clocks(dut.timingClk, dut.axisClk, period_ns=10)]
    else:
        clocks = [
            cocotb.start_soon(Clock(dut.timingClk, 5.4, unit="ns").start(start_high=False)),
            cocotb.start_soon(Clock(dut.axisClk, 6.4, unit="ns").start(start_high=False)),
        ]
    return sink, clocks


async def reset_and_idle(dut):
    """Reset both domains for 3 cycles, release, then idle past the FIFO reset recovery."""
    dut.timingMessageStrobe.value = 0
    dut.timingRst.value = 1
    dut.axisRst.value = 1
    for _ in range(RESET_CYCLES):
        await sample_after_tpd(dut.axisClk, propagation_time=2)
    dut.timingRst.value = 0
    dut.axisRst.value = 0
    for _ in range(IDLE_CYCLES):
        await sample_after_tpd(dut.axisClk, propagation_time=2)


async def send(dut, vector):
    """One timingClk cycle of timingMessageStrobe carrying ``vector``."""
    dut.timingMessage.value = vector
    dut.timingMessageStrobe.value = 1
    await sample_after_tpd(dut.timingClk, propagation_time=2)
    dut.timingMessageStrobe.value = 0
    dut.timingMessage.value = 0


async def wait_cycles(dut, count):
    for _ in range(count):
        await sample_after_tpd(dut.axisClk, propagation_time=2)


async def run_message(dut, vector, cycles):
    """Reset, send one message, return the beat log after ``cycles`` axisClk cycles."""
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await send(dut, vector)
    start = log.cycle
    await wait_cycles(dut, cycles)
    log.stop()
    return log, start


def assert_message_leads(beats, vector, label):
    """The first DATA_WORDS beats are the vector words in order, then zero, with tkeep full."""
    words = message_words(vector)
    assert len(beats) >= DATA_WORDS, f"{label}: only {len(beats)} beats, expected at least {DATA_WORDS}"
    got = [beat.data for beat in beats[:DATA_WORDS]]
    assert got == words, f"{label}: words differ at index {[i for i, (a, b) in enumerate(zip(got, words)) if a != b]}"
    assert all(beat.keep == (1 << OUT_BYTES) - 1 for beat in beats), f"{label}: a beat has tkeep other than all ones"
    assert all(beat.dest == 0 for beat in beats), f"{label}: a beat has a nonzero tdest"
    assert beats[0].user & (1 << SOF_BIT), f"{label}: first beat has no SOF in tuser"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def msgtoaxis_spike_and_content(dut):
    """The vector leaves least significant 64 bit word first, then zero beats.

    Propagation sampling: inputs change 2 ns after the clock edge. A random
    model message, an all-ones vector and a one-hot top bit are each sent after
    a fresh reset. No beat may appear before the strobe; the leading beats
    equal the vector words in order and the padding above bit VECTOR_SIZE_G is
    zero. In the 128 bit shift case the last data word is followed by one more
    zero word, so the zero tail is checked as well.
    """
    sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vectors = {
        "random": timing_model.pack_message(timing_model.random_message(rng)),
        "all ones": (1 << VECTOR_SIZE) - 1,
        "top bit": 1 << (VECTOR_SIZE - 1),
    }
    for label, vector in vectors.items():
        log, start = await run_message(dut, vector, 120)
        assert log.beats, f"{label}: no beat within 120 cycles of the strobe"
        assert log.beats[0].cycle > start, f"{label}: a beat appeared before the strobe"
        assert_message_leads(log.beats, vector, label)
        tail = log.beats[DATA_WORDS:]
        assert tail and all(beat.data == 0 for beat in tail), f"{label}: nonzero data after the message words"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def msgtoaxis_framing_observed(dut):
    """Observed, intent unconfirmed: tLast never asserts and zero beats follow the message.

    Propagation sampling: inputs change 2 ns after the clock edge. After one
    message the output is logged for 400 axisClk cycles. tLast is never high,
    the sink completes no frame, zero beats keep arriving to the end of the
    window, and SOF keeps being flagged on beats after the message.
    """
    sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vector = timing_model.pack_message(timing_model.random_message(rng))
    log, start = await run_message(dut, vector, OBSERVE_CYCLES)
    assert_message_leads(log.beats, vector, "framing")
    assert not any(beat.last for beat in log.beats), "tlast asserted: the frame ends, the observed behavior changed"
    assert sink.count() == 0, "the sink completed a frame, the observed behavior changed"
    late = log.beats_from(start + OBSERVE_CYCLES - 50)
    assert len(late) >= 20, f"only {len(late)} beats in the last 50 cycles, the stream stopped"
    assert all(beat.data == 0 for beat in log.beats[DATA_WORDS:]), "nonzero data after the message words"
    assert any(beat.user & (1 << SOF_BIT) for beat in log.beats[DATA_WORDS:]), "no SOF after the message words"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def msgtoaxis_framing_intended(dut):
    """Known issue: the message should be one frame of INTENDED_BEATS shifts ending in tlast.

    Propagation sampling: inputs change 2 ns after the clock edge. The eof
    comparison counts VECTOR_SIZE_G / SHIFT_SIZE_G + 1 shifts, so the sink
    must see one frame of that many shift widths, tlast on the last byte, the
    message bytes first and zero padding after, and nothing more for 100
    cycles. Gated by RUN_KNOWN_ISSUE_TESTS.
    """
    sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    vector = timing_model.pack_message(timing_model.random_message(rng))
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await send(dut, vector)
    for _ in range(OBSERVE_CYCLES):
        await sample_after_tpd(dut.axisClk, propagation_time=2)
        if sink.count():
            break
    beats_seen = len(log.beats)
    assert sink.count() == 1, (
        f"frame never terminates: no tlast after {beats_seen} beats in {OBSERVE_CYCLES} cycles, "
        f"expected one frame of {INTENDED_BYTES} bytes"
    )
    frame = sink.recv_nowait()
    message_bytes = VECTOR_SIZE // 8
    assert len(frame.tdata) == INTENDED_BYTES, f"frame has {len(frame.tdata)} bytes, expected {INTENDED_BYTES}"
    assert bytes(frame.tdata[:message_bytes]) == vector.to_bytes(message_bytes, "little"), "frame bytes differ from the vector"
    assert not any(frame.tdata[message_bytes:]), "nonzero padding after the message bytes"
    before = len(log.beats)
    await wait_cycles(dut, 100)
    log.stop()
    assert len(log.beats) == before, f"output continues after the frame: {len(log.beats) - before} more beats"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def msgtoaxis_backpressure(dut):
    """Observed, intent unconfirmed: the input FIFO never backpressures, a full FIFO drops later words.

    Propagation sampling: inputs change 2 ns after the clock edge. With the
    sink paused one cycle in three the whole message still arrives in order.
    With the sink stalled for 150 cycles the FIFO fills with the zero beats
    that follow message A; message B, sent into the full FIFO, never reaches
    the output, while message A is delivered intact once the stall ends.
    """
    sink, clocks = await start_up(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    message_a = timing_model.pack_message(timing_model.random_message(rng))
    message_b = timing_model.pack_message(timing_model.random_message(rng))

    sink.set_pause_generator(itertools.cycle(PERIODIC_PAUSE))
    log, start = await run_message(dut, message_a, 300)
    assert_message_leads(log.beats, message_a, "periodic pause")
    assert log.stalled > 0, "tvalid was never held off by tready low, the pause pattern had no effect"
    sink.clear_pause_generator()

    sink.pause = True
    await reset_and_idle(dut)
    log = BeatLog(dut)
    await send(dut, message_a)
    await wait_cycles(dut, STALL_CYCLES)
    assert not log.beats, "a beat was delivered during the stall"
    await send(dut, message_b)
    await wait_cycles(dut, 50)
    sink.pause = False
    await wait_cycles(dut, 300)
    log.stop()
    assert_message_leads(log.beats, message_a, "stalled")
    seen = {beat.data for beat in log.beats}
    lost = [word for word in message_words(message_b) if word and word in seen]
    assert not lost, f"message B reached the output ({len(lost)} words), the FIFO did not drop it"
    for clock in clocks:
        clock.cancel()


CASES = [
    parameter_case("common_clock_shift32", COMMON_CLOCK_G="true", SHIFT_SIZE_G=32, VECTOR_SIZE_G=944),
    parameter_case("async_clock_shift128", COMMON_CLOCK_G="false", SHIFT_SIZE_G=128, VECTOR_SIZE_G=944),
]


def run_case(params, test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingmsgtoaxistreamwrapper",
        parameters=hdl_parameters_from(params),
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(params, test_filter),
    )


@pytest.mark.parametrize("params", CASES)
def test_TimingMsgToAxiStream(params):
    run_case(params, cocotb_test_filter_excluding(KNOWN_ISSUE_ENTRYPOINT))


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TimingMsgToAxiStream never ends a frame; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
@pytest.mark.parametrize("params", CASES)
def test_TimingMsgToAxiStream_known_issue_framing(params):
    run_case(params, cocotb_test_filter(KNOWN_ISSUE_ENTRYPOINT))
