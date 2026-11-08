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
        rxClk is 10 ns, txClk 12 ns and axilClk 8 ns, all unrelated. Every run
        starts with a short axilRst while the receive lines carry idle commas.
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
TX_PERIOD_NS = 12
AXIL_PERIOD_NS = 8
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


def lcls2_symbols(frames, slots=FRAME_SLOTS):
    """Idle lead-in, then each frame padded to ``slots`` symbols, then idle."""
    symbols = timing_model.idle_symbols(LEAD_CYCLES)
    for frame in frames:
        symbols += padded(frame, slots)
    return symbols + timing_model.idle_symbols(LEAD_CYCLES)


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


async def start_up(dut):
    """Drive resets and idle inputs, build the AXI-Lite master, then start the clocks (cocotbext-axi order)."""
    idle_data, idle_k = timing_model.IDLE_SYMBOL
    dut.axilRst.value = 1
    dut.rxData.value = idle_data
    dut.rxDataK.value = idle_k
    dut.rxDecErr.value = 0
    dut.rxDspErr.value = 0
    dut.rxStatusLocked.value = 1
    dut.rxStatusResetDone.value = 1
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
    master, clocks = await start_up(dut)
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


ENTRYPOINTS_BY_CASE = {
    "SELECT": ("timingrx_lcls2_path", "timingrx_register_smoke"),
    "LCLSI": ("timingrx_lcls1_path", "timingrx_register_smoke"),
    "LCLSII": ("timingrx_lcls2_path", "timingrx_register_smoke"),
    "LCLSIIPIC": ("timingrx_lcls2_path", "timingrx_register_smoke"),
    "LCLSIPIIC": ("timingrx_lcls1_path", "timingrx_register_smoke"),
    "SELECT-default0": ("timingrx_register_smoke",),
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
