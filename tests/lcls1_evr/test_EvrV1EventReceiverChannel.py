#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1EventReceiverChannel leaf test under Icarus Verilog.

Test methodology:
    Sweep: delays 0, 1 and 5 with widths 1 and 3; prescales 0, 1, 3 and 4;
        both polarities; width 0; setPulse and resetPulse in every
        combination; a second myEvent edge during the delay and during the
        pulse; Reset in the middle of a delay and of a pulse.
    Stimulus: Reset is held high for 3 Clock cycles, then released, and the
        checks start after that. myEvent is high for one cycle, so one
        rising edge starts the delay. Inputs are driven one time step after
        a rising edge, so the next edge captures them. Cycle index i is the
        edge that captures the inputs driven for step i, and every trace
        sample is the output after that edge.
    Checks: with the event captured at index E, the trigger first becomes
        active at index E + 1 + delay * ticks and stays active for
        width * ticks samples, where ticks is the prescale (1 for a prescale
        of 0 or 1). Those latencies were measured before they were asserted.
        The trigger is active high for polarity 1 and active low for 0. A
        width of 0 gives no pulse. setPulse forces 1 and resetPulse forces 0
        with setPulse winning, without disturbing the pulse underneath.
        Reset returns the channel to idle. trigD and trigLe have no reset,
        so no check runs before the first Clock edge after the clock starts;
        every checked output is resolvable on every sample.
    Timing: 10 ns Clock. The language mode is the runner default: cocotb-test
        passes -g2012 to Icarus, and -g2005 also compiles this file.
    Propagation sampling: the module has no delayed assignments, so each
        sample settles through a ReadOnly phase after the rising edge
        instead of a time offset.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep

from tests.common.regression_utils import (
    run_icarus_verilog_test,
    sample_after_delta_cycles,
)

CLOCK_PERIOD_NS = 10
RESET_CYCLES = 3
EVENT_INDEX = 4
STATE_IDLE = 0
DELAYS = (0, 1, 5)
WIDTHS = (1, 3)
PRESCALES = (0, 1, 3, 4)
TAIL_CYCLES = 8


class Sample:
    """Outputs after one rising edge."""

    def __init__(self, dut):
        assert dut.trigger.value.is_resolvable, "trigger is not resolvable"
        assert dut.channelDebug.value.is_resolvable, "channelDebug is not resolvable"
        self.trigger = int(dut.trigger.value)
        debug = int(dut.channelDebug.value)
        self.counter = debug & 0xFFFFFFFF
        self.delay_pulse = (debug >> 64) & 1
        self.state = (debug >> 69) & 3


def ticks_for(prescale):
    """Clocks per tick: a prescale of 0 and of 1 both mean every clock."""
    return max(prescale, 1)


async def start_and_release(dut):
    """Hold Reset for a few clocks, then release it after an edge."""
    dut.Reset.value = 1
    dut.myEvent.value = 0
    dut.setPulse.value = 0
    dut.resetPulse.value = 0
    dut.myDelay.value = 0
    dut.myWidth.value = 0
    dut.myPolarity.value = 1
    dut.myPreScale.value = 0
    cocotb.start_soon(Clock(dut.Clock, CLOCK_PERIOD_NS, unit="ns").start())
    for _ in range(RESET_CYCLES):
        await sample_after_delta_cycles(dut.Clock)
        await NextTimeStep()
    dut.Reset.value = 0


def configure(dut, *, delay, width, polarity=1, prescale=0):
    dut.myDelay.value = delay
    dut.myWidth.value = width
    dut.myPolarity.value = polarity
    dut.myPreScale.value = prescale


async def run_cycles(dut, count, *, events=(), set_cycles=(), reset_pulse_cycles=(), reset_cycles=()):
    """Drive `count` cycles and return the Sample after each edge.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the edge, then the test moves one time step on before it drives again.
    """
    trace = []
    for index in range(count):
        dut.myEvent.value = int(index in events)
        dut.setPulse.value = int(index in set_cycles)
        dut.resetPulse.value = int(index in reset_pulse_cycles)
        dut.Reset.value = int(index in reset_cycles)
        await sample_after_delta_cycles(dut.Clock)
        trace.append(Sample(dut))
        await NextTimeStep()
    dut.myEvent.value = 0
    dut.setPulse.value = 0
    dut.resetPulse.value = 0
    dut.Reset.value = 0
    return trace


def active_indices(trace, polarity=1):
    return [index for index, sample in enumerate(trace) if sample.trigger == polarity]


def expected_active(delay, width, prescale, event=EVENT_INDEX):
    ticks = ticks_for(prescale)
    first = event + 1 + delay * ticks
    return list(range(first, first + width * ticks))


def run_length(delay, width, prescale):
    return EVENT_INDEX + 2 + (delay + width) * ticks_for(prescale) + TAIL_CYCLES


async def single_event(dut, *, delay, width, polarity=1, prescale=0, extra_events=()):
    configure(dut, delay=delay, width=width, polarity=polarity, prescale=prescale)
    count = run_length(delay, width, prescale) + max(extra_events, default=0)
    return await run_cycles(dut, count, events={EVENT_INDEX, *extra_events})


