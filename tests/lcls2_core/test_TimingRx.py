#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingRx test: protocol selection by generic, status counters and AXI-Lite registers.

TimingRx instantiates the LCLS-I receiver (TimingStreamRx) unless
CLKSEL_MODE_G is LCLSII or LCLSIIPIC, and the LCLS-II receiver
(TimingFrameRx) unless it is LCLSI or LCLSIPIIC. Register 0x20 picks the
receiver that feeds the status counters and the receiver that is held in
reset; in every mode other than SELECT the three selection bits are read only
and hold the value the mode implies.

Test methodology:
    Sweep: CLKSEL_MODE_G in SELECT, LCLSI, LCLSII, LCLSIIPIC and LCLSIPIIC,
        plus SELECT with DEFAULT_CLK_SEL_G 0 (the default is 1). One compiled
        simulation per case, each running only the entrypoints that are valid
        for that mode. The generics are handed to the cocotb module through
        the environment because the test filter replaces the automatic export.
    Stimulus: model-encoded LCLS-II frames (message_frame) or LCLS-I frames
        (encode_lcls1_frame) are presented one symbol per rxClk. Register
        accesses use a cocotbext-axi AxiLiteMaster on the S_AXI port.
        rxClk is 10 ns, txClk 6 ns and axilClk 12 ns, all unrelated. axilClk
        is the slow one on purpose: a one-cycle axilClk pulse (messageDelayRst)
        then always spans a rxClk edge, and rx error pulses are held for two
        rxClk cycles so the slow clock always sees them. Every run starts with
        a short axilRst while the receive lines carry idle commas.
    Checks: a protocol mode that has no receiver for a protocol leaves that
        protocol's outputs at their reset values (all-zero stream, the default
        message, no strobe or valid); the receiver a mode does have decodes
        model traffic into the model fields; the reset value of every
        selection bit follows the mode; an unmapped address answers DECERR.
        Every checked output is resolvable on every sampled cycle after reset
        release. Waits are bounded loops of clock cycles.
    Timing: strobes of the LCLS-II receiver follow the model frame spacing; the
        LCLS-I strobe is 14002 clocks after the event code marker symbol.
    Propagation sampling: every sample waits 2 ns past the rising edge so the
        registered outputs, which settle TPD_G = 1 ns after the edge, are
        stable.
