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
    Sweep: a read-back walk of every register word the crossbar passes on
        (twelve channel groups, the global words, and the two trigger groups
        that answer); trigger 2 and trigger 3 end to end; channels 0, 5 and
        11 as the arming channel of trigger 2; per-channel and global event
        counts; the status and tap outputs; and LCLS-I event codes 40, 140
        and 255 with evrModeSel low. Addresses 0x400, 0x500, 0xB00 and
        0xF00 are probed for a decode error.
    Stimulus: a cocotbext-axi AxiLiteMaster (axilClk 10 ns) writes the
        channel registers (group i at 0x20 + 32 * i), the trigger registers
        (groups at 0x200 and 0x300) and the count reset; the evrClk side
        (7 ns) is driven one timing-bus step per cycle with frames 200
        steps apart. The trigger register block sits at crossbar address
        0x200 with a 9-bit window, but EvrV2TrigReg decodes twelve 256-byte
        groups counted from address 0, so only the groups at 0x200 and 0x300
        answer, as triggers 2 and 3, and the other triggers have no
        reachable register. That layout is observed, intent unconfirmed: it
        is asserted as measured, not as a defect. The same applies to the
        register words EvrV2Axi only maps with DMA_ENABLE_G true, which
        EvrV2CorePulseGen leaves false, and to irqReq, which nothing drives.
    Checks: every step's trigOut equals a composite model (the strobe
        shift register, per-channel event select with its tap at 12 steps
        per channel, and one cycle-accurate trigger model per output), and
        independently of the model a trigger raises one pulse of the
        written width at a fixed offset after the bus strobe of every frame
        that follows a frame its channel selected, and nothing else toggles.
        Read-back masks and reset values equal the layout tables. Event
        counts read back equal the model after a bounded wait. Every
        checked output is asserted resolvable after reset release.
    Timing: only the evrClk offsets from the bus strobe are exact; register
        writes cross a synchronizer, so they are given a bounded settle,
        and event counts are read after a bounded wait.
    Propagation sampling: the registered outputs update after TPD_G (1 ns),
        so every output is sampled 2 ns after the rising evrClk edge.
