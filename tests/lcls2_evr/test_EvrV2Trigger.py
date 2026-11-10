#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2Trigger test: the RTL output equals a cycle-accurate model on every clock.

Test methodology:
    Sweep: TRIG_DEPTH_G 0, 1, 4, 16, 28 and 127 with CHANNELS_G 1 and
        USE_MASK_G false, plus CHANNELS_G 4 with USE_MASK_G true. Delays 0, 1,
        2, 3, 10 and 50 with widths 1, 2 and 5; fire spacings of 2 and 3
        cycles and of 10 cycles with a delay of 40; queue depths up to 127
        pulses; polarity 0 and 1; a seeded random train of 2000 cycles.
    Stimulus: reset for 3 cycles, then a packed trigger configuration from
        tests.common.evr_model, arm held high (or pulsed) and fire pulses at
        chosen cycles. Two known issues run only in their own simulation when
        RUN_KNOWN_ISSUE_TESTS=1: the idle level of a polarity 0 output and a
        channel number at or above CHANNELS_G.
    Checks: trigstate equals the TriggerModel output on every sampled clock
        after reset release, is resolvable on every one of them, and the
        pulse edges, the accepted pulse count and the skip rules match the
        values stated in each test. The model is derived from the RTL, so
        behavior marked "observed, intent unconfirmed" is asserted as
        measured and the maintainers have not confirmed it as intended.
    Timing: 10 ns clk; inputs change right after a rising edge.
    Propagation sampling: registered outputs settle after TPD_G (1 ns), so
        every output is sampled 2 ns after the rising edge.