"""

import os
from pathlib import Path
from typing import NamedTuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiResp
import pytest

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingRxWrapper.vhd"

RX_PERIOD_NS = 10
TX_PERIOD_NS = 6
AXIL_PERIOD_NS = 12
RESET_CYCLES = 5
LEAD_CYCLES = 50
FRAME_SLOTS = 200
LCLS1_SLOT = 14400
LCLS1_TAIL = 300
SETTLE_AXIL_CYCLES = 40

REG_CONTROL = 0x20
BIT_CLK_SEL = 4
BIT_MODE_SEL = 9
BIT_MODE_SEL_EN = 10
REG_COUNTER_RX_CLK = 0x10
REG_MESSAGE_DELAY = 0x24
REG_TX_CLK_COUNTER = 0x28
REG_VERSION = 0x30
REG_TS_EVENT_COUNTER = 0x40
BIT_CNT_RST = 0
BIT_LINK_UP = 1
BIT_POLARITY = 2
BIT_RESET = 3
BIT_RX_DOWN = 5
BIT_BUFFER_BY_RST = 6
BIT_PLL_RESET = 7
BIT_VERSION_ERROR = 8
BIT_STREAM_NO_DELAY = 24
DELAY_RESET_BIT = 1 << 31
# Positions in read_counters: registers 0x00 to 0x1C.
(
    COUNTER_SOF, COUNTER_EOF, COUNTER_FIDUCIAL, COUNTER_CRC,
    COUNTER_RX_CLK, COUNTER_RESET_DONE, COUNTER_DEC_ERR, COUNTER_DSP_ERR,
) = range(8)

STREAM_INIT = 0
MESSAGE_INIT = timing_model.pack_message(timing_model.default_message())
MESSAGE_MASK = (1 << timing_model.TIMING_MESSAGE_BITS) - 1

# (clkSel, modeSel, modeSelEn) the mode implies at reset; SELECT follows DEFAULT_CLK_SEL_G.
FIXED_MODE_BITS = {
    "LCLSI": (0, 0, 1),
    "LCLSII": (1, 1, 1),
    "LCLSIIPIC": (0, 1, 1),
    "LCLSIPIIC": (1, 0, 1),
}


def mode():
    return os.environ["CLKSEL_MODE_G"]


def default_clk_sel():
    return int(os.environ["DEFAULT_CLK_SEL_G"])


def reset_mode_bits():
    """(clkSel, modeSel, modeSelEn) after reset for the compiled mode."""
    if mode() == "SELECT":
        return (default_clk_sel(), default_clk_sel(), 0)
    return FIXED_MODE_BITS[mode()]


def has_lcls1_receiver():
    return mode() not in ("LCLSII", "LCLSIIPIC")


def has_lcls2_receiver():
    return mode() not in ("LCLSI", "LCLSIPIIC")


def active_protocol():
    """1 or 2: the receiver that is out of reset after reset release."""
    return 2 if reset_mode_bits()[1] else 1


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


def golden_message(pulse_id=0x0123456789ABCDEF):
    msg = timing_model.default_message()
    msg["pulseId"] = pulse_id
    msg["timeStamp"] = 0xFEDCBA9876543210
    msg["beamRequest"] = 0xA5A5A5A5
    msg["bsaDone"] = 0x0F0F0F0F0F0F0F0F
    msg["control"][17] = 0xBEEF
    return msg


def sent_messages(count):
    first = golden_message()
    return [golden_message(first["pulseId"] + index) for index in range(count)]


def padded(symbols, slots=FRAME_SLOTS):
    return symbols + timing_model.idle_symbols(slots - len(symbols))


def lcls2_symbols(frames, slots=FRAME_SLOTS, tail=LEAD_CYCLES):
    """Idle lead-in, then each frame padded to ``slots`` symbols, then ``tail`` idle symbols."""
    symbols = timing_model.idle_symbols(LEAD_CYCLES)
    for frame in frames:
        symbols += padded(frame, slots)
    return symbols + timing_model.idle_symbols(tail)


def lcls2_frame_start(index, slots=FRAME_SLOTS):
    """Symbol number of the alignment comma of frame ``index`` in lcls2_symbols."""
    return LEAD_CYCLES + slots * index


def sequential_databuff():
    """A data buffer whose byte k holds k + 1, so every byte position is distinct."""
    return timing_model.unpack_databuff(int.from_bytes(bytes(range(1, 53)), "little"))


def lcls1_symbols(streams):
    symbols = timing_model.lcls1_idle_symbols(LEAD_CYCLES)
    for stream in streams:
        frame = timing_model.encode_lcls1_frame(stream["pulseId"], stream["eventCodes"], stream["dbuff"])
        symbols += frame + timing_model.lcls1_idle_symbols(LCLS1_SLOT - len(frame), start_phase=1)
    return symbols + timing_model.lcls1_idle_symbols(LCLS1_TAIL)


def lcls1_marker(index):
    return LEAD_CYCLES + index * LCLS1_SLOT + timing_model.LCLS1_MARKER_INDEX


def lcls1_strobe_cycle(index):
    return lcls1_marker(index) + timing_model.LCLS1_FRAME_LEN + 2


class Traffic(NamedTuple):
    """What run_traffic saw: per-cycle flags and the wide outputs at each strobe."""

    trace: list
    messages: list
    streams: list


async def start_up(dut, restore=True):
    """Drive resets and idle inputs, build the AXI-Lite master, then start the clocks (cocotbext-axi order).

    rxStatusResetDone is held low for a few rxClk cycles after axilRst
    releases so frames left in either receiver by an earlier entrypoint (all
    entrypoints of a case share one simulation) cannot leak into this one.
    With ``restore`` the configuration registers, which axilRst does not
    touch, are written back to their reset values.
    """
    idle_data, idle_k = timing_model.IDLE_SYMBOL
    dut.axilRst.value = 1
    dut.rxData.value = idle_data
    dut.rxDataK.value = idle_k
    dut.rxDecErr.value = 0
    dut.rxDspErr.value = 0
    dut.rxStatusLocked.value = 1
    dut.rxStatusResetDone.value = 0
    dut.rxStatusBufferByDone.value = 0
    dut.rxStatusBufferByErr.value = 0
    master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "S_AXI"), dut.axilClk, dut.axilRst, reset_active_level=True)
    await Timer(1, unit="ns")
    clocks = [
        cocotb.start_soon(Clock(dut.rxClk, RX_PERIOD_NS, unit="ns").start(start_high=False)),
        cocotb.start_soon(Clock(dut.txClk, TX_PERIOD_NS, unit="ns").start(start_high=False)),
        cocotb.start_soon(Clock(dut.axilClk, AXIL_PERIOD_NS, unit="ns").start(start_high=False)),
    ]
    for _ in range(RESET_CYCLES):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
    dut.axilRst.value = 0
    await wait_axil(dut, SETTLE_AXIL_CYCLES)
    await wait_rx(dut, RESET_CYCLES)
    dut.rxStatusResetDone.value = 1
    if restore:
        clk_sel, mode_sel, _ = reset_mode_bits()
        select = mode() == "SELECT"
        await write_reg(master, REG_CONTROL, ((clk_sel << BIT_CLK_SEL) | (mode_sel << BIT_MODE_SEL)) if select else 0)
        await write_reg(master, REG_MESSAGE_DELAY, 0)
    await wait_axil(dut, SETTLE_AXIL_CYCLES)
    return master, clocks


async def wait_axil(dut, count):
    for _ in range(count):
        await sample_after_tpd(dut.axilClk, propagation_time=2)


async def wait_rx(dut, count):
    for _ in range(count):
        await sample_after_tpd(dut.rxClk, propagation_time=2)


async def run_traffic(dut, symbols, events=None, wide_period=1):
    """Present one symbol per rxClk and sample every cycle.

    ``events`` maps a symbol index to {port: value} applied together with that
    symbol. Wide outputs are checked resolvable every ``wide_period`` cycles
    and recorded on each strobe.
    """
    events = events or {}
    trace = []
    messages = []
    streams = []
    for cycle, (data, data_k) in enumerate(symbols):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
        sample = (
            resolved_int(dut.timingMessageStrobe),
            resolved_int(dut.timingMessageValid),
            resolved_int(dut.timingStreamStrobe),
            resolved_int(dut.timingStreamValid),
        )
        trace.append(sample)
        wide = cycle % wide_period == 0
        if wide:
            resolved_int(dut.timingMessage)
            resolved_int(dut.timingStreamUser)
            resolved_int(dut.timingStreamPrompt)
            resolved_int(dut.extensionValid)
        if sample[0]:
            messages.append((cycle, timing_model.unpack_message(resolved_int(dut.timingMessage))))
        if sample[2]:
            streams.append(
                (
                    cycle,
                    timing_model.unpack_stream(resolved_int(dut.timingStreamPrompt)),
                    timing_model.unpack_stream(resolved_int(dut.timingStreamUser)),
                )
            )
        dut.rxData.value = data
        dut.rxDataK.value = data_k
        for port, value in events.get(cycle, {}).items():
            getattr(dut, port).value = value
    return Traffic(trace, messages, streams)


async def write_reg(master, address, value):
    response = await master.write(address, value.to_bytes(4, "little"))
    assert response.resp == AxiResp.OKAY, f"write 0x{address:02X} response {response.resp!r}"


async def read_reg(master, address):
    response = await master.read(address, 4)
    assert response.resp == AxiResp.OKAY, f"read 0x{address:02X} response {response.resp!r}"
    return int.from_bytes(response.data, "little")


def bit_of(value, bit):
    return (value >> bit) & 1


def assert_idle_lcls1_outputs(dut, label):
    """LCLS-I outputs of a mode without that receiver: all-zero stream, no strobe, no valid."""
    assert resolved_int(dut.timingStreamStrobe) == 0, f"{label}: timingStreamStrobe"
    assert resolved_int(dut.timingStreamValid) == 0, f"{label}: timingStreamValid"
    assert resolved_int(dut.timingStreamPrompt) == STREAM_INIT, f"{label}: timingStreamPrompt"
    assert resolved_int(dut.timingStreamUser) == STREAM_INIT, f"{label}: timingStreamUser"


def assert_idle_lcls2_outputs(dut, label):
    """LCLS-II outputs of a mode without that receiver: the default message, no strobe, no valid."""
    assert resolved_int(dut.timingMessageStrobe) == 0, f"{label}: timingMessageStrobe"
    assert resolved_int(dut.timingMessageValid) == 0, f"{label}: timingMessageValid"
    assert resolved_int(dut.timingMessage) == MESSAGE_INIT, f"{label}: timingMessage is not the default message"
    assert resolved_int(dut.extensionValid) == 0, f"{label}: extensionValid"


@cocotb.test(timeout_time=1000, timeout_unit="us")
async def timingrx_lcls2_path(dut):
    """The LCLS-II receiver decodes model frames and, where the mode has no LCLS-I receiver, the LCLS-I outputs stay idle.

    Two model frames give one strobe carrying the first message (the strobe
    belongs to the start of the second frame). timingMessageValid is high from
    the cycle after the strobe. The stream outputs never strobe; in LCLSII and
    LCLSIIPIC they equal the all-zero stream the entity ties them to.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    msg_a, msg_b = sent_messages(2)
    master, clocks = await start_up(dut)
    traffic = await run_traffic(
        dut, lcls2_symbols([timing_model.message_frame(msg_a), timing_model.message_frame(msg_b)])
    )
    strobes = [cycle for cycle, _ in traffic.messages]
    assert len(strobes) == 1, f"expected one timingMessageStrobe, saw cycles {strobes}"
    assert traffic.messages[0][1] == msg_a, f"decoded message differs from frame A: {traffic.messages[0][1]}"
    assert traffic.trace[strobes[0] + 1][1] == 1, "timingMessageValid is low on the cycle after the strobe"
    assert not any(sample[2] for sample in traffic.trace), "timingStreamStrobe pulsed with LCLS-II traffic"
    if not has_lcls1_receiver():
        assert_idle_lcls1_outputs(dut, mode())
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=1000, timeout_unit="us")
async def timingrx_lcls1_path(dut):
    """The LCLS-I receiver decodes model frames and, where the mode has no LCLS-II receiver, the LCLS-II outputs stay idle.

    Three model LCLS-I frames give three strobes on the stream outputs,
    14002 clocks after each event code marker, with the prompt stream equal to
    the sent stream and the user stream lagging by two frames in the data
    buffer. timingMessageStrobe never pulses; in LCLSI and LCLSIPIIC
    timingMessage equals the default message the entity ties it to.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info("seed %d", seed)
    streams = [
        {"pulseId": 0x80000001, "eventCodes": 1 | (1 << 254), "dbuff": sequential_databuff()},
        timing_model.random_stream(rng),
        timing_model.random_stream(rng),
    ]
    master, clocks = await start_up(dut)
    traffic = await run_traffic(dut, lcls1_symbols(streams), wide_period=1000)
    assert [cycle for cycle, _, _ in traffic.streams] == [lcls1_strobe_cycle(i) for i in range(3)], (
        f"stream strobes on cycles {[cycle for cycle, _, _ in traffic.streams]}"
    )
    zero_buff = timing_model.unpack_databuff(0)
    for index, (_, prompt, user) in enumerate(traffic.streams):
        stream = streams[index]
        assert prompt["pulseId"] == stream["pulseId"], f"frame {index}: prompt pulse id"
        assert prompt["eventCodes"] == stream["eventCodes"] | 1, f"frame {index}: prompt event codes"
        assert prompt["dbuff"] == stream["dbuff"], f"frame {index}: prompt data buffer"
        assert user["pulseId"] == stream["pulseId"], f"frame {index}: user pulse id"
        older = streams[index - 2]["dbuff"] if index >= 2 else zero_buff
        lagged = dict(older)
        keep = (1 << 160) - 1
        lagged["dmod"] = (older["dmod"] & keep) | (stream["dbuff"]["dmod"] & ~keep)
        assert user["dbuff"] == lagged, f"frame {index}: user data buffer"
    assert not any(sample[0] for sample in traffic.trace), "timingMessageStrobe pulsed with LCLS-I traffic"
    if not has_lcls2_receiver():
        assert_idle_lcls2_outputs(dut, mode())
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=300, timeout_unit="us")
async def timingrx_register_smoke(dut):
    """Control register reset values follow the mode, and an unmapped address answers DECERR.

    clkSel (bit 4), modeSel (bit 9) and modeSelEn (bit 10) read the values the
    mode implies; register 0x20 reads OKAY, the version register 0x30 reads
    OKAY, and a read and a write at 0x80 answer DECERR. Every S_AXI output is
    resolvable after reset release.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, clocks = await start_up(dut, restore=False)
    for _ in range(10):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
        for name in (
            "S_AXI_AWREADY", "S_AXI_WREADY", "S_AXI_BRESP", "S_AXI_BVALID",
            "S_AXI_ARREADY", "S_AXI_RDATA", "S_AXI_RRESP", "S_AXI_RVALID",
            "timingClkSel", "timingModeSel", "rxControlReset", "rxControlInhibit",
            "rxControlPolarity", "rxControlBufferByRst", "rxControlPllReset",
        ):
            assert getattr(dut, name).value.is_resolvable, f"{name} is {getattr(dut, name).value} after reset release"
    control = await read_reg(master, REG_CONTROL)
    clk_sel, mode_sel, mode_sel_en = reset_mode_bits()
    assert (bit_of(control, BIT_CLK_SEL), bit_of(control, BIT_MODE_SEL), bit_of(control, BIT_MODE_SEL_EN)) == (
        clk_sel, mode_sel, mode_sel_en
    ), f"register 0x20 is 0x{control:08X} after reset in mode {mode()}"
    assert resolved_int(dut.timingClkSel) == clk_sel, "timingClkSel differs from the clkSel reset value"
    assert resolved_int(dut.timingModeSel) == mode_sel, "timingModeSel differs from the modeSel reset value"
    await read_reg(master, 0x30)
    response = await master.read(0x80, 4)
    assert response.resp == AxiResp.DECERR, f"unmapped read response {response.resp!r}"
    response = await master.write(0x80, (0).to_bytes(4, "little"))
    assert response.resp == AxiResp.DECERR, f"unmapped write response {response.resp!r}"
    for clock in clocks:
        clock.cancel()


