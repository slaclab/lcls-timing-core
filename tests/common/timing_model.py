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