"""

import os
from pathlib import Path

import cocotb
import pytest
from cocotbext.axi import AxiResp

from tests.common import evr_model, timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    run_lcls_vhdl_test,
    sample_after_tpd,
)
from tests.lcls2_evr import composite_bench as cb
from tests.lcls2_evr import register_walk as rw

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2CorePulseGenWrapper.vhd"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
LCLS1_ENTRYPOINT = "pulsegen_lcls1_event_code"
IRQ_ENTRYPOINT = "pulsegen_irq_request_resolvable"

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
# Addresses the crossbar has no slave for: where triggers 4 to 11 would sit.
UNREACHABLE = (0x400, 0x500, 0xB00, 0xF00)
COUNT_RESET = 0x010

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
CONTROL_WORD_MODE = 2 << 11


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


def control_channel(index):
    """Return a channel configuration that selects when bit ``index`` of control word ``index`` is set.

    Control words 0 to 11 are all that twelve channels need and each has a
    single condition, so any subset of channels can be selected by one frame.
    """
    return {"enabled": 1, "rateSel": CONTROL_WORD_MODE | (index << 4) | index, "destSel": cb.ALL_DESTINATIONS}


def control_frame(mask):
    """Return a frame whose control words select exactly the channels in the bit mask ``mask``."""
    words = [(1 << index) if (mask >> index) & 1 else 0 for index in range(CHANNELS)]
    words += [0] * (evr_model.EVENT_SELECT_CONTROL_WORDS - CHANNELS)
    return cb.make_step(cb.frame_message(control=words), cb.blank_stream())


def trigger_config(channel, delay=DELAY, width=WIDTH):
    return {**evr_model.TRIGGER_CONFIG_DEFAULTS, "enabled": 1, "channel": channel, "delay": delay, "width": width}


async def run_case(bench, channels, triggers, steps, label, clear=False):
    """Reset, write the registers, settle, run ``steps`` and compare each step with the model.

    The model sees the same reset sequence, with every channel and trigger
    disabled, then takes the configuration for the same bounded settle.
    ``clear`` pulses the count reset word after the registers are written.
    Returns ``(samples, model)``.
    """
    await bench.reset()
    # EvrV2Axi has no reset, so every channel is written, not only the enabled ones.
    channels = {index: channels.get(index, {}) for index in range(CHANNELS)}
    await bench.program(channels, triggers)
    if clear:
        await clear_counts(bench)
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


async def wait_axil(bench, clocks=cb.COUNT_SETTLE_CLOCKS):
    """Wait a bounded number of axilClk cycles for a value to cross a clock domain."""
    for _ in range(clocks):
        await sample_after_tpd(bench.dut.axilClk, propagation_time=cb.PROPAGATION_NS)


async def clear_counts(bench):
    """Pulse the count reset word and wait for it to cross into the evrClk domain and back."""
    await bench.write(COUNT_RESET, 1)
    await wait_axil(bench)
    await bench.write(COUNT_RESET, 0)
    await wait_axil(bench)


async def read_counts(bench):
    """Return ``(per-channel counts, global count)`` after a bounded wait for the counters to cross back."""
    await wait_axil(bench)
    per_channel = [await bench.read(channel_base(index) + 0x08) for index in range(CHANNELS)]
    return per_channel, await bench.read(rw.AXI_GLOBAL_COUNT)


def expected_rises(strobes, selected, delay):
    """Return the sample indices at which a trigger rises.

    The trigger fires on the bus strobe of frame ``f`` when frame ``f - 1``
    selected its channel, because the channel's tap arrives after the strobe
    of the frame that produced it.
    """
    return [strobes[frame] + delay + RISE_FROM_STROBE for frame in range(1, len(strobes)) if selected[frame - 1]]


def check_pulses(samples, bit, rises_at, width, label):
    """Assert that bit ``bit`` of trigOut rises exactly at ``rises_at`` and each pulse lasts ``width`` samples."""
    rises, falls = pulse_edges(samples, bit)
    assert rises == rises_at, f"{label}: trigOut({bit}) rises at {rises}, expected {rises_at}"
    assert [fall - rise for rise, fall in zip(rises, falls)] == [width] * len(rises_at), (
        f"{label}: trigOut({bit}) falls at {falls} for rises at {rises}, expected width {width}"
    )


def check_only_bits(samples, bits, label):
    """Assert that no bit of trigOut outside ``bits`` is ever high."""
    keep = sum(1 << bit for bit in bits)
    stray = [index for index, sample in enumerate(samples) if sample & ~keep]
    assert not stray, f"{label}: an output outside {bits} is high at samples {stray[:5]}"


@cocotb.test(timeout_time=60, timeout_unit="ms")
async def pulsegen_csr_walk(dut):
    """The channel, global and trigger words read back the layout tables through the crossbar.

    Every word of the twelve channel groups and the global words, and the
    trigger groups at 0x200 and 0x300, is read after reset, written with 0
    and then with each single bit, and compared with the layout table. There
    is no configuration port on the wrapper, so only the read-back is
    checked. Words that EvrV2Axi maps only with DMA_ENABLE_G true, and the
    trigger tap word, read as 0 and ignore writes. Observed, intent
    unconfirmed: the crossbar answers OKAY for every unmapped address inside
    its two windows.

    Propagation sampling: the walk is paced by axilClk edges followed by a 2 ns wait.
    """
    bench = make_bench(dut)
    await bench.start()
    await bench.reset()
    await clear_counts(bench)
    settle = rw.make_settle(dut)

    async def walk(address, layout, defaults, word, label):
        walked = await rw.walk_word(bench.master, address, lambda: 0, settle, {}, ignore=())
        reset, mask = cb.expected_word(layout, defaults, word)
        assert walked.reset_value == reset, f"{label} reads 0x{walked.reset_value:08X} after reset, expected 0x{reset:08X}"
        assert walked.readback_mask == mask, f"{label} read-back mask 0x{walked.readback_mask:08X}, expected 0x{mask:08X}"

    def present(layout):
        return [word for word, fields in layout.items() if any(entry.condition is None for entry in fields)]

    def absent(layout):
        return [word for word, fields in layout.items() if all(entry.condition is not None for entry in fields)]

    channel_layout = rw.CHANREG_LAYOUT
    for index in range(CHANNELS):
        for word in present(channel_layout):
            await walk(channel_base(index) + word, channel_layout, evr_model.CHANNEL_CONFIG_DEFAULTS, word, f"channel {index} word 0x{word:02X}")
        for word in absent(channel_layout):
            await absent_word(bench, channel_base(index) + word, f"channel {index} word 0x{word:02X}")

    axi_defaults = {**evr_model.CHANNEL_CONFIG_DEFAULTS, "countReset": 0, "trigSel": 0}
    for word in present(rw.AXI_LAYOUT):
        await walk(word, rw.AXI_LAYOUT, axi_defaults, word, f"global word 0x{word:03X}")
    for word in absent(rw.AXI_LAYOUT):
        await absent_word(bench, word, f"global word 0x{word:03X}")

    trigger_layout = rw.TRIGREG_LAYOUT
    for trigger, base in TRIGGER_BASES.items():
        for word in present(trigger_layout):
            await walk(base + word, trigger_layout, evr_model.TRIGGER_CONFIG_DEFAULTS, word, f"trigger {trigger} word 0x{word:02X}")
        for word in absent(trigger_layout):
            await absent_word(bench, base + word, f"trigger {trigger} word 0x{word:02X}")
    bench.stop()


async def absent_word(bench, address, label):
    """Assert that a word is not implemented: it reads 0 and a write of all ones does not stick."""
    assert await bench.read(address) == 0, f"{label} should read 0"
    await bench.write(address, 0xFFFFFFFF)
    assert await bench.read(address) == 0, f"{label} holds a written value"
    await bench.write(address, 0)


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def pulsegen_trigger_groups(dut):
    """Only the trigger groups at 0x200 and 0x300 answer, and they are independent of each other.

    Observed, intent unconfirmed: the trigger block sits at crossbar base
    0x200 with addrBits 9 while EvrV2TrigReg decodes twelve 256-byte groups
    from address 0, so the groups at 0x200 and 0x300 are triggers 2 and 3.
    Each group holds its own control, delay and width words, a write to one
    leaves the other unchanged, and the bytes of a group above its last word
    read 0.

    Propagation sampling: the walk is paced by axilClk edges followed by a 2 ns wait.
    """
    bench = make_bench(dut)
    await bench.start()
    await bench.reset()
    values = {
        2: {0x00: cb.trigger_control_word(trigger_config(channel=7)), 0x04: 0x111, 0x08: 0x222},
        3: {0x00: cb.trigger_control_word(trigger_config(channel=9)), 0x04: 0x333, 0x08: 0x444},
    }
    for trigger, words in values.items():
        for word, value in words.items():
            await bench.write(TRIGGER_BASES[trigger] + word, value)
    for trigger, words in values.items():
        for word, value in words.items():
            got = await bench.read(TRIGGER_BASES[trigger] + word)
            assert got == value, f"trigger {trigger} word 0x{word:02X} reads 0x{got:08X}, expected 0x{value:08X}"
        for word in (0x0C, 0x10, 0x80, 0xFC):
            assert await bench.read(TRIGGER_BASES[trigger] + word) == 0, f"trigger {trigger} word 0x{word:02X} should read 0"
    for trigger, words in values.items():
        for word in words:
            await bench.write(TRIGGER_BASES[trigger] + word, 0)
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def pulsegen_unreachable_decerr(dut):
    """Addresses at and above 0x400 answer a decode error for both reads and writes.

    Observed, intent unconfirmed: these are where triggers 4 to 11 would sit
    if the trigger block were decoded from its own base, and the crossbar
    has no slave for them. A decode error does not disturb the two windows
    that do answer: a trigger word written before the probes reads back the
    same afterwards.

    Propagation sampling: the walk is paced by axilClk edges followed by a 2 ns wait.
    """
    bench = make_bench(dut)
    await bench.start()
    await bench.reset()
    await bench.write(TRIGGER_BASES[2] + 0x04, 0x55)
    for address in UNREACHABLE:
        await rw.write_word(bench.master, address, 0xFFFFFFFF, expect=AxiResp.DECERR)
        await rw.read_word(bench.master, address, expect=AxiResp.DECERR)
    assert await bench.read(TRIGGER_BASES[2] + 0x04) == 0x55, "a decode error changed a trigger word"
    await bench.write(TRIGGER_BASES[2] + 0x04, 0)
    bench.stop()


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def pulsegen_trigger3_end_to_end(dut):
    """Trigger 3 at 0x300 follows channel 1, and no other trigger output toggles.

    Channels 0 and 1 both select every frame, and enable words for triggers
    4, 5 and 11 are written at the addresses where they would sit; the
    crossbar answers each with a decode error. Observed, intent unconfirmed:
    those triggers have no reachable register, so trigOut(0), (1), (2) and
    (4) to (11) stay idle while trigOut(3) pulses.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    await bench.reset()
    for address in (0x400, 0x500, 0xB00):
        await rw.write_word(bench.master, address + 0x04, 2, expect=AxiResp.DECERR)
        await rw.write_word(bench.master, address + 0x08, 3, expect=AxiResp.DECERR)
        await rw.write_word(bench.master, address, cb.trigger_control_word(trigger_config(channel=0)), expect=AxiResp.DECERR)
    frames = [frame_with_rates(0b11) for _ in range(3)]
    steps, strobes = cb.build_schedule(frames, FRAME_SPACING)
    samples, _ = await run_case(
        bench,
        {0: fixed_channel(0), 1: fixed_channel(1)},
        {3: trigger_config(channel=1, delay=2, width=4)},
        steps,
        "trigger 3",
    )
    check_pulses(samples, 3, expected_rises(strobes, [True] * 3, 2), 4, "trigger 3")
    check_only_bits(samples, [3], "trigger 3")
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def pulsegen_channel_taps(dut):
    """Channels 0, 5 and 11, each through its own tap, arm trigger 2 and no other channel does.

    All twelve channels are enabled, channel j on bit j of control word j.
    Trigger 2 is pointed at channel k in turn. A frame that sets only that
    bit arms it; a frame that sets only the next channel's bit arms the
    neighbour channel and leaves trigger 2 alone. The tap of channel 11
    reaches 137 steps past the bus strobe, so for every channel the trigger
    fires on the frame after the one that armed it.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    for k in (0, 5, 11):
        neighbour = (k + 1) % CHANNELS
        hit = control_frame(1 << k)
        miss = control_frame(1 << neighbour)
        pattern = [hit, miss, miss, hit, hit]
        selected = [True, False, False, True, True]
        steps, strobes = cb.build_schedule(pattern, FRAME_SPACING, tail=SHIFT_LENGTH)
        samples, model = await run_case(
            bench,
            {index: control_channel(index) for index in range(CHANNELS)},
            {2: trigger_config(channel=k)},
            steps,
            f"channel {k}",
        )
        check_pulses(samples, 2, expected_rises(strobes, selected, DELAY), WIDTH, f"channel {k}")
        check_only_bits(samples, [2], f"channel {k}")
        want = [0] * CHANNELS
        want[k] = 3
        want[neighbour] = 2
        assert model.counts == want, f"channel {k}: selected counts {model.counts}, expected {want}"
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def pulsegen_event_counts(dut):
    """Per-channel and global event counts read back the number of selected frames and strobes.

    Channel j is selected by j % 4 + 1 of six frames; the last two frames
    select nothing. The counters are cleared through the count reset word
    first, which also shows that the reset reaches every counter.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    wanted = [index % 4 + 1 for index in range(CHANNELS)]
    masks = [sum(1 << index for index in range(CHANNELS) if round_index < wanted[index]) for round_index in range(4)]
    frames = [control_frame(mask) for mask in masks + [0, 0]]
    steps, _ = cb.build_schedule(frames, FRAME_SPACING, tail=SHIFT_LENGTH)
    samples, model = await run_case(
        bench,
        {index: control_channel(index) for index in range(CHANNELS)},
        {},
        steps,
        "event counts",
        clear=True,
    )
    assert model.counts == wanted, f"model counts {model.counts} differ from the selection plan {wanted}"
    assert all(sample == 0 for sample in samples), "trigOut toggled with no trigger enabled"
    per_channel, total = await read_counts(bench)
    assert per_channel == wanted, f"channel counts {per_channel}, expected {wanted}"
    assert total == len(frames), f"global count {total}, expected {len(frames)}"
    await clear_counts(bench)
    per_channel, total = await read_counts(bench)
    assert per_channel == [0] * CHANNELS and total == 0, f"counts {per_channel} and {total} after a count reset"
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def pulsegen_status_outputs(dut):
    """The status, interrupt and tap ports read as measured.

    Observed, intent unconfirmed: EvrV2CorePulseGen builds EvrV2Axi without
    DMA_ENABLE_G and builds EvrV2TrigReg without USE_TAP_C, so the words for
    irqEnable, irqReq, gtxDebug and the delay tap are not mapped. Writing 1
    to the irqEnable word leaves irqEnable low, and the word for gtxDebug
    reads 0 for a pattern driven on the input. delay_ld and delay_wr stay at
    0 when the tap word is written, and delay_rd has no readable word.
    irqReq is driven by nothing in the entity and stays unresolved, so it is
    not among the outputs asserted resolvable.

    Propagation sampling: outputs are sampled 2 ns after the rising edge of the clock they follow.
    """
    bench = make_bench(dut)
    await bench.start()
    await bench.reset()
    assert not dut.irqReq.value.is_resolvable, f"irqReq is driven to {dut.irqReq.value}"
    await bench.write(0x000, 1)
    for pattern in (0xA5, 0x5A):
        dut.gtxDebug.value = pattern
        await wait_axil(bench)
        assert await bench.read(0x00C) == 0, f"gtxDebug pattern 0x{pattern:02X} is visible through the CSR"
    await wait_axil(bench)
    assert rw.flat_value(dut.irqEnable, "irqEnable") == 0, "irqEnable followed a write to an unmapped word"
    assert await bench.read(0x000) == 0
    dut.delay_rd.value = (1 << 72) - 1
    for trigger, base in TRIGGER_BASES.items():
        await bench.write(base + 0x0C, 0x3F)
        assert await bench.read(base + 0x0C) == 0, f"trigger {trigger} tap word is readable"
    await wait_axil(bench)
    await bench.run([cb.hold_step(bench.default_step)] * cb.SETTLE_CLOCKS)
    assert rw.flat_value(dut.delay_ld, "delay_ld") == 0, "delay_ld changed"
    assert rw.flat_value(dut.delay_wr, "delay_wr") == 0, "delay_wr changed"
    dut.gtxDebug.value = 0
    dut.delay_rd.value = 0
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def pulsegen_lcls1_event_code(dut):
    """With evrModeSel low, event codes 40, 140 and 255 select through control-word channels.

    Channel 0 watches code 40, channel 1 code 140 and channel 2 code 255. A
    frame whose stream sets one code arms the trigger on that channel: trigger
    2 follows channel 0 and trigger 3 follows channel 1 in the first run, and
    trigger 2 follows channel 2 in the second. A frame that sets no code arms
    nothing. This is the behavior the entity is meant to have: on the current
    RTL the first strobe with evrModeSel low aborts the simulator, so the
    test runs only in its own simulation when the known-issue tests are
    enabled.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()

    def code_frame(*codes):
        mask = sum(1 << code for code in codes)
        return cb.make_step(cb.frame_message(), {**cb.blank_stream(), "eventCodes": mask}, mode=0)

    def code_channel(code):
        rate_sel = (2 << 11) | ((code // 16) << 4) | (code % 16)
        return {"enabled": 1, "rateSel": rate_sel, "destSel": cb.ALL_DESTINATIONS}

    channels = {0: code_channel(40), 1: code_channel(140), 2: code_channel(255)}
    frames = [code_frame(40), code_frame(140), code_frame(40, 140), code_frame(), code_frame(), code_frame(140), code_frame()]
    steps, strobes = cb.build_schedule(frames, FRAME_SPACING)
    samples, _ = await run_case(
        bench,
        channels,
        {2: trigger_config(channel=0), 3: trigger_config(channel=1)},
        steps,
        "event codes 40 and 140",
    )
    check_pulses(samples, 2, expected_rises(strobes, [True, False, True, False, False, False, False], DELAY), WIDTH, "code 40")
    check_pulses(samples, 3, expected_rises(strobes, [False, True, True, False, False, True, False], DELAY), WIDTH, "code 140")
    check_only_bits(samples, [2, 3], "event codes 40 and 140")
    frames = [code_frame(255), code_frame(40), code_frame(255), code_frame()]
    steps, strobes = cb.build_schedule(frames, FRAME_SPACING)
    samples, _ = await run_case(bench, channels, {2: trigger_config(channel=2)}, steps, "event code 255")
    check_pulses(samples, 2, expected_rises(strobes, [True, False, True, False], DELAY), WIDTH, "code 255")
    check_only_bits(samples, [2], "event code 255")
    bench.stop()

@cocotb.test(timeout_time=2, timeout_unit="ms")
async def pulsegen_irq_request_resolvable(dut):
    """irqReq carries a resolved level once reset is released.

    Nothing in the entity drives the signal behind irqReq, so it stays
    unresolved. This is the behavior the entity is meant to have, so the test
    runs only in its own simulation when the known-issue tests are enabled.

    Propagation sampling: the output is sampled 2 ns after the rising axilClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    await bench.reset()
    await sample_after_tpd(dut.axilClk, propagation_time=cb.PROPAGATION_NS)
    assert dut.irqReq.value.is_resolvable, f"irqReq carries unresolved bits: {dut.irqReq.value}"
    bench.stop()


