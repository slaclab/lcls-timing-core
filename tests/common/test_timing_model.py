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
