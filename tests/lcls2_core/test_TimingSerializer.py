#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingSerializer wire grammar: every frame equals the model encoding.

Test methodology:
    Sweep: STREAMS_G in 1 and 2, one compiled simulation per value. The
        two-stream entrypoint runs only with STREAMS_G = 2; the other
        entrypoints run for both and keep stream 1 not ready when it exists.
    Stimulus: rst is held for 3 clk cycles, then released. A Python source
        per stream answers the advance handshake the way WordSerializer
        does: it presents word 0 with ready high from the fiducial cycle,
        steps to the next word on the cycle after each advance pulse, and
        drops ready after its last word. Cases are the golden message
        frame, a two-segment frame (stream 0 with id 0 and 3 words, stream 1
        with id 5, 2 words, offset 3 and last clear), a fiducial with no
        stream ready, and a reset in the middle of a frame followed by a
        fresh golden frame.
    Checks: the captured (data, dataK) symbols, from the cycle after the
        fiducial, equal timing_model.encode_frame of the same segments
        followed by idle commas, with the CRC words 0x4292 then 0x37EF for
        the golden frame; every K-character carries D21.5 in the high byte
        with dataK 01 and every data word carries dataK 00; the decoded SOS
        fields are stream id, last and offset; one advance pulse is seen per
        word of each stream; after a mid-frame reset the output is the idle
        comma within 2 cycles; advance, data and dataK are resolvable on
        every sampled cycle after reset release.
    Timing: 10 ns clk.
    Propagation sampling: inputs are driven 2 ns past the rising edge and
        outputs are read 2 ns later, so the registered outputs, which settle
        TPD_G = 1 ns after the edge, and the combinational advance output
        have both settled for the stimulus of the same cycle.
