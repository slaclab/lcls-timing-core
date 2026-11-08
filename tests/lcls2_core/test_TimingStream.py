#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""LCLS-I stream pair test: TimingStreamTx and TimingStreamRx against the model.

Test methodology:
    Sweep: the transmitter runs the named stream (pulse id 0x80000001, event
        codes 0, 1, 254 and 255, data-buffer bytes 1 to 52) in both phases of
        its 2-clock idle pattern, then 5 seeded random streams alternating
        the phase. The receiver runs four model frames (pulse id bits 31 and
        0, event codes 0, 254 and 255, all 52 data-buffer bytes) and, in a
        second simulation, seven frame slots where rxDecErr="01",
        rxDspErr="01" and rxDspErr="10" are each injected for one cycle
        after the event-code marker.
    Stimulus: the transmitter gets one fiducial pulse per frame and 700
        symbols are captured. The receiver is driven one model symbol per
        rxClk, each frame padded with idle symbols to a 14400-symbol slot so
        the 14000-clock event window of one frame ends before the next
        frame starts.
    Checks: the captured transmitter symbols equal encode_lcls1_frame of the
        same stream with event-code bit 255 cleared, symbol for symbol, and
        the idle that follows equals lcls1_idle_symbols; only the first
        symbol differs between the two idle phases (0x1C00/10 or 0x1CBC/11);
        event code 255 never reaches the wire (observed, intent unconfirmed).
        The receiver strobes no earlier than 14000 clocks after the 0x7D
        marker; the prompt output carries the newest pulse id, event codes
        and data buffer; the user data buffer lags two frames except
        dmod(191 downto 160); timingMessageNoDely selects the newest data
        buffer; staData start-of-frame and end-of-frame pulse once per frame;
        an error cycle after the marker clears the receiver so that frame
        gives no strobe, timingMessageValid and the data-buffer history are
        cleared, and the next clean frame decodes again. Every checked
        output is resolvable on every sampled cycle after reset release.
    Timing: 10 ns clk and rxClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        are stable.
"""

from pathlib import Path
from typing import NamedTuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

TX_WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingStreamTxWrapper.vhd"
RX_WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingStreamRxWrapper.vhd"

CODE_255 = 1 << 255
FRAME_SYMBOLS = 684
CAPTURE_SYMBOLS = 700
START_SYMBOL_OTHER_PHASE = (0x1CBC, 0b11)
IDLE_COMMA = timing_model.LCLS1_COMMA_SYMBOL
IDLE_ZERO = timing_model.LCLS1_UNSET_SYMBOL


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


def sequential_databuff():
    """A data buffer whose byte k holds k + 1, so every byte position is distinct."""
    return timing_model.unpack_databuff(int.from_bytes(bytes(range(1, 53)), "little"))


def named_stream():
    return {
        "pulseId": 0x80000001,
        "eventCodes": 1 | (1 << 1) | (1 << 254) | CODE_255,
        "dbuff": sequential_databuff(),
    }


def first_difference(actual, expected):
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            return f"first difference at symbol {index}: got 0x{got[0]:04X}/{got[1]:02b}, expected 0x{want[0]:04X}/{want[1]:02b}"
    return f"lengths differ: {len(actual)} against {len(expected)}"


# Transmitter ---------------------------------------------------------------


async def start_transmitter(dut):
    """Hold reset for 3 clocks, release it and check the idle pattern."""
    dut.rst.value = 1
    dut.fiducial.value = 0
    dut.dataBuff.value = 0
    dut.pulseId.value = 0
    dut.eventCodes.value = 0
    clock_task = cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0

    idle = []
    for _ in range(12):
        await sample_after_tpd(dut.clk, propagation_time=2)
        idle.append((resolved_int(dut.data), resolved_int(dut.dataK)))
    settled = idle[2:]
    assert all(symbol in (IDLE_COMMA, IDLE_ZERO) for symbol in settled), f"idle is not the comma/zero pattern: {settled}"
    assert all(a != b for a, b in zip(settled, settled[1:])), f"idle symbols do not alternate: {settled}"
    return clock_task


async def send_frame(dut, stream, extra_idle=0):
    """Pulse fiducial for one clock and capture CAPTURE_SYMBOLS symbols from the start symbol."""
    for _ in range(extra_idle):
        await sample_after_tpd(dut.clk, propagation_time=2)
    dut.dataBuff.value = timing_model.pack_databuff(stream["dbuff"])
    dut.pulseId.value = stream["pulseId"]
    dut.eventCodes.value = stream["eventCodes"]
    dut.fiducial.value = 1
    symbols = []
    for count in range(CAPTURE_SYMBOLS):
        await sample_after_tpd(dut.clk, propagation_time=2)
        if count == 0:
            dut.fiducial.value = 0
        symbols.append((resolved_int(dut.data), resolved_int(dut.dataK)))
    return symbols


def expected_transmitter_symbols(stream):
    """The model frame with code 255 cleared, then the idle that continues its alternation."""
    frame = timing_model.encode_lcls1_frame(stream["pulseId"], stream["eventCodes"] & ~CODE_255, stream["dbuff"])
    assert len(frame) == FRAME_SYMBOLS
    return frame + timing_model.lcls1_idle_symbols(CAPTURE_SYMBOLS - FRAME_SYMBOLS, start_phase=1)


@cocotb.test(timeout_time=400, timeout_unit="us")
async def streamtx_matches_model(dut):
    """The transmitter output equals the model frame in both idle phases.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    cases = [(named_stream(), 0), (named_stream(), 1)]
    cases += [(timing_model.random_stream(rng), index % 2) for index in range(5)]

    clock_task = await start_transmitter(dut)
    first_symbols = set()
    for index, (stream, extra_idle) in enumerate(cases):
        symbols = await send_frame(dut, stream, extra_idle)
        expected = expected_transmitter_symbols(stream)
        assert symbols[1:] == expected[1:], f"case {index}: {first_difference(symbols[1:], expected[1:])}"
        assert symbols[0] in (expected[0], START_SYMBOL_OTHER_PHASE), f"case {index}: start symbol {symbols[0]}"
        first_symbols.add(symbols[0])

    assert first_symbols == {timing_model.LCLS1_START_SYMBOL, START_SYMBOL_OTHER_PHASE}, (
        f"both idle phases were expected to be exercised, saw {first_symbols}"
    )
    clock_task.cancel()


