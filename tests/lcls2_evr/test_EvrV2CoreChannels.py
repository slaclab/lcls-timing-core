#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2CoreChannels driven from AXI-Lite register writes to event-select outputs.

Test methodology:
    Sweep: NCHANNELS_G over 1, 4 and 16 with separate clocks (axilClk 10 ns,
        evrClk 7 ns), a reduced smoke set with COMMON_CLK_G true on 4
        channels, and a register walk with EVR_CARD_G true on 4 channels.
        Within a set: fixed-rate, AC, control-word and LCLS-I event-code
        selections, per-channel event counts, and seeded random
        configurations.
    Stimulus: a cocotbext-axi AxiLiteMaster writes the channel registers,
        group 0 at address 0 with a stride of 256 bytes (4096 when EVR_CARD_G
        is true); the evrClk side is driven one timing-bus step per cycle
        through the wrapper. Random configurations keep rateSel(8:4) at most
        17; no register is ever filled with random or all-ones values.
    Checks: after a bounded 30-cycle settle that follows the last register
        write, every step's trigPulse, timeStamp, bsa and dmod equal the
        channel model (the strobe pipeline, an EvrV2FromV1 copy and one
        EventSelectModel per channel), trigPulse(i) is high exactly one step
        at a fixed offset after the strobe of every frame that channel i
        selects and nowhere else, and the event count of channel i read
        back equals the number of frames it selected. The register walk
        compares read-back masks and reset values with the layout table at
        both register strides. Every output is asserted resolvable.
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

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2CoreChannelsWrapper.vhd"

CHANNELS = env_int("NCHANNELS_G", default=1)
COMMON = os.getenv("COMMON_CLK_G", "false") == "true"
CARD = os.getenv("EVR_CARD_G", "false") == "true"

# Steps from the strobe step to the sample that shows the select output: the
# strobe crosses two register stages before it gates the select, and the
# select output is registered (measured).
SELECT_FROM_STROBE = 2

FRAME_GAP = 12
RANDOM_FRAMES = 50
NOISE_STEPS = 6
FIXED_RATE_MODE = 0
AC_MODE = 1 << 11
CONTROL_WORD_MODE = 2 << 11
ALL_DESTINATIONS = cb.ALL_DESTINATIONS
CHANNEL_BASE = 0

# Event codes watched by channels 0 to 15 in the LCLS-I test.
EVENT_CODES = (1, 40, 140, 255, 2, 17, 33, 64, 100, 128, 200, 250, 254, 16, 15, 47)

SMOKE_ENTRYPOINT = "corechannels_smoke"
WALK_ENTRYPOINT = "corechannels_register_walk"

fixed_frame = cb.fixed_frame


class CoreChannelsModel:
    """Model of EvrV2CoreChannels on the evrClk side: trigPulse(i) is the select register of channel i."""

    def __init__(self, nchannels):
        self.path = cb.ChannelPathModel(nchannels)

    def set_channel(self, index, **fields):
        self.path.set_channel(index, **fields)

    def step(self, step):
        self.path.step(step)
        pulses = sum(bit << index for index, bit in enumerate(self.path.select_out))
        stamp, bsa, dmod = self.path.bus_outputs(step)
        return cb.Sample(pulses, stamp, bsa, dmod)

    def run(self, steps):
        return [self.step(step) for step in steps]


def make_bench(dut):
    return cb.Bench(dut, COMMON, channel_base=CHANNEL_BASE)


def make_model(channels):
    model = CoreChannelsModel(CHANNELS)
    for index, fields in channels.items():
        model.set_channel(index, **fields)
    return model


async def run_case(bench, channels, steps, label):
    """Reset, write the channel registers, settle, run ``steps`` and compare each step with the model.

    The model is warmed with the same number of idle cycles as the settle.
    Returns ``(samples, model)``.
    """
    await bench.reset()
    await bench.program(CARD, channels)
    await bench.settle()
    model = make_model(channels)
    idle = cb.hold_step(bench.default_step)
    for _ in range(cb.SETTLE_CLOCKS):
        model.step(idle)
    samples = await bench.run(steps)
    cb.compare_samples(samples, model.run(steps), label)
    return samples, model


def channel_kind(index):
    """Return 0 for a fixed-rate channel, 1 for an AC channel and 2 for a control-word channel."""
    return index % 3


def channel_setup(index):
    """Return ``(config, hit message fields, miss message fields)`` for channel ``index``.

    The selection fields of different channels never overlap: fixed-rate
    channels use distinct indices, AC channels use distinct time slots 1 to 5
    with rate index 1, and control-word channels use distinct words. The miss
    message leaves the channel's own condition clear and meets no other
    channel's condition.
    """
    n = index // 3
    kind = channel_kind(index)
    if kind == 0:
        rate_sel = FIXED_RATE_MODE | n
        hit = {"fixedRates": 1 << n}
        miss = {"fixedRates": 0}
    elif kind == 1:
        slot = 1 + n % 5
        rate_sel = AC_MODE | (1 << (slot + 2)) | 1
        hit = {"acTimeSlot": slot, "acRates": 0b000010}
        miss = {"acTimeSlot": slot, "acRates": 0}
    else:
        bit = (index * 5) % 16
        rate_sel = CONTROL_WORD_MODE | (n << 4) | bit
        words = [0] * evr_model.EVENT_SELECT_CONTROL_WORDS
        hit_words = list(words)
        hit_words[n] = 1 << bit
        hit = {"control": hit_words}
        miss = {"control": words}
    config = {"enabled": 1, "rateSel": rate_sel, "destSel": ALL_DESTINATIONS}
    return config, hit, miss