async def update_control(master, set_bits=0, clear_bits=0):
    """Read-modify-write register 0x20 so a write never flips the selection bits by accident."""
    value = (await read_reg(master, REG_CONTROL) | set_bits) & ~clear_bits
    await write_reg(master, REG_CONTROL, value)
    return value


async def clear_counters(master):
    await update_control(master, set_bits=1 << BIT_CNT_RST)
    await update_control(master, clear_bits=1 << BIT_CNT_RST)
    await settle_counters(master)


async def settle_counters(master):
    """Let the synchronized counters catch up with the last input event."""
    for _ in range(SETTLE_AXIL_CYCLES):
        await read_reg(master, REG_CONTROL)


async def read_counters(master):
    """Registers 0x00 to 0x1C in order."""
    return [await read_reg(master, 4 * index) for index in range(8)]


def deltas(after, before):
    return [now - then for now, then in zip(after, before)]


def assert_cleared(counters, when):
    """Every counter except the free running rx clock counter (0x10) is zero."""
    others = [value for index, value in enumerate(counters) if index != COUNTER_RX_CLK]
    assert others == [0] * 7, f"counters 0x00 to 0x1C are {counters} {when}"


def good_frames(messages):
    return [timing_model.message_frame(msg) for msg in messages]


def pulse_events(cycle, port, value=1, width=1):
    """Events that hold ``port`` at ``value`` for ``width`` rxClk cycles starting with symbol ``cycle``."""
    return {cycle: {port: value}, cycle + width: {port: 0}}