"""

import os
from pathlib import Path

import cocotb
import pytest
from cocotb.clock import Clock

from tests.common import evr_model, timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    env_int,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2TriggerWrapper.vhd"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
POLARITY_ENTRYPOINT = "trigger_polarity_idle_high"
CHANNEL_ENTRYPOINT = "trigger_channel_out_of_range"
MASK_ENTRYPOINTS = ("trigger_mask_mode",)
MASK_MODE = os.getenv("USE_MASK_G") == "true"

DEPTHS = [0, 1, 4, 16, 28, 127]
RESET_CYCLES = 3
CLOCK_NS = 10
FIRST_CONFIG_CYCLE = RESET_CYCLES
IDLE_SETTLE_CYCLES = 2


def trigger_fields(**fields):
    """Return a complete trigger configuration dictionary with the defaults filled in."""
    return {**evr_model.TRIGGER_CONFIG_DEFAULTS, **fields}


class Scenario:
    """Per-cycle inputs of one run: configuration, arm, fire and reset."""

    def __init__(self, length, **fields):
        self.length = length
        self.config = [trigger_fields(**fields) for _ in range(length)]
        self.arm = [0] * length
        self.fire = [0] * length
        self.rst = [1 if cycle < RESET_CYCLES else 0 for cycle in range(length)]

    def set_config(self, first_cycle, last_cycle=None, **fields):
        """Use a new configuration from ``first_cycle`` up to ``last_cycle`` (default: the end)."""
        for cycle in range(first_cycle, self.length if last_cycle is None else last_cycle):
            self.config[cycle] = trigger_fields(**fields)

    def hold_arm(self, first_cycle=FIRST_CONFIG_CYCLE):
        """Keep arm(0) high from ``first_cycle`` on, so every fire that finds the trigger armed is accepted."""
        for cycle in range(first_cycle, self.length):
            self.arm[cycle] = 1


async def start_clock(dut):
    return cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start(start_high=False))


def make_model(dut):
    return evr_model.TriggerModel(
        trig_depth=env_int("TRIG_DEPTH_G", default=16),
        channels=len(dut.arm),
        use_mask=MASK_MODE,
    )


async def run_scenario(dut, scenario, model=None):
    """Drive every cycle, step the model with the same inputs and compare the outputs.

    Returns the trigstate level seen during each cycle: element k is the
    output after the edge that captures the inputs of cycle k - 1, so a pulse
    "active in cycle k" is trace[k] equal to 1 and element 0 is the power-up
    level. The samples inside reset are recorded as 0 and not compared. With
    no model the outputs are only checked for X and U.
    """
    trace = [0]
    for cycle in range(scenario.length):
        fields = scenario.config[cycle]
        dut.rst.value = scenario.rst[cycle]
        dut.config.value = evr_model.pack_trigger_config(**fields)
        dut.arm.value = scenario.arm[cycle]
        dut.fire.value = scenario.fire[cycle]
        await sample_after_tpd(dut.clk, propagation_time=2)
        if model is not None:
            expected = model.step(fields, scenario.arm[cycle], scenario.fire[cycle], scenario.rst[cycle])
        if cycle < RESET_CYCLES:
            trace.append(0)
            continue
        assert dut.trigstate.value.is_resolvable, f"trigstate carries unresolved bits at cycle {cycle}: {dut.trigstate.value}"
        got = int(dut.trigstate.value)
        if model is not None:
            assert got == expected, f"cycle {cycle}: trigstate {got}, model {expected}"
        trace.append(got)
    return trace


def edges(trace):
    """Return (rising cycles, falling cycles) of a trace."""
    rises = [cycle for cycle in range(1, len(trace)) if trace[cycle - 1] == 0 and trace[cycle] == 1]
    falls = [cycle for cycle in range(1, len(trace)) if trace[cycle - 1] == 1 and trace[cycle] == 0]
    return rises, falls


def expected_rise(fire_cycle, delay):
    """Cycle in which a trigger accepted at ``fire_cycle`` first reads active (observed, intent unconfirmed)."""
    return fire_cycle + evr_model.FIRE_TO_RISE_CYCLES + delay


@cocotb.test(timeout_time=200, timeout_unit="us")
async def trigger_single_pulse_matches_model(dut):
    """One pulse of delay 3 and width 2 equals the model and has the measured edges.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    delay, width = 3, 2
    arm_cycle = 10
    fire_cycle = 12
    scenario = Scenario(RESET_CYCLES + 100, enabled=1, polarity=1, delay=delay, width=width, channel=0)
    scenario.arm[arm_cycle] = 1
    scenario.fire[fire_cycle] = 1
    clock_task = await start_clock(dut)
    trace = await run_scenario(dut, scenario, make_model(dut))
    rises, falls = edges(trace)
    assert rises == [expected_rise(fire_cycle, delay)], f"rising edges at {rises}"
    assert falls == [expected_rise(fire_cycle, delay) + width], f"falling edges at {falls}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def trigger_latency_table(dut):
    """The pulse rises delay + 4 cycles after fire and lasts width cycles, for delay 0 to 50 and width 1 to 5.

    Observed, intent unconfirmed: the RTL header comment says delay plus 5.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    model = make_model(dut)
    for delay in (0, 1, 2, 3, 10, 50):
        for width in (1, 2, 5):
            fire_cycle = 12
            scenario = Scenario(RESET_CYCLES + delay + width + 40, enabled=1, polarity=1, delay=delay, width=width)
            scenario.arm[8] = 1
            scenario.fire[fire_cycle] = 1
            trace = await run_scenario(dut, scenario, model)
            rises, falls = edges(trace)
            rise = expected_rise(fire_cycle, delay)
            assert rises == [rise], f"delay {delay} width {width}: rising edges at {rises}, expected [{rise}]"
            assert falls == [rise + width], f"delay {delay} width {width}: falling edges at {falls}, expected [{rise + width}]"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def trigger_min_fire_spacing(dut):
    """A fire 2 cycles after an accepted fire is lost; a fire 3 or more cycles after it is accepted.

    Observed, intent unconfirmed: the state machine needs two cycles after a
    push to re-arm, so spacing below 3 drops the trigger without any flag.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    delay, width = 3, 1
    clock_task = await start_clock(dut)
    model = make_model(dut)
    for label, fires, accepted in (
        ("2 apart", [20, 22, 24], [20, 24]),
        ("3 apart", [20, 23, 26], [20, 23, 26]),
        ("1 apart", [20, 21, 22, 23], [20, 23]),
    ):
        scenario = Scenario(RESET_CYCLES + 70, enabled=1, polarity=1, delay=delay, width=width)
        scenario.hold_arm()
        for fire_cycle in fires:
            scenario.fire[fire_cycle] = 1
        trace = await run_scenario(dut, scenario, model)
        rises, falls = edges(trace)
        want = [expected_rise(fire_cycle, delay) for fire_cycle in accepted]
        assert rises == want, f"fires {label}: rising edges at {rises}, expected {want}"
        assert falls == [rise + width for rise in want], f"fires {label}: falling edges at {falls}"
    assert evr_model.MIN_FIRE_SPACING == 3
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def trigger_pulses_in_flight(dut):
    """Several pulses are queued when delay exceeds the fire period, each at its own fire + delay + 4.

    A queue that holds fewer pulses than fires (TRIG_DEPTH_G 0 and 1 hold 3)
    drops the later fires, so only the first queue_capacity(depth) pulses are
    expected there. The falling level of the last accepted pulse is lost with
    them and the output stays high (observed, intent unconfirmed).

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    depth = env_int("TRIG_DEPTH_G", default=16)
    delay, width, period = 40, 2, 10
    fires = [20 + period * k for k in range(4)]
    scenario = Scenario(RESET_CYCLES + 120, enabled=1, polarity=1, delay=delay, width=width)
    scenario.hold_arm()
    for fire_cycle in fires:
        scenario.fire[fire_cycle] = 1
    clock_task = await start_clock(dut)
    trace = await run_scenario(dut, scenario, make_model(dut))
    rises, falls = edges(trace)
    capacity = evr_model.queue_capacity(depth)
    accepted = fires[:capacity]
    want = [expected_rise(fire_cycle, delay) for fire_cycle in accepted]
    assert rises == want, f"rising edges at {rises}, expected {want}"
    want_falls = [rise + width for rise in want]
    if capacity < len(fires):
        want_falls = want_falls[:-1]
    assert falls == want_falls, f"falling edges at {falls}, expected {want_falls}"
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def trigger_queue_capacity(dut):
    """The pulse queue accepts evr_model.queue_capacity(depth) pulses, then drops the rest silently.

    Observed, intent unconfirmed: the RTL header comment promises up to 127
    triggers. Fires come every 4 cycles with delay 1000 and width 1, so no
    pulse leaves the queue while the 140 fires arrive. Fires after the queue
    is full are dropped with no flag, and the trace after the overflow
    (including an output left high when the last fall entry is lost) equals
    the model.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    depth = env_int("TRIG_DEPTH_G", default=16)
    delay, width, period, fire_count = 1000, 1, 4, 140
    first_fire = 20
    scenario = Scenario(RESET_CYCLES + first_fire + period * fire_count + delay + 100, enabled=1, polarity=1, delay=delay, width=width)
    scenario.hold_arm()
    for k in range(fire_count):
        scenario.fire[first_fire + period * k] = 1
    clock_task = await start_clock(dut)
    trace = await run_scenario(dut, scenario, make_model(dut))
    rises, _ = edges(trace)
    capacity = evr_model.queue_capacity(depth)
    assert len(rises) == capacity, f"TRIG_DEPTH_G {depth}: {len(rises)} pulses accepted, queue_capacity says {capacity}"
    assert len(rises) < fire_count, "the fire train never overflowed the queue"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def trigger_skip_rules(dut):
    """A delay below the pending fifo_delay skips the trigger, and so does a width of 0.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    model = make_model(dut)

    # The second trigger would fall before the first one, so it is eaten.
    scenario = Scenario(RESET_CYCLES + 120, enabled=1, polarity=1, delay=50, width=1)
    scenario.hold_arm()
    scenario.fire[20] = 1
    scenario.set_config(24, enabled=1, polarity=1, delay=5, width=1)
    scenario.fire[28] = 1
    trace = await run_scenario(dut, scenario, model)
    rises, _ = edges(trace)
    assert rises == [expected_rise(20, 50)], f"reduced delay: rising edges at {rises}, only the first pulse is expected"

    # Once the first pulse is gone the short delay is accepted again.
    scenario = Scenario(RESET_CYCLES + 160, enabled=1, polarity=1, delay=50, width=1)
    scenario.hold_arm()
    scenario.fire[20] = 1
    scenario.set_config(24, enabled=1, polarity=1, delay=5, width=1)
    scenario.fire[100] = 1
    trace = await run_scenario(dut, scenario, model)
    rises, _ = edges(trace)
    assert rises == [expected_rise(20, 50), expected_rise(100, 5)], f"delay reduced after the queue drained: rising edges at {rises}"

    # A width of 0 never produces a pulse.
    scenario = Scenario(RESET_CYCLES + 80, enabled=1, polarity=1, delay=3, width=0)
    scenario.hold_arm()
    scenario.fire[20] = 1
    scenario.fire[40] = 1
    trace = await run_scenario(dut, scenario, model)
    assert not any(trace), f"width 0 produced a pulse: {trace}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def trigger_disable_and_reset(dut):
    """Clearing enabled or pulsing rst drops every queued pulse and returns the output to 0.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    clock_task = await start_clock(dut)
    model = make_model(dut)
    for label in ("enabled", "rst"):
        # Queued pulse: fire at 20 with delay 60, cleared at 30 for one cycle.
        scenario = Scenario(RESET_CYCLES + 140, enabled=1, polarity=1, delay=60, width=3)
        scenario.hold_arm()
        scenario.fire[20] = 1
        if label == "enabled":
            scenario.config[30] = trigger_fields(enabled=0, polarity=1, delay=60, width=3)
        else:
            scenario.rst[30] = 1
        trace = await run_scenario(dut, scenario, model)
        assert not any(trace), f"{label}: a queued pulse survived the clear: rises at {edges(trace)[0]}"

        # Active pulse: delay 2, width 30, cleared 8 cycles after the rise.
        rise = expected_rise(20, 2)
        scenario = Scenario(RESET_CYCLES + 100, enabled=1, polarity=1, delay=2, width=30)
        scenario.hold_arm()
        scenario.fire[20] = 1
        clear = rise + 8
        if label == "enabled":
            scenario.config[clear] = trigger_fields(enabled=0, polarity=1, delay=2, width=30)
        else:
            scenario.rst[clear] = 1
        trace = await run_scenario(dut, scenario, model)
        rises, falls = edges(trace)
        assert rises == [rise], f"{label}: rising edges at {rises}"
        assert falls == [clear + 1], f"{label}: the output fell at {falls}, expected the cycle after the clear at {clear + 1}"
        assert not any(trace[clear + 1:]), f"{label}: the output rose again after the clear"
    clock_task.cancel()


