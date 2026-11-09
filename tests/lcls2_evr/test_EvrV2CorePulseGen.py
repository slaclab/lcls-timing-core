#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2CorePulseGen configured over AXI-Lite and fired by timing frames.

Test methodology:
    Sweep: trigger 2 with channel 0 as the first case. The trigger register
        block sits at crossbar address 0x200 with a 9-bit window, but
        EvrV2TrigReg decodes twelve 256-byte groups counted from address 0,
        so the group at 0x200 answers as trigger 2. That layout is observed,
        intent unconfirmed: it is asserted as measured, not as a defect.
    Stimulus: a cocotbext-axi AxiLiteMaster writes channel 0 (enable at 0x20,
        rate and destination at 0x24) and trigger 2 (control at 0x200, delay
        at 0x204, width at 0x208) with axilClk at 10 ns; the evrClk side
        (7 ns) is driven one timing-bus step per cycle with frames 200
        steps apart, all with fixedRates bit 0 set.
    Checks: every step's trigOut equals a composite model (the strobe
        shift register, per-channel event select with its tap at 12 steps
        per channel, and one cycle-accurate trigger model per output), and
        independently of the model the first frame raises no edge, because
        the channel arms the trigger after the bus strobe that would fire
        it, and each following frame raises one pulse of the written width
        at a fixed offset after its own strobe. Every checked output is
        asserted resolvable after reset release.
    Timing: only the evrClk offsets from the bus strobe are exact; register
        writes cross a synchronizer, so they are given a bounded settle.
    Propagation sampling: the registered outputs update after TPD_G (1 ns),
        so every output is sampled 2 ns after the rising evrClk edge.
"""

from pathlib import Path

import cocotb

from tests.common import evr_model, timing_model
from tests.common.regression_utils import REPO_ROOT, run_lcls_vhdl_test, sample_after_tpd
from tests.lcls2_evr import composite_bench as cb
from tests.lcls2_evr import register_walk as rw

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2CorePulseGenWrapper.vhd"

CHANNELS = 12
TRIGGERS = 12
# The select of channel i takes its strobe from stage i * TAP_STRIDE + TAP_FIRST
# of the strobe shift register (the register output is stage 0).
TAP_STRIDE = 12
TAP_FIRST = 4
SHIFT_LENGTH = CHANNELS * TAP_STRIDE + 35

CSR_CHANNEL_BASE = rw.AXI_CHANNEL_BASE
CSR_CHANNEL_STRIDE = rw.AXI_CHANNEL_STRIDE
# Trigger register groups that answer through the crossbar, keyed by the
# trigger they configure.
TRIGGER_BASES = {2: 0x200, 3: 0x300}

# Frames are far enough apart that the last channel tap has fired before the
# next strobe.
FRAME_SPACING = 200
# From the strobe step of the firing frame to the first high sample: the
# trigger sees the bus strobe directly, then adds its own delay (measured).
RISE_FROM_STROBE = 3
# Idle steps after a reset that push any earlier strobe out of the shift
# register, which has no reset.
FLUSH_STEPS = SHIFT_LENGTH + 5

DELAY = 5
WIDTH = 3


def channel_base(index):
    return CSR_CHANNEL_BASE + index * CSR_CHANNEL_STRIDE


class PulseGenModel:
    """Model of EvrV2CorePulseGen on the evrClk side, one clock per ``step``."""

    def __init__(self):
        self.selects = [evr_model.EventSelectModel() for _ in range(CHANNELS)]
        self.channel_configs = [dict(evr_model.CHANNEL_CONFIG_DEFAULTS) for _ in range(CHANNELS)]
        self.trigger_configs = [dict(evr_model.TRIGGER_CONFIG_DEFAULTS) for _ in range(TRIGGERS)]
        self.triggers = [evr_model.TriggerModel(channels=CHANNELS) for _ in range(TRIGGERS)]
        self.history = [0] * SHIFT_LENGTH
        self.message = timing_model.default_message()
        self.select_out = [0] * CHANNELS
        self.counts = [0] * CHANNELS
        self.frames = 0

    def set_channel(self, index, **fields):
        self.channel_configs[index] = {**evr_model.CHANNEL_CONFIG_DEFAULTS, **fields}

    def set_trigger(self, index, **fields):
        self.trigger_configs[index] = {**evr_model.TRIGGER_CONFIG_DEFAULTS, **fields}

    def step(self, step):
        """Advance one clock and return the 12-bit trigOut after it."""
        arm = sum(bit << index for index, bit in enumerate(self.select_out))
        out = 0
        for index, trigger in enumerate(self.triggers):
            out |= trigger.step(self.trigger_configs[index], arm, step.strobe) << index
        new_select = [
            select.step(config, self.history[index * TAP_STRIDE + TAP_FIRST], self.message)[0]
            for index, (select, config) in enumerate(zip(self.selects, self.channel_configs))
        ]
        if step.strobe:
            self.frames += 1
            self.message = dict(step.message) if step.mode else self.lcls1_message(step.stream)
        self.history = [step.strobe] + self.history[:-1]
        self.select_out = new_select
        for index, bit in enumerate(new_select):
            self.counts[index] += bit
        return out

    def lcls1_message(self, stream):
        """Return the message the LCLS-I mapping holds: control words 16 and 17 are zero."""
        message = evr_model.from_v1(stream, self.message)
        message["control"] = message["control"][:16] + [0, 0]
        return message

    def run(self, steps):
        return [self.step(step) for step in steps]


class PulseBench(cb.Bench):
    """The composite bench with this wrapper's outputs: trigOut is the only sampled trace."""

    async def run(self, steps):
        """Apply ``steps`` one per evrClk cycle and return the list of trigOut values."""
        dut = self.dut
        samples = []
        for step in steps:
            self._drive(step)
            await sample_after_tpd(dut.evrClk, propagation_time=cb.PROPAGATION_NS)
            self.cycle += 1
            samples.append(rw.flat_value(dut.trigOut, "trigOut"))
            rw.flat_value(dut.delay_ld, "delay_ld")
            rw.flat_value(dut.delay_wr, "delay_wr")
            rw.flat_value(dut.irqEnable, "irqEnable")
        return samples

    async def reset(self):
        """Reset, send the priming strobe, and flush the strobe shift register."""
        await super().reset()
        await self.run([cb.hold_step(self.default_step)] * FLUSH_STEPS)

    async def program(self, channels, triggers):
        """Write channel and trigger configuration dictionaries, enable words last."""
        for index, fields in sorted(channels.items()):
            config = {**evr_model.CHANNEL_CONFIG_DEFAULTS, **fields}
            await self.write(channel_base(index) + 0x04, cb.channel_rate_dest_word(config))
            await self.write(channel_base(index) + 0x00, config["enabled"])
        for index, fields in sorted(triggers.items()):
            config = {**evr_model.TRIGGER_CONFIG_DEFAULTS, **fields}
            await self.write(TRIGGER_BASES[index] + 0x04, config["delay"])
            await self.write(TRIGGER_BASES[index] + 0x08, config["width"])
            await self.write(TRIGGER_BASES[index] + 0x00, cb.trigger_control_word(config))


