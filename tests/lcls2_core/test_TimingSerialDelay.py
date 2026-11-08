#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingSerialDelay test: frames come out one frame later, at a measured delay.

Test methodology:
    Sweep: one compiled simulation of TimingSerialDelayWrapper with
        NWORDS_G=4 and FDEPTH_G=16. The delay input is swept inside the
        entrypoints (0, 1, 37 and 200 clocks). The known-issue entrypoint
        runs in its own simulation and only when RUN_KNOWN_ISSUE_TESTS=1.
    Stimulus: every scenario is a list of per-cycle inputs applied from one
        drive-and-sample loop, after a 3 cycle reset. A frame is one
        fiducial_i cycle, then NWORDS_G advance_i cycles starting 3 cycles
        after the fiducial with the word on streamData (the timing of
        TimingDeserializer), with streamReady high from the fiducial to the
        last advance. Frames are 66 cycles apart unless stated, matching the
        legacy testbench. Scenarios: four frames at four delays; the delay
        raised and lowered between frames; a reset in the middle of a
        frame; 25 frames 20 cycles apart under a 600 cycle delay to overrun
        the 128 entry delay FIFO; a fiducial in the same cycle as the first
        advance; and an empty frame (fiducial with no advance).
    Checks: frame N is delivered on strobe_o, with valid_o high and frame_o
        equal to its words, on the cycle 4 + delay after the fiducial of
        frame N + 1 (a one frame lag); strobe_o is a single cycle pulse; no
        other strobe occurs; every output is resolvable on every cycle after
        reset release. Behaviors whose intent is unconfirmed are asserted as
        observed and say so in their docstring.
    Timing: 10 ns clk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        are stable; the next cycle's inputs are applied right after the
        sample.
"""

import os
from pathlib import Path
from typing import NamedTuple

import cocotb
import pytest
from cocotb.clock import Clock

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingSerialDelayWrapper.vhd"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
KNOWN_ISSUE_ENTRYPOINT = "serialdelay_empty_frame_header_behavior"

NWORDS = 4
FDEPTH = 16
FIFO_ENTRIES = 128  # 2**log2((NWORDS + 1) * FDEPTH)
FRAME_PERIOD = 66
FIRST_FIDUCIAL = 10
ADVANCE_OFFSET = 3
RESET_CYCLES = 3
# strobe_o rises this many cycles after fiducial(N + 1) + delay
LATENCY = 4


class Sample(NamedTuple):
    """Outputs of one clk cycle."""

    cycle: int
    strobe: int
    valid: int
    overflow: int
    frame: int


class Scenario:
    """Per-cycle inputs of one run."""

    def __init__(self, length, delay=0):
        self.length = length
        self.fiducial = [0] * length
        self.advance = [0] * length
        self.data = [0] * length
        self.ready = [0] * length
        self.rst = [1 if cycle < RESET_CYCLES else 0 for cycle in range(length)]
        self.delay = [delay] * length

    def add_frame(self, fiducial, words, advance_offset=ADVANCE_OFFSET):
        """Fiducial at ``fiducial``, then one advance per word from ``fiducial + advance_offset``."""
        self.fiducial[fiducial] = 1
        for cycle in range(fiducial, fiducial + advance_offset + len(words) + 1):
            self.ready[cycle] = 1
        for index, word in enumerate(words):
            self.advance[fiducial + advance_offset + index] = 1
            self.data[fiducial + advance_offset + index] = word

    def add_empty_frame(self, fiducial, ready=0):
        """A fiducial with no advance; ``ready`` is what streamReady carries around it."""
        self.fiducial[fiducial] = 1
        for cycle in range(fiducial, fiducial + ADVANCE_OFFSET + 1):
            self.ready[cycle] = ready

    def set_delay(self, first_cycle, delay):
        for cycle in range(first_cycle, self.length):
            self.delay[cycle] = delay


def resolved_int(handle, cycle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits at cycle {cycle}: {value}"
    return int(value)


def pack(words):
    return sum(word << (16 * index) for index, word in enumerate(words))


def tagged_words(tag):
    return [(tag << 8) | index for index in range(NWORDS)]


async def start_clock(dut):
    return cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))


async def run_scenario(dut, scenario):
    """Apply the inputs of each cycle, sample the outputs 2 ns after that cycle's edge."""
    assert len(dut.frame_o) == 16 * NWORDS, "the wrapper was built with a different NWORDS_G"
    samples = []
    for cycle in range(scenario.length):
        dut.rst.value = scenario.rst[cycle]
        dut.fiducial_i.value = scenario.fiducial[cycle]
        dut.advance_i.value = scenario.advance[cycle]
        dut.streamData.value = scenario.data[cycle]
        dut.streamReady.value = scenario.ready[cycle]
        dut.delay.value = scenario.delay[cycle]
        await sample_after_tpd(dut.clk, propagation_time=2)
        if cycle < RESET_CYCLES:
            samples.append(Sample(cycle, 0, 0, 0, 0))
            continue
        samples.append(
            Sample(
                cycle,
                resolved_int(dut.strobe_o, cycle),
                resolved_int(dut.valid_o, cycle),
                resolved_int(dut.overflow_o, cycle),
                resolved_int(dut.frame_o, cycle),
            )
        )
    return samples


