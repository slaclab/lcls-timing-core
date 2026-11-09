#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2TriggerCompl test: the complementary AND/OR stage equals the model.

Test methodology:
    Sweep: REG_OUT_G false and true; every combination of complEn and complAnd
        on both outputs (16 configurations) with every trigIn value (4), then
        a seeded random run of 500 cycles.
    Stimulus: the 174-bit config word packs two trigger configurations with
        tests.common.evr_model; the other fields of each configuration are
        random in the random run to show that they have no effect. trigIn and
        config change right after a rising edge; rst is pulsed in the random
        run and held for several cycles in the reset test.
    Checks: trigOut equals evr_model.trigger_compl in the same cycle with
        REG_OUT_G false and one clock later with REG_OUT_G true, both read
        mid-cycle; after the next edge the output of either mode equals the
        value computed from that cycle. trigOut is 0 while rst is high and
        is resolvable on every sample.
    Timing: 10 ns clk; the combinational path is read 1 ns after the inputs
        change, the registered one 2 ns after the next rising edge.
    Propagation sampling: the unregistered output is combinational, so it is
        read 1 ns after the inputs change; registered state settles after
        TPD_G (1 ns), so the post-edge reads wait 2 ns after the edge.
"""

import os
from pathlib import Path

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import Timer

from tests.common import evr_model, timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2TriggerComplWrapper.vhd"

REG_OUT = os.getenv("REG_OUT_G", "false") == "true"
CLOCK_NS = 10


def config_word(compl_en, compl_and, **others):
    """Pack the two trigger configurations; element i lands in bits 87*i+86 downto 87*i."""
    word = 0
    for index in range(2):
        word |= evr_model.pack_trigger_config(complEn=compl_en[index], complAnd=compl_and[index], **others) << (
            evr_model.TRIGGER_CONFIG_BITS * index
        )
    return word


class Cycle:
    """Inputs of one clock cycle."""

    def __init__(self, compl_en=(0, 0), compl_and=(0, 0), trig_in=0, rst=0, others=None):
        self.compl_en = compl_en
        self.compl_and = compl_and
        self.trig_in = trig_in
        self.rst = rst
        self.others = others or {}

    def expected(self):
        if self.rst:
            return 0
        return evr_model.trigger_compl(self.compl_en, self.compl_and, self.trig_in)


def resolved(dut, label):
    value = dut.trigOut.value
    assert value.is_resolvable, f"trigOut carries unresolved bits {label}: {value}"
    return int(value)


async def run_cycles(dut, cycles):
    """Apply each cycle, read trigOut mid-cycle and after the next edge, and compare with the model.

    The mid-cycle read equals the model of the same cycle without an output
    register and of the previous cycle with one; the first cycle of a run is
    not compared mid-cycle in that mode because the register still holds the
    end of the previous test. The post-edge read equals the model of the
    cycle in both modes. Returns the post-edge values.
    """
    seen = []
    previous = None
    for index, cycle in enumerate(cycles):
        dut.rst.value = cycle.rst
        dut.config.value = config_word(cycle.compl_en, cycle.compl_and, **cycle.others)
        dut.trigIn.value = cycle.trig_in
        await Timer(1, unit="ns")
        mid = resolved(dut, f"mid-cycle {index}")
        want_mid = previous if REG_OUT else cycle.expected()
        assert want_mid is None or mid == want_mid, (
            f"cycle {index} (en={cycle.compl_en} and={cycle.compl_and} in={cycle.trig_in} rst={cycle.rst}): "
            f"mid-cycle trigOut {mid}, expected {want_mid}"
        )
        await sample_after_tpd(dut.clk, propagation_time=2)
        post = resolved(dut, f"after the edge {index}")
        assert post == cycle.expected(), (
            f"cycle {index} (en={cycle.compl_en} and={cycle.compl_and} in={cycle.trig_in} rst={cycle.rst}): "
            f"trigOut {post} after the edge, expected {cycle.expected()}"
        )
        seen.append(post)
        previous = cycle.expected()
    return seen


async def start_clock(dut):
    return cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start(start_high=False))


@cocotb.test(timeout_time=200, timeout_unit="us")
async def compl_truth_table(dut):
    """Every complEn and complAnd combination with every trigIn value equals the model.

    Propagation sampling: the combinational output is read 1 ns after the
    inputs change and the registered one 2 ns after the next edge.
    """
    clock_task = await start_clock(dut)
    cycles = [Cycle(rst=1), Cycle(rst=1)]
    for bits in range(16):
        compl_en = (bits & 1, (bits >> 1) & 1)
        compl_and = ((bits >> 2) & 1, (bits >> 3) & 1)
        for trig_in in range(4):
            cycles.append(Cycle(compl_en, compl_and, trig_in))
    seen = await run_cycles(dut, cycles)
    assert {0, 1, 2, 3} <= set(seen), f"the truth table never produced every output value: {sorted(set(seen))}"
    clock_task.cancel()


@cocotb.test(timeout_time=200, timeout_unit="us")
async def compl_reset_forces_zero(dut):
    """trigOut is 0 while rst is high, whatever trigIn and the configuration are.

    Propagation sampling: the combinational output is read 1 ns after the
    inputs change and the registered one 2 ns after the next edge.
    """
    clock_task = await start_clock(dut)
    cycles = [Cycle(rst=1)]
    cycles += [Cycle((0, 0), (0, 0), 3) for _ in range(3)]
    cycles += [Cycle((1, 1), (0, 0), trig_in, rst=1) for trig_in in (3, 1, 2, 3, 3)]
    cycles += [Cycle((1, 1), (0, 0), 3) for _ in range(3)]
    seen = await run_cycles(dut, cycles)
    assert seen[1:4] == [3, 3, 3], f"unreset passthrough produced {seen[1:4]}"
    assert seen[4:9] == [0] * 5, f"trigOut was not 0 while rst was high: {seen[4:9]}"
    assert seen[9:] == [3, 3, 3], f"trigOut did not recover after rst: {seen[9:]}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def compl_random(dut):
    """A seeded random run of configurations, trigIn values and resets equals the model.

    Propagation sampling: the combinational output is read 1 ns after the
    inputs change and the registered one 2 ns after the next edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    clock_task = await start_clock(dut)
    cycles = [Cycle(rst=1), Cycle(rst=1)]
    for _ in range(500):
        cycles.append(
            Cycle(
                (rng.getrandbits(1), rng.getrandbits(1)),
                (rng.getrandbits(1), rng.getrandbits(1)),
                rng.getrandbits(2),
                rst=1 if rng.random() < 0.05 else 0,
                others={
                    "enabled": rng.getrandbits(1),
                    "polarity": rng.getrandbits(1),
                    "delay": rng.getrandbits(28),
                    "width": rng.getrandbits(28),
                    "channel": rng.getrandbits(4),
                    "channels": rng.getrandbits(16),
                },
            )
        )
    seen = await run_cycles(dut, cycles)
    assert {0, 1, 2, 3} <= set(seen), f"the random run never produced every output value: {sorted(set(seen))}"
    clock_task.cancel()


@pytest.mark.parametrize("reg_out", ["false", "true"])
def test_EvrV2TriggerCompl(reg_out):
    parameters = {"REG_OUT_G": reg_out}
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2triggercomplwrapper",
        parameters=parameters,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