@cocotb.test(timeout_time=200, timeout_unit="us")
async def channel_delay_and_width(dut):
    """The pulse starts delay + 1 clocks after the event and lasts width clocks.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    for delay in DELAYS:
        for width in WIDTHS:
            trace = await single_event(dut, delay=delay, width=width)
            got = active_indices(trace)
            expected = expected_active(delay, width, 0)
            assert got == expected, f"delay {delay} width {width}: active at {got}, expected {expected}"
            assert trace[-1].state == STATE_IDLE, f"delay {delay} width {width}: not idle after the pulse"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def channel_prescale(dut):
    """A prescale of N stretches the delay and the width to N clocks per tick.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    width = 2
    traces = {}
    for prescale in PRESCALES:
        for delay in (0, 2):
            trace = await single_event(dut, delay=delay, width=width, prescale=prescale)
            got = active_indices(trace)
            expected = expected_active(delay, width, prescale)
            assert got == expected, (
                f"prescale {prescale} delay {delay}: active at {got}, expected {expected}"
            )
            traces[prescale, delay] = got
    for delay in (0, 2):
        assert traces[0, delay] == traces[1, delay], f"prescale 0 and 1 differ at delay {delay}"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def channel_polarity(dut):
    """Polarity 0 inverts the idle and the active level of the trigger.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    delay, width = 2, 3
    high = await single_event(dut, delay=delay, width=width, polarity=1)
    low = await single_event(dut, delay=delay, width=width, polarity=0)
    assert active_indices(high, 1) == expected_active(delay, width, 0), "polarity 1 pulse is wrong"
    assert active_indices(low, 0) == expected_active(delay, width, 0), "polarity 0 pulse is wrong"
    assert [sample.trigger for sample in low] == [1 - sample.trigger for sample in high], (
        "polarity 0 trace is not the inverse of the polarity 1 trace"
    )
    assert high[0].trigger == 0 and low[0].trigger == 1, "idle levels are wrong"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def channel_set_and_reset_override(dut):
    """setPulse forces 1 and resetPulse forces 0, setPulse winning.

    The forcing is on the output only: the pulse underneath keeps running,
    so the trigger follows it again once the override is released.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    delay, width = 3, 4
    set_cycles = {1, 2, 9, 10}
    reset_cycles = {2, 3, 7, 8}
    for polarity in (1, 0):
        configure(dut, delay=delay, width=width, polarity=polarity)
        count = run_length(delay, width, 0)
        base = await run_cycles(dut, count, events={EVENT_INDEX})
        forced = await run_cycles(
            dut,
            count,
            events={EVENT_INDEX},
            set_cycles=set_cycles,
            reset_pulse_cycles=reset_cycles,
        )
        for index, (plain, got) in enumerate(zip(base, forced)):
            if index in set_cycles:
                expected = 1
            elif index in reset_cycles:
                expected = 0
            else:
                expected = plain.trigger
            assert got.trigger == expected, (
                f"polarity {polarity} cycle {index}: trigger {got.trigger}, expected {expected}"
            )
            assert got.state == plain.state, f"polarity {polarity} cycle {index}: override changed the state"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def channel_width_zero(dut):
    """A width of 0 produces no pulse and leaves the state machine idle.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    for delay in DELAYS:
        trace = await single_event(dut, delay=delay, width=0)
        assert active_indices(trace) == [], f"delay {delay}: pulse at {active_indices(trace)} with width 0"
        assert all(sample.state == STATE_IDLE for sample in trace), f"delay {delay}: state left idle"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def channel_retrigger_during_delay(dut):
    """A second event edge during the delay or the pulse.

    This is observed, intent unconfirmed. With no prescale the second edge
    is ignored in both places. With a prescale of 4 an edge during the delay
    also restarts the prescaler, which moves the pulse later.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    delay, width = 10, 2
    base = expected_active(delay, width, 0)

    during_delay = await single_event(dut, delay=delay, width=width, extra_events={EVENT_INDEX + 4})
    assert active_indices(during_delay) == base, (
        f"edge during the delay: active at {active_indices(during_delay)}, expected {base}"
    )
    during_pulse = await single_event(dut, delay=delay, width=width, extra_events={base[0] + 1})
    assert active_indices(during_pulse) == base, (
        f"edge during the pulse: active at {active_indices(during_pulse)}, expected {base}"
    )

    prescale = 4
    plain = await single_event(dut, delay=delay, width=width, prescale=prescale)
    assert active_indices(plain) == expected_active(delay, width, prescale), "prescaled pulse is wrong"
    restarted = await single_event(
        dut, delay=delay, width=width, prescale=prescale, extra_events={EVENT_INDEX + 6}
    )
    moved = [index - plain_index for index, plain_index in zip(active_indices(restarted), active_indices(plain))]
    # The second edge lands 6 clocks after the first, when the prescaler is
    # 2 counts into its 4 clock cycle, so the restart delays every action
    # by 2 clocks.
    assert moved == [2] * len(moved), f"second edge moved the prescaled pulse by {moved}, expected 2 clocks"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def channel_reset_returns_to_idle(dut):
    """Reset in the middle of a delay or a pulse returns the channel to idle.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge; the module has no delayed assignments.
    """
    await start_and_release(dut)
    delay, width = 10, 5
    configure(dut, delay=delay, width=width)
    first = expected_active(delay, width, 0)[0]
    for reset_at in (EVENT_INDEX + 5, first + 2):
        count = run_length(delay, width, 0)
        trace = await run_cycles(dut, count, events={EVENT_INDEX}, reset_cycles={reset_at})
        assert trace[reset_at].trigger == 0, f"trigger active in the Reset cycle {reset_at}"
        assert trace[reset_at].state == STATE_IDLE and trace[reset_at].counter == 0, (
            f"state {trace[reset_at].state} counter {trace[reset_at].counter} in the Reset cycle"
        )
        late = [index for index in active_indices(trace) if index > reset_at]
        assert late == [], f"pulse at {late} after Reset at {reset_at}"


def test_EvrV1EventReceiverChannel():
    run_icarus_verilog_test(
        test_file=Path(__file__),
        toplevel="EvrV1EventReceiverChannel",
    )