def strobes_of(samples):
    return [sample for sample in samples if sample.strobe]


def fiducial_cycles(count, period=FRAME_PERIOD, first=FIRST_FIDUCIAL):
    return [first + period * index for index in range(count)]


def expected_strobe_cycle(next_fiducial, delay):
    return next_fiducial + delay + LATENCY


def assert_delivered(strobes, expected, label):
    """``expected`` is a list of (cycle, words); every strobe must have valid_o high."""
    got = [(strobe.cycle, strobe.frame) for strobe in strobes]
    want = [(cycle, pack(words)) for cycle, words in expected]
    assert got == want, f"{label}: strobes {[(c, hex(f)) for c, f in got]}, expected {[(c, hex(f)) for c, f in want]}"
    assert all(strobe.valid == 1 for strobe in strobes), f"{label}: a strobe came with valid_o low"


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_delay_accuracy(dut):
    """Frame N is delivered 4 + delay cycles after the fiducial of frame N + 1, for delay 0, 1, 37 and 200.

    Five random-word frames are sent per delay, so four strobes are expected:
    the last frame stays in the pipeline until another fiducial arrives.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    for delay in (0, 1, 37, 200):
        frames = [[rng.getrandbits(16) for _ in range(NWORDS)] for _ in range(5)]
        fiducials = fiducial_cycles(len(frames))
        scenario = Scenario(fiducials[-1] + delay + 100, delay)
        for fiducial, words in zip(fiducials, frames):
            scenario.add_frame(fiducial, words)
        samples = await run_scenario(dut, scenario)
        strobes = strobes_of(samples)
        expected = [
            (expected_strobe_cycle(fiducials[index + 1], delay), frames[index]) for index in range(len(frames) - 1)
        ]
        assert_delivered(strobes, expected, f"delay {delay} (seed {seed})")
        assert all(sample.overflow == 0 for sample in samples), f"delay {delay}: overflow_o asserted"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_delay_increase(dut):
    """Raising delay from 37 to 200 after frame 3 starts moves the strobes it applies to by exactly 163 cycles.

    The delay in force at the fiducial of frame N + 1 sets the strobe that
    delivers frame N, so the strobes for frames 1 and 2 keep the old delay and
    those for frames 3 and 4 use the new one.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    old, new = 37, 200
    frames = [tagged_words(tag) for tag in range(1, 6)]
    fiducials = fiducial_cycles(len(frames))
    scenario = Scenario(fiducials[-1] + new + 100, old)
    for fiducial, words in zip(fiducials, frames):
        scenario.add_frame(fiducial, words)
    scenario.set_delay(fiducials[2] + 10, new)
    samples = await run_scenario(dut, scenario)
    expected = [
        (expected_strobe_cycle(fiducials[1], old), frames[0]),
        (expected_strobe_cycle(fiducials[2], old), frames[1]),
        (expected_strobe_cycle(fiducials[3], new), frames[2]),
        (expected_strobe_cycle(fiducials[4], new), frames[3]),
    ]
    strobes = strobes_of(samples)
    assert_delivered(strobes, expected, "delay raised")
    shifted = strobes[2].cycle - expected_strobe_cycle(fiducials[3], old)
    assert shifted == new - old, f"frame 3 moved by {shifted} cycles, expected {new - old}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_delay_decrease_stalls(dut):
    """Lowering delay from 200 to 0 stalls the pipeline for the whole 5000 cycle window (observed, intent unconfirmed).

    The read side waits for the stored target count to equal its free running
    20 bit counter, so a target already in the past is only met when the
    counter wraps after 2**20 clocks. Eight frames are sent (48 FIFO entries,
    no overflow); the two frames queued before the change are delivered, and
    no strobe follows in the 5000 cycles after the first fiducial that used
    the lowered delay. The wrap itself is documented here and not simulated:
    it takes about a million clocks.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    old, new = 200, 0
    frames = [tagged_words(tag) for tag in range(1, 9)]
    fiducials = fiducial_cycles(len(frames))
    window = 5000
    scenario = Scenario(fiducials[3] + window + 1, old)
    for fiducial, words in zip(fiducials, frames):
        scenario.add_frame(fiducial, words)
    scenario.set_delay(fiducials[2] + 10, new)
    samples = await run_scenario(dut, scenario)
    expected = [
        (expected_strobe_cycle(fiducials[1], old), frames[0]),
        (expected_strobe_cycle(fiducials[2], old), frames[1]),
    ]
    assert_delivered(strobes_of(samples), expected, "delay lowered")
    assert samples[-1].cycle - fiducials[3] >= window, "the observation window is shorter than 5000 cycles"
    assert all(sample.overflow == 0 for sample in samples), "overflow_o asserted during the stall"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_reset_midframe(dut):
    """A reset in the middle of frame 3 removes everything queued; the next frames are delivered normally.

    Frames 1 and 2 are still waiting out a 100 cycle delay when the 2 cycle
    reset hits the advance words of frame 3. No strobe appears for them and
    valid_o stays low until frame 4 has been read back. The remaining
    advance words of frame 3 arrive with the write state machine idle and
    are ignored.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    delay = 100
    frames = [tagged_words(tag) for tag in range(1, 6)]
    fiducials = fiducial_cycles(len(frames))
    scenario = Scenario(fiducials[-1] + delay + 100, delay)
    for fiducial, words in zip(fiducials, frames):
        scenario.add_frame(fiducial, words)
    reset_start = fiducials[2] + ADVANCE_OFFSET + 1
    scenario.rst[reset_start] = 1
    scenario.rst[reset_start + 1] = 1
    samples = await run_scenario(dut, scenario)
    assert_delivered(
        strobes_of(samples),
        [(expected_strobe_cycle(fiducials[4], delay), frames[3])],
        "reset in the middle of frame 3",
    )
    stale = [s.cycle for s in samples if s.valid and reset_start + 2 <= s.cycle < fiducials[3] + delay]
    assert stale == [], f"valid_o was high before frame 4 was read back: cycles {stale}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_overflow(dut):
    """Holding more frames than the 128 entry FIFO stores asserts overflow_o and drops what does not fit (observed).

    25 frames 20 cycles apart under a 600 cycle delay need 150 entries.
    overflow_o rises on the first write that finds the FIFO full. Frames 1 to
    21 (126 entries, plus the start token of frame 22) are delivered intact,
    20 cycles apart; frame 22 is truncated and never completes, and frames 23
    to 25 are lost. Frames sent long after the burst show the recovery: the
    first of them is dropped (the reader, still inside the truncated frame,
    consumes its start token) and the following frames are delivered normally.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    delay, period, burst = 600, 20, 25
    burst_frames = [tagged_words(tag) for tag in range(1, burst + 1)]
    burst_fiducials = fiducial_cycles(burst, period)
    late_frames = [tagged_words(0x40 + index) for index in range(5)]
    late_fiducials = fiducial_cycles(len(late_frames), FRAME_PERIOD, 1300)
    scenario = Scenario(late_fiducials[-1] + delay + 100, delay)
    for fiducial, words in zip(burst_fiducials, burst_frames):
        scenario.add_frame(fiducial, words)
    for fiducial, words in zip(late_fiducials, late_frames):
        scenario.add_frame(fiducial, words)
    samples = await run_scenario(dut, scenario)

    overflow_cycles = [sample.cycle for sample in samples if sample.overflow]
    assert overflow_cycles, "overflow_o never asserted"
    assert all(cycle < burst_fiducials[-1] + 10 for cycle in overflow_cycles), "overflow_o asserted after the burst"
    stored = FIFO_ENTRIES // (NWORDS + 2)
    assert stored == 21
    expected = [
        (expected_strobe_cycle(burst_fiducials[index + 1], delay), burst_frames[index]) for index in range(stored)
    ]
    expected += [
        (expected_strobe_cycle(late_fiducials[index + 1], delay), late_frames[index])
        for index in range(1, len(late_frames) - 1)
    ]
    assert_delivered(strobes_of(samples), expected, "after overflow")
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_fiducial_with_advance(dut):
    """An advance_i in the fiducial cycle is ignored, so that frame is one word short (observed, intent unconfirmed).

    The RTL comment in the write state machine asks whether fiducial_i and
    advance_i can assert at the same time. When they do, the write state
    machine is idle and only starts a frame, so the word presented in that
    cycle is lost; the three words that follow are stored and the frame is
    delivered with the previous frame's last word in position 0 (the output
    is a shift register).

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    frames = [tagged_words(tag) for tag in range(1, 5)]
    fiducials = fiducial_cycles(len(frames))
    scenario = Scenario(fiducials[-1] + 100, 0)
    for index, (fiducial, words) in enumerate(zip(fiducials, frames)):
        scenario.add_frame(fiducial, words, advance_offset=0 if index == 1 else ADVANCE_OFFSET)
    samples = await run_scenario(dut, scenario)
    short = [frames[0][-1]] + frames[1][1:]
    assert_delivered(
        strobes_of(samples),
        [
            (expected_strobe_cycle(fiducials[1], 0), frames[0]),
            (expected_strobe_cycle(fiducials[2], 0), short),
            (expected_strobe_cycle(fiducials[3], 0), frames[2]),
        ],
        "fiducial with advance",
    )
    clock_task.cancel()