ENTRYPOINTS = (
    "pulsegen_trigger2_end_to_end",
    "pulsegen_csr_walk",
    "pulsegen_trigger_groups",
    "pulsegen_unreachable_decerr",
    "pulsegen_trigger3_end_to_end",
    "pulsegen_channel_taps",
    "pulsegen_event_counts",
    "pulsegen_status_outputs",
)


def run_entrypoint(entrypoint):
    """Run one entrypoint in its own simulation: EvrV2Axi has no reset, so a shared run would leak register state."""
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2corepulsegenwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({}, cocotb_test_filter(entrypoint)),
    )


@pytest.mark.parametrize("entrypoint", [pytest.param(name, id=name.removeprefix("pulsegen_")) for name in ENTRYPOINTS])
def test_EvrV2CorePulseGen(entrypoint):
    run_entrypoint(entrypoint)


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2CorePulseGen with evrModeSel low aborts the simulator at the first timing strobe "
        "because the event message assignment is 32 bits narrower than its target; "
        "see https://github.com/slaclab/lcls-timing-core/issues/217; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2CorePulseGen_known_issue_lcls1_strobe():
    run_entrypoint(LCLS1_ENTRYPOINT)


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2CorePulseGen leaves irqReq undriven so it reads unresolved after reset; "
        "see https://github.com/slaclab/lcls-timing-core/issues/217; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2CorePulseGen_known_issue_irq_request():
    run_entrypoint(IRQ_ENTRYPOINT)
