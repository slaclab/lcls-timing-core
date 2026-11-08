#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""WordSerializer leaf test: a latched frame is shifted out one word per advance.

Test methodology:
    Sweep: NWORDS_G in 1, 2 and 3, one compiled simulation per value.
    Stimulus: txRst is held for 3 txClk cycles. A fiducial with ready=1
        latches the frame (word k is 0x1111 * (k + 1)); NWORDS_G advances
        follow, one per cycle. A second fiducial with ready=0 latches the
        frame without raising streamReady, and a reset in mid frame clears
        the stream.
    Checks: streamReady is low after reset; the fiducial presents word 0
        with streamReady=1, streamOffset=0 and streamLast=1; each of the
        next NWORDS_G-1 advances presents the next word with streamReady
        high; advance number NWORDS_G drops streamReady.
    Timing: 10 ns txClk.
    Propagation sampling: every sample waits 2 ns past the rising edge so
        the registered outputs have settled; the registers have no TPD_G
        delay, so the margin only guards against delta-cycle ordering.
"""

from pathlib import Path

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common.regression_utils import (
    REPO_ROOT,
    env_int,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/WordSerializerWrapper.vhd"


def pack_words(nwords):
    return sum((0x1111 * (k + 1)) << (16 * k) for k in range(nwords))


async def clock_once(dut, *, fiducial=0, ready=0, advance=0):
    """Apply one cycle of stimulus and sample the outputs after the edge."""
    dut.fiducial.value = fiducial
    dut.ready.value = ready
    dut.advance.value = advance
    await sample_after_tpd(dut.txClk, propagation_time=2)
    return (
        int(dut.streamReady.value),
        int(dut.streamData.value),
        int(dut.streamOffset.value),
        int(dut.streamLast.value),
    )


@cocotb.test(timeout_time=50, timeout_unit="us")
async def wordserializer_shifts_frame(dut):
    """Frame words appear in order and streamReady drops after the last word.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    nwords = env_int("NWORDS_G", default=2)
    words = pack_words(nwords)

    dut.txRst.value = 1
    dut.fiducial.value = 0
    dut.ready.value = 0
    dut.advance.value = 0
    dut.words.value = words

    cocotb.start_soon(Clock(dut.txClk, 10, unit="ns").start(start_high=False))

    for _ in range(3):
        await RisingEdge(dut.txClk)
    dut.txRst.value = 0

    ready, _, _, _ = await clock_once(dut)
    assert ready == 0, "streamReady must be low after reset"

    ready, data, offset, last = await clock_once(dut, fiducial=1, ready=1)
    assert (ready, data, offset, last) == (1, 0x1111, 0, 1), (
        f"fiducial with ready=1 gave ready={ready} data=0x{data:04x} "
        f"offset={offset} last={last}"
    )

    for advance_number in range(1, nwords + 1):
        ready, data, offset, last = await clock_once(dut, advance=1)
        if advance_number < nwords:
            expected = 0x1111 * (advance_number + 1)
            assert (ready, data, offset, last) == (1, expected, 0, 1), (
                f"advance {advance_number} of {nwords} gave ready={ready} "
                f"data=0x{data:04x} offset={offset} last={last}, "
                f"expected word 0x{expected:04x}"
            )
        else:
            assert ready == 0, (
                f"streamReady still high on advance {advance_number} of {nwords}"
            )

    ready, _, _, _ = await clock_once(dut)
    assert ready == 0, "streamReady must stay low once the frame is exhausted"

    ready, data, _, _ = await clock_once(dut, fiducial=1, ready=0)
    assert (ready, data) == (0, 0x1111), (
        f"fiducial with ready=0 gave ready={ready} data=0x{data:04x}"
    )

    ready, data, _, _ = await clock_once(dut, fiducial=1, ready=1)
    assert (ready, data) == (1, 0x1111)
    dut.txRst.value = 1
    ready, data, _, _ = await clock_once(dut)
    dut.txRst.value = 0
    assert (ready, data) == (0, 0), (
        f"reset in mid frame left ready={ready} data=0x{data:04x}"
    )


@pytest.mark.parametrize("nwords", [1, 2, 3])
def test_WordSerializer(nwords):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.wordserializerwrapper",
        parameters={"NWORDS_G": nwords},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
