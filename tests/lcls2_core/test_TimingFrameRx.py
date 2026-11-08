#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingFrameRx test: model-encoded frames are decoded by the production receiver.

Test methodology:
    Sweep: none, one compiled simulation of TimingFrameRxWrapper.
    Stimulus: rxRst is held for 3 rxClk cycles with idle commas on the flat
        rx ports, then released. A driver task presents one model-encoded
        symbol per rxClk: the golden message as frame A, the same message
        with pulseId + 1 as frame B, each padded with idle commas to 200
        symbols.
    Checks: the first timingMessageStrobe, caused by the start of frame B
        because the message delay line holds a frame back until the next
        one starts, carries timingMessageValid=1, staData bit 3 (CRC error
        or overflow) low, and every decoded field equal to frame A; every
        checked output is resolvable on every sampled cycle after reset
        release; a missing strobe fails after a bounded 600-cycle wait.
    Timing: 10 ns rxClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs, which settle TPD_G = 1 ns after the edge,
        are stable.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingFrameRxWrapper.vhd"

FRAME_SLOTS = 200
STROBE_WAIT_CYCLES = 600
CHECKED_OUTPUTS = ("timingMessage", "timingMessageStrobe", "timingMessageValid", "staData")


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


def padded(symbols, slots=FRAME_SLOTS):
    return symbols + timing_model.idle_symbols(slots - len(symbols))


async def drive_symbols(dut, symbols):
    """Present one symbol per rxClk edge, then return."""
    for data, data_k in symbols:
        await RisingEdge(dut.rxClk)
        dut.rxData.value = data
        dut.rxDataK.value = data_k


async def start_receiver(dut):
    """Hold reset with idle commas, start the clock, release reset."""
    idle_data, idle_k = timing_model.IDLE_SYMBOL
    dut.rxRst.value = 1
    dut.rxData.value = idle_data
    dut.rxDataK.value = idle_k
    clock_task = cocotb.start_soon(Clock(dut.rxClk, 10, unit="ns").start(start_high=False))
    for _ in range(3):
        await RisingEdge(dut.rxClk)
    dut.rxRst.value = 0
    return clock_task


@cocotb.test(timeout_time=200, timeout_unit="us")
async def framerx_decodes_model_frames(dut):
    """The first strobe delivers frame A with every field equal to the model.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    msg_a = golden_message()
    msg_b = golden_message(pulse_id=msg_a["pulseId"] + 1)
    symbols = (
        padded(timing_model.message_frame(msg_a))
        + padded(timing_model.message_frame(msg_b))
        + timing_model.idle_symbols(100)
    )

    clock_task = await start_receiver(dut)
    for _ in range(20):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
    driver = cocotb.start_soon(drive_symbols(dut, symbols))

    strobe_seen = False
    for cycle in range(STROBE_WAIT_CYCLES):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
        sampled = {name: resolved_int(getattr(dut, name)) for name in CHECKED_OUTPUTS}
        if sampled["timingMessageStrobe"]:
            strobe_seen = True
            dut._log.info(f"first strobe on cycle {cycle}")
            assert sampled["timingMessageValid"] == 1, "strobe without timingMessageValid"
            assert not (sampled["staData"] >> 3) & 1, f"staData=0x{sampled['staData']:02x} flags a CRC error"
            decoded = timing_model.unpack_message(sampled["timingMessage"])
            assert decoded == msg_a, f"decoded message differs from frame A: {decoded}"
            break

    assert strobe_seen, f"no timingMessageStrobe within {STROBE_WAIT_CYCLES} cycles"

    driver.cancel()
    clock_task.cancel()


PARTIAL_STREAM = 2
PARTIAL_WORDS = 20
FULL_STREAMS = (1, 15)


def extension_slice(dut, stream_id):
    return (resolved_int(dut.extensionData) >> ((stream_id - 1) * 512)) & ((1 << 512) - 1)


@cocotb.test(timeout_time=200, timeout_unit="us")
async def framerx_extension_segments(dut):
    """Extension segments appear in their extensionData slice at the modeled placement.

    A 32-word segment fills its 512-bit slice with word 0 in the lowest
    bits. A 20-word segment is shifted in last and lands at the top of the
    slice, so its word 0 sits at word index 12; this placement was measured
    on the production receiver before the model encoded it.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    msg = golden_message()
    full = {stream_id: rng.getrandbits(512) for stream_id in FULL_STREAMS}
    partial_words = [rng.getrandbits(16) or 1 for _ in range(PARTIAL_WORDS)]
    segments = [
        timing_model.Segment(0, tuple(timing_model.message_words(msg))),
        *(timing_model.extension_segment(stream_id, full[stream_id]) for stream_id in FULL_STREAMS),
        timing_model.Segment(PARTIAL_STREAM, tuple(partial_words)),
    ]
    symbols = padded(timing_model.encode_frame(segments)) * 2 + timing_model.idle_symbols(100)

    clock_task = await start_receiver(dut)
    for _ in range(20):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
    driver = cocotb.start_soon(drive_symbols(dut, symbols))

    strobe_seen = False
    for _ in range(STROBE_WAIT_CYCLES):
        await sample_after_tpd(dut.rxClk, propagation_time=2)
        if resolved_int(dut.timingMessageStrobe):
            strobe_seen = True
            break
    assert strobe_seen, f"no timingMessageStrobe within {STROBE_WAIT_CYCLES} cycles"

    # extensionValid is registered one cycle after the strobe.
    await sample_after_tpd(dut.rxClk, propagation_time=2)
    valid = resolved_int(dut.extensionValid)
    expected_valid = sum(1 << (stream_id - 1) for stream_id in (*FULL_STREAMS, PARTIAL_STREAM))
    assert valid == expected_valid, f"extensionValid=0x{valid:04x}, expected 0x{expected_valid:04x}"
    for stream_id in FULL_STREAMS:
        value = extension_slice(dut, stream_id)
        assert value == timing_model.extension_data(timing_model.extension_segment(stream_id, full[stream_id]).words)
        assert value == full[stream_id], f"stream {stream_id} slice differs from the sent 512 bits"
    value = extension_slice(dut, PARTIAL_STREAM)
    assert value == timing_model.extension_data(partial_words), (
        f"stream {PARTIAL_STREAM} slice 0x{value:0128x} differs from the modeled top-aligned placement"
    )
    assert (value >> (16 * 12)) & 0xFFFF == partial_words[0], "word 0 of a 20-word segment is not at word index 12"
    assert value & ((1 << (16 * 12)) - 1) == 0, "the low 12 words of a 20-word segment are not zero after reset"
    for stream_id in range(1, 16):
        if stream_id not in (*FULL_STREAMS, PARTIAL_STREAM):
            assert extension_slice(dut, stream_id) == 0, f"idle stream {stream_id} slice is not zero"

    driver.cancel()
    clock_task.cancel()


def test_TimingFrameRx():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingframerxwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