@cocotb.test(skip=not MASK_MODE, timeout_time=500, timeout_unit="us")
async def trigger_mask_mode(dut):
    """With USE_MASK_G true any arm bit in the channels mask arms the trigger and the channel field is ignored.

    Skipped unless USE_MASK_G is "true".

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    assert len(dut.arm) == 4, "this test expects CHANNELS_G 4"
    clock_task = await start_clock(dut)
    model = make_model(dut)
    delay, width = 3, 2
    mask = 0b0110
    for arm, channel, fires in (
        (0b0001, 0, False),
        (0b1000, 0, False),
        (0b0010, 0, True),
        (0b0100, 3, True),
        (0b1010, 1, True),
    ):
        scenario = Scenario(RESET_CYCLES + 60, enabled=1, polarity=1, delay=delay, width=width, channel=channel, channels=mask)
        scenario.fire[20] = 1
        for cycle in range(FIRST_CONFIG_CYCLE, scenario.length):
            scenario.arm[cycle] = arm
        trace = await run_scenario(dut, scenario, model)
        rises, _ = edges(trace)
        want = [expected_rise(20, delay)] if fires else []
        assert rises == want, f"arm 0b{arm:04b} channel {channel} mask 0b{mask:04b}: rising edges at {rises}, expected {want}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def trigger_polarity_observed(dut):
    """Polarity 1 pulses are active high; polarity 0 idles low until the first pulse ends, then idles high.

    Observed, intent unconfirmed: the PyRogue TriggerPolarity description says
    0 is negative and the Polarity enum names 0 Falling, so an idle level of 1
    is expected before the first pulse. The
    initial level entry written when the trigger is enabled is lost because
    the queue is still in reset, and the output stays at its reset level 0.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    delay, width = 3, 2
    fires = [20, 60, 100]
    clock_task = await start_clock(dut)
    model = make_model(dut)
    traces = {}
    for polarity in (1, 0):
        scenario = Scenario(RESET_CYCLES + 140, enabled=1, polarity=polarity, delay=delay, width=width)
        scenario.hold_arm()
        for fire_cycle in fires:
            scenario.fire[fire_cycle] = 1
        traces[polarity] = await run_scenario(dut, scenario, model)
    rises, falls = edges(traces[1])
    want = [expected_rise(fire_cycle, delay) for fire_cycle in fires]
    assert rises == want, f"polarity 1: rising edges at {rises}, expected {want}"
    assert falls == [rise + width for rise in want], f"polarity 1: falling edges at {falls}"

    rises, falls = edges(traces[0])
    assert falls == want[1:], f"polarity 0: active-low pulses start at {falls}, expected {want[1:]}"
    assert rises == [want[0] + width] + [rise + width for rise in want[1:]], f"polarity 0: levels return high at {rises}"
    assert not any(traces[0][:want[0] + width]), "polarity 0: the output was expected low until the first pulse ends"
    clock_task.cancel()