def make_bench(dut):
    return PulseBench(dut, False)


def fixed_channel(rate_index=0):
    """Return a channel configuration that selects fixedRates bit ``rate_index`` for every destination."""
    return {"enabled": 1, "rateSel": rate_index, "destSel": cb.ALL_DESTINATIONS}


def trigger_config(channel, delay=DELAY, width=WIDTH):
    return {"enabled": 1, "polarity": 1, "channel": channel, "delay": delay, "width": width}


async def run_case(bench, channels, triggers, steps, label):
    """Reset, write the registers, settle, run ``steps`` and compare each step with the model.

    The model sees the same reset sequence, with every channel and trigger
    disabled, then takes the configuration for the same bounded settle.
    Returns ``(samples, model)``.
    """
    await bench.reset()
    await bench.program(channels, triggers)
    await bench.settle()
    model = PulseGenModel()
    primer = bench.default_step
    model.run([primer] + [cb.hold_step(primer)] * 8 + [cb.hold_step(primer)] * FLUSH_STEPS)
    for index, fields in channels.items():
        model.set_channel(index, **fields)
    for index, fields in triggers.items():
        model.set_trigger(index, **fields)
    model.run([cb.hold_step(primer)] * cb.SETTLE_CLOCKS)
    samples = await bench.run(steps)
    expected = model.run(steps)
    for index, (got, want) in enumerate(zip(samples, expected)):
        assert got == want, f"{label}: step {index} trigOut 0x{got:03X} differs from the model 0x{want:03X}"
    return samples, model


def frame_with_rates(mask):
    return cb.fixed_frame(fixed_rates=mask)


def pulse_edges(samples, bit):
    """Return ``(rises, falls)``: the sample indices at which ``bit`` of trigOut goes high and low."""
    changes = cb.edges(samples, bit)
    return [index for index, level in changes if level == 1], [index for index, level in changes if level == 0]


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def pulsegen_trigger2_end_to_end(dut):
    """Trigger 2 armed by channel 0 fires on the frame after the arming frame.

    Channel 0 and trigger 2 are written over AXI-Lite. The first frame
    arms the trigger only after its own strobe has passed, so it raises no
    edge. The next two frames each raise one pulse of the written width at a
    fixed offset after their strobe. Observed, intent unconfirmed: the
    trigger registers at 0x200 configure trigger 2 because of the address
    decode of the trigger register block.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    frames = [frame_with_rates(1) for _ in range(3)]
    steps, strobes = cb.build_schedule(frames, FRAME_SPACING)
    samples, _ = await run_case(
        bench,
        {0: fixed_channel(0)},
        {2: trigger_config(channel=0)},
        steps,
        "trigger 2",
    )
    rises, falls = pulse_edges(samples, 2)
    assert rises == [strobes[1] + DELAY + RISE_FROM_STROBE, strobes[2] + DELAY + RISE_FROM_STROBE], (
        f"trigOut(2) rises at {rises}, strobes at {strobes}"
    )
    assert [fall - rise for rise, fall in zip(rises, falls)] == [WIDTH, WIDTH], (
        f"trigOut(2) falls at {falls} for rises at {rises}"
    )
    assert all(sample & ~(1 << 2) == 0 for sample in samples), "an output other than trigOut(2) toggled"
    bench.stop()


def test_EvrV2CorePulseGen():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2corepulsegenwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
