#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingDeserializer against model symbols, with fault injection.

Test methodology:
    Sweep: STREAMS_G in 1 and 2, one compiled simulation per value, with
        streamIds (0) and (0, 5). The routing entrypoint runs only with
        STREAMS_G = 2; the others run for both widths.
    Stimulus: rst is held for 3 clk cycles with idle commas on the rx ports,
        then released. A Python driver presents one model symbol per clk.
        Frames come from timing_model.encode_frame; faults are applied by
        editing the symbol list (a flipped CRC or data word, a K28.5 comma
        written over a data symbol) or by pulsing rxDecErr, rxDspErr or rst
        for one cycle at a chosen symbol. Frames are separated by 10 idle
        commas.
    Checks: one advance pulse per word on the stream whose streamIds entry
        matches the SOS stream id, with streamData equal to word k and
        streamOffset and streamLast equal to the SOS fields; a segment for
        an id that no stream carries produces no advance; sof, fiducial and
        eof pulse once per frame (sof and fiducial together); crcErr pulses
        once for a flipped CRC low word, CRC high word or data word and
        never for a good frame; a frame interrupted by rxDecErr, rxDspErr or
        rst produces neither eof nor crcErr and the next frame decodes in
        full; an empty frame pulses sof and eof with no advance; every
        sampled output is resolvable after reset release.
    Timing: 10 ns clk.
    Propagation sampling: the driver changes inputs 2 ns past the rising
        edge and every output is read at the same instant; all outputs are
        registered with TPD_G = 1 ns, so they are stable by then.
"""

from pathlib import Path
from typing import NamedTuple

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingDeserializerWrapper.vhd"

STREAM_IDS = (0, 5)
UNKNOWN_ID = 9
GAP = 10
LEAD = 6
TAIL = 8
IDLE = timing_model.IDLE_SYMBOL
SOF_INDEX = 1
FIRST_WORD_INDEX = 3


class Beat(NamedTuple):
    """Inputs of one clk cycle."""

    data: int
    data_k: int
    dec_err: int = 0
    dsp_err: int = 0
    rst: int = 0


class Trace:
    """Outputs sampled on every cycle of a run."""

    def __init__(self, streams):
        self.streams = streams
        self.cycles = []

    def pulses(self, name):
        return [index for index, cycle in enumerate(self.cycles) if cycle[name]]

    def words(self, stream):
        """Return (data, offset, last) for every advance pulse of ``stream``."""
        return [
            (cycle["data"][stream], cycle["offset"][stream], cycle["last"][stream])
            for cycle in self.cycles
            if cycle["advance"][stream]
        ]

    def ready_at_sof(self, stream):
        """Return streamReady on the cycle where each frame's fiducial pulse is visible."""
        return [self.cycles[index]["ready"][stream] for index in self.pulses("fiducial")]


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


def unpack(value, width, count):
    return [(value >> (width * index)) & ((1 << width) - 1) for index in range(count)]


def sample_outputs(dut, streams):
    return {
        "fiducial": resolved_int(dut.fiducial),
        "sof": resolved_int(dut.sof),
        "eof": resolved_int(dut.eof),
        "crcErr": resolved_int(dut.crcErr),
        "ready": unpack(resolved_int(dut.streamReady), 1, streams),
        "last": unpack(resolved_int(dut.streamLast), 1, streams),
        "data": unpack(resolved_int(dut.streamData), 16, streams),
        "offset": unpack(resolved_int(dut.streamOffset), 7, streams),
        "advance": unpack(resolved_int(dut.advance), 1, streams),
    }


def beats_of(symbols, **flags):
    return [Beat(data, data_k, **flags) for data, data_k in symbols]


def frames_to_beats(frames):
    """Two reset cycles of lead idle, each frame followed by a gap of idle commas, then a tail.

    Starting every run from a reset makes the carried-over frame flags of an
    earlier run in the same simulation irrelevant.
    """
    beats = beats_of([IDLE] * 2, rst=1) + beats_of([IDLE] * (LEAD - 2))
    for frame in frames:
        beats += beats_of(frame) + beats_of([IDLE] * GAP)
    return beats + beats_of([IDLE] * TAIL)