def empty_frame_scenario(ready):
    """Frames A, empty, B, C, D at 66 cycle spacing, delay 0, with ``ready`` around the empty frame."""
    frames = {"A": tagged_words(1), "B": tagged_words(2), "C": tagged_words(3), "D": tagged_words(4)}
    fiducials = fiducial_cycles(5)
    scenario = Scenario(fiducials[-1] + 100, 0)
    scenario.add_frame(fiducials[0], frames["A"])
    scenario.add_empty_frame(fiducials[1], ready=ready)
    scenario.add_frame(fiducials[2], frames["B"])
    scenario.add_frame(fiducials[3], frames["C"])
    scenario.add_frame(fiducials[4], frames["D"])
    return scenario, frames, fiducials


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_empty_frame_observed(dut):
    """An empty frame (fiducial, no advance) makes no strobe and swallows the next frame's fiducial (observed).

    The empty frame's fiducial writes a start token; with no words there is no
    stop token, so the write state machine stays in its message state and the
    fiducial of frame B is ignored: B's words are appended behind the empty
    frame's token. Frame A is delivered at the empty frame's delayed fiducial
    (the next token), the empty frame has no strobe, and B is delivered at
    the delayed fiducial of C as usual. streamReady has no effect: the same
    stimulus with streamReady low and high around the empty frame gives
    identical outputs, although the RTL header says ready is tested on the
    fiducial.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    runs = []
    for ready in (0, 1):
        scenario, frames, fiducials = empty_frame_scenario(ready)
        runs.append(await run_scenario(dut, scenario))
    assert runs[0] == runs[1], "streamReady changed the outputs; the RTL now reads it"
    assert_delivered(
        strobes_of(runs[0]),
        [
            (expected_strobe_cycle(fiducials[1], 0), frames["A"]),
            (expected_strobe_cycle(fiducials[3], 0), frames["B"]),
            (expected_strobe_cycle(fiducials[4], 0), frames["C"]),
        ],
        "empty frame",
    )
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def serialdelay_empty_frame_header_behavior(dut):
    """The RTL header says stream_i ready is tested on the fiducial: an empty frame must not start a frame.

    With streamReady low around the empty frame no frame should be started,
    so frame B has its own start token and frame A is delivered at the delayed
    fiducial of B, not at the delayed fiducial of the empty frame. The
    current RTL never reads streamReady and fails this test.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    scenario, frames, fiducials = empty_frame_scenario(0)
    samples = await run_scenario(dut, scenario)
    strobes = strobes_of(samples)
    want_a = expected_strobe_cycle(fiducials[2], 0)
    got = [(strobe.cycle, strobe.frame) for strobe in strobes]
    early = [cycle for cycle, _ in got if cycle == expected_strobe_cycle(fiducials[1], 0)]
    assert not early, (
        "empty frame merged into the next frame: "
        f"frame A was delivered at cycle {early[0]}, the delayed fiducial of the empty frame, "
        f"expected cycle {want_a}, the delayed fiducial of frame B"
    )
    want = [
        (want_a, pack(frames["A"])),
        (expected_strobe_cycle(fiducials[3], 0), pack(frames["B"])),
        (expected_strobe_cycle(fiducials[4], 0), pack(frames["C"])),
    ]
    assert got == want, f"empty frame merged into the next frame: strobes {[(c, hex(f)) for c, f in got]}"
    clock_task.cancel()


def test_TimingSerialDelay():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingserialdelaywrapper",
        parameters={"NWORDS_G": NWORDS, "FDEPTH_G": FDEPTH},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({}, cocotb_test_filter_excluding(KNOWN_ISSUE_ENTRYPOINT)),
    )


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TimingSerialDelay never reads stream_i.ready, so an empty frame merges into the next frame; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_TimingSerialDelay_known_issue_empty_frame():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingserialdelaywrapper",
        parameters={"NWORDS_G": NWORDS, "FDEPTH_G": FDEPTH},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({}, cocotb_test_filter(KNOWN_ISSUE_ENTRYPOINT)),
    )