@cocotb.test(timeout_time=300, timeout_unit="us")
async def streamtx_never_sends_code_255(dut):
    """Event code 255 never appears in the event block of a transmitted frame.

    The state machine leaves the event block when its counter reaches 255,
    before slot 255 is examined. This is observed, intent unconfirmed.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    only_255 = {**timing_model.random_stream(rng), "eventCodes": CODE_255}
    with_254 = {**timing_model.random_stream(rng), "eventCodes": CODE_255 | (1 << 254)}

    def low_lane_codes(symbols):
        marker = symbols.index(timing_model.LCLS1_MARKER_SYMBOL)
        return [data & 0xFF for data, data_k in symbols[marker + 1:] if not data_k & 1]

    clock_task = await start_transmitter(dut)
    codes = low_lane_codes(await send_frame(dut, only_255))
    assert 0xFF not in codes, "code 255 reached the wire with only code 255 requested"
    assert set(codes) == {0x00}, f"unexpected event-block symbols {sorted(set(codes))}"

    codes = low_lane_codes(await send_frame(dut, with_254))
    assert 0xFE in codes, "code 254 did not reach the wire"
    assert 0xFF not in codes, "code 255 reached the wire next to code 254"
    clock_task.cancel()


# Receiver ------------------------------------------------------------------

SLOT = 14400
LEAD_IN = 50
TAIL = 300
MARKER_INDEX = timing_model.LCLS1_MARKER_INDEX
END_INDEX = timing_model.LCLS1_END_INDEX
INJECT_AT = 5000
ZERO_DBUFF = timing_model.unpack_databuff(0)
DMOD_TOP_SHIFT = 160


class Slot(NamedTuple):
    """One frame slot: the stream sent and an optional (port, value) error cycle."""

    stream: dict
    error: tuple | None = None


class Strobe(NamedTuple):
    cycle: int
    prompt: dict
    user: dict
    version: int


def slot_symbols(stream):
    frame = timing_model.encode_lcls1_frame(stream["pulseId"], stream["eventCodes"], stream["dbuff"])
    return frame + timing_model.lcls1_idle_symbols(SLOT - len(frame), start_phase=1)


def build_symbols(slots):
    symbols = timing_model.lcls1_idle_symbols(LEAD_IN)
    for slot in slots:
        symbols += slot_symbols(slot.stream)
    return symbols + timing_model.lcls1_idle_symbols(TAIL)


def slot_start(slot_index):
    return LEAD_IN + slot_index * SLOT


async def start_receiver(dut):
    """Hold reset with idle commas on the flat ports, then release it."""
    idle_data, idle_k = IDLE_COMMA
    dut.rxRst.value = 1
    dut.rxData.value = idle_data
    dut.rxDataK.value = idle_k
    dut.rxDecErr.value = 0
    dut.rxDspErr.value = 0
    dut.timingMessageNoDely.value = 0
    clock_task = cocotb.start_soon(Clock(dut.rxClk, 10, unit="ns").start(start_high=False))
    for _ in range(3):
        await RisingEdge(dut.rxClk)
    dut.rxRst.value = 0
    return clock_task


async def drive_symbols(dut, symbols, errors):
    """Present one symbol per rxClk; ``errors`` maps a symbol index to a (port, value) pulse of one clock."""
    active = None
    for index, (data, data_k) in enumerate(symbols):
        await RisingEdge(dut.rxClk)
        dut.rxData.value = data
        dut.rxDataK.value = data_k
        if active is not None:
            getattr(dut, active).value = 0
            active = None
        if index in errors:
            port, value = errors[index]
            getattr(dut, port).value = value
            active = port


async def watch_receiver(dut, cycles, no_delay_after=None):
    """Sample every cycle; return (trace, strobes). Wide outputs are read on each strobe."""
    trace = []
    strobes = []
    for cycle in range(cycles):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
        strobe = resolved_int(dut.timingMessageStrobe)
        trace.append((strobe, resolved_int(dut.timingMessageValid), resolved_int(dut.staData)))
        version = resolved_int(dut.rxVersion)
        if cycle % 1000 == 0:
            resolved_int(dut.timingMessageUser)
            resolved_int(dut.timingMessagePrompt)
        if strobe:
            strobes.append(
                Strobe(
                    cycle,
                    timing_model.unpack_stream(resolved_int(dut.timingMessagePrompt)),
                    timing_model.unpack_stream(resolved_int(dut.timingMessageUser)),
                    version,
                )
            )
            if no_delay_after is not None and len(strobes) == no_delay_after:
                dut.timingMessageNoDely.value = 1
    return trace, strobes


def lagged_dbuff(older, newest):
    """The user data buffer: the older frame with dmod(191 downto 160) taken from the newest."""
    keep = (1 << DMOD_TOP_SHIFT) - 1
    result = dict(older)
    result["dmod"] = (older["dmod"] & keep) | (newest["dmod"] & ~keep)
    return result


def pulse_cycles(trace, bit):
    return [cycle for cycle, (_, _, sta) in enumerate(trace) if (sta >> bit) & 1]


def expected_strobe_cycle(slot_index):
    return slot_start(slot_index) + MARKER_INDEX + timing_model.LCLS1_FRAME_LEN + 2


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def streamrx_decodes_model_frames(dut):
    """The receiver decodes model frames: prompt, two-frame lag, no-delay select, timing and status.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    streams = [
        {"pulseId": 0x80000001, "eventCodes": 1 | (1 << 254), "dbuff": sequential_databuff()},
        timing_model.random_stream(rng),
        {**timing_model.random_stream(rng), "pulseId": 0x7FFFFFFE, "eventCodes": CODE_255 | (1 << 100)},
        timing_model.random_stream(rng),
    ]
    slots = [Slot(stream) for stream in streams]
    symbols = build_symbols(slots)

    clock_task = await start_receiver(dut)
    driver = cocotb.start_soon(drive_symbols(dut, symbols, {}))
    trace, strobes = await watch_receiver(dut, len(symbols) + 10, no_delay_after=3)
    driver.cancel()
    clock_task.cancel()

    assert len(strobes) == len(streams), f"expected {len(streams)} strobes, saw {[s.cycle for s in strobes]}"
    for index, (stream, strobe) in enumerate(zip(streams, strobes)):
        marker = slot_start(index) + MARKER_INDEX
        assert strobe.cycle - marker >= timing_model.LCLS1_FRAME_LEN, (
            f"frame {index}: strobe {strobe.cycle - marker} clocks after the marker, before {timing_model.LCLS1_FRAME_LEN}"
        )
        assert strobe.cycle == expected_strobe_cycle(index), (
            f"frame {index}: strobe on cycle {strobe.cycle}, expected {expected_strobe_cycle(index)}"
        )
        # An unset slot and the data-buffer symbols read as event code 0.
        want_codes = stream["eventCodes"] | 1
        assert strobe.prompt["pulseId"] == stream["pulseId"], f"frame {index}: prompt pulse id"
        assert strobe.prompt["eventCodes"] == want_codes, f"frame {index}: prompt event codes"
        assert strobe.prompt["dbuff"] == stream["dbuff"], f"frame {index}: prompt data buffer"
        assert strobe.user["pulseId"] == stream["pulseId"], f"frame {index}: user pulse id"
        assert strobe.user["eventCodes"] == want_codes, f"frame {index}: user event codes"
        if index < 3:
            older = streams[index - 2]["dbuff"] if index >= 2 else ZERO_DBUFF
            expected_user = lagged_dbuff(older, stream["dbuff"])
        else:
            expected_user = stream["dbuff"]
        assert strobe.user["dbuff"] == expected_user, f"frame {index}: user data buffer"
        assert strobe.version == expected_user["version"], f"frame {index}: rxVersion"

    strobe_cycles = [cycle for cycle, (strobe, _, _) in enumerate(trace) if strobe]
    assert strobe_cycles == [s.cycle for s in strobes]
    assert pulse_cycles(trace, 2) == strobe_cycles, "staData strobe bit differs from timingMessageStrobe"
    assert pulse_cycles(trace, 0) == [slot_start(index) + 1 for index in range(len(streams))], "start-of-frame pulses"
    assert pulse_cycles(trace, 1) == [slot_start(index) + END_INDEX + 1 for index in range(len(streams))], (
        "end-of-frame pulses"
    )
    assert all(valid == 0 for _, valid, _ in trace[:strobe_cycles[0] + 1]), "valid asserted before the first strobe"
    assert all(valid == 1 for _, valid, _ in trace[strobe_cycles[0] + 1:]), "valid dropped after the first strobe"