def inject(beats, index, **flags):
    """Return ``beats`` with the flags applied to the beat at ``index``."""
    result = list(beats)
    result[index] = result[index]._replace(**flags)
    return result


def message_words_of(seed_word):
    """Return 59 distinct words so a misplaced or repeated word is visible."""
    return tuple((seed_word + 0x0101 * index) & 0xFFFF for index in range(timing_model.TIMING_MESSAGE_WORDS))


async def start_deserializer(dut, ids):
    """Drive defined inputs, start the clock, hold reset 3 cycles, release it."""
    idle_data, idle_k = IDLE
    dut.rst.value = 1
    dut.rxData.value = idle_data
    dut.rxDataK.value = idle_k
    dut.rxDecErr.value = 0
    dut.rxDspErr.value = 0
    dut.streamIds.value = sum(stream_id << (4 * index) for index, stream_id in enumerate(ids))
    clock_task = cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    return clock_task


async def run_beats(dut, beats):
    """Present one beat per cycle and return the outputs sampled on every cycle."""
    streams = len(dut.advance)
    trace = Trace(streams)
    for beat in beats:
        await sample_after_tpd(dut.clk, propagation_time=2)
        trace.cycles.append(sample_outputs(dut, streams))
        dut.rxData.value = beat.data
        dut.rxDataK.value = beat.data_k
        dut.rxDecErr.value = beat.dec_err
        dut.rxDspErr.value = beat.dsp_err
        dut.rst.value = beat.rst
    for _ in range(2):
        await sample_after_tpd(dut.clk, propagation_time=2)
        trace.cycles.append(sample_outputs(dut, streams))
    return trace


def segment_ids(dut):
    return list(STREAM_IDS[:len(dut.advance)])


def expected_words(segment):
    return [(word, segment.offset, segment.last) for word in segment.words]