def all_channels():
    return {index: channel_setup(index)[0] for index in range(CHANNELS)}


def message_step(fields, mode=1):
    return cb.make_step(cb.frame_message(**fields), cb.blank_stream(), mode=mode)


def expected_levels(steps, strobes, hits):
    """Return the trigPulse trace with one single-step pulse per ``(frame, channel)`` in ``hits``."""
    want = [0] * len(steps)
    for frame, channel in hits:
        want[strobes[frame] + SELECT_FROM_STROBE] |= 1 << channel
    return want


def check_levels(samples, want, label):
    got = [sample.trig_pulse for sample in samples]
    if got != want:
        index = next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)
        raise AssertionError(f"{label}: trigPulse is 0x{got[index]:X} at step {index}, expected 0x{want[index]:X}")


def select_scenario():
    """Return ``(steps, strobes, hits)``: for each channel a hit frame and then a miss frame."""
    frames = []
    hits = []
    for index in range(CHANNELS):
        _, hit, miss = channel_setup(index)
        hits.append((len(frames), index))
        frames.append(message_step(hit))
        frames.append(message_step(miss))
    steps, strobes = cb.build_schedule(frames, FRAME_GAP)
    return steps, strobes, hits


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def corechannels_select_end_to_end(dut):
    """trigPulse(i) is the select output of channel i for fixed, AC and control-word selections.

    Each channel is written over AXI-Lite with one selection kind. A frame
    that meets only that channel's condition raises only that bit of
    trigPulse, one step wide at a fixed offset after the strobe, and the
    frame that leaves the condition clear raises nothing.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    steps, strobes, hits = select_scenario()
    samples, _ = await run_case(bench, all_channels(), steps, "select")
    check_levels(samples, expected_levels(steps, strobes, hits), "select")
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def corechannels_register_walk(dut):
    """The channel address map reads back the layout table at the active stride.

    The walk reads each word after reset, writes 0 and then each single bit,
    and compares the read-back mask and the reset value with the layout
    table. There is no configuration port, so only the read-back is checked.
    Words that exist only with the DMA generic read 0.

    Propagation sampling: the walk is paced by axilClk edges followed by a 2 ns wait.
    """
    bench = make_bench(dut)
    await bench.start()
    settle = rw.make_settle(dut)
    layout = rw.CHANREG_LAYOUT
    present = [word for word, fields in layout.items() if any(entry.condition is None for entry in fields)]
    absent = [word for word in layout if word not in present]
    for group in cb.groups_to_walk(CHANNELS):
        base = cb.channel_address(group, CARD, CHANNEL_BASE)
        for word in present:
            walk = await rw.walk_word(bench.master, base + word, lambda: 0, settle, {}, ignore=())
            reset, mask = cb.expected_word(layout, evr_model.CHANNEL_CONFIG_DEFAULTS, word)
            assert walk.reset_value == reset, (
                f"channel {group} word 0x{word:02X} reads 0x{walk.reset_value:08X} after reset, expected 0x{reset:08X}"
            )
            assert walk.readback_mask == mask, (
                f"channel {group} word 0x{word:02X} read-back mask 0x{walk.readback_mask:08X}, expected 0x{mask:08X}"
            )
        for word in absent:
            assert await bench.read(base + word) == 0, f"channel {group} word 0x{word:02X} should read 0"
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def corechannels_event_counts(dut):
    """The event count read back for each channel equals the number of frames it selected.

    Channel i sees i % 4 + 1 hit frames, each followed by a frame that
    misses, so the counts differ from channel to channel.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    frames = []
    hits = []
    wanted = [index % 4 + 1 for index in range(CHANNELS)]
    for round_index in range(4):
        for index in range(CHANNELS):
            if round_index < wanted[index]:
                _, hit, miss = channel_setup(index)
                hits.append((len(frames), index))
                frames.append(message_step(hit))
                frames.append(message_step(miss))
    steps, strobes = cb.build_schedule(frames, FRAME_GAP)
    samples, model = await run_case(bench, all_channels(), steps, "event counts")
    check_levels(samples, expected_levels(steps, strobes, hits), "event counts")
    for index in range(CHANNELS):
        count = await bench.event_count(index, CARD)
        assert count == wanted[index] == model.path.counts[index], (
            f"channel {index}: event count {count}, expected {wanted[index]} (model {model.path.counts[index]})"
        )
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def corechannels_lcls1_event_codes(dut):
    """With evrModeSel low, channel i selects LCLS-I event code EVENT_CODES[i] and no other.

    The codes include 1, 40, 140 and 255. A stream with only that code set
    selects only that channel, and a stream with no code set selects none.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    channels = {}
    frames = []
    hits = []
    for index in range(CHANNELS):
        code = EVENT_CODES[index]
        rate_sel = CONTROL_WORD_MODE | ((code // 16) << 4) | (code % 16)
        channels[index] = {"enabled": 1, "rateSel": rate_sel, "destSel": ALL_DESTINATIONS}
        hits.append((len(frames), index))
        for mask in (1 << code, 0):
            frames.append(cb.make_step(cb.frame_message(), {**cb.blank_stream(), "eventCodes": mask}, mode=0))
    steps, strobes = cb.build_schedule(frames, FRAME_GAP)
    samples, _ = await run_case(bench, channels, steps, "event codes")
    check_levels(samples, expected_levels(steps, strobes, hits), "event codes")
    bench.stop()


def random_channel_config(rng):
    mode = rng.randrange(4)
    rate_sel = (mode << 11) | (rng.getrandbits(2) << 9) | (rng.randrange(18) << 4) | rng.getrandbits(4)
    dest_mode = rng.choice((0, 1, 2, 2))
    dest_sel = (dest_mode << 16) | rng.getrandbits(16) | (rng.getrandbits(1) << 18)
    return {"enabled": int(rng.random() < 0.8), "rateSel": rate_sel, "destSel": dest_sel}


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def corechannels_random(dut):
    """50 seeded random frames with constrained random channel configurations match the model.

    One run uses LCLS-II messages and one maps random LCLS-I streams. The
    bus values change on idle cycles too, to show that only a strobe moves
    them into the composite. rateSel(8:4) stays at most 17 because the
    entity aborts above that.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"corechannels_random seed {seed}")
    bench = make_bench(dut)
    await bench.start()
    noise = [
        cb.make_step(timing_model.random_message(rng), timing_model.random_stream(rng), strobe=0)
        for _ in range(NOISE_STEPS)
    ]
    for mode in (1, 0):
        channels = {index: random_channel_config(rng) for index in range(CHANNELS)}
        # One enabled channel that selects a good share of the frames, so the run always has pulses to compare:
        # a fixed rate for LCLS-II messages, and acRates(0) in slots 1 to 5 for the LCLS-I mapping (which
        # never sets fixedRates).
        rate_sel = rng.randrange(evr_model.FIXED_RATE_COUNT) if mode == 1 else AC_MODE | 0xF8
        channels[0] = {"enabled": 1, "rateSel": rate_sel, "destSel": ALL_DESTINATIONS}
        frames = [
            cb.make_step(timing_model.random_message(rng), timing_model.random_stream(rng), mode=mode)
            for _ in range(RANDOM_FRAMES)
        ]
        gaps = [0] + [rng.randrange(6, 40) for _ in range(RANDOM_FRAMES - 1)]
        steps, _ = cb.build_schedule(frames, gaps, idle=[step._replace(mode=mode) for step in noise])
        samples, _ = await run_case(bench, channels, steps, f"random mode {mode} seed {seed}")
        selected = sum(bin(sample.trig_pulse).count("1") for sample in samples)
        dut._log.info(f"random mode {mode}: {selected} selections over {len(steps)} steps")
        assert selected > 0, "the random run selected no frame"
    bench.stop()


