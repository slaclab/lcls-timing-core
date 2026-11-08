#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingMsgDelay test: each message comes out unchanged, a fixed delay later.

Test methodology:
    Sweep: FIFO_ADDR_WIDTH_G in 4 and 7, one compiled simulation each. The
        RTL does not use the generic (both FIFOs are built with ADDR_WIDTH_G
        9), so both builds must behave identically; the FIFO limit case
        checks that. Inside the entrypoints delay is swept over 0 to 15
        (to find the smallest value that delivers), then the smallest
        delivering value, 10, 1000 and 65535.
    Stimulus: every scenario is a list of per-cycle inputs applied from one
        drive-and-sample loop after a 3 cycle reset. A message is one
        timingMessageStrobeIn cycle with a model-packed 944 bit vector on
        timingMessageIn. Messages are sent no earlier than cycle 30, after
        the internal FIFOs have left reset. Scenarios: one message per delay;
        three messages 5 cycles apart; two messages queued when timingRst
        pulses for 2 cycles; delay lowered while messages are queued and a
        message sent after the change; strobes on consecutive cycles; and
        520 messages 3 cycles apart under a 2000 cycle delay.
    Checks: timingMessageOut equals the model message with the unused bits
        zero, read on timingMessageStrobeOut, which is a single cycle pulse
        delay - 1 cycles after the input strobe; delivery order equals send
        order; the strobe is resolvable on every cycle after reset release
        and the message on every strobe. Behaviors whose intent is unconfirmed are asserted as
        observed and say so in their docstring.
    Timing: 10 ns timingClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        are stable; the next cycle's inputs are applied right after the
        sample.