def merge_events(*groups):
    merged = {}
    for group in groups:
        for cycle, ports in group.items():
            merged.setdefault(cycle, {}).update(ports)
    return merged


async def watch_flag(dut, name, seen):
    """Lifetime agent: append the axilClk cycle number of every cycle on which ``name`` is high."""
    cycle = 0
    while True:
        await sample_after_tpd(dut.axilClk, propagation_time=2)
        if resolved_int(getattr(dut, name)):
            seen.append(cycle)
        cycle += 1


@cocotb.test(timeout_time=1500, timeout_unit="us")
async def timingrx_status_counters(dut):
    """Registers 0x00 to 0x30 count and report the selected receiver's frames, errors, clock and link.

    Counters 0x00, 0x04 and 0x08 (sof, eof, fiducial) count once per frame,
    0x0C counts a frame whose CRC word is wrong (the frame is still
    delivered), 0x10 counts the rx clock once per 16 cycles, 0x14 counts
    rxStatusResetDone rising edges, 0x18 and 0x1C count rxDecErr and rxDspErr
    pulses (either bit of the 2-bit port), and register 0x20 bit 0 clears
    every one of them. Bit 1 follows rxStatusLocked; bit 5 latches a link drop
    and software cannot clear it while the link is down; bit 8 flags a
    version other than 1 until a version 1 frame is delivered, and 0x30 holds
    that frame's version. A decode or disparity error with resetDone high
    pulses rxControlReset (observed, intent unconfirmed).

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, clocks = await start_up(dut)
    msgs = sent_messages(4)

    await clear_counters(master)
    assert_cleared(await read_counters(master), "right after the clear")
    await run_traffic(dut, lcls2_symbols(good_frames(msgs)))
    await settle_counters(master)
    counters = await read_counters(master)
    assert counters[:4] == [4, 4, 4, 0], f"counters 0x00 to 0x0C after 4 good frames: {counters[:4]}"

    bad = timing_model.message_frame(msgs[2])
    bad[-2] = (bad[-2][0] ^ 0x0001, 0b00)
    await run_traffic(dut, lcls2_symbols(good_frames(msgs[:2]) + [bad]))
    await settle_counters(master)
    counters = await read_counters(master)
    assert counters[:4] == [7, 7, 7, 1], f"counters 0x00 to 0x0C after 3 more frames, one with a bad CRC: {counters[:4]}"

    await clear_counters(master)
    assert_cleared(await read_counters(master), "after the second clear")

    first = await read_reg(master, REG_COUNTER_RX_CLK)
    await wait_rx(dut, 1600)
    second = await read_reg(master, REG_COUNTER_RX_CLK)
    assert 98 <= second - first <= 104, f"rx clock counter advanced by {second - first} over 1600 rx cycles, expected 100"

    quiet = timing_model.idle_symbols(300)
    resets = []
    watcher = cocotb.start_soon(watch_flag(dut, "rxControlReset", resets))
    events = merge_events(
        pulse_events(20, "rxDecErr", 0b01, width=2),
        pulse_events(60, "rxDecErr", 0b10, width=2),
        pulse_events(100, "rxDspErr", 0b01, width=2),
        pulse_events(140, "rxDspErr", 0b10, width=2),
        {180: {"rxStatusResetDone": 0}, 190: {"rxStatusResetDone": 1}},
        {230: {"rxStatusResetDone": 0}, 240: {"rxStatusResetDone": 1}},
    )
    before = await read_counters(master)
    await run_traffic(dut, quiet, events)
    await settle_counters(master)
    watcher.cancel()
    step = deltas(await read_counters(master), before)
    assert step[COUNTER_SOF:COUNTER_CRC + 1] == [0, 0, 0, 0], f"frame counters moved without frames: {step[:4]}"
    assert step[COUNTER_DEC_ERR] == 2, f"rxDecErr counter 0x18 moved by {step[COUNTER_DEC_ERR]}, expected 2"
    assert step[COUNTER_DSP_ERR] == 2, f"rxDspErr counter 0x1C moved by {step[COUNTER_DSP_ERR]}, expected 2"
    assert step[COUNTER_RESET_DONE] == 2, f"resetDone counter 0x14 moved by {step[COUNTER_RESET_DONE]}, expected 2"
    assert resets, "rxControlReset never pulsed after a decode or disparity error"

    control = await read_reg(master, REG_CONTROL)
    assert bit_of(control, BIT_LINK_UP) == 1, f"bit 1 is low with rxStatusLocked high, register 0x{control:08X}"
    assert bit_of(control, BIT_RX_DOWN) == 0, f"bit 5 set with the link up, register 0x{control:08X}"
    dut.rxStatusLocked.value = 0
    await wait_axil(dut, SETTLE_AXIL_CYCLES)
    control = await read_reg(master, REG_CONTROL)
    assert bit_of(control, BIT_LINK_UP) == 0, "bit 1 does not follow rxStatusLocked going low"
    assert bit_of(control, BIT_RX_DOWN) == 1, "bit 5 did not latch the link drop"
    await update_control(master, clear_bits=1 << BIT_RX_DOWN)
    assert bit_of(await read_reg(master, REG_CONTROL), BIT_RX_DOWN) == 1, "software cleared bit 5 while the link is down"
    dut.rxStatusLocked.value = 1
    await wait_axil(dut, SETTLE_AXIL_CYCLES)
    control = await read_reg(master, REG_CONTROL)
    assert bit_of(control, BIT_LINK_UP) == 1, "bit 1 does not follow rxStatusLocked going high"
    assert bit_of(control, BIT_RX_DOWN) == 1, "bit 5 cleared by itself when the link returned"
    await update_control(master, clear_bits=1 << BIT_RX_DOWN)
    assert bit_of(await read_reg(master, REG_CONTROL), BIT_RX_DOWN) == 0, "software could not clear bit 5 with the link up"

    sent = [msgs[0], {**msgs[1], "version": 0x0002}, msgs[2]]
    await run_traffic(dut, lcls2_symbols(good_frames(sent)))
    await settle_counters(master)
    control = await read_reg(master, REG_CONTROL)
    assert bit_of(control, BIT_VERSION_ERROR) == 1, f"bit 8 not set after a version 2 frame, register 0x{control:08X}"
    assert await read_reg(master, REG_VERSION) == 2, "register 0x30 does not hold the version 2 of the delivered frame"
    await run_traffic(dut, lcls2_symbols(good_frames(msgs)))
    await settle_counters(master)
    control = await read_reg(master, REG_CONTROL)
    assert bit_of(control, BIT_VERSION_ERROR) == 0, f"bit 8 still set after version 1 frames, register 0x{control:08X}"
    assert await read_reg(master, REG_VERSION) == timing_model.TIMING_MESSAGE_VERSION, "register 0x30 is not version 1"
    for clock in clocks:
        clock.cancel()


async def flush_receivers(dut):
    """Pulse rxStatusResetDone low so a frame held by the active receiver cannot be delivered into the next run."""
    dut.rxStatusResetDone.value = 0
    await wait_rx(dut, RESET_CYCLES)
    dut.rxStatusResetDone.value = 1
    await wait_rx(dut, RESET_CYCLES)


async def frame_counters(dut, master, symbols):
    """Flush the receivers, clear the counters, run ``symbols``, and return (registers 0x00 to 0x0C, traffic)."""
    await flush_receivers(dut)
    await clear_counters(master)
    traffic = await run_traffic(dut, symbols, wide_period=1000)
    await settle_counters(master)
    return (await read_counters(master))[:4], traffic


async def assert_selection(dut, master, clk_sel, mode_sel, mode_sel_en, label):
    """Register 0x20 bits 4, 9 and 10 and the timingClkSel and timingModeSel outputs."""
    await wait_axil(dut, 10)
    control = await read_reg(master, REG_CONTROL)
    bits = (bit_of(control, BIT_CLK_SEL), bit_of(control, BIT_MODE_SEL), bit_of(control, BIT_MODE_SEL_EN))
    assert bits == (clk_sel, mode_sel, mode_sel_en), f"{label}: bits 4, 9, 10 are {bits}, register 0x{control:08X}"
    assert resolved_int(dut.timingClkSel) == clk_sel, f"{label}: timingClkSel"
    assert resolved_int(dut.timingModeSel) == mode_sel, f"{label}: timingModeSel"


@cocotb.test(timeout_time=1500, timeout_unit="us")
async def timingrx_select_switching(dut):
    """In SELECT mode clkSel and modeSel pick the receiver, independently once modeSelEn is set.

    The entrypoint begins at the reset value (equal to DEFAULT_CLK_SEL_G for
    clkSel and modeSel, modeSelEn clear) and then drives LCLS-II frames through
    each selection while watching the counters at 0x00 to 0x0C and the
    message strobes. With modeSelEn clear, modeSel follows clkSel. clkSel 1
    makes the LCLS-II receiver feed the counters (3 frames give 3, 3, 3, 0
    and 2 strobes); clkSel 0 holds the LCLS-II receiver in reset (no strobe)
    and the LCLS-I receiver, which sees the LCLS-II symbols, counts nothing;
    one LCLS-I frame then gives 1, 1, 1, 0 and one stream strobe. With
    modeSelEn set, modeSel 1 with clkSel 0 selects the LCLS-II receiver and
    modeSel 0 with clkSel 1 selects the LCLS-I receiver, so the counters
    follow modeSel and timingClkSel follows clkSel. The selection registers
    drive timingClkSel and timingModeSel with no synchronizer. axilRst does
    not touch the selection or polarity configuration but does clear cntRst.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, clocks = await start_up(dut)
    frames = good_frames(sent_messages(3))
    lcls1_stream = {"pulseId": 0x80000001, "eventCodes": 1 | (1 << 254), "dbuff": sequential_databuff()}
    lcls2_run = lcls2_symbols(frames)
    moved = [3, 3, 3, 0]
    still = [0, 0, 0, 0]

    await assert_selection(dut, master, default_clk_sel(), default_clk_sel(), 0, "reset value")

    await update_control(master, set_bits=1 << BIT_CLK_SEL)
    await assert_selection(dut, master, 1, 1, 0, "clkSel set")
    counters, traffic = await frame_counters(dut, master, lcls2_run)
    assert counters == moved, f"clkSel 1: counters {counters} after 3 LCLS-II frames"
    assert len(traffic.messages) == 2, f"clkSel 1: {len(traffic.messages)} message strobes"

    await update_control(master, clear_bits=1 << BIT_CLK_SEL)
    await assert_selection(dut, master, 0, 0, 0, "clkSel cleared")
    counters, traffic = await frame_counters(dut, master, lcls2_run)
    assert counters == still, f"clkSel 0: counters {counters} after 3 LCLS-II frames"
    assert not traffic.messages, f"clkSel 0: {len(traffic.messages)} message strobes from the held LCLS-II receiver"
    counters, traffic = await frame_counters(dut, master, lcls1_symbols([lcls1_stream]))
    assert counters == [1, 1, 1, 0], f"clkSel 0: counters {counters} after one LCLS-I frame"
    assert len(traffic.streams) == 1 and not traffic.messages, "clkSel 0: one stream strobe and no message strobe expected"

    await update_control(master, set_bits=1 << BIT_CLK_SEL)
    counters, traffic = await frame_counters(dut, master, lcls2_run)
    assert counters == moved and len(traffic.messages) == 2, f"clkSel set again: counters {counters}"

    await update_control(master, set_bits=(1 << BIT_MODE_SEL_EN) | (1 << BIT_MODE_SEL), clear_bits=1 << BIT_CLK_SEL)
    await assert_selection(dut, master, 0, 1, 1, "modeSelEn with modeSel 1, clkSel 0")
    counters, traffic = await frame_counters(dut, master, lcls2_run)
    assert counters == moved and len(traffic.messages) == 2, f"modeSel 1 with clkSel 0: counters {counters}"

    await update_control(master, set_bits=1 << BIT_CLK_SEL, clear_bits=1 << BIT_MODE_SEL)
    await assert_selection(dut, master, 1, 0, 1, "modeSelEn with modeSel 0, clkSel 1")
    counters, traffic = await frame_counters(dut, master, lcls2_run)
    assert counters == still and not traffic.messages, f"modeSel 0 with clkSel 1: counters {counters}"

    await update_control(master, set_bits=1 << BIT_POLARITY, clear_bits=(1 << BIT_CLK_SEL) | (1 << BIT_MODE_SEL_EN))
    await assert_selection(dut, master, 0, 0, 0, "modeSelEn cleared")
    await update_control(master, set_bits=1 << BIT_CNT_RST)
    dut.axilRst.value = 1
    await wait_axil(dut, 4)
    dut.axilRst.value = 0
    await wait_axil(dut, SETTLE_AXIL_CYCLES)
    control = await read_reg(master, REG_CONTROL)
    assert bit_of(control, BIT_CLK_SEL) == 0, f"axilRst changed clkSel, register 0x{control:08X}"
    assert bit_of(control, BIT_POLARITY) == 1, f"axilRst changed polarity, register 0x{control:08X}"
    assert bit_of(control, BIT_CNT_RST) == 0, f"axilRst did not clear cntRst, register 0x{control:08X}"
    for clock in clocks:
        clock.cancel()