def check_frame_pulses(trace, frames, crc_errors=0):
    assert len(trace.pulses("sof")) == frames, f"sof pulses at {trace.pulses('sof')}"
    assert trace.pulses("sof") == trace.pulses("fiducial"), "sof and fiducial do not pulse together"
    assert len(trace.pulses("eof")) == frames, f"eof pulses at {trace.pulses('eof')}"
    assert len(trace.pulses("crcErr")) == crc_errors, f"crcErr pulses at {trace.pulses('crcErr')}"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def deserializer_good_frame(dut):
    """A model frame is delivered word by word; a segment with an unknown id is sunk.

    Propagation sampling: inputs change 2 ns after the edge and outputs are
    read at the same instant.
    """
    ids = segment_ids(dut)
    message = timing_model.Segment(ids[0], message_words_of(0x0001), 0, 1)
    sunk = timing_model.Segment(UNKNOWN_ID, (0xDEAD, 0xBEEF, 0xFACE, 0xF00D), 0, 1)
    frames = [
        timing_model.encode_frame([message]),
        timing_model.encode_frame([message, sunk]),
        timing_model.encode_frame([sunk, message]),
    ]
    clock_task = await start_deserializer(dut, ids)
    trace = await run_beats(dut, frames_to_beats(frames))
    check_frame_pulses(trace, len(frames))
    assert trace.words(0) == expected_words(message) * len(frames), (
        f"stream 0 words differ: {len(trace.words(0))} delivered for {len(frames) * len(message.words)} sent"
    )
    for index in range(1, len(ids)):
        assert trace.words(index) == [], f"stream {index} advanced for a frame with no segment for it"
    # streamReady is the previous frame's "segment was received" flag, loaded at the SOF.
    assert trace.ready_at_sof(0) == [0, 1, 1], f"streamReady at each SOF: {trace.ready_at_sof(0)}"
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def deserializer_stream_routing(dut):
    """Each segment reaches only the stream whose id matches, with its own offset and last.

    Propagation sampling: inputs change 2 ns after the edge and outputs are
    read at the same instant.
    """
    ids = segment_ids(dut)
    seg0 = timing_model.Segment(ids[0], (0x1111, 0x2222, 0x3333), 0, 1)
    seg1 = timing_model.Segment(ids[1], (0xA5A5, 0x5A5A), 3, 0)
    sunk = timing_model.Segment(UNKNOWN_ID, (0xCAFE, 0xBABE), 7, 1)
    frames = [
        timing_model.encode_frame([seg0, seg1, sunk]),
        timing_model.encode_frame([sunk, seg1, seg0]),
        timing_model.encode_frame([seg1]),
    ]
    clock_task = await start_deserializer(dut, ids)
    trace = await run_beats(dut, frames_to_beats(frames))
    check_frame_pulses(trace, len(frames))
    assert trace.words(0) == expected_words(seg0) * 2, f"stream 0 words {trace.words(0)}"
    assert trace.words(1) == expected_words(seg1) * 3, f"stream 1 words {trace.words(1)}"
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def deserializer_crc_errors(dut):
    """A flipped CRC word or data word pulses crcErr once; good frames never do.

    Propagation sampling: inputs change 2 ns after the edge and outputs are
    read at the same instant.
    """
    ids = segment_ids(dut)
    segment = timing_model.Segment(ids[0], message_words_of(0x0100), 0, 1)
    good = timing_model.encode_frame([segment])
    bad_low = list(good)
    bad_low[-2] = (good[-2][0] ^ 0x0001, 0b00)
    bad_high = list(good)
    bad_high[-1] = (good[-1][0] ^ 0x8000, 0b00)
    bad_data = list(good)
    flipped_index = FIRST_WORD_INDEX + 20
    bad_data[flipped_index] = (good[flipped_index][0] ^ 0x0010, 0b00)
    frames = [good, bad_low, good, bad_high, good, bad_data, good]
    clock_task = await start_deserializer(dut, ids)
    trace = await run_beats(dut, frames_to_beats(frames))
    check_frame_pulses(trace, len(frames), crc_errors=3)
    cycles_per_frame = len(good) + GAP
    frame_of = [(index - LEAD) // cycles_per_frame for index in trace.pulses("crcErr")]
    assert frame_of == [1, 3, 5], f"crcErr pulses landed in frames {frame_of}"
    # The corrupted word is forwarded before the CRC is known to be wrong.
    delivered = [word for word, _, _ in trace.words(0)]
    sent = [word for frame in frames for word, data_k in frame[FIRST_WORD_INDEX:-3] if data_k == 0]
    assert delivered == sent, "stream 0 words differ from the symbols sent, including the corrupted word"
    # A CRC error clears the stream's served flag, so the next SOF loads streamReady low.
    assert trace.ready_at_sof(0) == [0, 1, 0, 1, 0, 1, 0], f"streamReady at each SOF: {trace.ready_at_sof(0)}"
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def deserializer_link_errors(dut):
    """rxDecErr, rxDspErr or rst in the middle of a segment abandons the frame.

    Propagation sampling: inputs change 2 ns after the edge and outputs are
    read at the same instant.
    """
    ids = segment_ids(dut)
    segment = timing_model.Segment(ids[0], message_words_of(0x0200), 0, 1)
    good = timing_model.encode_frame([segment])
    mid = LEAD + len(good) + GAP + FIRST_WORD_INDEX + 25
    cases = {
        "rxDecErr": {"dec_err": 0b01},
        "rxDspErr": {"dsp_err": 0b10},
        "rst": {"rst": 1},
    }
    clock_task = await start_deserializer(dut, ids)
    for name, flags in cases.items():
        beats = inject(frames_to_beats([good, good, good]), mid, **flags)
        trace = await run_beats(dut, beats)
        sof_cycles = trace.pulses("sof")
        eof_cycles = trace.pulses("eof")
        assert len(sof_cycles) == 3, f"{name}: sof pulses at {sof_cycles}"
        assert len(eof_cycles) == 2, f"{name}: eof pulses at {eof_cycles}, the interrupted frame must not end"
        assert trace.pulses("crcErr") == [], f"{name}: crcErr pulsed for an abandoned frame"
        cycles_per_frame = len(good) + GAP
        eof_frames = [(index - LEAD) // cycles_per_frame for index in eof_cycles]
        assert eof_frames == [0, 2], f"{name}: eof landed in frames {eof_frames}"
        delivered = trace.words(0)
        full = expected_words(segment)
        assert delivered[:len(full)] == full, f"{name}: first frame words differ"
        assert delivered[-len(full):] == full, f"{name}: frame after the error was not delivered in full"
        assert len(delivered) < 3 * len(full), f"{name}: words after the error leaked through"
        # The error clears the served flag, so the next SOF loads streamReady low.
        assert trace.ready_at_sof(0) == [0, 1, 0], f"{name}: streamReady at each SOF: {trace.ready_at_sof(0)}"
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def deserializer_empty_frame(dut):
    """A frame with no segment pulses sof and eof, with no advance and no crcErr.

    Propagation sampling: inputs change 2 ns after the edge and outputs are
    read at the same instant.
    """
    ids = segment_ids(dut)
    empty = timing_model.encode_frame([])
    clock_task = await start_deserializer(dut, ids)
    trace = await run_beats(dut, frames_to_beats([empty, empty]))
    check_frame_pulses(trace, 2)
    for index in range(len(ids)):
        assert trace.words(index) == [], f"stream {index} advanced for an empty frame"
    first_sof = trace.pulses("sof")[0]
    first_eof = trace.pulses("eof")[0]
    assert first_eof - first_sof == 1, f"eof follows sof by {first_eof - first_sof} cycles"
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def deserializer_kchar_in_segment(dut):
    """A K28.5 comma inside a segment is delivered as a data word (observed, intent unconfirmed).

    The deserializer checks dataK only for the end-of-segment and
    end-of-frame symbols, so a comma written over a data symbol is passed to
    the stream and counted into the CRC like any other word. When the
    replaced word already equals 0xB5BC the CRC still matches; otherwise
    crcErr pulses.

    Propagation sampling: inputs change 2 ns after the edge and outputs are
    read at the same instant.
    """
    ids = segment_ids(dut)
    comma_data = IDLE[0]
    words = list(message_words_of(0x0300))
    comma_at = 12
    words[comma_at] = comma_data
    segment = timing_model.Segment(ids[0], tuple(words), 0, 1)
    matching = timing_model.encode_frame([segment])
    matching[FIRST_WORD_INDEX + comma_at] = IDLE
    mismatching = timing_model.encode_frame([timing_model.Segment(ids[0], message_words_of(0x0300), 0, 1)])
    mismatching[FIRST_WORD_INDEX + comma_at] = IDLE
    clock_task = await start_deserializer(dut, ids)
    trace = await run_beats(dut, frames_to_beats([matching, mismatching]))
    check_frame_pulses(trace, 2, crc_errors=1)
    delivered = [word for word, _, _ in trace.words(0)]
    assert len(delivered) == 2 * len(words), f"{len(delivered)} words delivered for {2 * len(words)} sent"
    assert delivered[comma_at] == comma_data, "the comma over a matching word was not delivered as data"
    assert delivered[len(words) + comma_at] == comma_data, "the comma over a mismatching word was not delivered as data"
    crc_cycle = trace.pulses("crcErr")[0]
    second_frame_start = trace.pulses("sof")[1]
    assert crc_cycle > second_frame_start, "crcErr pulsed for the frame whose CRC still matched"
    clock_task.cancel()


@pytest.mark.parametrize("streams", [1, 2])
def test_TimingDeserializer(streams):
    extra_env = (
        cocotb_filtered_env({}, cocotb_test_filter_excluding("deserializer_stream_routing"))
        if streams == 1
        else None
    )
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingdeserializerwrapper",
        parameters={"STREAMS_G": streams},
        extra_env=extra_env,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
