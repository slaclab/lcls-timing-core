#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""surf.Crc32Parallel pin: the frame CRC parameters, independent of any frame test.

Test methodology:
    Sweep: one compiled simulation of surf.Crc32Parallel with
        BYTE_WIDTH_G = 2 and crcDataWidth = 001, the settings used by
        TimingSerializer and TimingDeserializer. Four word lists are
        checked: the 62 CRC-covered words of the golden message frame, a
        single word, eight zero words, and 100 seeded random words.
    Stimulus: crcReset is pulsed for one crcClk cycle with crcDataValid low,
        then one 16-bit word is presented per cycle with crcDataValid high,
        then crcDataValid is dropped and crcOut is sampled for six more
        cycles.
    Checks: crcOut, read after the input and CRC registers have settled,
        equals (high << 16) | low from timing_model.frame_crc_words, which
        is 0x37EF4292 for the golden words; the number of cycles from the
        last word to the settled value is measured on the first list and
        is the same for every other list; crcOut holds that value on the
        following cycles.
    Timing: 10 ns crcClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registers, which update TPD_G = 1 ns after the edge, are stable.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common import timing_model
from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd

SETTLE_CYCLES = 6
GOLDEN_CRC_OUT = 0x37EF4292


def golden_covered_words():
    """Return the 62 words the serializer feeds its CRC for the golden frame."""
    msg = timing_model.default_message()
    msg["pulseId"] = 0x0123456789ABCDEF
    msg["timeStamp"] = 0xFEDCBA9876543210
    msg["beamRequest"] = 0xA5A5A5A5
    msg["bsaDone"] = 0x0F0F0F0F0F0F0F0F
    msg["control"][17] = 0xBEEF
    symbols = timing_model.message_frame(msg)
    # Alignment comma and SOF are not covered; the two CRC words are not either.
    return [data for data, _ in symbols[2:-2]]


def expected_crc(words):
    low, high = timing_model.frame_crc_words(words)
    return (high << 16) | low


async def run_sequence(dut, words):
    """Feed one word list and return crcOut sampled on each cycle after the last word."""
    dut.crcReset.value = 1
    dut.crcDataValid.value = 0
    await sample_after_tpd(dut.crcClk, propagation_time=2)
    dut.crcReset.value = 0
    for word in words:
        dut.crcIn.value = word
        dut.crcDataValid.value = 1
        await sample_after_tpd(dut.crcClk, propagation_time=2)
    dut.crcDataValid.value = 0
    samples = []
    for _ in range(SETTLE_CYCLES):
        await sample_after_tpd(dut.crcClk, propagation_time=2)
        value = dut.crcOut.value
        assert value.is_resolvable, f"crcOut carries unresolved bits: {value}"
        samples.append(int(value))
    return samples


@cocotb.test(timeout_time=100, timeout_unit="us")
async def crc32_parallel_matches_model(dut):
    """crcOut equals the model CRC for the golden, one-word, zero and random lists.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    golden = golden_covered_words()
    assert len(golden) == 62, f"golden covered word count {len(golden)}"
    assert expected_crc(golden) == GOLDEN_CRC_OUT, f"model golden CRC 0x{expected_crc(golden):08X}"

    word_lists = {
        "golden": golden,
        "one word": [0xB5FD],
        "eight zero words": [0x0000] * 8,
        "100 random words": [rng.getrandbits(16) for _ in range(100)],
    }

    dut.crcReset.value = 0
    dut.crcDataValid.value = 0
    dut.crcDataWidth.value = 0b001
    dut.crcIn.value = 0
    clock_task = cocotb.start_soon(Clock(dut.crcClk, 10, unit="ns").start(start_high=False))
    for _ in range(3):
        await sample_after_tpd(dut.crcClk, propagation_time=2)

    latency = None
    for name, words in word_lists.items():
        expected = expected_crc(words)
        samples = await run_sequence(dut, words)
        assert expected in samples, (
            f"{name}: crcOut never reached 0x{expected:08X}, samples "
            + ", ".join(f"0x{sample:08X}" for sample in samples)
        )
        settled_at = samples.index(expected)
        if latency is None:
            latency = settled_at
            dut._log.info(f"crcOut settles {latency + 1} cycles after the last word is presented")
        assert settled_at == latency, f"{name}: settled after {settled_at} samples, first list took {latency}"
        assert all(sample == expected for sample in samples[settled_at:]), (
            f"{name}: crcOut moved after settling: " + ", ".join(f"0x{sample:08X}" for sample in samples)
        )

    clock_task.cancel()


def test_crc32_parallel():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="surf.crc32parallel",
        parameters={"BYTE_WIDTH_G": 2},
    )