async def strobe_offsets(dut, master, delay, symbols, discard_with=None):
    """Offsets from the start of frame B of every message strobe with ``delay`` programmed.

    ``discard_with``, if given, is written to the delay register 100 rxClk
    cycles after frame B starts, while frame A is still waiting in the delay
    line.
    """
    await write_reg(master, REG_MESSAGE_DELAY, delay)
    await wait_axil(dut, SETTLE_AXIL_CYCLES)
    await flush_receivers(dut)
    if discard_with is None:
        traffic = await run_traffic(dut, symbols)
    else:
        task = cocotb.start_soon(run_traffic(dut, symbols))
        await wait_rx(dut, lcls2_frame_start(1) + 100)
        await write_reg(master, REG_MESSAGE_DELAY, discard_with)
        traffic = await task
    return [(cycle - lcls2_frame_start(1), message) for cycle, message in traffic.messages]


@cocotb.test(timeout_time=1500, timeout_unit="us")
async def timingrx_message_delay(dut):
    """Register 0x24 delays the message strobe by exactly the programmed clocks, and a delay change discards a pending message.

    With frames A and B sent, the strobe for A (caused by the start of B)
    moves later by exactly the difference between two programmed delays, in
    both directions, so the fixed pipeline latency is not pinned. Observed,
    intent unconfirmed: a write that changes the delay, up or down, pulses
    messageDelayRst by itself and a message already waiting in the delay line
    is discarded (its strobe never comes), and writing bit 31 with an
    unchanged delay does the same; a write of the same delay without bit 31
    leaves the waiting message alone. Writing a decreased delay therefore does
    not stall the delay line the way TimingSerialDelay alone would.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, clocks = await start_up(dut)
    msg_a, msg_b = sent_messages(2)
    symbols = lcls2_symbols(good_frames([msg_a, msg_b]), tail=700)
    base = None
    for delay in (100, 300, 0, 300, 1000):
        strobes = await strobe_offsets(dut, master, delay, lcls2_symbols(good_frames([msg_a, msg_b]), tail=delay + 400))
        assert len(strobes) == 1, f"delay {delay}: {len(strobes)} strobes, offsets {[offset for offset, _ in strobes]}"
        offset, message = strobes[0]
        assert message == msg_a, f"delay {delay}: the strobe carries a message other than frame A"
        base = offset - delay if base is None else base
        assert offset - delay == base, f"delay {delay}: strobe offset {offset}, expected {delay + base} (fixed latency {base})"

    unchanged = await strobe_offsets(dut, master, 300, symbols, discard_with=300)
    assert [offset for offset, _ in unchanged] == [300 + base], f"unchanged delay write moved or dropped the strobe: {unchanged}"
    for label, value in (("lower delay", 200), ("higher delay", 400), ("reset bit", 300 | DELAY_RESET_BIT)):
        strobes = await strobe_offsets(dut, master, 300, symbols, discard_with=value)
        assert not strobes, f"{label}: a waiting message was still delivered at offsets {[o for o, _ in strobes]}"
    after = await strobe_offsets(dut, master, 300, symbols)
    assert [offset for offset, _ in after] == [300 + base], f"delivery did not resume after the discard: {after}"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=300, timeout_unit="us")
async def timingrx_control_bits(dut):
    """Register 0x20 control bits drive the rxControl outputs, and the read-only bits ignore writes.

    Each of bit 2 (polarity), 3 (reset), 6 (bufferByRst) and 7 (pllReset),
    written alone, reads back set and raises only its own rxControl output
    (bufferByRst after its rxClk synchronizer) and clears again; rxControlInhibit
    stays low; bit 24 (streamNoDelay) reads back. Writing the inverse of the
    read-only bits 1 (link up) and 8 (version error) changes neither. Outside
    SELECT mode, writing the inverse of bits 4, 9 and 10 changes neither the
    register nor timingClkSel and timingModeSel.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, clocks = await start_up(dut)
    outputs = {
        BIT_POLARITY: "rxControlPolarity",
        BIT_RESET: "rxControlReset",
        BIT_BUFFER_BY_RST: "rxControlBufferByRst",
        BIT_PLL_RESET: "rxControlPllReset",
    }
    for bit, name in outputs.items():
        await update_control(master, set_bits=1 << bit)
        await wait_axil(dut, 10)
        await wait_rx(dut, 10)
        control = await read_reg(master, REG_CONTROL)
        assert bit_of(control, bit) == 1, f"bit {bit} does not read back set, register 0x{control:08X}"
        for other_bit, other_name in outputs.items():
            expected = int(other_bit == bit)
            assert resolved_int(getattr(dut, other_name)) == expected, f"bit {bit} set: {other_name} is not {expected}"
        assert resolved_int(dut.rxControlInhibit) == 0, f"bit {bit} set: rxControlInhibit is high"
        await update_control(master, clear_bits=1 << bit)
        await wait_axil(dut, 10)
        await wait_rx(dut, 10)
        control = await read_reg(master, REG_CONTROL)
        assert bit_of(control, bit) == 0, f"bit {bit} does not read back clear, register 0x{control:08X}"
        assert all(resolved_int(getattr(dut, name)) == 0 for name in outputs.values()), f"bit {bit} cleared: an output is high"

    await update_control(master, set_bits=1 << BIT_STREAM_NO_DELAY)
    assert bit_of(await read_reg(master, REG_CONTROL), BIT_STREAM_NO_DELAY) == 1, "bit 24 does not read back set"
    await update_control(master, clear_bits=1 << BIT_STREAM_NO_DELAY)
    assert bit_of(await read_reg(master, REG_CONTROL), BIT_STREAM_NO_DELAY) == 0, "bit 24 does not read back clear"

    before = await read_reg(master, REG_CONTROL)
    await write_reg(master, REG_CONTROL, before ^ (1 << BIT_LINK_UP) ^ (1 << BIT_VERSION_ERROR))
    after = await read_reg(master, REG_CONTROL)
    assert after == before, f"writing the read-only bits 1 and 8 changed register 0x20 from 0x{before:08X} to 0x{after:08X}"

    if mode() != "SELECT":
        flip = (1 << BIT_CLK_SEL) | (1 << BIT_MODE_SEL) | (1 << BIT_MODE_SEL_EN)
        before = await read_reg(master, REG_CONTROL)
        await write_reg(master, REG_CONTROL, before ^ flip)
        await wait_axil(dut, 10)
        after = await read_reg(master, REG_CONTROL)
        assert after == before, f"writing bits 4, 9, 10 changed register 0x20 from 0x{before:08X} to 0x{after:08X}"
        clk_sel, mode_sel, _ = reset_mode_bits()
        assert resolved_int(dut.timingClkSel) == clk_sel, "timingClkSel changed after a write to read-only bit 4"
        assert resolved_int(dut.timingModeSel) == mode_sel, "timingModeSel changed after a write to read-only bit 9"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=1500, timeout_unit="us")