@cocotb.test(timeout_time=2000, timeout_unit="us")
async def trigger_random_trains(dut):
    """A seeded random run of configuration changes, fires, arms and resets equals the model.

    Delay runs up to 200, width 1 to 20, polarity and enable change every 100
    to 400 cycles, fire gaps are 1 to 30 cycles, and rst pulses at random.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    channels = len(dut.arm)
    length = RESET_CYCLES + 2000
    scenario = Scenario(length)
    cycle = FIRST_CONFIG_CYCLE
    while cycle < length:
        span = rng.randint(100, 400)
        scenario.set_config(
            cycle,
            min(cycle + span, length),
            enabled=1 if rng.random() < 0.9 else 0,
            polarity=rng.getrandbits(1),
            delay=rng.randint(0, 200),
            width=rng.randint(1, 20),
            channel=rng.randrange(channels),
            channels=rng.getrandbits(16),
        )
        cycle += span
    cycle = FIRST_CONFIG_CYCLE + 1
    while cycle < length:
        scenario.fire[cycle] = 1
        cycle += rng.randint(1, 30)
    for cycle in range(FIRST_CONFIG_CYCLE, length):
        scenario.arm[cycle] = rng.getrandbits(channels)
        if rng.random() < 0.003:
            scenario.rst[cycle] = 1
    clock_task = await start_clock(dut)
    trace = await run_scenario(dut, scenario, make_model(dut))
    assert any(trace), "the random run never produced an active output"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def trigger_polarity_idle_high(dut):
    """A polarity 0 trigger idles high from just after it is enabled until the first pulse starts.

    Known issue entrypoint: it fails on the current RTL, which keeps the
    output low until the first pulse completes.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    enable_cycle = FIRST_CONFIG_CYCLE
    fire_cycle = 40
    delay, width = 3, 2
    scenario = Scenario(RESET_CYCLES + 80, enabled=1, polarity=0, delay=delay, width=width)
    scenario.hold_arm()
    scenario.fire[fire_cycle] = 1
    clock_task = await start_clock(dut)
    trace = await run_scenario(dut, scenario)
    first_active = expected_rise(fire_cycle, delay)
    idle = trace[enable_cycle + IDLE_SETTLE_CYCLES:first_active]
    assert all(idle), (
        f"polarity 0 output idles low: trigstate was {idle} from cycle {enable_cycle + IDLE_SETTLE_CYCLES} "
        f"until the first pulse at cycle {first_active}, expected 1"
    )
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def trigger_channel_out_of_range(dut):
    """A trigger enabled on a channel at or above CHANNELS_G must not abort the simulation.

    Known issue entrypoint: with CHANNELS_G 1 and channel 1 the simulator
    reports an index out of bounds in EvrV2Trigger.vhd and stops.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    assert len(dut.arm) == 1, "this test expects CHANNELS_G 1"
    clock_task = await start_clock(dut)
    scenario = Scenario(RESET_CYCLES + 50, enabled=1, polarity=1, delay=3, width=2, channel=1)
    await run_scenario(dut, scenario)
    clock_task.cancel()


def run_trigger_simulation(parameters, test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2triggerwrapper",
        parameters=parameters,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(parameters, test_filter),
    )


@pytest.mark.parametrize("depth", DEPTHS)
def test_EvrV2Trigger(depth):
    run_trigger_simulation(
        {"TRIG_DEPTH_G": depth},
        cocotb_test_filter_excluding(*MASK_ENTRYPOINTS, POLARITY_ENTRYPOINT, CHANNEL_ENTRYPOINT),
    )


def test_EvrV2Trigger_mask():
    run_trigger_simulation(
        {"CHANNELS_G": 4, "USE_MASK_G": "true"},
        cocotb_test_filter(*MASK_ENTRYPOINTS, "trigger_random_trains"),
    )


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2Trigger with polarity 0 idles low until the first pulse completes; "
        "see https://github.com/slaclab/lcls-timing-core/issues/266; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2Trigger_known_issue_polarity_idle():
    run_trigger_simulation({}, cocotb_test_filter(POLARITY_ENTRYPOINT))


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2Trigger indexes arm with a channel at or above CHANNELS_C and GHDL aborts; "
        "see https://github.com/slaclab/lcls-timing-core/issues/212; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2Trigger_known_issue_channel_index():
    run_trigger_simulation({}, cocotb_test_filter(CHANNEL_ENTRYPOINT))
