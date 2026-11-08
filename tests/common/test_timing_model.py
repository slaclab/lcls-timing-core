#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Unit tests for the timing reference model.

Test methodology:
    Sweep: the TimingMessageType field table, one golden message frame, the
        CRC-32 helpers over fixed and seeded random byte strings, and the
        field packers over valid and over-wide values.
    Stimulus: timing_model functions are called directly. No simulator is
        launched.
    Checks: field offsets and widths match the TimingPkg toSlv layout and
        sum to 944 bits; the default message sets mpsClass to all ones; the
        golden message frame has the expected SOS, 59 words, EOS, EOF and
        CRC words; the bitwise CRC equals zlib.crc32; an over-wide field
        value raises ValueError.
    Timing: none, no simulator.
"""

import random
import zlib

import pytest

from tests.common import timing_model

# Words of the golden message after the SOS word. The golden frame was
# captured from the production TPSerializer and TimingSerializer under GHDL
# 6.0.0, so this vector and the CRC words below are a regression pin and not
# independent evidence.
GOLDEN_WORDS = (
    [0x0001, 0xCDEF, 0x89AB, 0x4567, 0x0123, 0x3210, 0x7654, 0xBA98, 0xFEDC]
    + [0x0000, 0x0000, 0xA5A5, 0xA5A5]
    + [0x0000] * 8
    + [0xFFFF] * 4
    + [0x0000] * 12
    + [0x0F0F] * 4
    + [0x0000] * 17
    + [0xBEEF]
)
GOLDEN_CRC_WORDS = (0x4292, 0x37EF)


def golden_message():
    msg = timing_model.default_message()
    msg["pulseId"] = 0x0123456789ABCDEF
    msg["timeStamp"] = 0xFEDCBA9876543210
    msg["beamRequest"] = 0xA5A5A5A5
    msg["bsaDone"] = 0x0F0F0F0F0F0F0F0F
    msg["control"][17] = 0xBEEF
    return msg


def test_message_layout_matches_timing_pkg_offsets():
    layout = timing_model.field_layout(timing_model.MESSAGE_FIELDS)

    assert layout["version"] == (0, 16, 1)
    assert layout["pulseId"] == (16, 64, 1)
    assert layout["timeStamp"] == (80, 64, 1)
    assert layout["beamRequest"] == (176, 32, 1)
    assert layout["unused"] == (304, 13, 1)
    assert layout["mpsLimit"] == (320, 16, 1)
    assert layout["mpsClass"] == (336, 4, 16)
    assert layout["bsaDone"] == (592, 64, 1)
    assert layout["control"] == (656, 16, 18)
    total = sum(width * count for _, width, count in timing_model.MESSAGE_FIELDS)
    assert total == timing_model.TIMING_MESSAGE_BITS == 944


def test_default_message_sets_mps_class_to_all_ones():
    vector = timing_model.pack_message(timing_model.default_message())

    assert (vector >> 336) & ((1 << 64) - 1) == (1 << 64) - 1
    assert vector & 0xFFFF == timing_model.TIMING_MESSAGE_VERSION
    assert vector >> 400 == 0


def test_pack_and_unpack_message_round_trip():
    msg = golden_message()

    assert timing_model.unpack_message(timing_model.pack_message(msg)) == msg


def test_message_frame_matches_golden_vector():
    symbols = timing_model.message_frame(golden_message())

    assert symbols[0] == timing_model.ALIGN_SYMBOL
    assert symbols[1] == timing_model.SOF_SYMBOL
    assert symbols[2] == (0x0080, 0b00)
    assert [data for data, _ in symbols[3:62]] == GOLDEN_WORDS
    assert all(data_k == 0b00 for _, data_k in symbols[3:62])
    assert symbols[62] == timing_model.EOS_SYMBOL == (0xB51C, 0b01)
    assert symbols[63] == timing_model.EOF_SYMBOL == (0xB5FD, 0b01)
    assert symbols[64:] == [(GOLDEN_CRC_WORDS[0], 0b00), (GOLDEN_CRC_WORDS[1], 0b00)]


def test_golden_crc_words_and_zlib_value():
    covered = [0x0080, *GOLDEN_WORDS, 0xB51C, 0xB5FD]
    data = b"".join(word.to_bytes(2, "big") for word in covered)

    assert len(covered) == 62
    assert zlib.crc32(data) == 0x9242EF37
    assert timing_model.frame_crc_words(covered) == GOLDEN_CRC_WORDS


def test_crc32_bitwise_matches_zlib():
    rng = random.Random(1234)
    vectors = [b"", b"\x00", b"123456789", bytes(rng.randrange(256) for _ in range(64))]

    for data in vectors:
        assert timing_model.crc32_bitwise(data) == zlib.crc32(data), data
    assert timing_model.crc32_bitwise(b"123456789") == 0xCBF43926


def test_pack_fields_rejects_over_wide_value():
    msg = timing_model.default_message()
    msg["resync"] = 2

    with pytest.raises(ValueError, match="resync"):
        timing_model.pack_message(msg)


def test_pack_fields_rejects_missing_and_unknown_keys():
    table = (("a", 4, 1), ("b", 4, 2))

    with pytest.raises(ValueError, match="missing"):
        timing_model.pack_fields(table, {"a": 1})
    with pytest.raises(ValueError, match="unknown"):
        timing_model.pack_fields(table, {"a": 1, "b": [0, 0], "c": 0})
    with pytest.raises(ValueError, match="2 elements"):
        timing_model.pack_fields(table, {"a": 1, "b": [0]})


def seeded_rng(seed=99):
    return random.Random(seed)


def test_decode_frame_round_trips_seeded_random_messages():
    rng = seeded_rng()

    for _ in range(50):
        msg = timing_model.random_message(rng)
        segments = [timing_model.Segment(0, tuple(timing_model.message_words(msg)))]
        decoded = timing_model.decode_frame(timing_model.encode_frame(segments))

        assert decoded.segments == segments
        assert decoded.crc_ok is True
        assert timing_model.unpack_message(
            sum(word << (16 * k) for k, word in enumerate(decoded.segments[0].words))
        ) == msg


def test_decode_frame_round_trips_multi_segment_frame_with_idle_padding():
    rng = seeded_rng()
    segments = [
        timing_model.Segment(0, tuple(timing_model.message_words(timing_model.random_message(rng)))),
        timing_model.extension_segment(1, rng.getrandbits(512)),
        timing_model.Segment(15, (0x1234, 0xABCD), offset=3, last=0),
    ]
    encoded = timing_model.encode_frame(segments)
    symbols = timing_model.idle_symbols(5) + encoded + timing_model.idle_symbols(5)

    decoded = timing_model.decode_frame(symbols)

    assert decoded.segments == segments
    assert decoded.crc_ok is True
    assert decoded.crc_words == (encoded[-2][0], encoded[-1][0])


def test_decode_frame_reports_bad_crc_without_raising():
    symbols = timing_model.message_frame(golden_message())
    symbols[-1] = (symbols[-1][0] ^ 1, symbols[-1][1])

    decoded = timing_model.decode_frame(symbols)

    assert decoded.crc_ok is False
    assert len(decoded.segments) == 1


def test_decode_frame_raises_for_missing_sof():
    symbols = timing_model.idle_symbols(10)

    with pytest.raises(ValueError, match="no SOF"):
        timing_model.decode_frame(symbols)


def test_decode_frame_raises_for_truncated_frame():
    symbols = timing_model.message_frame(golden_message())

    for cut in (3, 30, len(symbols) - 3, len(symbols) - 1):
        with pytest.raises(ValueError, match="truncated"):
            timing_model.decode_frame(symbols[:cut])


def test_decode_frame_raises_for_k_character_inside_a_segment():
    symbols = timing_model.message_frame(golden_message())
    symbols[10] = timing_model.IDLE_SYMBOL

    with pytest.raises(ValueError, match="K-character"):
        timing_model.decode_frame(symbols)


def test_extension_segment_holds_512_bits_least_significant_word_first():
    data = (0xBEEF << 496) | 0x1234
    segment = timing_model.extension_segment(7, data)

    assert segment.stream_id == 7
    assert len(segment.words) == timing_model.TIMING_EXTENSION_WORDS == 32
    assert segment.words[0] == 0x1234
    assert segment.words[31] == 0xBEEF
    assert timing_model.TIMING_EXTENSION_BITS == 512


@pytest.mark.parametrize("stream_id", [0, 16, -1])
def test_extension_segment_rejects_stream_ids_outside_1_to_15(stream_id):
    with pytest.raises(ValueError, match="stream id"):
        timing_model.extension_segment(stream_id, 0)


def test_extension_segment_rejects_data_wider_than_512_bits():
    with pytest.raises(ValueError, match="512"):
        timing_model.extension_segment(1, 1 << 512)


def test_expt_layout_is_320_bits_packed_least_significant_first():
    values = {
        "baseRateSince1Hz": 0x11111111,
        "baseRateSinceTM": 0x22222222,
        "irigTimeCode": (0x33 << 248) | 0x44,
    }

    vector = timing_model.pack_expt(values)

    assert timing_model.EXPT_MESSAGE_BITS == 320
    assert timing_model.EXPT_STREAM_ID == 2
    assert vector & 0xFFFFFFFF == 0x11111111
    assert (vector >> 32) & 0xFFFFFFFF == 0x22222222
    assert vector >> 64 == values["irigTimeCode"]
    assert timing_model.unpack_expt(vector) == values


def test_no_bsa_layout_widths_and_round_trip():
    assert sum(w * c for _, w, c in timing_model.MESSAGE_NO_BSA_FIELDS) == 672
    assert timing_model.TIMING_MESSAGE_BITS_NO_BSA == 672
    rng = seeded_rng()
    msg = timing_model.random_message(rng)

    decoded = timing_model.unpack_message_no_bsa(timing_model.pack_message_no_bsa(msg))

    assigned = set(msg) - {"version", "syncStatus", "mpsValid", "bcsFault",
                           "bsaInit", "bsaActive", "bsaAvgDone", "bsaDone"}
    assert set(decoded) == assigned
    assert decoded == {name: msg[name] for name in assigned}


def test_no_bsa_vector_carries_control_16_twice():
    msg = timing_model.default_message()
    msg["control"][16] = 0xCAFE

    vector = timing_model.pack_message_no_bsa(msg)

    assert (vector >> 288) & 0xFFFF == 0xCAFE
    assert (vector >> 640) & 0xFFFF == 0xCAFE


def test_databuff_and_stream_widths_and_round_trip():
    rng = seeded_rng()

    assert sum(w * c for _, w, c in timing_model.DATABUFF_FIELDS) == 416
    assert sum(w * c for _, w, c in timing_model.STREAM_FIELDS) == 704
    assert timing_model.TIMING_DATABUFF_BITS == 416
    assert timing_model.TIMING_STREAM_BITS == 704
    dbuff = timing_model.random_databuff(rng)
    assert timing_model.unpack_databuff(timing_model.pack_databuff(dbuff)) == dbuff
    stream = timing_model.random_stream(rng)
    assert timing_model.unpack_stream(timing_model.pack_stream(stream)) == stream
    packed = timing_model.pack_stream(stream)
    assert packed & 0xFFFFFFFF == stream["pulseId"]
    assert (packed >> 32) & ((1 << 256) - 1) == stream["eventCodes"]
    assert packed >> 288 == timing_model.pack_databuff(stream["dbuff"])


def test_lcls1_frame_round_trips_seeded_random_streams():
    rng = seeded_rng()
    streams = [timing_model.random_stream(rng) for _ in range(17)]
    streams.append({**timing_model.random_stream(rng), "eventCodes": 1 | (1 << 254) | (1 << 255)})
    streams.append({**timing_model.random_stream(rng), "eventCodes": 0})
    streams.append({**timing_model.random_stream(rng), "eventCodes": (1 << 256) - 1})

    for stream in streams:
        symbols = timing_model.encode_lcls1_frame(
            stream["pulseId"], stream["eventCodes"], stream["dbuff"]
        )
        decoded = timing_model.decode_lcls1_frame(symbols)

        # An unset slot is 0x0000 / 00, which the receiver reads as event code 0.
        assert decoded == (stream["pulseId"], stream["eventCodes"] | 1, stream["dbuff"])
        assert isinstance(decoded, timing_model.Lcls1Frame)


def test_lcls1_frame_grammar_matches_the_documented_symbol_positions():
    dbuff = timing_model.unpack_databuff(0x0102030405060708 | (1 << 400))
    symbols = timing_model.encode_lcls1_frame(0x80000001, (1 << 3) | (1 << 200), dbuff)

    assert symbols[0] == (0x1C00, 0b10)
    assert symbols[1] == (0x00BC, 0b01)
    assert symbols[2] == (0x0800, 0b00)
    assert symbols[4] == (0x0700, 0b00)
    assert symbols[105] == (0x3CBC, 0b11)
    assert symbols[106] == (0x0071, 0b00)
    assert symbols[107] == (0x00BC, 0b01)
    assert symbols[108] == (0x0070, 0b00)
    assert symbols[168] == (0x0071, 0b00)
    assert symbols[170] == (0x007D, 0b00)
    assert symbols[172 + 2 * 3] == (0x0003, 0b00)
    assert symbols[172 + 2 * 200] == (0x00C8, 0b00)
    assert symbols[172 + 2 * 4] == (0x0000, 0b00)
    assert symbols[172 + 2 * 4 + 1] == (0x00BC, 0b01)


def test_lcls1_unset_event_code_slots_are_zero_data_symbols_like_the_transmitter():
    # Positions measured on TimingStreamTx: set codes 1, 7 and 254 appear as
    # 0x00nn / 00, every other even slot is 0x0000 / 00, odd slots are commas,
    # and the frame ends with a data-only slot for code 255 that is not sent.
    dbuff = timing_model.unpack_databuff(int.from_bytes(bytes(range(1, 53)), "little"))
    symbols = timing_model.encode_lcls1_frame(0x80000001, (1 << 1) | (1 << 7) | (1 << 254), dbuff)

    assert len(symbols) == 684
    assert symbols[102] == (0x3300, 0b00)
    assert symbols[104] == (0x3400, 0b00)
    assert symbols[172] == (0x0000, 0b00)
    assert symbols[174] == (0x0001, 0b00)
    assert symbols[176] == (0x0000, 0b00)
    assert symbols[186] == (0x0007, 0b00)
    assert symbols[680] == (0x00FE, 0b00)
    assert symbols[681] == (0x00BC, 0b01)
    assert symbols[682] == (0x0000, 0b00)
    assert symbols[683] == (0x00BC, 0b01)
    assert timing_model.lcls1_idle_symbols(2, start_phase=1) == [(0x0000, 0b00), (0x00BC, 0b01)]


def test_decode_lcls1_frame_raises_for_missing_start_and_end():
    symbols = timing_model.encode_lcls1_frame(1, 0, timing_model.random_databuff(seeded_rng()))

    with pytest.raises(ValueError, match="K28.0"):
        timing_model.decode_lcls1_frame(symbols[1:])
    with pytest.raises(ValueError, match="end"):
        timing_model.decode_lcls1_frame(symbols[:105] + timing_model.lcls1_idle_symbols(300))
    with pytest.raises(ValueError, match="marker"):
        timing_model.decode_lcls1_frame(symbols[:170])


def test_lcls1_idle_symbols_alternate_comma_and_zero():
    assert timing_model.lcls1_idle_symbols(4) == [(0x00BC, 0b01), (0x0000, 0b00)] * 2
    assert timing_model.lcls1_idle_symbols(3, start_phase=1) == [
        (0x0000, 0b00), (0x00BC, 0b01), (0x0000, 0b00)
    ]
    assert timing_model.LCLS1_FRAME_LEN == 14000


def test_make_rng_reads_the_seed_environment_variable(monkeypatch):
    monkeypatch.setenv("LCLS_TIMING_SEED", "7")

    rng_a, seed_a = timing_model.make_rng()
    rng_b, seed_b = timing_model.make_rng()

    assert seed_a == seed_b == 7
    assert rng_a.random() == rng_b.random()
    assert timing_model.SEED_ENV == "LCLS_TIMING_SEED"


def test_make_rng_falls_back_to_the_default_seed(monkeypatch):
    monkeypatch.delenv("LCLS_TIMING_SEED", raising=False)

    _, seed = timing_model.make_rng()

    assert seed == timing_model.DEFAULT_SEED


def test_make_rng_rejects_a_non_integer_seed(monkeypatch):
    monkeypatch.setenv("LCLS_TIMING_SEED", "abc")

    with pytest.raises(ValueError, match="LCLS_TIMING_SEED"):
        timing_model.make_rng()


def test_random_message_masks_unused_bits_and_uses_version_1():
    rng = seeded_rng()

    for _ in range(20):
        msg = timing_model.random_message(rng)
        assert msg["version"] == 1
        assert "unused" not in msg
        vector = timing_model.pack_message(msg)
        assert (vector >> 304) & 0x1FFF == 0
        assert timing_model.unpack_message(vector) == msg
    assert timing_model.random_message(rng, version=2)["version"] == 2


def test_random_stream_never_sets_event_code_255_by_default():
    rng = seeded_rng()

    for _ in range(200):
        assert not (timing_model.random_stream(rng)["eventCodes"] >> 255) & 1
    assert any(
        (timing_model.random_stream(rng, allow_code_255=True)["eventCodes"] >> 255) & 1
        for _ in range(2000)
    )