"""

from pathlib import Path
from typing import NamedTuple

import cocotb
import pytest
from cocotb.clock import Clock

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingMsgDelayWrapper.vhd"

RESET_CYCLES = 3
FIRST_SEND = 30
# strobe out rises this many cycles before input strobe + delay
LATENCY = 1
FIFO_DEPTH = 512  # both FIFOs hard-code ADDR_WIDTH_G => 9
UNUSED_OFFSET, UNUSED_WIDTH, _ = timing_model.field_layout(timing_model.MESSAGE_FIELDS)["unused"]
UNUSED_MASK = ((1 << UNUSED_WIDTH) - 1) << UNUSED_OFFSET
PROBE_DELAYS = range(16)
PROBE_WINDOW = 120


class Sample(NamedTuple):
    """Outputs of one timingClk cycle; ``message`` is only read on a strobe."""

    cycle: int
    strobe: int
    message: int | None


class Scenario:
    """Per-cycle inputs of one run."""

    def __init__(self, length, delay=0):
        self.length = length
        self.strobe = [0] * length
        self.message = [0] * length
        self.rst = [1 if cycle < RESET_CYCLES else 0 for cycle in range(length)]
        self.delay = [delay] * length

    def send(self, cycle, message):
        self.strobe[cycle] = 1
        self.message[cycle] = message

    def set_delay(self, first_cycle, delay):
        for cycle in range(first_cycle, self.length):
            self.delay[cycle] = delay


def resolved_int(handle, cycle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits at cycle {cycle}: {value}"
    return int(value)


async def start_clock(dut):
    return cocotb.start_soon(Clock(dut.timingClk, 10, unit="ns").start(start_high=False))


async def run_scenario(dut, scenario):
    """Apply the inputs of each cycle, sample the outputs 2 ns after that cycle's edge.

    timingMessageOut is read only while the strobe is high: it is qualified by
    the strobe and carries unwritten FIFO data (U in simulation) from reset
    release until the first message has passed (observed, intent unconfirmed).
    """
    samples = []
    for cycle in range(scenario.length):
        dut.timingRst.value = scenario.rst[cycle]
        dut.timingMessageStrobeIn.value = scenario.strobe[cycle]
        dut.timingMessageIn.value = scenario.message[cycle]
        dut.delay.value = scenario.delay[cycle]
        await sample_after_tpd(dut.timingClk, propagation_time=2)
        if cycle < RESET_CYCLES:
            samples.append(Sample(cycle, 0, None))
            continue
        strobe = resolved_int(dut.timingMessageStrobeOut, cycle)
        message = resolved_int(dut.timingMessageOut, cycle) if strobe else None
        samples.append(Sample(cycle, strobe, message))
    return samples


def strobes_of(samples):
    return [sample for sample in samples if sample.strobe]


def new_messages(rng, count):
    """``count`` random model messages as (message dict, 944 bit vector) pairs."""
    messages = [timing_model.random_message(rng) for _ in range(count)]
    return [(message, timing_model.pack_message(message)) for message in messages]


def assert_delivered(strobes, expected, label):
    """``expected`` is a list of (cycle, vector)."""
    got = [(strobe.cycle, strobe.message) for strobe in strobes]
    assert [cycle for cycle, _ in got] == [cycle for cycle, _ in expected], (
        f"{label}: strobe cycles {[cycle for cycle, _ in got]}, expected {[cycle for cycle, _ in expected]}"
    )
    for (cycle, message), (_, vector) in zip(got, expected):
        assert message == vector, f"{label}: the message delivered at cycle {cycle} differs from the one sent"


async def delivers(dut, delay, vector):
    """Send ``vector`` with ``delay`` and return the cycle offset of its strobe, or None.

    The input carries ones in the unused bits; the delivered message must not.
    """
    scenario = Scenario(FIRST_SEND + PROBE_WINDOW, delay)
    scenario.send(FIRST_SEND, vector | UNUSED_MASK)
    strobes = strobes_of(await run_scenario(dut, scenario))
    assert len(strobes) <= 1, f"delay {delay}: {len(strobes)} strobes for one message"
    if not strobes:
        return None
    assert strobes[0].message == vector, f"delay {delay}: the delivered message differs from the one sent"
    return strobes[0].cycle - FIRST_SEND


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def msgdelay_small_delay_spike_and_accuracy(dut):
    """Delays below the FIFO latency never deliver; from the smallest delivering delay on the offset is delay - 1.

    Delays 0 to 15 are tried with one message each to find the smallest one
    that delivers inside a 120 cycle window. The read side compares the
    stored time to a free running 32 bit counter for equality, so a delay too
    short for the message to cross the FIFO is only met after the counter
    wraps (2**32 clocks, documented here and not simulated); that part is
    observed, intent unconfirmed. Delays from the smallest delivering value
    up deliver exactly delay - 1 cycles after the input strobe. 10, 1000 and
    65535 follow, the last being the maximum of the 16 bit input. The input
    carries ones in the 13 unused bits; the output has them zero.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    (_, vector), = new_messages(rng, 1)

    offsets = {delay: await delivers(dut, delay, vector) for delay in PROBE_DELAYS}
    smallest = min(delay for delay, offset in offsets.items() if offset is not None)
    dut._log.info(f"smallest delivering delay {smallest}; offsets {offsets}")
    assert 2 <= smallest < PROBE_DELAYS[-1], f"smallest delivering delay {smallest} is outside the probed range"
    for delay in PROBE_DELAYS:
        if delay < smallest:
            assert offsets[delay] is None, f"delay {delay} delivered although {smallest} is the smallest"
        else:
            assert offsets[delay] == delay - LATENCY, f"delay {delay}: offset {offsets[delay]}, expected {delay - LATENCY}"

    for delay in (10, 1000, 65535):
        (_, vector), = new_messages(rng, 1)
        scenario = Scenario(FIRST_SEND + delay + 100, delay)
        scenario.send(FIRST_SEND, vector | UNUSED_MASK)
        strobes = strobes_of(await run_scenario(dut, scenario))
        assert_delivered(strobes, [(FIRST_SEND + delay - LATENCY, vector)], f"delay {delay} (seed {seed})")
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def msgdelay_ordering(dut):
    """Several messages in flight come out in order with their input spacing, 5 cycles apart.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    delay = 100
    sent = new_messages(rng, 3)
    scenario = Scenario(FIRST_SEND + delay + 100, delay)
    cycles = [FIRST_SEND + 5 * index for index in range(len(sent))]
    for cycle, (_, vector) in zip(cycles, sent):
        scenario.send(cycle, vector)
    strobes = strobes_of(await run_scenario(dut, scenario))
    expected = [(cycle + delay - LATENCY, vector) for cycle, (_, vector) in zip(cycles, sent)]
    assert_delivered(strobes, expected, f"ordering (seed {seed})")
    for strobe, (message, _) in zip(strobes, sent):
        assert timing_model.unpack_message(strobe.message) == message
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def msgdelay_reset_drops_queue(dut):
    """timingRst for 2 cycles drops the messages still waiting; a message sent afterwards is delivered.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    delay = 100
    queued = new_messages(rng, 2)
    (_, after), = new_messages(rng, 1)
    reset_start = FIRST_SEND + 30
    after_cycle = reset_start + 30
    scenario = Scenario(after_cycle + delay + 100, delay)
    scenario.send(FIRST_SEND, queued[0][1])
    scenario.send(FIRST_SEND + 5, queued[1][1])
    scenario.rst[reset_start] = 1
    scenario.rst[reset_start + 1] = 1
    scenario.send(after_cycle, after)
    strobes = strobes_of(await run_scenario(dut, scenario))
    assert_delivered(strobes, [(after_cycle + delay - LATENCY, after)], f"reset (seed {seed})")
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def msgdelay_delay_decrease(dut):
    """Lowering delay leaves queued messages alone and stalls a message sent afterwards (observed, intent unconfirmed).

    Messages 1 and 2 are written under a 1000 cycle delay and keep their
    stored delivery times after the delay drops to 10. Message 3, written
    after the change, has a delivery time that has already passed by the
    time the reader reaches it behind messages 1 and 2, and equality is only
    met when the 32 bit counter wraps (2**32 clocks, documented here and not
    simulated), so no strobe follows for the 5000 cycles after it is sent.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    old, new = 1000, 10
    sent = new_messages(rng, 3)
    third_cycle = FIRST_SEND + 70
    window = 5000
    scenario = Scenario(third_cycle + window + 1, old)
    scenario.send(FIRST_SEND, sent[0][1])
    scenario.send(FIRST_SEND + 20, sent[1][1])
    scenario.set_delay(FIRST_SEND + 40, new)
    scenario.send(third_cycle, sent[2][1])
    samples = await run_scenario(dut, scenario)
    expected = [
        (FIRST_SEND + old - LATENCY, sent[0][1]),
        (FIRST_SEND + 20 + old - LATENCY, sent[1][1]),
    ]
    assert_delivered(strobes_of(samples), expected, f"delay lowered (seed {seed})")
    assert samples[-1].cycle - third_cycle >= window, "the observation window is shorter than 5000 cycles"
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def msgdelay_consecutive_strobes(dut):
    """Strobes on consecutive cycles deliver only the first message; two cycles apart all are delivered (observed, intent unconfirmed).

    The read side reads one message per two cycles at most (it does not read
    while its read enable is high), so with strobes one cycle apart the
    delivery time of the second message has passed when the reader gets to it,
    and the queue stalls until the 32 bit counter wraps (2**32 clocks, not
    simulated). Ten messages 2 cycles apart are all delivered in order.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    delay = 100
    for spacing, count in ((1, 1), (2, 10)):
        sent = new_messages(rng, 10)
        scenario = Scenario(FIRST_SEND + delay + 200, delay)
        cycles = [FIRST_SEND + spacing * index for index in range(len(sent))]
        for cycle, (_, vector) in zip(cycles, sent):
            scenario.send(cycle, vector)
        strobes = strobes_of(await run_scenario(dut, scenario))
        expected = [(cycle + delay - LATENCY, vector) for cycle, (_, vector) in zip(cycles[:count], sent[:count])]
        assert_delivered(strobes, expected, f"spacing {spacing} (seed {seed})")
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def msgdelay_fifo_limit(dut):
    """520 queued messages overrun the 512 deep FIFO: the first 512 are delivered, the last 8 are lost (observed, intent unconfirmed).

    Messages are 3 cycles apart under a 2000 cycle delay, so all 520 are
    written before the first one is read. Both FIFOs are built with
    ADDR_WIDTH_G 9 whatever FIFO_ADDR_WIDTH_G is, so the depth is the same for
    the 4 and 7 builds of this test. Messages beyond the depth are dropped
    without any status output.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    delay, spacing, count = 2000, 3, FIFO_DEPTH + 8
    sent = new_messages(rng, count)
    cycles = [FIRST_SEND + spacing * index for index in range(count)]
    scenario = Scenario(cycles[-1] + delay + 300, delay)
    for cycle, (_, vector) in zip(cycles, sent):
        scenario.send(cycle, vector)
    strobes = strobes_of(await run_scenario(dut, scenario))
    expected = [(cycle + delay - LATENCY, vector) for cycle, (_, vector) in zip(cycles[:FIFO_DEPTH], sent[:FIFO_DEPTH])]
    assert_delivered(strobes, expected, f"fifo limit (seed {seed})")
    clock_task.cancel()


@pytest.mark.parametrize("addr_width", [4, 7])
def test_TimingMsgDelay(addr_width):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingmsgdelaywrapper",
        parameters={"FIFO_ADDR_WIDTH_G": addr_width},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
