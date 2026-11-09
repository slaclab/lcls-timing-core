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
    Sweep: a single pulse with delay 3 and width 2 on the default
        TRIG_DEPTH_G of 16, CHANNELS_G 1 and USE_MASK_G false.
    Stimulus: reset for 3 cycles, then a packed trigger configuration with
        enabled 1, polarity 1, delay 3, width 2 and channel 0; arm(0) is high
        for one cycle, and fire is high for one cycle two cycles later. The
        configuration word comes from tests.common.evr_model.
    Checks: trigstate equals the TriggerModel output on every sampled clock
        for 100 cycles after reset release, is resolvable on every one of
        them, and rises delay + 4 cycles after the fire cycle and falls width
        cycles later.
    Timing: 10 ns clk; inputs change right after a rising edge.
    Propagation sampling: registered outputs settle after TPD_G (1 ns), so
        every output is sampled 2 ns after the rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common import evr_model
from tests.common.regression_utils import (
    REPO_ROOT,
    env_int,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2TriggerWrapper.vhd"

RESET_CYCLES = 3
CLOCK_NS = 10


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

    def set_config(self, first_cycle, **fields):
        """Use a new configuration from ``first_cycle`` to the end."""
        for cycle in range(first_cycle, self.length):
            self.config[cycle] = trigger_fields(**fields)


async def start_clock(dut):
    return cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start(start_high=False))


def make_model(dut):
    return evr_model.TriggerModel(
        trig_depth=env_int("TRIG_DEPTH_G", default=16),
        channels=len(dut.arm),
        use_mask=False,
    )


async def run_scenario(dut, scenario, model):
    """Drive every cycle, step the model with the same inputs and compare the outputs.

    Returns the trigstate level seen during each cycle: element k is the
    output after the edge that captures the inputs of cycle k - 1, so a pulse
    "active in cycle k" is trace[k] equal to 1 and element 0 is the power-up
    level. The samples inside reset are recorded as 0 and not compared.
    """
    trace = [0]
    for cycle in range(scenario.length):
        fields = scenario.config[cycle]
        dut.rst.value = scenario.rst[cycle]
        dut.config.value = evr_model.pack_trigger_config(**fields)
        dut.arm.value = scenario.arm[cycle]
        dut.fire.value = scenario.fire[cycle]
        await sample_after_tpd(dut.clk, propagation_time=2)
        expected = model.step(fields, scenario.arm[cycle], scenario.fire[cycle], scenario.rst[cycle])
        if cycle < RESET_CYCLES:
            trace.append(0)
            continue
        assert dut.trigstate.value.is_resolvable, f"trigstate carries unresolved bits at cycle {cycle}: {dut.trigstate.value}"
        got = int(dut.trigstate.value)
        assert got == expected, f"cycle {cycle}: trigstate {got}, model {expected}"
        trace.append(got)
    return trace


def edges(trace):
    """Return (rising cycles, falling cycles) of a trace."""
    rises = [cycle for cycle in range(1, len(trace)) if trace[cycle - 1] == 0 and trace[cycle] == 1]
    falls = [cycle for cycle in range(1, len(trace)) if trace[cycle - 1] == 1 and trace[cycle] == 0]
    return rises, falls


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
    expected_rise = fire_cycle + evr_model.FIRE_TO_RISE_CYCLES + delay
    assert rises == [expected_rise], f"rising edges at {rises}, expected [{expected_rise}]"
    assert falls == [expected_rise + width], f"falling edges at {falls}, expected [{expected_rise + width}]"
    clock_task.cancel()


def test_EvrV2Trigger():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2triggerwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
