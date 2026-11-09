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
    Sweep: NCHANNELS_G, NTRIGGERS_G and TRIG_PIPE_G over (1, 1, 0), (2, 4, 16),
        (3, 3, 4) and (16, 16, 1) with separate clocks (axilClk 10 ns, evrClk
        7 ns), a reduced smoke set with COMMON_CLK_G true on (2, 4, 16), and a
        register walk with EVR_CARD_G true on (2, 4, 16). TRIG_DEPTH_G stays
        28. Within a set: delays 0, 5 and 40, widths 1 and 3, both
        polarities, the four destination modes, LCLS-I event codes 1, 40, 140
        and 255, complementary pairs, queue depth, adjacency, empty,
        ordering, idempotency and concurrency edge cases, and seeded random
        configurations.
    Stimulus: a cocotbext-axi AxiLiteMaster writes the channel registers at
        0x80000 and the trigger registers at 0x81000 (0xA0000 when
        EVR_CARD_G is true); the evrClk side is driven one timing-bus step per
        cycle through the wrapper. Random configurations keep rateSel(8:4)
        at most 17 and every enabled trigger on a channel below NCHANNELS_G;
        no register is ever filled with random or all-ones values.
    Checks: after a bounded 30-cycle settle that follows the last register
        write, every step's trigPulse, timeStamp, bsa and dmod equal the
        composite model (an EvrV2FromV1 copy, EventSelectModel on the second
        strobe stage, TriggerModel fired by the fourth stage, and the
        complementary stage), and each directed case also states its
        expected edges or counts independently of the model. The register
        walk compares read-back masks and reset values with the layout
        tables at both register strides. Every output is asserted resolvable.
    Timing: only evrClk timing relative to the bus strobe is exact; the
        register writes cross a synchronizer, so they are given a bounded
        settle instead of an exact cycle count, and event counts are read
        after a bounded wait.
    Propagation sampling: the registered outputs update after TPD_G (1 ns),
        so every output is sampled 2 ns after the rising evrClk edge.
