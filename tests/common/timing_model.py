#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reference model of the LCLS-II timing frame and the TimingMessageType.

The model is written from an independent reading of
LCLS-II/core/rtl/TimingPkg.vhd (``toSlv`` and ``toTimingMessageType``) and of
the serializer, deserializer and frame receiver state machines. It uses only
the Python standard library, so it runs in the common test leg and can be
imported by path from every datapath test.

Cross-check outcome:

* IBIC 2023 paper TH1I01, Table 2, lists the timing pattern fields and their
  sizes and states that the frame is validated by a 32-bit CRC
  (https://proceedings.jacow.org/ibic2023/papers/th1i01.pdf). The field sizes
  agree with TimingPkg.vhd. The paper gives no bit order, K-character values,
  CRC polynomial or byte order.
* The slaclab/pgp-gen3-pcie-card copy of TimingPkg.vhd and
  TimingDeserializer.vhd carries identical K-characters and the same 944-bit
  message size. It is the same code lineage, so it shows consistency across
  deployed firmware rather than an independent derivation.
* slaclab/l2si-core XpmRxLink.vhd is an independent consumer that tests the
  same SOF and EOF characters.
* The production RTL under GHDL: model-encoded frames are decoded by the
  unmodified TimingFrameRx.
* The LCLS-II Timing System Engineering Specifications could not be read
  (SLAC login required), so the K-character values, CRC parameters and byte
  order are derived from the shipped VHDL only.

Wire grammar on the 16-bit link, one symbol per clock, ``data`` is
{high byte, low byte} and ``dataK`` is {K of high byte, K of low byte}::

    idle      0xB5BC / 01   D21.5, K28.5
    align     0xB53C / 01   D21.5, K28.1, once before the start of frame
    SOF       0xB5F7 / 01   D21.5, K23.7
    per segment:
      SOS     (stream_id << 12) | (last << 7) | offset   / 00
      words   16-bit data words, LSW first for multiword fields / 00
      EOS     0xB51C / 01   D21.5, K28.0
    EOF       0xB5FD / 01   D21.5, K29.7
    CRC       low 16 bits, then high 16 bits / 00

The CRC-32 covers the SOS words, the data words, the EOS words and the EOF
word. It does not cover the commas or the SOF.
"""

from __future__ import annotations

import os
import random
import zlib
from typing import NamedTuple

D_102 = 0x4A
D_215 = 0xB5
K_COM = 0xBC
K_SOF = 0xF7
K_EOF = 0xFD
K_280 = 0x1C
K_281 = 0x3C
K_EOS = K_280

TIMING_MESSAGE_BITS = 944
TIMING_MESSAGE_WORDS = 59
TIMING_MESSAGE_VERSION = 0x0001

IDLE_SYMBOL = ((D_215 << 8) | K_COM, 0b01)
ALIGN_SYMBOL = ((D_215 << 8) | K_281, 0b01)
SOF_SYMBOL = ((D_215 << 8) | K_SOF, 0b01)
EOS_SYMBOL = ((D_215 << 8) | K_EOS, 0b01)
EOF_SYMBOL = ((D_215 << 8) | K_EOF, 0b01)

# (name, element width in bits, element count) in the order TimingPkg
# toSlv packs them, least significant bits first. The "unused" entry is
# written as zero by toSlv and skipped by toTimingMessageType.
MESSAGE_FIELDS = (
    ("version", 16, 1),
    ("pulseId", 64, 1),
    ("timeStamp", 64, 1),
    ("fixedRates", 10, 1),
    ("acRates", 6, 1),
    ("acTimeSlot", 3, 1),
    ("acTimeSlotPhase", 12, 1),
    ("resync", 1, 1),
    ("beamRequest", 32, 1),
    ("beamEnergy", 16, 4),
    ("photonWavelen", 16, 2),
    ("unused", 13, 1),
    ("syncStatus", 1, 1),
    ("mpsValid", 1, 1),
    ("bcsFault", 1, 1),
    ("mpsLimit", 16, 1),
    ("mpsClass", 4, 16),
    ("bsaInit", 64, 1),
    ("bsaActive", 64, 1),
    ("bsaAvgDone", 64, 1),
    ("bsaDone", 64, 1),
    ("control", 16, 18),
)


def field_layout(table) -> dict[str, tuple[int, int, int]]:
    """Map each field name to (lsb offset, element width, element count)."""
    layout = {}
    offset = 0
    for name, width, count in table:
        layout[name] = (offset, width, count)
        offset += width * count
    return layout


def _table_bits(table) -> int:
    return sum(width * count for _, width, count in table)


def pack_fields(table, values) -> int:
    """Pack a field dictionary into an integer, element 0 at the lowest bits.

    Array fields (count above 1) are lists. A missing or unknown key, a
    list of the wrong length, or a value wider than its field raises
    ValueError.
    """
    layout = field_layout(table)
    unknown = sorted(set(values) - set(layout))
    if unknown:
        raise ValueError(f"unknown field(s): {', '.join(unknown)}")
    missing = [name for name in layout if name not in values]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")

    result = 0
    for name, (offset, width, count) in layout.items():
        value = values[name]
        if count == 1:
            elements = [value]
        else:
            elements = list(value)
            if len(elements) != count:
                raise ValueError(f"field {name} needs {count} elements, got {len(elements)}")
        for index, element in enumerate(elements):
            if not isinstance(element, int) or element < 0 or element >> width:
                raise ValueError(f"field {name} element {index} value {element!r} does not fit in {width} bits")
            result |= element << (offset + index * width)
    return result


def unpack_fields(table, value: int) -> dict:
    """Split an integer into a field dictionary, the inverse of pack_fields."""
    if value < 0 or value >> _table_bits(table):
        raise ValueError(f"value does not fit in {_table_bits(table)} bits")
    result = {}
    for name, (offset, width, count) in field_layout(table).items():
        mask = (1 << width) - 1
        elements = [(value >> (offset + index * width)) & mask for index in range(count)]
        result[name] = elements[0] if count == 1 else elements
    return result


def default_message() -> dict:
    """Return the equivalent of TIMING_MESSAGE_INIT_C (mpsClass is all ones)."""
    message = {}
    for name, width, count in MESSAGE_FIELDS:
        if name == "unused":
            continue
        fill = 0xF if name == "mpsClass" else 0
        message[name] = fill if count == 1 else [fill] * count
    message["version"] = TIMING_MESSAGE_VERSION
    return message


def pack_message(msg: dict) -> int:
    """Return the 944-bit vector TimingPkg toSlv produces for a message."""
    values = {key: value for key, value in msg.items() if key != "unused"}
    values["unused"] = 0
    return pack_fields(MESSAGE_FIELDS, values)


def unpack_message(value: int) -> dict:
    """Return the message dictionary toTimingMessageType reads from 944 bits."""
    message = unpack_fields(MESSAGE_FIELDS, value)
    del message["unused"]
    return message


def message_words(msg: dict) -> list[int]:
    """Return the 59 wire words, word k is bits 16k+15 downto 16k."""
    vector = pack_message(msg)
    return [(vector >> (16 * k)) & 0xFFFF for k in range(TIMING_MESSAGE_WORDS)]


def crc32_bitwise(data: bytes, init: int = 0xFFFFFFFF) -> int:
    """Reflected CRC-32 (polynomial 0x04C11DB7, reflected 0xEDB88320).

    The result is complemented, so it equals zlib.crc32 for the default init.
    """
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
    return crc ^ 0xFFFFFFFF


def frame_crc_words(words) -> tuple[int, int]:
    """Return (low16, high16) as sent on the wire after the EOF word.

    ``words`` are the CRC-covered 16-bit words in transmission order. The
    bytes are fed high byte first. The serializer sends the byte swap of the
    standard CRC-32, low 16 bits first.
    """
    data = b"".join(word.to_bytes(2, "big") for word in words)
    crc = crc32_bitwise(data)
    assert crc == zlib.crc32(data), "bitwise CRC disagrees with zlib"
    wire = int.from_bytes(crc.to_bytes(4, "little"), "big")
    return wire & 0xFFFF, wire >> 16


class Segment(NamedTuple):
    """One frame segment: a stream id, its words, and the SOS fields."""

    stream_id: int
    words: tuple
    offset: int = 0
    last: int = 1


def encode_frame(segments) -> list[tuple[int, int]]:
    """Encode segments into (data16, dataK2) symbols.

    The result is the alignment comma, SOF, then SOS, words and EOS for each
    segment, then EOF and the two CRC words. Idle symbols are not appended.
    """
    symbols = [ALIGN_SYMBOL, SOF_SYMBOL]
    covered = []
    for segment in segments:
        stream_id, words, offset, last = segment
        if not 0 <= stream_id <= 15:
            raise ValueError(f"stream id {stream_id} is outside 0 to 15")
        if not 0 <= offset <= 0x7F:
            raise ValueError(f"offset {offset} is outside 0 to 127")
        if last not in (0, 1):
            raise ValueError(f"last {last} must be 0 or 1")
        for index, word in enumerate(words):
            if not isinstance(word, int) or not 0 <= word <= 0xFFFF:
                raise ValueError(f"word {index} value {word!r} is not a 16-bit integer")
        sos = (stream_id << 12) | (last << 7) | offset
        symbols.append((sos, 0b00))
        symbols.extend((word, 0b00) for word in words)
        symbols.append(EOS_SYMBOL)
        covered.append(sos)
        covered.extend(words)
        covered.append(EOS_SYMBOL[0])
    covered.append(EOF_SYMBOL[0])
    low, high = frame_crc_words(covered)
    symbols.append(EOF_SYMBOL)
    symbols.append((low, 0b00))
    symbols.append((high, 0b00))
    return symbols


def message_frame(msg: dict, stream_id: int = 0) -> list[tuple[int, int]]:
    """Encode one timing message as a single-segment frame."""
    return encode_frame([Segment(stream_id, tuple(message_words(msg)))])


def idle_symbols(count: int) -> list[tuple[int, int]]:
    """Return ``count`` idle comma symbols."""
    return [IDLE_SYMBOL] * count


class DecodedFrame(NamedTuple):
    """Result of decode_frame: segments, CRC verdict and the received CRC words."""

    segments: list
    crc_ok: bool
    crc_words: tuple


def decode_frame(symbols) -> DecodedFrame:
    """Decode (data16, dataK2) symbols into segments and a CRC verdict.

    Leading idle and alignment commas are skipped and symbols after the CRC
    words are ignored. A structural problem raises ValueError naming the
    symbol index and value; a CRC mismatch is reported through ``crc_ok``.
    """
    symbols = list(symbols)
    try:
        start = symbols.index(SOF_SYMBOL)
    except ValueError:
        raise ValueError("no SOF symbol 0xB5F7/01 in the symbol list") from None

    def fetch(index, what):
        if index >= len(symbols):
            raise ValueError(f"truncated frame: ran out of symbols at index {index} while reading {what}")
        return symbols[index]

    segments = []
    covered = []
    index = start + 1
    end_of_frame = False
    while index < len(symbols) and not end_of_frame:
        data, data_k = symbols[index]
        index += 1
        if (data, data_k) == EOF_SYMBOL:
            covered.append(data)
            end_of_frame = True
            continue
        if data_k != 0b00:
            raise ValueError(f"expected SOS or EOF at index {index - 1}, got 0x{data:04X}/{data_k:02b}")
        covered.append(data)
        words = []
        end_of_segment = False
        while index < len(symbols) and not end_of_segment:
            word, word_k = symbols[index]
            if (word, word_k) == EOS_SYMBOL:
                covered.append(word)
                end_of_segment = True
            elif word_k != 0b00:
                raise ValueError(
                    f"K-character 0x{word:04X}/{word_k:02b} inside a segment at index {index}"
                )
            else:
                words.append(word)
                covered.append(word)
            index += 1
        if not end_of_segment:
            raise ValueError(
                f"truncated frame: no EOS after the segment opened by SOS 0x{data:04X} (index {index})"
            )
        segments.append(Segment(data >> 12, tuple(words), data & 0x7F, (data >> 7) & 1))
    if not end_of_frame:
        raise ValueError(f"truncated frame: no EOF symbol before index {index}")

    low, low_k = fetch(index, "CRC low word")
    high, high_k = fetch(index + 1, "CRC high word")
    if low_k != 0b00 or high_k != 0b00:
        raise ValueError(f"CRC words at index {index} carry a K-character: {low_k:02b} {high_k:02b}")
    return DecodedFrame(segments, frame_crc_words(covered) == (low, high), (low, high))


# Extensions: raw 512-bit TimingExtensionMessageType segments on stream ids 1
# to 15, which is what TimingFrameRx compiles.
TIMING_EXTENSION_BITS = 512
TIMING_EXTENSION_WORDS = 32


def extension_segment(stream_id: int, data: int) -> Segment:
    """Return a 32-word segment holding ``data``, least significant word first."""
    if not 1 <= stream_id <= 15:
        raise ValueError(f"extension stream id {stream_id} is outside 1 to 15")
    if not isinstance(data, int) or data < 0 or data >> TIMING_EXTENSION_BITS:
        raise ValueError(f"extension data does not fit in {TIMING_EXTENSION_BITS} bits")
    words = tuple((data >> (16 * k)) & 0xFFFF for k in range(TIMING_EXTENSION_WORDS))
    return Segment(stream_id, words)


def extension_data(words) -> int:
    """Return the 512-bit value TimingFrameRx presents for a segment.

    Measured on the production receiver: each segment word is shifted into
    the top of a 32-word register, so a segment of n words lands with its
    word 0 at word index 32 - n and the last word at index 31. A 20-word
    segment therefore occupies words 12 to 31. The words below it keep
    whatever earlier frames shifted in; this model returns zero for them,
    which is the value after reset.
    """
    words = list(words)
    if not 1 <= len(words) <= TIMING_EXTENSION_WORDS:
        raise ValueError(f"an extension segment has 1 to {TIMING_EXTENSION_WORDS} words, got {len(words)}")
    first = TIMING_EXTENSION_WORDS - len(words)
    return sum(word << (16 * (first + k)) for k, word in enumerate(words))


# Default extension layout of default/TimingExtnPkg.vhd (ExptMessageType).
EXPT_MESSAGE_BITS = 320
EXPT_STREAM_ID = 2
EXPT_FIELDS = (
    ("baseRateSince1Hz", 32, 1),
    ("baseRateSinceTM", 32, 1),
    ("irigTimeCode", 256, 1),
)


def pack_expt(values: dict) -> int:
    """Pack an ExptMessageType dictionary into 320 bits, least significant first.

    default/TimingExtnPkg.vhd is not loaded by any ruckus.tcl, so it is
    outside the CI import set and this layout is verified only through a
    test-only wrapper that is given that file explicitly.
    """
    return pack_fields(EXPT_FIELDS, values)


def unpack_expt(value: int) -> dict:
    """Split a 320-bit ExptMessageType vector into its fields."""
    return unpack_fields(EXPT_FIELDS, value)


# toSlvNoBsa order: the control(16) word appears again as the modifier word
# between photonWavelen and mpsLimit, as the RTL does.
TIMING_MESSAGE_BITS_NO_BSA = 672
MESSAGE_NO_BSA_FIELDS = (
    ("pulseId", 64, 1),
    ("timeStamp", 64, 1),
    ("fixedRates", 10, 1),
    ("acRates", 6, 1),
    ("acTimeSlot", 3, 1),
    ("acTimeSlotPhase", 12, 1),
    ("resync", 1, 1),
    ("beamRequest", 32, 1),
    ("beamEnergy", 16, 4),
    ("photonWavelen", 16, 2),
    ("modifier", 16, 1),
    ("mpsLimit", 16, 1),
    ("mpsClass", 4, 16),
    ("control", 16, 18),
)


def pack_message_no_bsa(msg: dict) -> int:
    """Return the 672-bit vector toSlvNoBsa produces for a message."""
    values = {name: msg[name] for name, _, _ in MESSAGE_NO_BSA_FIELDS if name != "modifier"}
    values["modifier"] = msg["control"][16]
    return pack_fields(MESSAGE_NO_BSA_FIELDS, values)


def unpack_message_no_bsa(value: int) -> dict:
    """Return the fields toTimingMessageType assigns for a 672-bit vector.

    version, syncStatus, mpsValid, bcsFault and the bsa fields are never
    assigned on this path. The modifier word is overwritten by control(16)
    from the trailing control array, so it is dropped.
    """
    message = unpack_fields(MESSAGE_NO_BSA_FIELDS, value)
    del message["modifier"]
    return message


TIMING_DATABUFF_BITS = 416
DATABUFF_FIELDS = (
    ("dtype", 16, 1),
    ("version", 16, 1),
    ("dmod", 192, 1),
    ("epicsTime", 64, 1),
    ("edefAvgDn", 32, 1),
    ("edefMinor", 32, 1),
    ("edefMajor", 32, 1),
    ("edefInit", 32, 1),
)

TIMING_STREAM_BITS = 704
STREAM_FIELDS = (
    ("pulseId", 32, 1),
    ("eventCodes", 256, 1),
    *DATABUFF_FIELDS,
)


def pack_databuff(dbuff: dict) -> int:
    """Return the 416-bit vector TimingPkg toSlv produces for a data buffer."""
    return pack_fields(DATABUFF_FIELDS, dbuff)


def unpack_databuff(value: int) -> dict:
    """Split a 416-bit data buffer vector into its fields."""
    return unpack_fields(DATABUFF_FIELDS, value)


def pack_stream(stream: dict) -> int:
    """Return the 704-bit TimingStreamType vector.

    ``stream`` has keys pulseId, eventCodes (a 256-bit integer mask) and
    dbuff (a data buffer dictionary).
    """
    unknown = sorted(set(stream) - {"pulseId", "eventCodes", "dbuff"})
    if unknown:
        raise ValueError(f"unknown stream field(s): {', '.join(unknown)}")
    if "dbuff" not in stream:
        raise ValueError("missing stream field: dbuff")
    values = {name: stream[name] for name in ("pulseId", "eventCodes") if name in stream}
    values.update(stream["dbuff"])
    return pack_fields(STREAM_FIELDS, values)


def unpack_stream(value: int) -> dict:
    """Split a 704-bit TimingStreamType vector into pulseId, eventCodes and dbuff."""
    fields = unpack_fields(STREAM_FIELDS, value)
    return {
        "pulseId": fields.pop("pulseId"),
        "eventCodes": fields.pop("eventCodes"),
        "dbuff": fields,
    }


# LCLS-I stream. Each 16-bit symbol carries two byte lanes: the high lane
# (data 15:8, dataK 1) holds data-buffer bytes and framing K-characters, the
# low lane (data 7:0, dataK 0) holds the idle comma, pulse-id bits and event
# codes. Symbol positions are relative to the K28.0 start symbol:
#
#     0            0x1C00 / 10   K28.0, start of the data buffer
#     2 + 2k       data-buffer byte k, k = 0..51, least significant byte first
#     105          0x3CBC / 11   K28.1 and K28.5, end of the data buffer
#     106 + 2j     0x0070 or 0x0071 pulse-id bit j, most significant first
#     170          0x007D        event-code block marker
#     172 + 2n     0x00nn        event code n, present when the code is set
#
# The odd slots between are the comma 0x00BC / 01. An unset event-code slot is
# 0x0000 / 00, which is what TimingStreamTx sends (TimingStreamTx.vhd lines 88
# to 96 set the default x"00" with dataK(0) = 0 on every other clock, and
# lines 137 to 146 replace it only when the event code bit is set). TimingStreamRx reads any low-lane data symbol outside a
# comma as an event code, so the receiver sets event code 0 for every frame:
# an unset slot, a data-buffer byte symbol and the idle fill all read as code
# 0. Event code 0 therefore cannot be sent as "clear" by the hardware pair, and
# decode_lcls1_frame reports it as set for every frame that has an unset slot.
# The first symbol is 0x1C00 / 10 when the idle symbol before the fiducial was
# 0x0000 / 00 (TimingStreamTx lets the idle default show through the low lane
# of the start symbol (lines 101 to 108); the other phase gives 0x1CBC / 11.
LCLS1_FRAME_LEN = 14000
LCLS1_START_SYMBOL = (0x1C00, 0b10)
LCLS1_END_SYMBOL = (0x3CBC, 0b11)
LCLS1_COMMA_SYMBOL = (0x00BC, 0b01)
LCLS1_MARKER_SYMBOL = (0x007D, 0b00)
LCLS1_UNSET_SYMBOL = (0x0000, 0b00)
LCLS1_DATABUFF_BYTES = TIMING_DATABUFF_BITS // 8
LCLS1_END_INDEX = 2 + 2 * (LCLS1_DATABUFF_BYTES - 1) + 1
LCLS1_PULSE_INDEX = LCLS1_END_INDEX + 1
LCLS1_MARKER_INDEX = LCLS1_PULSE_INDEX + 2 * 32
LCLS1_CODE_INDEX = LCLS1_MARKER_INDEX + 2


class Lcls1Frame(NamedTuple):
    """A decoded LCLS-I frame: pulse id, event-code mask and data buffer dictionary."""

    pulse_id: int
    event_codes: int
    databuff: dict


def encode_lcls1_frame(pulse_id: int, event_codes: int, databuff: dict) -> list[tuple[int, int]]:
    """Encode one LCLS-I frame into (data16, dataK2) symbols, 684 symbols long.

    The caller pads with lcls1_idle_symbols up to LCLS1_FRAME_LEN; the idle
    pattern continues the frame's alternation when it starts at phase 1.
    """
    if not isinstance(pulse_id, int) or pulse_id < 0 or pulse_id >> 32:
        raise ValueError(f"pulse id {pulse_id!r} does not fit in 32 bits")
    if not isinstance(event_codes, int) or event_codes < 0 or event_codes >> 256:
        raise ValueError("event codes must be a 256-bit mask")
    packed = pack_databuff(databuff)

    symbols = [LCLS1_START_SYMBOL, LCLS1_COMMA_SYMBOL]
    # TimingStreamTx.vhd lines 110 to 125: one byte every other clock, least significant first.
    for k in range(LCLS1_DATABUFF_BYTES):
        symbols.append((((packed >> (8 * k)) & 0xFF) << 8, 0b00))
        if k < LCLS1_DATABUFF_BYTES - 1:
            symbols.append(LCLS1_COMMA_SYMBOL)
    symbols.append(LCLS1_END_SYMBOL)
    for bit in range(31, -1, -1):
        symbols.append((0x70 | ((pulse_id >> bit) & 1), 0b00))
        symbols.append(LCLS1_COMMA_SYMBOL)
    symbols.append(LCLS1_MARKER_SYMBOL)
    symbols.append(LCLS1_COMMA_SYMBOL)
    # TimingStreamTx.vhd lines 137 to 146: slot n is the code when its bit is set, else 0x0000 / 00.
    for code in range(256):
        symbols.append((code, 0b00) if (event_codes >> code) & 1 else LCLS1_UNSET_SYMBOL)
        symbols.append(LCLS1_COMMA_SYMBOL)
    return symbols


def lcls1_idle_symbols(count: int, start_phase: int = 0) -> list[tuple[int, int]]:
    """Return ``count`` idle symbols alternating the comma and 0x0000 / 00."""
    pattern = (LCLS1_COMMA_SYMBOL, (0x0000, 0b00))
    return [pattern[(start_phase + k) % 2] for k in range(count)]


def decode_lcls1_frame(symbols) -> Lcls1Frame:
    """Decode an LCLS-I frame by K-character framing, as TimingStreamRx does.

    The frame starts at the first K28.0 on the high lane. Every symbol after
    the marker whose low lane is data (dataK 0 low) sets the event code named
    by its low byte, so a 0x0000 / 00 symbol sets event code 0 exactly as the
    receiver does. A missing start, end or marker raises ValueError.
    """
    symbols = list(symbols)
    start = next(
        (i for i, (data, data_k) in enumerate(symbols) if data_k & 0b10 and data >> 8 == K_280),
        None,
    )
    if start is None:
        raise ValueError("no K28.0 start symbol on the high lane")

    def at(offset):
        index = start + offset
        if index >= len(symbols):
            raise ValueError(f"truncated LCLS-I frame: no symbol at index {index}")
        return symbols[index]

    end_data, end_k = at(LCLS1_END_INDEX)
    if not (end_k & 0b10 and end_data >> 8 in (K_281, K_COM)):
        raise ValueError(
            f"no K28.1 or K28.5 end of data buffer at index {start + LCLS1_END_INDEX}: "
            f"0x{end_data:04X}/{end_k:02b}"
        )
    packed = 0
    for k in range(LCLS1_DATABUFF_BYTES):
        data, data_k = at(2 + 2 * k)
        if data_k & 0b10:
            raise ValueError(f"K-character in data-buffer byte {k}: 0x{data:04X}/{data_k:02b}")
        packed |= (data >> 8) << (8 * k)

    pulse_id = 0
    for j in range(32):
        data, data_k = at(LCLS1_PULSE_INDEX + 2 * j)
        if data_k & 0b01 or data & 0xFF not in (0x70, 0x71):
            raise ValueError(f"pulse-id bit {j} is not 0x70 or 0x71: 0x{data:04X}/{data_k:02b}")
        pulse_id = (pulse_id << 1) | (data & 1)

    marker_index = start + LCLS1_MARKER_INDEX
    if marker_index >= len(symbols) or symbols[marker_index] != LCLS1_MARKER_SYMBOL:
        raise ValueError(f"no 0x007D event-code marker at index {start + LCLS1_MARKER_INDEX}")
    event_codes = 0
    for data, data_k in symbols[start + LCLS1_MARKER_INDEX + 1:]:
        if not data_k & 0b01:
            event_codes |= 1 << (data & 0xFF)
    return Lcls1Frame(pulse_id, event_codes, unpack_databuff(packed))


# Seeded randomness: every seeded test takes its generator from make_rng so a
# failure replays exactly with the logged seed.
SEED_ENV = "LCLS_TIMING_SEED"
DEFAULT_SEED = 20261107


def make_rng(default: int = DEFAULT_SEED) -> tuple[random.Random, int]:
    """Return (generator, seed). LCLS_TIMING_SEED overrides ``default``."""
    raw = os.environ.get(SEED_ENV)
    if raw is None:
        seed = default
    else:
        try:
            seed = int(raw.strip())
        except ValueError:
            raise ValueError(f"{SEED_ENV} must be an integer, got {raw!r}") from None
    return random.Random(seed), seed


def _random_fields(rng: random.Random, table, skip=()) -> dict:
    values = {}
    for name, width, count in table:
        if name in skip:
            continue
        elements = [rng.getrandbits(width) for _ in range(count)]
        values[name] = elements[0] if count == 1 else elements
    return values


def random_message(rng: random.Random, *, version: int = TIMING_MESSAGE_VERSION) -> dict:
    """Return a random message with the unused bits absent and a fixed version."""
    message = _random_fields(rng, MESSAGE_FIELDS, skip=("unused", "version"))
    message["version"] = version
    return message


def random_databuff(rng: random.Random) -> dict:
    """Return a random data buffer dictionary."""
    return _random_fields(rng, DATABUFF_FIELDS)


def random_stream(rng: random.Random, *, allow_code_255: bool = False) -> dict:
    """Return a random LCLS-I stream with a sparse event-code mask.

    TimingStreamTx never transmits event code 255, so bit 255 stays clear
    unless ``allow_code_255`` is set.
    """
    top = 256 if allow_code_255 else 255
    codes = 0
    for _ in range(rng.randrange(0, 40)):
        codes |= 1 << rng.randrange(top)
    return {
        "pulseId": rng.getrandbits(32),
        "eventCodes": codes,
        "dbuff": random_databuff(rng),
    }