@cocotb.test(timeout_time=10, timeout_unit="ms")
async def corechannels_smoke(dut):
    """The reduced set for a shared clock: one end-to-end selection and one read-back word.

    Propagation sampling: outputs are sampled 2 ns after the rising evrClk edge.
    """
    bench = make_bench(dut)
    await bench.start()
    steps, strobes, hits = select_scenario()
    channels = all_channels()
    samples, _ = await run_case(bench, channels, steps, "smoke")
    check_levels(samples, expected_levels(steps, strobes, hits), "smoke")
    word = await bench.read(cb.channel_address(0, CARD, CHANNEL_BASE) + 0x04)
    assert word == cb.channel_rate_dest_word({**evr_model.CHANNEL_CONFIG_DEFAULTS, **channels[0]}), (
        f"channel 0 rate and destination word reads 0x{word:08X}"
    )
    bench.stop()


def run_corechannels_simulation(parameters, test_filter):
    generics = hdl_parameters_from(parameters)
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2corechannelswrapper",
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
    return cocotb_test_filter_excluding(SMOKE_ENTRYPOINT)


def channels_case(case_id, channels, *, common="false", card="false", test_set="full"):
    return parameter_case(
        case_id,
        NCHANNELS_G=str(channels),
        COMMON_CLK_G=common,
        EVR_CARD_G=card,
        TEST_SET=test_set,
    )


@pytest.mark.parametrize(
    "params",
    [
        channels_case("one_async", 1),
        channels_case("four_async", 4),
        channels_case("sixteen_async", 16),
        channels_case("four_common", 4, common="true", test_set="smoke"),
        channels_case("four_card", 4, card="true", test_set="walk"),
    ],
)
def test_EvrV2CoreChannels(params):
    run_corechannels_simulation(params, filter_for(params))