"""

import os
from pathlib import Path

import cocotb
import pytest

from tests.common import evr_model, timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    env_int,
    hdl_parameters_from,
    parameter_case,
    run_lcls_vhdl_test,
)
from tests.lcls2_evr import composite_bench as cb
from tests.lcls2_evr import register_walk as rw

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2CoreTriggersWrapper.vhd"

CHANNELS = env_int("NCHANNELS_G", default=1)
TRIGGERS = env_int("NTRIGGERS_G", default=1)
TRIG_DEPTH = env_int("TRIG_DEPTH_G", default=28)
TRIG_PIPE = env_int("TRIG_PIPE_G", default=0)
COMMON = os.getenv("COMMON_CLK_G", "false") == "true"
CARD = os.getenv("EVR_CARD_G", "false") == "true"

# Steps from the strobe step to the first high sample is this constant plus
# the trigger delay: the strobe crosses four register stages before it fires
# the trigger, and the trigger adds its delay plus a fixed latency (measured).
FIRE_TO_RISE_BASE = 7

FRAME_GAP = 100
RANDOM_FRAMES = 50
NOISE_STEPS = 6
FIXED_RATE_MODE = 0
CONTROL_WORD_MODE = 2 << 11
ALL_DESTINATIONS = cb.ALL_DESTINATIONS

SMOKE_ENTRYPOINT = "coretriggers_smoke"
WALK_ENTRYPOINT = "coretriggers_register_walk"
PAIRS_ENTRYPOINT = "coretriggers_compl_pairs"


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


def warmed_model(channels, triggers, bench):
    """Return a model that has seen the same idle settle cycles as the bench."""
    model = make_model(channels, triggers)
    idle = cb.hold_step(bench.default_step)
    for _ in range(cb.SETTLE_CLOCKS):
        model.step(idle)
    return model


async def prepare(bench, channels, triggers):
    """Reset both domains, write the registers, and wait the bounded settle."""
    await bench.reset()
    await bench.program(CARD, channels, triggers)
    await bench.settle()
    return warmed_model(channels, triggers, bench)


async def run_case(bench, channels, triggers, steps, label):
    """Prepare a case, run ``steps``, and compare every step with the model.

    Returns ``(samples, model)``.
    """
    model = await prepare(bench, channels, triggers)
    samples = await bench.run(steps)
    cb.compare_samples(samples, model.run(steps), label)
    return samples, model


def fixed_frame(fixed_rates=1, **fields):
    """Return a bus step with the given fixedRates and message fields."""
    return cb.make_step(cb.frame_message(fixedRates=fixed_rates, **fields), cb.blank_stream())


def fixed_channel(index=0, **fields):
    """Return ``{index: config}`` for a channel that selects fixed rate 0 for all destinations."""
    return {index: {"enabled": 1, "rateSel": 0, "destSel": ALL_DESTINATIONS, **fields}}


def trigger_on(channel=0, **fields):
    """Return an enabled trigger configuration armed by ``channel``."""
    return {"enabled": 1, "channel": channel, "polarity": 1, "delay": 5, "width": 3, **fields}


def check_pulses(levels, strobes, delay, width, label, bit=0):
    """Assert one pulse per strobe with the expected rise offset and width."""
    up = cb.rises(levels, bit)
    down = [index for index, level in cb.edges(levels, bit) if level == 0]
    assert up == [strobe + FIRE_TO_RISE_BASE + delay for strobe in strobes], (
        f"{label}: rises {up}, expected strobes {strobes} plus {FIRE_TO_RISE_BASE + delay}"
    )
    widths = [low - high for high, low in zip(up, down)]
    assert widths == [width] * len(strobes), f"{label}: pulse widths {widths}, expected {width}"


def one_trigger_scenario():
    """Return ``(channels, triggers, steps, strobes)`` of the single trigger scenario.

    Channel 0 selects fixed rate 0 for all destinations, trigger 0 is armed by
    channel 0 with delay 5 and width 3, and frames 1 and 3 of four carry
    fixedRates(0).
    """
    miss = fixed_frame(0)
    hit = fixed_frame(1)
    steps, strobes = cb.build_schedule([miss, hit, miss, hit], FRAME_GAP)
    return fixed_channel(), {0: trigger_on()}, steps, strobes


def check_one_trigger(samples, strobes):
    levels = [sample.trig_pulse for sample in samples]
    check_pulses(levels, [strobes[1], strobes[3]], 5, 3, "one trigger")


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def coretriggers_one_trigger_end_to_end(dut):
    """One register-configured trigger fires on the selected frames at the modeled cycles.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    channels, triggers, steps, strobes = one_trigger_scenario()
    samples, _ = await run_case(bench, channels, triggers, steps, "one trigger")
    check_one_trigger(samples, strobes)
    bench.stop()


def groups_to_walk(count):
    """Return every group index for up to four groups, otherwise the first and the last."""
    return list(range(count)) if count <= 4 else [0, count - 1]


def expected_word(layout, defaults, word):
    """Return ``(reset value, read-back mask)`` of a register word with no optional generic enabled."""
    reset = 0
    mask = 0
    for entry in layout[word]:
        if entry.condition is not None or entry.mode != "RW":
            continue
        mask |= ((1 << entry.width) - 1) << entry.lsb
        reset |= defaults[entry.name] << entry.lsb
    return reset, mask


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_register_walk(dut):
    """The composite address map reads back the channel and trigger layouts at the active stride.

    The walk reads each word after reset, writes 0 and then each single bit,
    and compares the read-back mask and the reset value with the layout
    tables. There is no configuration port, so only the read-back is checked.
    Words that exist only with the DMA or delay-tap generics read 0.

    Propagation sampling: the walk is paced by axilClk edges followed by a 2 ns wait.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    settle = rw.make_settle(dut)
    for kind, count, address, layout, defaults in (
        ("channel", CHANNELS, cb.channel_address, rw.CHANREG_LAYOUT, evr_model.CHANNEL_CONFIG_DEFAULTS),
        ("trigger", TRIGGERS, cb.trigger_address, rw.TRIGREG_LAYOUT, evr_model.TRIGGER_CONFIG_DEFAULTS),
    ):
        present = [
            word for word, fields in layout.items() if any(entry.condition is None for entry in fields)
        ]
        absent = [word for word in layout if word not in present]
        for group in groups_to_walk(count):
            base = address(group, CARD)
            for word in present:
                walk = await rw.walk_word(bench.master, base + word, lambda: 0, settle, {}, ignore=())
                reset, mask = expected_word(layout, defaults, word)
                assert walk.reset_value == reset, (
                    f"{kind} {group} word 0x{word:02X} reads 0x{walk.reset_value:08X} after reset, "
                    f"expected 0x{reset:08X}"
                )
                assert walk.readback_mask == mask, (
                    f"{kind} {group} word 0x{word:02X} read-back mask 0x{walk.readback_mask:08X}, "
                    f"expected 0x{mask:08X}"
                )
            for word in absent:
                assert await bench.read(base + word) == 0, f"{kind} {group} word 0x{word:02X} should read 0"
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_delay_width_polarity(dut):
    """Delays 0, 5, 40, widths 1 and 3, and both polarities follow the model, with edges stated for polarity 1.

    Polarity 0 is asserted as the model reports it (observed, intent
    unconfirmed): the output does not idle high until the first pulse ends.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    frames = [fixed_frame(1), fixed_frame(0), fixed_frame(1), fixed_frame(1)]
    steps, strobes = cb.build_schedule(frames, FRAME_GAP, tail=80)
    selected = [strobes[0], strobes[2], strobes[3]]
    for polarity in (1, 0):
        for delay in (0, 5, 40):
            for width in (1, 3):
                label = f"polarity {polarity} delay {delay} width {width}"
                triggers = {0: trigger_on(polarity=polarity, delay=delay, width=width)}
                samples, _ = await run_case(bench, fixed_channel(), triggers, steps, label)
                levels = [sample.trig_pulse for sample in samples]
                assert cb.edges(levels), f"{label}: the output never changed"
                if polarity == 1:
                    check_pulses(levels, selected, delay, width, label)
    bench.stop()