async def timingrx_reset_done_gating(dut):
    """With rxStatusResetDone low both receivers are held, so no strobe appears; raising it restores decoding.

    Frames of the receiver the mode has out of reset are presented while
    rxStatusResetDone is low: no message or stream strobe comes from the
    frames sent during the hold, even though they are valid. Raising the input
    shortly before a later frame restores decoding: exactly that frame is
    delivered, with its own content, and nothing earlier.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, clocks = await start_up(dut)
    dut.rxStatusResetDone.value = 0
    await wait_rx(dut, 10)
    if active_protocol() == 2:
        msgs = sent_messages(5)
        release = lcls2_frame_start(3) - 20
        traffic = await run_traffic(
            dut, lcls2_symbols(good_frames(msgs)), {release: {"rxStatusResetDone": 1}}
        )
        assert not any(sample[2] for sample in traffic.trace), "stream strobe with LCLS-II traffic"
        strobes = [cycle for cycle, _ in traffic.messages]
        assert len(strobes) == 1 and lcls2_frame_start(4) < strobes[0] < lcls2_frame_start(4) + 20, (
            f"message strobes on cycles {strobes}, expected one just after the start of the fifth frame"
        )
        assert traffic.messages[0][1] == msgs[3], "the delivered message is not the first frame sent after the release"
    else:
        rng, seed = timing_model.make_rng()
        dut._log.info("seed %d", seed)
        streams = [timing_model.random_stream(rng), timing_model.random_stream(rng)]
        release = LEAD_CYCLES + LCLS1_SLOT - 100
        traffic = await run_traffic(dut, lcls1_symbols(streams), {release: {"rxStatusResetDone": 1}}, wide_period=1000)
        assert not any(sample[0] for sample in traffic.trace), "message strobe with LCLS-I traffic"
        assert [cycle for cycle, _, _ in traffic.streams] == [lcls1_strobe_cycle(1)], (
            f"stream strobes on cycles {[cycle for cycle, _, _ in traffic.streams]}"
        )
        assert traffic.streams[0][1]["pulseId"] == streams[1]["pulseId"], "the delivered stream is not the second frame"
    for clock in clocks:
        clock.cancel()


@cocotb.test(timeout_time=300, timeout_unit="us")
async def timingrx_tx_and_ts_counters(dut):
    """The txClk counter at 0x28 runs while txClk runs and holds when it stops; 0x40 reads OKAY.

    Register 0x28 counts one per 16 txClk cycles; two reads separated by 1600
    txClk cycles differ by 100 within the read latency. After txClk stops the
    counter holds its value across 200 axilClk cycles. The event counter at
    0x40 reads OKAY with a resolvable value.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, clocks = await start_up(dut)
    await clear_counters(master)
    first = await read_reg(master, REG_TX_CLK_COUNTER)
    for _ in range(1600):
        await sample_after_tpd(dut.txClk, propagation_time=2)
    second = await read_reg(master, REG_TX_CLK_COUNTER)
    assert 98 <= second - first <= 106, f"txClk counter advanced by {second - first} over 1600 txClk cycles, expected 100"
    clocks[1].cancel()
    await wait_axil(dut, SETTLE_AXIL_CYCLES)
    held = await read_reg(master, REG_TX_CLK_COUNTER)
    await wait_axil(dut, 200)
    assert await read_reg(master, REG_TX_CLK_COUNTER) == held, "txClk counter changed after txClk stopped"
    await read_reg(master, REG_TS_EVENT_COUNTER)
    for clock in clocks:
        clock.cancel()


