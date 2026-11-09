#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2FromV1 test: the LCLS-I stream maps onto an LCLS-II message as the model says.

Test methodology:
    Sweep: disable 1 and 0; strobe high for one cycle and low for 20 cycles
        while the inputs change; the destination rule with dmod(61) and
        dmod(60) clear, set alone and set together, and dmod(83) clear and
        set; fields that the entity never assigns after a copy with disable
        high; 50 seeded random streams with disable low.
    Stimulus: the 704-bit stream and the 944-bit message are packed with
        tests.common.timing_model; strobe is pulsed for one cycle and the
        inputs change right after a rising edge. The random run draws its
        seed from tests.common.timing_model.make_rng, logs it, and honors
        LCLS_TIMING_SEED.
    Checks: timingOut equals the message held by evr_model.from_v1 on every
        sampled clock, field for field, and changes only on a strobe. With
        disable high it equals the input message. The destination values are
        also stated directly. Fields the entity does not assign keep their
        previous value, asserted as observed, intent unconfirmed.
    Timing: 10 ns clk; inputs change right after a rising edge.
    Propagation sampling: the output register updates on the rising edge, so
        timingOut is sampled 2 ns after the rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer

from tests.common import evr_model, timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2FromV1Wrapper.vhd"

CLOCK_NS = 10
IDLE_CYCLES = 20
RANDOM_STREAMS = 50


def blank_stream(**dbuff):
    values = {name: 0 for name, _, _ in timing_model.DATABUFF_FIELDS}
    values.update(dbuff)
    return {"pulseId": 0, "eventCodes": 0, "dbuff": values}


async def start_clock(dut):
    return cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start(start_high=False))


class Checker:
    """Drives the wrapper one clock at a time and keeps the message the entity should hold.

    The output register keeps its value from one entrypoint to the next, so
    the expected message starts from whatever the output reads at the start,
    which must be resolvable.
    """

    def __init__(self, dut):
        self.dut = dut
        assert dut.timingOut.value.is_resolvable, "timingOut carries unresolved bits at the start"
        self.expected = timing_model.unpack_message(int(dut.timingOut.value))
        self.steps = 0

    async def step(self, disable, strobe, msg, stream):
        dut = self.dut
        dut.disable.value = disable
        dut.strobe.value = strobe
        dut.message.value = timing_model.pack_message(msg)
        dut.stream.value = timing_model.pack_stream(stream)
        await sample_after_tpd(dut.clk, propagation_time=2)
        if strobe:
            self.expected = msg if disable else evr_model.from_v1(stream, self.expected)
        assert dut.timingOut.value.is_resolvable, f"timingOut carries unresolved bits at step {self.steps}"
        got = timing_model.unpack_message(int(dut.timingOut.value))
        assert got == self.expected, (
            f"step {self.steps} (disable {disable} strobe {strobe}): fields differing from the model: "
            f"{sorted(name for name in got if got[name] != self.expected[name])}"
        )
        self.steps += 1
        return got


async def new_checker(dut):
    """Let the power-up values propagate for 1 ns, then start a checker from the output."""
    await Timer(1, unit="ns")
    return Checker(dut)


@cocotb.test(timeout_time=200, timeout_unit="us")
async def fromv1_disable_copies_message(dut):
    """With disable high a strobe copies the input message and nothing changes without one.

    Propagation sampling: timingOut is sampled 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"fromv1_disable_copies_message seed {seed}")
    checker = await new_checker(dut)
    clock_task = await start_clock(dut)
    await checker.step(1, 0, timing_model.default_message(), blank_stream())
    for _ in range(3):
        msg = timing_model.random_message(rng)
        copied = await checker.step(1, 1, msg, timing_model.random_stream(rng))
        assert copied == msg, "disable high did not copy the input message"
        for _ in range(IDLE_CYCLES):
            await checker.step(1, 0, timing_model.random_message(rng), timing_model.random_stream(rng))
        assert checker.expected == msg
    clock_task.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def fromv1_strobe_gates_update(dut):
    """The output changes only on a strobe, and the fields it never assigns keep their value.

    The version, resync, syncStatus, mpsValid and bcsFault fields keep the
    value of the last message copied with disable high: observed, intent
    unconfirmed.

    Propagation sampling: timingOut is sampled 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"fromv1_strobe_gates_update seed {seed}")
    checker = await new_checker(dut)
    clock_task = await start_clock(dut)
    start = timing_model.default_message()
    await checker.step(0, 0, start, blank_stream())
    first = timing_model.random_stream(rng)
    mapped = await checker.step(0, 1, start, first)
    assert mapped["fixedRates"] == 0 and mapped["acRates"] & 1 == 1, "fixedRates is not cleared or acRates(0) is not set"
    for _ in range(IDLE_CYCLES):
        held = await checker.step(0, 0, timing_model.random_message(rng), timing_model.random_stream(rng))
        assert held == mapped, "timingOut changed without a strobe"
    for _ in range(IDLE_CYCLES):
        held = await checker.step(1, 0, timing_model.random_message(rng), timing_model.random_stream(rng))
        assert held == mapped, "disable alone changed timingOut"
    marked = {**timing_model.random_message(rng), "version": 5, "resync": 1, "syncStatus": 1, "mpsValid": 1, "bcsFault": 1}
    await checker.step(1, 1, marked, timing_model.random_stream(rng))
    later = await checker.step(0, 1, timing_model.random_message(rng), timing_model.random_stream(rng))
    for name in ("version", "resync", "syncStatus", "mpsValid", "bcsFault"):
        assert later[name] == marked[name], f"{name} did not keep its previous value"
    clock_task.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def fromv1_destination_rule(dut):
    """beamRequest destination is 2, 0 for dmod(61), 1 for dmod(60) and 1 when both are set.

    beamRequest(0) follows dmod(83).

    Propagation sampling: timingOut is sampled 2 ns after the edge.
    """
    checker = await new_checker(dut)
    clock_task = await start_clock(dut)
    await checker.step(0, 0, timing_model.default_message(), blank_stream())
    for bit_61 in (0, 1):
        for bit_60 in (0, 1):
            for bit_83 in (0, 1):
                dmod = (bit_61 << 61) | (bit_60 << 60) | (bit_83 << 83)
                got = await checker.step(0, 1, timing_model.default_message(), blank_stream(dmod=dmod))
                destination = 1 if bit_60 else (0 if bit_61 else 2)
                assert got["beamRequest"] == (destination << 4) | bit_83, (
                    f"dmod(61) {bit_61} dmod(60) {bit_60} dmod(83) {bit_83}: beamRequest {got['beamRequest']:#x}"
                )
                await checker.step(0, 0, timing_model.default_message(), blank_stream())
    clock_task.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def fromv1_random_streams(dut):
    """50 seeded random streams with disable low map to the model field for field.

    Propagation sampling: timingOut is sampled 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"fromv1_random_streams seed {seed}")
    checker = await new_checker(dut)
    clock_task = await start_clock(dut)
    await checker.step(0, 0, timing_model.default_message(), blank_stream())
    for _ in range(RANDOM_STREAMS):
        stream = timing_model.random_stream(rng)
        await checker.step(0, 1, timing_model.random_message(rng), stream)
        await checker.step(0, 0, timing_model.random_message(rng), timing_model.random_stream(rng))
    clock_task.cancel()


def test_EvrV2FromV1():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2fromv1wrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