def selected_by_rule(mode, mask, destination, beam):
    """Return whether a destination request selects the channel, from the register description."""
    requested = beam and (mask >> destination) & 1
    return bool({0: requested, 1: not requested, 2: True, 3: False}[mode])


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_destinations(dut):
    """The four destination modes select as the beam request word says.

    Mode 0 selects a requested destination in the mask, mode 1 selects every
    frame except those, mode 2 always selects and mode 3 never does.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    requests = [(destination, beam) for destination in (0, 5, 3) for beam in (0, 1)]
    frames = [fixed_frame(1, beamRequest=(destination << 4) | beam) for destination, beam in requests]
    steps, strobes = cb.build_schedule(frames, 40)
    for mode in range(4):
        for mask in (0x0021, 0x0008):
            label = f"destination mode {mode} mask 0x{mask:04X}"
            channels = fixed_channel(destSel=(mode << 16) | mask)
            triggers = {0: trigger_on(delay=2, width=2)}
            samples, _ = await run_case(bench, channels, triggers, steps, label)
            wanted = [
                strobe
                for strobe, (destination, beam) in zip(strobes, requests)
                if selected_by_rule(mode, mask, destination, beam)
            ]
            got = cb.rises([sample.trig_pulse for sample in samples])
            assert got == [strobe + FIRE_TO_RISE_BASE + 2 for strobe in wanted], (
                f"{label}: rises {got}, expected frames at {wanted}"
            )
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_lcls1_event_codes(dut):
    """With evrModeSel low, an LCLS-I event code selects through control word n // 16 bit n % 16.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    for code in (1, 40, 140, 255):
        label = f"event code {code}"
        other = (code + 7) % 255 + 1
        masks = [1 << code, 0, 1 << other, 1 << code]
        frames = [
            cb.make_step(cb.frame_message(), {**cb.blank_stream(), "eventCodes": mask}, mode=0)
            for mask in masks
        ]
        steps, strobes = cb.build_schedule(frames, 40)
        rate_sel = CONTROL_WORD_MODE | ((code // 16) << 4) | (code % 16)
        channels = fixed_channel(rateSel=rate_sel)
        triggers = {0: trigger_on(delay=3, width=2)}
        samples, _ = await run_case(bench, channels, triggers, steps, label)
        got = cb.rises([sample.trig_pulse for sample in samples])
        assert got == [strobes[0] + FIRE_TO_RISE_BASE + 3, strobes[3] + FIRE_TO_RISE_BASE + 3], (
            f"{label}: rises {got}, expected frames 0 and 3 at strobes {strobes}"
        )
    bench.stop()


@cocotb.test(skip=TRIGGERS < 2, timeout_time=10, timeout_unit="ms")
async def coretriggers_compl_pairs(dut):
    """A complementary pair outputs the AND or the OR of its two triggers, and an odd trigger bypasses the stage.

    The raw traces come from a run with complEn clear; the AND and OR runs
    use the same stimulus, so their outputs are compared with the bitwise AND
    and OR of the raw traces. With an odd trigger count the last trigger
    passes straight through even when its own complementary bits are set.

    Skipped when NTRIGGERS_G is below 2 because there is no pair.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    frames = [fixed_frame(1)] * 3
    steps, _ = cb.build_schedule(frames, 60)
    odd = TRIGGERS % 2 == 1 and TRIGGERS >= 3
    timing = [(2, 6), (5, 6), (8, 6)]
    count = 3 if odd else 2

    def triggers_for(compl):
        result = {}
        for index in range(count):
            delay, width = timing[index]
            fields = {"complEn": 0, "complAnd": 0, **compl.get(index, {})}
            result[index] = trigger_on(delay=delay, width=width, **fields)
        return result

    async def trace(compl, label):
        samples, _ = await run_case(bench, fixed_channel(), triggers_for(compl), steps, label)
        return [sample.trig_pulse for sample in samples]

    def bit(value, index):
        return (value >> index) & 1

    raw = await trace({}, "raw")
    low = [bit(value, 0) for value in raw]
    high = [bit(value, 1) for value in raw]
    assert any(a and b for a, b in zip(low, high)), "the two raw pulses never overlap"
    assert any(a != b for a, b in zip(low, high)), "the two raw pulses are never different"
    for complement, label, combine in (
        (1, "and", lambda a, b: a & b),
        (0, "or", lambda a, b: a | b),
    ):
        compl = {index: {"complEn": 1, "complAnd": complement} for index in range(count)}
        got = await trace(compl, label)
        want = [combine(a, b) for a, b in zip(low, high)]
        assert [bit(v, 0) for v in got] == want, f"{label}: output 0 is not the {label} of the two triggers"
        assert [bit(v, 1) for v in got] == want, f"{label}: output 1 is not the {label} of the two triggers"
        if odd:
            assert [bit(v, 2) for v in got] == [bit(v, 2) for v in raw], f"{label}: the odd trigger was not bypassed"
    mixed = await trace({1: {"complEn": 1, "complAnd": 1}}, "mixed")
    assert [bit(v, 0) for v in mixed] == low, "output 0 changed although its complEn is clear"
    assert [bit(v, 1) for v in mixed] == [a & b for a, b in zip(low, high)], "output 1 is not the AND"
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_queue_depth(dut):
    """The pulses accepted while the delay runs equal the queue capacity of TRIG_PIPE_G.

    Observed, intent unconfirmed: TRIG_PIPE_G is the queue-depth generic of
    each trigger, and TRIG_DEPTH_G (28 here) is only the width of the delay
    and width counters. With a delay longer than the whole burst of fires
    every frame, the number of pulses equals queue_capacity(TRIG_PIPE_G), so
    the capacity follows TRIG_PIPE_G and not TRIG_DEPTH_G. The default
    TRIG_PIPE_G of 0 therefore accepts only 3 pulses.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    capacity = evr_model.queue_capacity(TRIG_PIPE)
    spacing = 4
    frames_count = capacity + 4
    delay = spacing * (frames_count + 10)
    frames = [fixed_frame(1)] * frames_count
    steps, _ = cb.build_schedule(frames, spacing, tail=delay + spacing * frames_count + 40)
    triggers = {0: trigger_on(delay=delay, width=2)}
    samples, _ = await run_case(bench, fixed_channel(), triggers, steps, "queue depth")
    pulses = len(cb.rises([sample.trig_pulse for sample in samples]))
    dut._log.info(f"TRIG_PIPE_G {TRIG_PIPE} TRIG_DEPTH_G {TRIG_DEPTH}: {pulses} pulses for {frames_count} fires")
    assert pulses == capacity, f"TRIG_PIPE_G {TRIG_PIPE}: {pulses} pulses accepted, queue capacity says {capacity}"
    bench.stop()


def ordering_selection(frame, channel):
    return ((frame * 7 + channel * 3) % 5) < 2


def ordering_rate_sel(channel):
    """Return the rateSel that watches message bit ``channel``: fixedRates up to 9, control word 0 above."""
    if channel < evr_model.FIXED_RATE_COUNT:
        return FIXED_RATE_MODE | channel
    return CONTROL_WORD_MODE | (channel - evr_model.FIXED_RATE_COUNT)


def ordering_frame(frame):
    fixed = 0
    control = 0
    for channel in range(CHANNELS):
        if ordering_selection(frame, channel):
            if channel < evr_model.FIXED_RATE_COUNT:
                fixed |= 1 << channel
            else:
                control |= 1 << (channel - evr_model.FIXED_RATE_COUNT)
    words = [control] + [0] * (evr_model.EVENT_SELECT_CONTROL_WORDS - 1)
    return fixed_frame(fixed, control=words)


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_edges(dut):
    """Adjacency, empty, and ordering edges of the composite.

    Adjacency: two triggers armed by the same channel with equal delay and
    width rise and fall on the same edge. Empty: a disabled channel, a
    disabled trigger, width 0, and a run with no frames each produce no
    trigger edge. Ordering: the event count read back for each channel equals
    the number of frames it selected, and each trigger's pulses come in frame
    order at a fixed offset from their strobes.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    frames = [fixed_frame(1)] * 3
    steps, strobes = cb.build_schedule(frames, 80)

    if TRIGGERS >= 2:
        triggers = {0: trigger_on(), 1: trigger_on()}
        samples, _ = await run_case(bench, fixed_channel(), triggers, steps, "adjacency")
        levels = [sample.trig_pulse & 0b11 for sample in samples]
        assert all(value in (0, 3) for value in levels), "two equal triggers did not move on the same edge"
        check_pulses(levels, strobes, 5, 3, "adjacency")
    else:
        dut._log.info("adjacency needs two triggers and is skipped for NTRIGGERS_G 1")

    empty_cases = (
        ("disabled channel", fixed_channel(enabled=0), {0: trigger_on()}, steps),
        ("disabled trigger", fixed_channel(), {0: trigger_on(enabled=0)}, steps),
        ("width 0", fixed_channel(), {0: trigger_on(width=0)}, steps),
        ("no frames", fixed_channel(), {0: trigger_on()}, [cb.hold_step(frames[0])] * len(steps)),
    )
    for label, channels, triggers, case_steps in empty_cases:
        samples, _ = await run_case(bench, channels, triggers, case_steps, label)
        levels = {sample.trig_pulse for sample in samples}
        assert len(levels) == 1, f"{label}: the outputs changed ({sorted(levels)})"

    frames_count = 14
    ordering = [ordering_frame(frame) for frame in range(frames_count)]
    order_steps, order_strobes = cb.build_schedule(ordering, 60)
    channels = {
        index: {"enabled": 1, "rateSel": ordering_rate_sel(index), "destSel": ALL_DESTINATIONS}
        for index in range(CHANNELS)
    }
    triggers = {index: trigger_on(channel=index % CHANNELS, delay=3, width=2) for index in range(TRIGGERS)}
    samples, model = await run_case(bench, channels, triggers, order_steps, "ordering")
    levels = [sample.trig_pulse for sample in samples]
    for index in range(TRIGGERS):
        picked = [frame for frame in range(frames_count) if ordering_selection(frame, index % CHANNELS)]
        want = [order_strobes[frame] + FIRE_TO_RISE_BASE + 3 for frame in picked]
        assert cb.rises(levels, index) == want, (
            f"trigger {index}: pulses are not the frames {picked} in order at a fixed offset"
        )
    for index in range(CHANNELS):
        expected = sum(ordering_selection(frame, index) for frame in range(frames_count))
        assert expected > 0, f"channel {index} selects no frame"
        count = await bench.event_count(index, CARD)
        assert count == expected == model.path.counts[index], (
            f"channel {index}: event count {count}, expected {expected} (model {model.path.counts[index]})"
        )
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_rewrite_is_idempotent(dut):
    """Rewriting identical registers while frames flow leaves the pulse train unchanged.

    A run without the rewrite gives the reference trace; the run with the
    rewrite must equal it step for step (asserted after measuring: a
    difference would be a behavior that is observed, intent unconfirmed).

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    frames = [fixed_frame(1)] * 6
    steps, strobes = cb.build_schedule(frames, FRAME_GAP)
    channels = fixed_channel()
    triggers = {0: trigger_on()}
    reference, _ = await run_case(bench, channels, triggers, steps, "reference")

    model = await prepare(bench, channels, triggers)
    start = bench.cycle
    runner = cocotb.start_soon(bench.run(steps))
    await bench.wait_for_cycle(start + strobes[2] + 40)
    await bench.program(CARD, channels, triggers)
    samples = await runner
    cb.compare_samples(samples, model.run(steps), "with rewrite")
    assert [s.trig_pulse for s in samples] == [s.trig_pulse for s in reference], (
        "an identical rewrite changed the pulse train"
    )
    assert len(cb.rises([s.trig_pulse for s in samples])) == 6
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_write_while_running(dut):
    """A delay write that lands while frames flow takes effect within the bounded window.

    Frames before the write keep the old delay, frames after the bounded
    window (30 evrClk cycles after the write returns) use the new delay, and
    the frames inside the window are only recorded: which delay they see is
    observed, intent unconfirmed.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    old_delay, new_delay = 5, 40
    frames = [fixed_frame(1)] * 8
    gaps = [0, 100, 100, 38, 22, 125, 100, 100]
    steps, strobes = cb.build_schedule(frames, gaps, lead=20, tail=80)
    channels = fixed_channel()
    model_old = await prepare(bench, channels, {0: trigger_on(delay=old_delay)})
    model_new = warmed_model(channels, {0: trigger_on(delay=new_delay)}, bench)
    start = bench.cycle
    runner = cocotb.start_soon(bench.run(steps))
    await bench.wait_for_cycle(start + strobes[2] + 30)
    write_start = bench.cycle - start
    await bench.write(cb.trigger_address(0, CARD) + 0x04, new_delay)
    window_end = bench.cycle - start + cb.SETTLE_CLOCKS
    samples = await runner
    levels = [sample.trig_pulse for sample in samples]
    expected_old = model_old.run(steps)
    expected_new = model_new.run(steps)
    cb.compare_samples(samples[:write_start], expected_old[:write_start], "before the write")
    before = [index for index, strobe in enumerate(strobes) if strobe + 4 < write_start]
    inside = [index for index, strobe in enumerate(strobes) if write_start <= strobe + 4 and strobe < window_end]
    after = [index for index, strobe in enumerate(strobes) if strobe >= window_end]
    assert before and inside and after, f"frames before {before}, inside {inside}, after {after}"
    first_after = strobes[after[0]] - 10
    cb.compare_samples(samples[first_after:], expected_new[first_after:], "after the window")
    rise = cb.rises(levels)

    def rises_of(index, horizon=None):
        if horizon is None:
            horizon = strobes[index + 1] - strobes[index] if index + 1 < len(strobes) else FRAME_GAP
        return [value - strobes[index] for value in rise if strobes[index] <= value < strobes[index] + horizon]

    for index in before:
        assert rises_of(index) == [FIRE_TO_RISE_BASE + old_delay], f"frame {index} before the write: {rises_of(index)}"
    for index in after:
        assert rises_of(index) == [FIRE_TO_RISE_BASE + new_delay], f"frame {index} after the window: {rises_of(index)}"
    for index in inside:
        dut._log.info(f"frame {index} inside the window rose {rises_of(index, FRAME_GAP)} steps after its strobe")
    bench.stop()


def random_channel_config(rng):
    mode = rng.randrange(4)
    rate_sel = (mode << 11) | (rng.getrandbits(2) << 9) | (rng.randrange(18) << 4) | rng.getrandbits(4)
    dest_mode = rng.choice((0, 1, 2, 2))
    dest_sel = (dest_mode << 16) | rng.getrandbits(16) | (rng.getrandbits(1) << 18)
    return {"enabled": int(rng.random() < 0.8), "rateSel": rate_sel, "destSel": dest_sel}


def random_trigger_config(rng):
    return {
        "enabled": int(rng.random() < 0.8),
        "channel": rng.randrange(CHANNELS),
        "polarity": rng.getrandbits(1),
        "delay": rng.randrange(0, 60),
        "width": 0 if rng.random() < 0.1 else rng.randrange(1, 8),
        "complEn": rng.getrandbits(1),
        "complAnd": rng.getrandbits(1),
    }


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_random(dut):
    """50 seeded random frames with constrained random configurations match the model.

    One run uses LCLS-II messages and one maps random LCLS-I streams. The
    bus values change on idle cycles too, to show that only a strobe moves
    them into the composite. rateSel(8:4) stays at most 17 and each trigger
    uses a channel below NCHANNELS_G, because the entities abort outside
    those limits.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"coretriggers_random seed {seed}")
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    noise = [
        cb.make_step(timing_model.random_message(rng), timing_model.random_stream(rng), strobe=0)
        for _ in range(NOISE_STEPS)
    ]
    for mode in (1, 0):
        channels = {index: random_channel_config(rng) for index in range(CHANNELS)}
        triggers = {index: random_trigger_config(rng) for index in range(TRIGGERS)}
        # One enabled path that selects a good share of the frames, so the run always has pulses to compare:
        # a fixed rate for LCLS-II messages, and acRates(0) in slots 1 to 5 for the LCLS-I mapping (which
        # never sets fixedRates).
        rate_sel = rng.randrange(evr_model.FIXED_RATE_COUNT) if mode == 1 else (1 << 11) | 0xF8
        channels[0] = {"enabled": 1, "rateSel": rate_sel, "destSel": ALL_DESTINATIONS}
        triggers[0] = {**random_trigger_config(rng), "enabled": 1, "channel": 0, "width": 2}
        frames = [
            cb.make_step(timing_model.random_message(rng), timing_model.random_stream(rng), mode=mode)
            for _ in range(RANDOM_FRAMES)
        ]
        gaps = [0] + [rng.randrange(6, 40) for _ in range(RANDOM_FRAMES - 1)]
        steps, _ = cb.build_schedule(frames, gaps, idle=[step._replace(mode=mode) for step in noise])
        samples, _ = await run_case(bench, channels, triggers, steps, f"random mode {mode} seed {seed}")
        changes = sum(len(cb.edges([sample.trig_pulse for sample in samples], bit)) for bit in range(TRIGGERS))
        dut._log.info(f"random mode {mode}: {changes} trigger edges over {len(steps)} steps")
        assert changes > 0, "the random run produced no trigger edge"
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def coretriggers_smoke(dut):
    """The reduced set for a shared clock: one end-to-end trigger and one read-back word.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = cb.Bench(dut, COMMON)
    await bench.start()
    channels, triggers, steps, strobes = one_trigger_scenario()
    samples, _ = await run_case(bench, channels, triggers, steps, "smoke")
    check_one_trigger(samples, strobes)
    word = await bench.read(cb.channel_address(0, CARD) + 0x04)
    assert word == cb.channel_rate_dest_word({**evr_model.CHANNEL_CONFIG_DEFAULTS, **channels[0]}), (
        f"channel 0 rate and destination word reads 0x{word:08X}"
    )
    bench.stop()


def run_coretriggers_simulation(parameters, test_filter):
    generics = hdl_parameters_from(parameters)
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2coretriggerswrapper",
        parameters=generics,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(generics, test_filter),
    )


def filter_for(parameters):
    """Return the cocotb filter for a case: the smoke set, the walk only, or everything else."""
    if parameters["TEST_SET"] == "smoke":
        return cocotb_test_filter(SMOKE_ENTRYPOINT)
    if parameters["TEST_SET"] == "walk":
        return cocotb_test_filter(WALK_ENTRYPOINT)
    skipped = [SMOKE_ENTRYPOINT]
    if int(parameters["NTRIGGERS_G"]) < 2:
        skipped.append(PAIRS_ENTRYPOINT)
    return cocotb_test_filter_excluding(*skipped)


def triggers_case(case_id, channels, triggers, pipe, *, common="false", card="false", test_set="full"):
    return parameter_case(
        case_id,
        NCHANNELS_G=str(channels),
        NTRIGGERS_G=str(triggers),
        TRIG_DEPTH_G="28",
        TRIG_PIPE_G=str(pipe),
        COMMON_CLK_G=common,
        EVR_CARD_G=card,
        TEST_SET=test_set,
    )


@pytest.mark.parametrize(
    "params",
    [
        triggers_case("defaults_async", 1, 1, 0),
        triggers_case("typical_async", 2, 4, 16),
        triggers_case("odd_async", 3, 3, 4),
        triggers_case("max_async", 16, 16, 1),
        triggers_case("typical_common", 2, 4, 16, common="true", test_set="smoke"),
        triggers_case("typical_card", 2, 4, 16, card="true", test_set="walk"),
    ],
)
def test_EvrV2CoreTriggers(params):
    run_coretriggers_simulation(params, filter_for(params))