@cocotb.test(timeout_time=3, timeout_unit="ms")
async def streamrx_error_resets_frame(dut):
    """A decode or disparity error after the marker clears the receiver and costs that frame its strobe.

    The dspErr comparison in the receiver is a 2-bit port against an 8-bit
    literal, so both dspErr bits are exercised on their own.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    errors = (("rxDecErr", 0b01), ("rxDspErr", 0b01), ("rxDspErr", 0b10))
    slots = []
    for error in errors:
        slots.append(Slot(timing_model.random_stream(rng)))
        slots.append(Slot(timing_model.random_stream(rng), error))
    slots.append(Slot(timing_model.random_stream(rng)))
    symbols = build_symbols(slots)
    injections = {slot_start(index) + INJECT_AT: slot.error for index, slot in enumerate(slots) if slot.error}

    clock_task = await start_receiver(dut)
    driver = cocotb.start_soon(drive_symbols(dut, symbols, injections))
    trace, strobes = await watch_receiver(dut, len(symbols) + 10)
    driver.cancel()
    clock_task.cancel()

    clean = [index for index, slot in enumerate(slots) if not slot.error]
    assert [s.cycle for s in strobes] == [expected_strobe_cycle(index) for index in clean], (
        f"strobes on cycles {[s.cycle for s in strobes]}, expected one per clean frame {clean}"
    )
    for index, strobe in zip(clean, strobes):
        stream = slots[index].stream
        assert strobe.prompt["pulseId"] == stream["pulseId"], f"slot {index}: prompt pulse id"
        assert strobe.prompt["eventCodes"] == stream["eventCodes"] | 1, f"slot {index}: prompt event codes"
        assert strobe.prompt["dbuff"] == stream["dbuff"], f"slot {index}: prompt data buffer"
        # The error reset also cleared the data-buffer history, so only the
        # newest dmod word is present in the lagged user data buffer.
        assert strobe.user["dbuff"] == lagged_dbuff(ZERO_DBUFF, stream["dbuff"]), f"slot {index}: user data buffer"
        assert trace[strobe.cycle][1] == 0, f"slot {index}: valid already set at the strobe"
        assert trace[strobe.cycle + 1][1] == 1, f"slot {index}: valid not set after the strobe"

    for index, slot in enumerate(slots):
        if not slot.error:
            continue
        first = slot_start(index) + INJECT_AT + 2
        last = expected_strobe_cycle(index + 1) - 1
        window = trace[first:last + 1]
        assert all(strobe == 0 for strobe, _, _ in window), f"slot {index}: strobe after {slot.error}"
        assert all(valid == 0 for _, valid, _ in window), f"slot {index}: valid not cleared by {slot.error}"


def test_TimingStreamTx():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingstreamtxwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(TX_WRAPPER)]},
        extra_env=cocotb_filtered_env(
            {},
            cocotb_test_filter("streamtx_matches_model", "streamtx_never_sends_code_255"),
        ),
    )


def test_TimingStreamRx():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingstreamrxwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(RX_WRAPPER)]},
        extra_env=cocotb_filtered_env(
            {},
            cocotb_test_filter("streamrx_decodes_model_frames", "streamrx_error_resets_frame"),
        ),
    )