"""

from pathlib import Path

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingSerializerWrapper.vhd"

IDLE = timing_model.IDLE_SYMBOL
TRAILING_IDLE = 2


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


def golden_message():
    msg = timing_model.default_message()
    msg["pulseId"] = 0x0123456789ABCDEF
    msg["timeStamp"] = 0xFEDCBA9876543210
    msg["beamRequest"] = 0xA5A5A5A5
    msg["bsaDone"] = 0x0F0F0F0F0F0F0F0F
    msg["control"][17] = 0xBEEF
    return msg


class StreamSource:
    """Stream side of the advance handshake, as WordSerializer implements it."""

    def __init__(self, segment):
        self.segment = segment
        self.index = 0
        self.active = False

    def start(self):
        self.index = 0
        self.active = True

    def clear(self):
        self.active = False

    @property
    def ready(self):
        return int(self.active and self.index < len(self.segment.words))

    @property
    def data(self):
        return self.segment.words[self.index] if self.ready else 0

    def advanced(self):
        self.index += 1


def pack(values, width):
    """Pack per-stream values into one flat integer, stream 0 in the low bits."""
    return sum(value << (width * index) for index, value in enumerate(values))


class Capture:
    """Per-cycle samples of one serialization run."""

    def __init__(self):
        self.symbols = []
        self.advances = []


async def run_cycles(dut, sources, ids, cycles, fiducials=(), resets=()):
    """Drive ``cycles`` clock cycles and return the per-cycle outputs.

    Cycle numbers start at 0. A fiducial in cycle c makes the first frame
    symbol appear in cycle c + 1. A reset in cycle c clears the sources for
    cycle c + 1.
    """
    streams = len(sources)
    capture = Capture()
    advance_counts = [0] * streams
    dut.streamIds.value = pack(ids, 4)
    for cycle in range(cycles):
        await sample_after_tpd(dut.clk, propagation_time=2)
        if cycle in fiducials:
            for source in sources:
                source.start()
        dut.fiducial.value = int(cycle in fiducials)
        dut.rst.value = int(cycle in resets)
        dut.streamReady.value = pack([source.ready for source in sources], 1)
        dut.streamData.value = pack([source.data for source in sources], 16)
        dut.streamOffset.value = pack([source.segment.offset for source in sources], 7)
        dut.streamLast.value = pack([source.segment.last for source in sources], 1)
        await Timer(2, unit="ns")
        advance = resolved_int(dut.advance)
        capture.symbols.append((resolved_int(dut.data), resolved_int(dut.dataK)))
        capture.advances.append(advance)
        for index, source in enumerate(sources):
            if (advance >> index) & 1:
                advance_counts[index] += 1
                source.advanced()
        if cycle in resets:
            for source in sources:
                source.clear()
    capture.advance_counts = advance_counts
    return capture


async def start_serializer(dut, sources, ids):
    """Drive defined inputs, start the clock, hold reset 3 cycles, release it."""
    streams = len(sources)
    dut.rst.value = 1
    dut.fiducial.value = 0
    dut.streamReady.value = 0
    dut.streamData.value = 0
    dut.streamOffset.value = 0
    dut.streamLast.value = (1 << streams) - 1
    dut.streamIds.value = pack(ids, 4)
    clock_task = cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    return clock_task


def check_grammar(symbols):
    """Check the K-character and data-word encoding rules on a captured frame."""
    for data, data_k in symbols:
        if data_k == 0b01:
            assert data >> 8 == timing_model.D_215, f"K symbol 0x{data:04X}/01 lacks D21.5 in the high byte"
        else:
            assert data_k == 0b00, f"symbol 0x{data:04X} carries dataK {data_k:02b}"


def frame_window(capture, fiducial, segments):
    """Return the captured symbols that should equal the model frame plus idle."""
    expected = timing_model.encode_frame(segments) + [IDLE] * TRAILING_IDLE
    start = fiducial + 1
    return capture.symbols[start:start + len(expected)], expected


def make_sources(segments, streams):
    """One source per hardware stream; segments fill the low indices, the rest stay empty."""
    empty = timing_model.Segment(0, ())
    return [StreamSource(segments[i] if i < len(segments) else empty) for i in range(streams)]


def stream_ids(segments, streams):
    return [segments[i].stream_id if i < len(segments) else 0 for i in range(streams)]


async def run_frame_case(dut, segments, name):
    streams = len(dut.advance)
    sources = make_sources(segments, streams)
    ids = stream_ids(segments, streams)
    clock_task = await start_serializer(dut, sources, ids)
    fiducial = 4
    cycles = fiducial + 1 + len(timing_model.encode_frame(segments)) + 8
    capture = await run_cycles(dut, sources, ids, cycles, fiducials=(fiducial,))
    window, expected = frame_window(capture, fiducial, segments)
    assert window == expected, f"{name}: symbols differ from the model frame at index " + str(
        next((i for i, (a, b) in enumerate(zip(window, expected)) if a != b), len(window))
    )
    assert all(symbol == IDLE for symbol in capture.symbols[:fiducial + 1]), f"{name}: output not idle before the frame"
    assert all(symbol == IDLE for symbol in capture.symbols[fiducial + 1 + len(expected) - TRAILING_IDLE:]), (
        f"{name}: output did not return to the idle comma"
    )
    check_grammar(capture.symbols)
    decoded = timing_model.decode_frame(window)
    assert decoded.crc_ok, f"{name}: model decode flags a CRC mismatch on the serializer output"
    assert decoded.segments == list(segments), f"{name}: decoded segments {decoded.segments}"
    for index, segment in enumerate(segments):
        assert capture.advance_counts[index] == len(segment.words), (
            f"{name}: stream {index} saw {capture.advance_counts[index]} advance pulses for {len(segment.words)} words"
        )
    for index in range(len(segments), streams):
        assert capture.advance_counts[index] == 0, f"{name}: idle stream {index} was advanced"
    clock_task.cancel()
    return capture, expected


@cocotb.test(timeout_time=100, timeout_unit="us")
async def serializer_golden_frame(dut):
    """The golden message frame equals the model, CRC words 0x4292 then 0x37EF.

    Propagation sampling: inputs are driven 2 ns after the edge and outputs
    are read 2 ns later.
    """
    segments = [timing_model.Segment(0, tuple(timing_model.message_words(golden_message())))]
    capture, expected = await run_frame_case(dut, segments, "golden frame")
    assert expected[-TRAILING_IDLE - 2:-TRAILING_IDLE] == [(0x4292, 0b00), (0x37EF, 0b00)], "model golden CRC words are not 0x4292, 0x37EF"
    sos = expected[2][0]
    assert sos == 0x0080, f"SOS word 0x{sos:04X}"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def serializer_two_streams(dut):
    """Two segments leave in stream index order with their own SOS fields.

    Propagation sampling: inputs are driven 2 ns after the edge and outputs
    are read 2 ns later.
    """
    segments = [
        timing_model.Segment(0, (0x1111, 0x2222, 0x3333), 0, 1),
        timing_model.Segment(5, (0xA5A5, 0x5A5A), 3, 0),
    ]
    capture, expected = await run_frame_case(dut, segments, "two-stream frame")
    sos_words = [expected[2][0], expected[2 + 1 + 3 + 1][0]]
    assert sos_words == [0x0080, 0x5003], f"SOS words {[hex(word) for word in sos_words]}"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def serializer_empty_frame(dut):
    """A fiducial with no stream ready gives ALIGN, SOF, EOF and the CRC of the EOF word.

    Propagation sampling: inputs are driven 2 ns after the edge and outputs
    are read 2 ns later.
    """
    capture, expected = await run_frame_case(dut, [], "empty frame")
    assert expected[:3] == [
        timing_model.ALIGN_SYMBOL,
        timing_model.SOF_SYMBOL,
        timing_model.EOF_SYMBOL,
    ], "model empty frame does not start ALIGN, SOF, EOF"
    low, high = timing_model.frame_crc_words([timing_model.EOF_SYMBOL[0]])
    assert expected[3:5] == [(low, 0b00), (high, 0b00)], "empty frame CRC is not the CRC of the EOF word only"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def serializer_reset_midframe(dut):
    """A reset in the middle of a frame returns the output to idle within 2 cycles.

    A fresh golden frame afterwards is serialized in full.

    Propagation sampling: inputs are driven 2 ns after the edge and outputs
    are read 2 ns later.
    """
    streams = len(dut.advance)
    segments = [timing_model.Segment(0, tuple(timing_model.message_words(golden_message())))]
    sources = make_sources(segments, streams)
    ids = stream_ids(segments, streams)
    clock_task = await start_serializer(dut, sources, ids)
    first_fiducial = 4
    reset_cycle = first_fiducial + 20
    second_fiducial = reset_cycle + 12
    cycles = second_fiducial + 1 + len(timing_model.encode_frame(segments)) + 8
    capture = await run_cycles(
        dut,
        sources,
        ids,
        cycles,
        fiducials=(first_fiducial, second_fiducial),
        resets=(reset_cycle,),
    )
    before = capture.symbols[first_fiducial + 1:reset_cycle + 1]
    assert before[0] == timing_model.ALIGN_SYMBOL and before[1] == timing_model.SOF_SYMBOL, "frame did not start"
    assert any(symbol != IDLE for symbol in before), "no frame symbols before the reset"
    for cycle in range(reset_cycle + 2, second_fiducial + 1):
        assert capture.symbols[cycle] == IDLE, (
            f"cycle {cycle - reset_cycle} after the reset: 0x{capture.symbols[cycle][0]:04X}/{capture.symbols[cycle][1]:02b}"
        )
    window, expected = frame_window(capture, second_fiducial, segments)
    assert window == expected, "frame after the mid-frame reset differs from the model frame"
    clock_task.cancel()


@pytest.mark.parametrize("streams", [1, 2])
def test_TimingSerializer(streams):
    extra_env = (
        cocotb_filtered_env({}, cocotb_test_filter_excluding("serializer_two_streams"))
        if streams == 1
        else None
    )
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingserializerwrapper",
        parameters={"STREAMS_G": streams},
        extra_env=extra_env,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
