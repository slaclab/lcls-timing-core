#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Bring-up, frame driver, and path model shared by the two EVR V2 composite tests.

This is a helper module: it holds no cocotb entrypoints. It serves
EvrV2CoreTriggers and EvrV2CoreChannels, which both take AXI-Lite register
writes in one clock domain and a timing bus in another.

``Bench`` resets both domains, drives one timing-bus step per evrClk cycle,
and records the outputs of every step. ``ChannelPathModel`` is the evrClk
side of the shared path: the four-stage strobe pipeline, the EvrV2FromV1
copy, and one ``EventSelectModel`` per channel. The trigger side is added by
the test that needs it.

Step convention: step ``t`` applies its inputs 2 ns after one rising evrClk
edge and reads the outputs 2 ns after the next edge, so the output of step
``t`` is what ``evr_model`` returns for the step with the same inputs.
"""

from typing import List, NamedTuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster

from tests.common import evr_model, timing_model
from tests.common.regression_utils import sample_after_tpd, start_lockstep_clocks
from tests.lcls2_evr import register_walk as rw

AXIL_CLOCK_NS = 10
EVR_CLOCK_NS = 7
RESET_CLOCKS = 6
PROPAGATION_NS = 2
# Bounded wait, in evrClk cycles, for a register write to cross into the
# evrClk domain; the synchronizers make an exact count meaningless.
SETTLE_CLOCKS = 30
# Bounded wait, in axilClk cycles, for an event count to cross back.
COUNT_SETTLE_CLOCKS = 30

CHANNEL_BASE = 0x80000
TRIGGER_BASE_TIGHT = 0x81000
TRIGGER_BASE_CARD = 0xA0000
ALL_DESTINATIONS = 0b10 << 16


class Step(NamedTuple):
    """One evrClk cycle of timing-bus input, with the packed vectors the wrapper takes."""

    strobe: int
    mode: int
    message: dict
    stream: dict
    message_bits: int
    stream_bits: int


class Sample(NamedTuple):
    """The four outputs read after one step."""

    trig_pulse: int
    time_stamp: int
    bsa: int
    dmod: int


def blank_stream(**dbuff):
    """Return an LCLS-I stream with a zero event-code mask and the given data-buffer fields."""
    values = {name: 0 for name, _, _ in timing_model.DATABUFF_FIELDS}
    values.update(dbuff)
    return {"pulseId": 0, "eventCodes": 0, "dbuff": values}


def make_step(message, stream, *, strobe=1, mode=1):
    """Return a step carrying ``message`` and ``stream``, packed once."""
    return Step(
        strobe,
        mode,
        message,
        stream,
        timing_model.pack_message(message),
        timing_model.pack_stream(stream),
    )


def hold_step(step, *, mode=None):
    """Return the step with strobe low, keeping the same bus values."""
    return step._replace(strobe=0, mode=step.mode if mode is None else mode)


def frame_message(**fields):
    """Return a default LCLS-II message with the given fields replaced."""
    return {**timing_model.default_message(), **fields}


def build_schedule(frames, spacing, *, lead=2, tail=40, idle=None):
    """Return ``(steps, strobe_steps)`` for ``frames``.

    ``frames`` is a list of steps with strobe high. ``spacing`` is the number
    of steps from one strobe to the next, either one int or a list with one
    entry per frame (the first entry is unused: ``lead`` idle steps come
    first). ``idle`` is an optional list of steps with strobe low whose bus
    values are cycled through on the idle cycles, so that the inputs change
    when no strobe is present; without it the previous frame's bus is held.
    ``tail`` idle steps follow the last frame.
    """
    gaps = [spacing] * len(frames) if isinstance(spacing, int) else list(spacing)
    steps = []
    strobe_steps = []
    noise = 0

    def filler(frame):
        nonlocal noise
        if idle:
            noise += 1
            return idle[noise % len(idle)]
        return hold_step(frame)

    steps.extend(filler(frames[0]) for _ in range(lead))
    for index, (frame, gap) in enumerate(zip(frames, gaps)):
        if index:
            target = strobe_steps[-1] + gap
            while len(steps) < target:
                steps.append(filler(frames[index - 1]))
        strobe_steps.append(len(steps))
        steps.append(frame)
    steps.extend(filler(frames[-1]) for _ in range(tail))
    return steps, strobe_steps


def edges(levels, bit=0):
    """Return ``[(index, level), ...]`` for each change of bit ``bit`` along ``levels``."""
    result = []
    previous = None
    for index, value in enumerate(levels):
        level = (value >> bit) & 1
        if previous is not None and level != previous:
            result.append((index, level))
        previous = level
    return result


def rises(levels, bit=0):
    """Return the indices at which bit ``bit`` goes from 0 to 1."""
    return [index for index, level in edges(levels, bit) if level == 1]


def channel_address(index, card):
    """Return the AXI-Lite address of channel register group ``index``."""
    return CHANNEL_BASE + index * rw.group_size(card)


def trigger_address(index, card):
    """Return the AXI-Lite address of trigger register group ``index``."""
    return (TRIGGER_BASE_CARD if card else TRIGGER_BASE_TIGHT) + index * rw.group_size(card)


def trigger_control_word(config):
    """Return the word at offset 0 of a trigger group for the configuration dictionary."""
    return (
        (config["channel"] & 0xF)
        | (config["polarity"] << 16)
        | (config["complEn"] << 28)
        | (config["complAnd"] << 29)
        | (config["enabled"] << 31)
    )


def channel_rate_dest_word(config):
    """Return the word at offset 4 of a channel group (rateSel then destSel)."""
    return config["rateSel"] | (config["destSel"] << 13)


class ChannelPathModel:
    """The evrClk side shared by both composites, one clock per ``step``.

    ``step`` is called once per clock with the bus step and returns
    ``(arm, fire)`` as they stand just before the edge, which is what the
    trigger logic sees; the select registers and strobe pipeline then move on.
    """

    def __init__(self, nchannels):
        self.nchannels = nchannels
        self.selects = [evr_model.EventSelectModel() for _ in range(nchannels)]
        self.configs = [dict(evr_model.CHANNEL_CONFIG_DEFAULTS) for _ in range(nchannels)]
        self.strobe = [0, 0, 0, 0]
        self.message = timing_model.default_message()
        self.select_out = [0] * nchannels
        self.counts = [0] * nchannels

    def set_channel(self, index, **fields):
        self.configs[index] = {**evr_model.CHANNEL_CONFIG_DEFAULTS, **fields}

    def step(self, step):
        arm = sum(bit << index for index, bit in enumerate(self.select_out))
        fire = self.strobe[3]
        new_select = [
            select.step(config, self.strobe[1], self.message)[0]
            for select, config in zip(self.selects, self.configs)
        ]
        if step.strobe:
            self.message = dict(step.message) if step.mode else evr_model.from_v1(step.stream, self.message)
        self.strobe = [step.strobe] + self.strobe[:3]
        self.select_out = new_select
        for index, bit in enumerate(new_select):
            self.counts[index] += bit
        return arm, fire

    def bus_outputs(self, step):
        """Return the expected ``(time_stamp, bsa, dmod)`` after ``step``."""
        dbuff = step.stream["dbuff"]
        bsa = (
            (dbuff["edefAvgDn"] << 96)
            | (dbuff["edefMinor"] << 64)
            | (dbuff["edefMajor"] << 32)
            | dbuff["edefInit"]
        )
        return self.message["timeStamp"], bsa, dbuff["dmod"]


class Bench:
    """Clocks, resets, an AXI-Lite master and the evrClk step driver for one composite wrapper."""

    def __init__(self, dut, common_clk):
        self.dut = dut
        self.common_clk = common_clk
        self.master = None
        self.clock_tasks: List = []
        self.cycle = 0
        self.default_step = make_step(timing_model.default_message(), blank_stream())

    async def start(self):
        """Hold both domains in reset, start the clocks, and return after reset release."""
        dut = self.dut
        dut.axilRst.value = 1
        dut.evrRst.value = 1
        self._drive(self.default_step, strobe=0)
        self.master = AxiLiteMaster(
            AxiLiteBus.from_prefix(dut, "S_AXI"),
            dut.axilClk,
            dut.axilRst,
            reset_active_level=True,
        )
        await Timer(1, unit="ns")
        if self.common_clk:
            self.clock_tasks.append(start_lockstep_clocks(dut.axilClk, dut.evrClk, period_ns=AXIL_CLOCK_NS))
        else:
            self.clock_tasks.append(cocotb.start_soon(Clock(dut.axilClk, AXIL_CLOCK_NS, unit="ns").start(start_high=False)))
            self.clock_tasks.append(cocotb.start_soon(Clock(dut.evrClk, EVR_CLOCK_NS, unit="ns").start(start_high=False)))
        await self._release()

    def stop(self):
        for task in self.clock_tasks:
            task.cancel()
        self.clock_tasks = []

    async def _release(self):
        dut = self.dut
        for _ in range(RESET_CLOCKS):
            await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)
        dut.axilRst.value = 0
        dut.evrRst.value = 0
        for _ in range(RESET_CLOCKS):
            await sample_after_tpd(dut.axilClk, propagation_time=PROPAGATION_NS)

    async def reset(self):
        """Pulse both resets, then send one strobe with the default message so the message register is known."""
        dut = self.dut
        dut.axilRst.value = 1
        dut.evrRst.value = 1
        self._drive(self.default_step, strobe=0)
        await self._release()
        await self.run([self.default_step] + [hold_step(self.default_step)] * 8)

    def _drive(self, step, *, strobe=None):
        dut = self.dut
        dut.evrStrobe.value = step.strobe if strobe is None else strobe
        dut.evrModeSel.value = step.mode
        dut.evrMessage.value = step.message_bits
        dut.evrStream.value = step.stream_bits

    async def run(self, steps):
        """Apply ``steps`` one per evrClk cycle and return the list of ``Sample``."""
        dut = self.dut
        samples = []
        for step in steps:
            self._drive(step)
            await sample_after_tpd(dut.evrClk, propagation_time=PROPAGATION_NS)
            self.cycle += 1
            samples.append(
                Sample(
                    rw.flat_value(dut.trigPulse, "trigPulse"),
                    rw.flat_value(dut.timeStamp, "timeStamp"),
                    rw.flat_value(dut.bsa, "bsa"),
                    rw.flat_value(dut.dmod, "dmod"),
                )
            )
        return samples

    async def settle(self):
        """Wait the bounded number of evrClk cycles a register write needs to take effect."""
        return await self.run([hold_step(self.default_step)] * SETTLE_CLOCKS)

    async def wait_for_cycle(self, cycle):
        """Return once the driver has completed ``cycle`` steps; the driver runs as another task."""
        while self.cycle < cycle:
            await RisingEdge(self.dut.evrClk)

    async def write(self, address, value):
        await rw.write_word(self.master, address, value)

    async def read(self, address):
        return await rw.read_word(self.master, address)

    async def event_count(self, index, card):
        """Read the event count of channel ``index`` after a bounded wait for it to cross back."""
        for _ in range(COUNT_SETTLE_CLOCKS):
            await sample_after_tpd(self.dut.axilClk, propagation_time=PROPAGATION_NS)
        return await self.read(channel_address(index, card) + 0x08)

    async def program(self, card, channels, triggers=None):
        """Write channel and trigger configuration dictionaries, enable words last.

        ``channels`` and ``triggers`` map an index to a configuration
        dictionary; fields that are missing take the register defaults.
        """
        for index, fields in sorted(channels.items()):
            config = {**evr_model.CHANNEL_CONFIG_DEFAULTS, **fields}
            base = channel_address(index, card)
            await self.write(base + 0x04, channel_rate_dest_word(config))
            await self.write(base + 0x00, config["enabled"])
        for index, fields in sorted((triggers or {}).items()):
            config = {**evr_model.TRIGGER_CONFIG_DEFAULTS, **fields}
            base = trigger_address(index, card)
            await self.write(base + 0x04, config["delay"])
            await self.write(base + 0x08, config["width"])
            await self.write(base + 0x00, trigger_control_word(config))


def compare_samples(samples, expected, label):
    """Assert that each sample equals the expected ``Sample`` of the same step."""
    assert len(samples) == len(expected), f"{label}: {len(samples)} samples for {len(expected)} steps"
    for index, (got, want) in enumerate(zip(samples, expected)):
        if got != want:
            names = [name for name in Sample._fields if getattr(got, name) != getattr(want, name)]
            detail = ", ".join(
                f"{name} 0x{getattr(got, name):X} against model 0x{getattr(want, name):X}" for name in names
            )
            raise AssertionError(f"{label}: step {index} differs from the model: {detail}")
