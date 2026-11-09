#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2CoreTriggers driven from AXI-Lite register writes to trigger outputs.

Test methodology:
    Sweep: one channel and one trigger configured over AXI-Lite with the
        default generics (one channel, one trigger, TRIG_PIPE_G 0), axilClk
        10 ns and evrClk 7 ns.
    Stimulus: a cocotbext-axi AxiLiteMaster writes the channel registers at
        0x80000 and the trigger registers at 0x81000; the evrClk side is
        driven one timing-bus step per cycle through the wrapper. Four frames
        arrive 100 cycles apart, and fixedRates(0) is set in two of them.
    Checks: after a bounded 30-cycle settle that follows the last register
        write, every step's trigPulse, timeStamp, bsa and dmod equal the
        composite model (an EvrV2FromV1 copy, EventSelectModel on the second
        strobe stage, TriggerModel fired by the fourth stage, and the
        complementary stage), and the selected frames produce a rise and a
        fall at fixed offsets from their strobe while the other frames
        produce none.
    Timing: only evrClk timing relative to the bus strobe is exact; the
        register writes cross a synchronizer, so they are given a bounded
        settle instead of an exact cycle count.
    Propagation sampling: the registered outputs update after TPD_G (1 ns),
        so every output is sampled 2 ns after the rising evrClk edge.
"""

import os
from pathlib import Path

import cocotb

from tests.common import evr_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    env_int,
    run_lcls_vhdl_test,
)
from tests.lcls2_evr import composite_bench as cb

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2CoreTriggersWrapper.vhd"

CHANNELS = env_int("NCHANNELS_G", default=1)
TRIGGERS = env_int("NTRIGGERS_G", default=1)
TRIG_DEPTH = env_int("TRIG_DEPTH_G", default=28)
TRIG_PIPE = env_int("TRIG_PIPE_G", default=0)
COMMON = os.getenv("COMMON_CLK_G", "false") == "true"
CARD = os.getenv("EVR_CARD_G", "false") == "true"

# Steps from the strobe step to the first high sample with delay 5: the strobe
# crosses four register stages before it fires the trigger, and the trigger
# adds its delay plus a fixed latency (measured).
RISE_FROM_STROBE = 12


class CoreTriggersModel:
    """Cycle-accurate model of EvrV2CoreTriggers on the evrClk side, one clock per ``step``.

    It composes the shared channel path (strobe pipeline, FromV1 copy and one
    EventSelectModel per channel), one TriggerModel per trigger armed by the
    channel outputs and fired by the fourth strobe stage, and the
    complementary stage on each pair. A trailing odd trigger bypasses the
    complementary stage. ``nchannels`` and ``ntriggers`` are NCHANNELS_G and
    NTRIGGERS_G, ``trig_pipe`` is TRIG_PIPE_G (the queue depth of each
    trigger) and ``trig_depth`` is TRIG_DEPTH_G (the counter width).
    """

    def __init__(self, nchannels, ntriggers, trig_pipe, trig_depth=28):
        self.path = cb.ChannelPathModel(nchannels)
        self.ntriggers = ntriggers
        self.triggers = [
            evr_model.TriggerModel(trig_pipe, nchannels, False, trig_depth) for _ in range(ntriggers)
        ]
        self.configs = [dict(evr_model.TRIGGER_CONFIG_DEFAULTS) for _ in range(ntriggers)]
        self.levels = [0] * ntriggers

    def set_channel(self, index, **fields):
        self.path.set_channel(index, **fields)

    def set_trigger(self, index, **fields):
        self.configs[index] = {**evr_model.TRIGGER_CONFIG_DEFAULTS, **fields}

    def trig_out(self):
        """Return the 16-bit trigPulse value for the trigger levels held now."""
        result = 0
        for pair in range(self.ntriggers // 2):
            low, high = 2 * pair, 2 * pair + 1
            both = evr_model.trigger_compl(
                (self.configs[low]["complEn"], self.configs[high]["complEn"]),
                (self.configs[low]["complAnd"], self.configs[high]["complAnd"]),
                self.levels[low] | (self.levels[high] << 1),
            )
            result |= both << low
        if self.ntriggers % 2:
            result |= self.levels[-1] << (self.ntriggers - 1)
        return result

    def step(self, step):
        arm, fire = self.path.step(step)
        self.levels = [
            trigger.step(config, arm, fire) for trigger, config in zip(self.triggers, self.configs)
        ]
        stamp, bsa, dmod = self.path.bus_outputs(step)
        return cb.Sample(self.trig_out(), stamp, bsa, dmod)

    def run(self, steps):
        return [self.step(step) for step in steps]


def make_model(channels, triggers):
    """Return a model configured like the registers written for ``channels`` and ``triggers``."""
    model = CoreTriggersModel(CHANNELS, TRIGGERS, TRIG_PIPE, TRIG_DEPTH)
    for index, fields in channels.items():
        model.set_channel(index, **fields)
    for index, fields in triggers.items():
        model.set_trigger(index, **fields)
    return model


async def run_case(bench, channels, triggers, steps, label):
    """Reset, program, settle, then run ``steps`` and compare every step with the model.

    The model is warmed with the same number of idle cycles as the settle so
    that both sides start from the state an enabled configuration reaches.
    Returns ``(samples, model)``.
    """
    await bench.reset()
    await bench.program(CARD, channels, triggers)
    await bench.settle()
    model = make_model(channels, triggers)
    idle = cb.hold_step(bench.default_step)
    for _ in range(cb.SETTLE_CLOCKS):
        model.step(idle)
    samples = await bench.run(steps)
    cb.compare_samples(samples, model.run(steps), label)
    return samples, model


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def coretriggers_one_trigger_end_to_end(dut):
    """One register-configured trigger fires on the selected frames at the modeled cycles.

    Channel 0 selects fixed rate 0 for all destinations, trigger 0 is armed
    by channel 0 with delay 5 and width 3, and frames 1 and 3 of four carry
    fixedRates(0).

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    channels = {0: {"enabled": 1, "rateSel": 0, "destSel": cb.ALL_DESTINATIONS}}
    triggers = {0: {"enabled": 1, "channel": 0, "polarity": 1, "delay": 5, "width": 3}}
    miss = cb.make_step(cb.frame_message(fixedRates=0), cb.blank_stream())
    hit = cb.make_step(cb.frame_message(fixedRates=1), cb.blank_stream())
    steps, strobes = cb.build_schedule([miss, hit, miss, hit], 100)
    samples, _ = await run_case(bench, channels, triggers, steps, "one trigger")
    levels = [sample.trig_pulse for sample in samples]
    rise = cb.rises(levels)
    fall = [index for index, level in cb.edges(levels) if level == 0]
    assert len(rise) == 2 and len(fall) == 2, f"expected two pulses, rises {rise} falls {fall}"
    for frame, (up, down) in zip((1, 3), zip(rise, fall)):
        assert up - strobes[frame] == RISE_FROM_STROBE, (
            f"frame {frame}: rise {up - strobes[frame]} steps after the strobe, expected {RISE_FROM_STROBE}"
        )
        assert down - up == 3, f"frame {frame}: pulse is {down - up} steps wide, expected 3"
    bench.stop()


def run_coretriggers_simulation(parameters, test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2coretriggerswrapper",
        parameters=parameters,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(parameters, test_filter),
    )


def test_EvrV2CoreTriggers():
    run_coretriggers_simulation({}, r".*")