COMMON_ENTRYPOINTS = (
    "timingrx_register_smoke",
    "timingrx_control_bits",
    "timingrx_reset_done_gating",
    "timingrx_tx_and_ts_counters",
)
LCLS2_ENTRYPOINTS = (
    "timingrx_lcls2_path",
    "timingrx_status_counters",
    "timingrx_message_delay",
)
ENTRYPOINTS_BY_CASE = {
    "SELECT": COMMON_ENTRYPOINTS + LCLS2_ENTRYPOINTS + ("timingrx_select_switching",),
    "LCLSI": COMMON_ENTRYPOINTS + ("timingrx_lcls1_path",),
    "LCLSII": COMMON_ENTRYPOINTS + LCLS2_ENTRYPOINTS,
    "LCLSIIPIC": COMMON_ENTRYPOINTS + LCLS2_ENTRYPOINTS,
    "LCLSIPIIC": COMMON_ENTRYPOINTS + ("timingrx_lcls1_path",),
    "SELECT-default0": ("timingrx_register_smoke", "timingrx_select_switching"),
}


@pytest.mark.parametrize(
    "case, clksel_mode, default_clk_sel_value",
    [
        pytest.param("SELECT", "SELECT", 1, id="SELECT"),
        pytest.param("LCLSI", "LCLSI", 1, id="LCLSI"),
        pytest.param("LCLSII", "LCLSII", 1, id="LCLSII"),
        pytest.param("LCLSIIPIC", "LCLSIIPIC", 1, id="LCLSIIPIC"),
        pytest.param("LCLSIPIIC", "LCLSIPIIC", 1, id="LCLSIPIIC"),
        pytest.param("SELECT-default0", "SELECT", 0, id="SELECT-default0"),
    ],
)
def test_TimingRx(case, clksel_mode, default_clk_sel_value):
    generics = {"CLKSEL_MODE_G": clksel_mode, "DEFAULT_CLK_SEL_G": default_clk_sel_value}
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingrxwrapper",
        parameters=generics,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(generics, cocotb_test_filter(*ENTRYPOINTS_BY_CASE[case])),
    )
