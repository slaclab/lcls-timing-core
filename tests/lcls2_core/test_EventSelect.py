#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EventSelect leaf test: rateSel follows the criteria of the selected rate type.

Test methodology:
    Sweep: rateType "00", "01", "10" and "11" with every valid index. The
        default TPD_G of 1 ns is kept. fxRateSel runs 0 to 9, acRateSel 0
        to 5, acTS 1 to 6, seqword 0 to 17 with seqbit 0 to 15; seqword 18,
        19 and 63 cover the out-of-range side.
    Stimulus: the fixed and AC rate vectors use a one-hot, an inverted
        one-hot and an alternating pattern. The 18 sequence words are 16-bit
        values with word 0 equal to 0x0001 and word 17 equal to 0x8000 so
        the lowest and highest valid cell each drive both a 1 and a 0.
    Checks: modes "00" and "01" match the selected bit combinationally;
        mode "01" is 0 when the mask bit for acTS is clear; mode "10"
        returns bit seqbit of word seqword one clock after the select
        changes and 0 for seqword 18 and above; mode "11" is 0.
    Timing: 10 ns clk; the combinational modes settle in 1 ns.
    Propagation sampling: the registered sequence word updates after TPD_G
        (1 ns), so mode "10" samples 2 ns past the rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer

from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/EventSelectWrapper.vhd"

FIXED_DEPTH = 10
AC_DEPTH = 6
SEQ_WORDS = 18

RATE_PATTERNS = (0x2AA, 0x155, 0x3FF, 0x000)


def bit(value, index):
    return (value >> index) & 1


def seq_word(index):
    if index == 0:
        return 0x0001
    if index == SEQ_WORDS - 1:
        return 0x8000
    return (0x9E37 * (index + 3) + index) & 0xFFFF


def pack_seq():
    return sum(seq_word(k) << (16 * k) for k in range(SEQ_WORDS))


async def settle():
    """Combinational outputs settle within one nanosecond."""
    await Timer(1, unit="ns")


def init_inputs(dut):
    dut.rateType.value = 0
    dut.fxRateSel.value = 0
    dut.acRateSel.value = 0
    dut.acTSmask.value = 0
    dut.seqword.value = 0
    dut.seqbit.value = 0
    dut.fixedRate.value = 0
    dut.acRate.value = 0
    dut.acTS.value = 1
    dut.expSeq.value = pack_seq()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def eventselect_fixed_rate(dut):
    """Mode "00" returns fixedRate(fxRateSel) for every valid index."""
    init_inputs(dut)
    dut.rateType.value = 0
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))

    seen = set()
    for pattern in (*(1 << k for k in range(FIXED_DEPTH)),
                    *(0x3FF ^ (1 << k) for k in range(FIXED_DEPTH)),
                    *RATE_PATTERNS):
        dut.fixedRate.value = pattern
        for index in range(FIXED_DEPTH):
            dut.fxRateSel.value = index
            await settle()
            expected = bit(pattern, index)
            seen.add(expected)
            assert int(dut.rateSel.value) == expected, (
                f"fixedRate=0x{pattern:03x} fxRateSel={index}: "
                f"rateSel={int(dut.rateSel.value)}, expected {expected}"
            )
    assert seen == {0, 1}, "fixed rate sweep never saw both output values"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def eventselect_ac_rate(dut):
    """Mode "01" masks acRate(acRateSel) with acTSmask(acTS - 1)."""
    init_inputs(dut)
    dut.rateType.value = 1
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))

    seen = set()
    for mask in (0x2A, 0x15, 0x3F, 0x00):
        dut.acTSmask.value = mask
        for rate in (0x2A, 0x15, 0x3F, 0x01, 0x20):
            dut.acRate.value = rate
            for ts in range(1, AC_DEPTH + 1):
                dut.acTS.value = ts
                for index in range(AC_DEPTH):
                    dut.acRateSel.value = index
                    await settle()
                    expected = bit(rate, index) if bit(mask, ts - 1) else 0
                    seen.add(expected)
                    assert int(dut.rateSel.value) == expected, (
                        f"mask=0x{mask:02x} acRate=0x{rate:02x} acTS={ts} "
                        f"acRateSel={index}: rateSel={int(dut.rateSel.value)}, "
                        f"expected {expected}"
                    )
    assert seen == {0, 1}, "AC rate sweep never saw both output values"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def eventselect_sequence_bit(dut):
    """Mode "10" returns bit seqbit of word seqword, 0 beyond the last word.

    Propagation sampling: the sequence word register updates after TPD_G, so
    each sample is taken 2 ns after the rising edge that follows the change.
    """
    init_inputs(dut)
    dut.rateType.value = 2
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))
    await sample_after_tpd(dut.clk, propagation_time=2)

    seen = set()
    for word in range(SEQ_WORDS):
        dut.seqword.value = word
        for index in range(16):
            dut.seqbit.value = index
            await sample_after_tpd(dut.clk, propagation_time=2)
            expected = bit(seq_word(word), index)
            seen.add(expected)
            assert int(dut.rateSel.value) == expected, (
                f"seqword={word} seqbit={index}: rateSel={int(dut.rateSel.value)}, "
                f"expected {expected}"
            )
    assert seen == {0, 1}, "sequence sweep never saw both output values"

    for word in (SEQ_WORDS, SEQ_WORDS + 1, 63):
        dut.seqword.value = word
        for index in (0, 15):
            dut.seqbit.value = index
            await sample_after_tpd(dut.clk, propagation_time=2)
            assert int(dut.rateSel.value) == 0, (
                f"seqword={word} seqbit={index} is out of range but rateSel is high"
            )


@cocotb.test(timeout_time=100, timeout_unit="us")
async def eventselect_reserved_mode(dut):
    """Mode "11" is 0 even with every input bit high."""
    init_inputs(dut)
    dut.rateType.value = 3
    dut.fixedRate.value = 0x3FF
    dut.acRate.value = 0x3F
    dut.acTSmask.value = 0x3F
    dut.expSeq.value = (1 << (16 * SEQ_WORDS)) - 1
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start(start_high=False))
    await sample_after_tpd(dut.clk, propagation_time=2)
    assert int(dut.rateSel.value) == 0, "rateType 11 must give rateSel 0"


def test_EventSelect():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.eventselectwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
