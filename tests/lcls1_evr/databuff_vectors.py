#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Shared vectors and checks for the EvrV1Databuff RAM and its test-only model.

The same stimulus and the same assertions run on the production
LCLS-I/evr/EvrV1Databuff.vhd under GHDL (test_EvrV1Databuff.py) and on the
behavioral Verilog model under Icarus (test_EvrV1DatabuffModel.py). The model
is only trusted because both simulators pass this one vector set.

The RAM writes one byte per clka cycle: byte lane addra(1:0) of word
addra(10:2) is written when wea(0) is high. Port B reads a whole 32 bit word
registered on clkb, with byte lane 0 in bits 7:0 (little-endian packing).
Words that were never written read 0.

This module holds no cocotb entrypoints. Every input is driven on a falling
edge of its own clock, so a sample taken after a rising edge never precedes
a write in the same simulation step.
"""

from cocotb.triggers import FallingEdge

# clkb edges between presenting addrb and seeing the word on doutb.
READ_LATENCY = 1

WORD_COUNT = 512
BLOCK_FIRST_WORD = 100
BLOCK_BYTES = tuple((index * 37 + 11) & 0xFF for index in range(64))


def byte_address(word, lane):
    """Byte address on port A of byte lane ``lane`` in word ``word``."""
    return (word << 2) | lane


# Byte writes as (addra, byte): a full word at 0, a word at 5 written lane by
# lane out of order, a single byte in lane 3 of word 7, the last word at 511,
# and 64 bytes that fill words 100 to 115.
WRITES = (
    (byte_address(0, 0), 0x01),
    (byte_address(0, 1), 0x02),
    (byte_address(0, 2), 0x03),
    (byte_address(0, 3), 0x04),
    (byte_address(5, 2), 0x33),
    (byte_address(5, 0), 0x11),
    (byte_address(5, 3), 0x44),
    (byte_address(5, 1), 0x22),
    (byte_address(7, 3), 0x80),
    (byte_address(511, 0), 0xDE),
    (byte_address(511, 1), 0xAD),
    (byte_address(511, 2), 0xBE),
    (byte_address(511, 3), 0xEF),
) + tuple(
    (byte_address(BLOCK_FIRST_WORD, 0) + index, value)
    for index, value in enumerate(BLOCK_BYTES)
)


def _block_words():
    words = []
    for word in range(len(BLOCK_BYTES) // 4):
        lanes = BLOCK_BYTES[4 * word:4 * word + 4]
        packed = lanes[0] | (lanes[1] << 8) | (lanes[2] << 16) | (lanes[3] << 24)
        words.append((BLOCK_FIRST_WORD + word, packed))
    return tuple(words)


# Reads as (addrb, expected word). Words 1, 6, 8, 99, 116, and 510 were
# never written and must read 0.
READS = (
    (0, 0x04030201),
    (1, 0x00000000),
    (5, 0x44332211),
    (6, 0x00000000),
    (7, 0x80000000),
    (8, 0x00000000),
    (99, 0x00000000),
) + _block_words() + (
    (116, 0x00000000),
    (510, 0x00000000),
    (511, 0xEFBEADDE),
)

# Word 10 is not used by the vectors above, so the repeated write below
# starts from an empty word.
LAST_WRITE_WORD = 10
LAST_WRITE_WRITES = (
    (byte_address(LAST_WRITE_WORD, 1), 0x77),
    (byte_address(LAST_WRITE_WORD, 0), 0x5A),
    (byte_address(LAST_WRITE_WORD, 0), 0xA5),
)
LAST_WRITE_EXPECTED = 0x000077A5


def idle_inputs(dut):
    """Park every input at 0 so nothing floats before the first write."""
    dut.wea.value = 0
    dut.addra.value = 0
    dut.dina.value = 0
    dut.addrb.value = 0


async def write_bytes(dut, writes):
    """Write each (addra, byte) with wea high for one clka cycle, back to back."""
    for address, value in writes:
        await FallingEdge(dut.clka)
        dut.addra.value = address
        dut.dina.value = value
        dut.wea.value = 1
    await FallingEdge(dut.clka)
    dut.wea.value = 0


async def read_word(dut, sample_b):
    """Return doutb after the next clkb edge, asserting it is resolvable."""
    await sample_b()
    assert dut.doutb.value.is_resolvable, f"doutb is not resolvable: {dut.doutb.value}"
    return int(dut.doutb.value)


async def check_reads(dut, sample_b, reads, log):
    """Present one address per clkb cycle, back to back, and assert each word.

    The word for the address presented before an edge shows up READ_LATENCY
    edges later, so a wrong latency makes every comparison fail instead of
    passing on a settled output.
    """
    lag = READ_LATENCY - 1
    for index in range(len(reads) + lag):
        await FallingEdge(dut.clkb)
        if index < len(reads):
            dut.addrb.value = reads[index][0]
        got = await read_word(dut, sample_b)
        if index >= lag:
            address, expected = reads[index - lag]
            assert got == expected, (
                f"word {address} read {got:#010x}, expected {expected:#010x}"
            )
    log.info(f"{len(reads)} words read back as expected")


async def run_databuff_vectors(dut, sample_b, log):
    """Write every byte of WRITES, then read and check every word of READS.

    ``sample_b`` waits for the next clkb rising edge and returns once the
    data output has settled.
    """
    idle_inputs(dut)
    await write_bytes(dut, WRITES)
    await check_reads(dut, sample_b, READS, log)


async def run_last_write_wins(dut, sample_b, log):
    """Two writes to one byte: the second value is read, its neighbour keeps its byte."""
    idle_inputs(dut)
    await write_bytes(dut, LAST_WRITE_WRITES)
    await check_reads(dut, sample_b, ((LAST_WRITE_WORD, LAST_WRITE_EXPECTED),), log)
