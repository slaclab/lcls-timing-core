#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGMiniEdef test: one event definition that loads a configuration and counts strobes.

The block is reached through TPGMiniEdefWrapper, which flattens the
TPGMiniEdefConfigType input and turns the EdefType generic into a natural
(EDEF_G, converted with toSlv).

Test methodology:
    Sweep: EDEF_G 0 and 15, one compiled simulation each. Inside the
        entrypoints (navg, nsmp) covers (0, 0), (1, 2) and (255, 0); the
        write checks use every other EDEF identity 0 to 15 as the
        non-matching case and sevr 00, 01, 10 and 11.
    Stimulus: a 10 ns clk. A cycle is one drive-then-sample step: inputs are
        applied 2 ns after the rising edge and the outputs are read at the
        falling edge, so the combinational outputs (actv, avgD and allD are
        gated by strb) are seen for the inputs of the same cycle and the
        registered outputs for the state before the next edge. Strobes are
        single cycle pulses 3 cycles apart with cen high, except where cen is
        the subject; configuration writes are single cycle pulses of wrEn.
    Checks: a write with a different edef leaves init low and the
        configuration unloaded; a matching write pulses init in the cycle
        after it was presented and raises the registered active flag one
        cycle later; rate, slot, smaj and smin reflect the loaded
        configuration; avgD is high on every (navg + 1) th strobe, allD
        exactly once on strobe (navg + 1) * (nsmp + 1), and no output moves
        on a cycle without a strobe or after allD; a write while the
        definition is running, or one cycle after the first write, is
        ignored; cen low freezes the state while the strobe gated outputs
        still follow the strobe (a strobe with cen low is not consumed);
        rst returns the block to idle and clears the loaded configuration
        even with cen low; every output is resolvable on every cycle after
        reset release.
    Timing: registered outputs settle TPD_G = 1 ns after a rising edge.
    Propagation sampling: inputs are applied 2 ns after the edge, past the
        TPD_G delay, and outputs are read at the falling edge.
"""

import os
from pathlib import Path
from typing import NamedTuple

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge

from tests.common.regression_utils import (
    REPO_ROOT,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TPGMiniEdefWrapper.vhd"

CLK_PERIOD_NS = 10
RESET_CYCLES = 3
IDLE_CYCLES = 5
STROBE_GAP = 3

DEFAULTS = {
    "rst": 0,
    "cen": 1,
    "strb": 0,
    "cnfgNavg": 0,
    "cnfgNsmp": 0,
    "cnfgEdef": 0,
    "cnfgSlot": 0,
    "cnfgRate": 0,
    "cnfgSevr": 0,
    "cnfgWrEn": 0,
}

OUTPUTS = ("actv", "avgD", "allD", "init", "smin", "smaj", "rate", "slot")


class Obs(NamedTuple):
    """Outputs of one cycle."""

    cycle: int
    actv: int
    avgD: int
    allD: int
    init: int
    smin: int
    smaj: int
    rate: int
    slot: int


class Bench:
    """Drive-then-sample bench: ``step`` applies inputs for one cycle and returns that cycle's outputs.

    Every input returns to its default on the next step, except cen, which
    stays at ``self.cen`` until a step overrides it. Inputs only change right
    after a rising edge, so they are held through the edge that ends the cycle.
    """

    def __init__(self, dut):
        self.dut = dut
        self.edef = int(os.environ["EDEF_G"])
        self.cen = 1
        self.trace = []
        self.checked = False
        for name, value in DEFAULTS.items():
            getattr(dut, name).value = value
        self.clock = cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start(start_high=False))

    async def step(self, **values):
        await sample_after_tpd(self.dut.clk, propagation_time=2)
        for name, value in {**DEFAULTS, "cen": self.cen, **values}.items():
            getattr(self.dut, name).value = value
        await FallingEdge(self.dut.clk)
        cycle = len(self.trace)
        read = []
        for name in OUTPUTS:
            value = getattr(self.dut, name).value
            if self.checked:
                assert value.is_resolvable, f"{name} carries unresolved bits at cycle {cycle}: {value}"
            read.append(int(value) if value.is_resolvable else 0)
        obs = Obs(cycle, *read)
        self.trace.append(obs)
        return obs

    async def idle(self, count, **values):
        return [await self.step(**values) for _ in range(count)]

    async def reset(self):
        self.checked = False
        self.cen = 1
        await self.idle(RESET_CYCLES, rst=1)
        await self.idle(IDLE_CYCLES, rst=0)
        self.checked = True

    async def write(self, navg, nsmp, slot=1, rate=2, sevr=0, edef=None, repeat=1):
        """Present a configuration write for ``repeat`` cycles; return the first cycle it was presented."""
        cycle = len(self.trace)
        await self.idle(
            repeat,
            cnfgWrEn=1,
            cnfgNavg=navg,
            cnfgNsmp=nsmp,
            cnfgEdef=self.edef if edef is None else edef,
            cnfgSlot=slot,
            cnfgRate=rate,
            cnfgSevr=sevr,
        )
        return cycle

    async def strobes(self, count, gap=STROBE_GAP):
        """``count`` single cycle strobes ``gap`` cycles apart; return the Obs of each strobe cycle."""
        seen = []
        for _ in range(count):
            seen.append(await self.step(strb=1))
            await self.idle(gap - 1, strb=0)
        return seen


def quiet(obs):
    return not (obs.actv or obs.avgD or obs.allD)


@cocotb.test(timeout_time=200, timeout_unit="us")
async def edef_write_matching(dut):
    """Only a write for this EDEF loads the configuration; init pulses the cycle after it.

    Propagation sampling: inputs are applied 2 ns after the edge, outputs read at the falling edge.
    """
    bench = Bench(dut)
    await bench.reset()

    # every other EDEF identity is ignored, with strobes running to expose a stray active flag
    for other in range(16):
        if other == bench.edef:
            continue
        await bench.write(5, 5, slot=3, rate=4, sevr=3, edef=other)
        seen = await bench.idle(3, strb=1)
        assert all(quiet(obs) and not obs.init for obs in seen), f"write for edef {other} started the definition"
        assert all((obs.rate, obs.slot, obs.smin, obs.smaj) == (0, 0, 0, 0) for obs in seen), (
            f"write for edef {other} loaded the configuration"
        )

    # a matching write: init one cycle later, the active flag one cycle after that
    for sevr in range(4):
        await bench.reset()
        written = await bench.write(3, 1, slot=5, rate=6, sevr=sevr)
        seen = await bench.idle(4, strb=1)
        by_cycle = {obs.cycle: obs for obs in seen}
        assert by_cycle[written + 1].init == 1, f"sevr {sevr}: init not high the cycle after the write"
        assert by_cycle[written + 2].init == 0, f"sevr {sevr}: init longer than one cycle"
        assert not by_cycle[written + 1].actv, f"sevr {sevr}: active flag set with init"
        assert by_cycle[written + 2].actv == 1, f"sevr {sevr}: active flag not set the cycle after init"
        for obs in seen:
            assert (obs.rate, obs.slot, obs.smaj, obs.smin) == (6, 5, sevr >> 1, sevr & 1), (
                f"sevr {sevr}: cycle {obs.cycle} shows rate {obs.rate} slot {obs.slot} smaj {obs.smaj} smin {obs.smin}"
            )

    # writes while running, or in the init cycle, are ignored
    await bench.reset()
    written = await bench.write(3, 1, slot=5, rate=6, sevr=1)
    await bench.write(7, 7, slot=1, rate=1, sevr=2)
    seen = await bench.idle(4, strb=1)
    assert sum(obs.init for obs in bench.trace[written:]) == 1, "the write in the init cycle pulsed init again"
    for obs in bench.trace[written + 1:]:
        assert (obs.rate, obs.slot, obs.smaj, obs.smin) == (6, 5, 0, 1), f"cycle {obs.cycle}: second write loaded"
    running = len(bench.trace)
    await bench.write(9, 9, slot=2, rate=3, sevr=2)
    seen = await bench.idle(3, strb=0)
    assert not any(obs.init for obs in bench.trace[running:]), "a write while running pulsed init"
    assert all((obs.rate, obs.slot) == (6, 5) for obs in seen), "a write while running changed the configuration"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def edef_counts(dut):
    """avgD every (navg + 1) strobes, allD once on strobe (navg + 1) * (nsmp + 1), then idle.

    Propagation sampling: inputs are applied 2 ns after the edge, outputs read at the falling edge.
    """
    bench = Bench(dut)
    for navg, nsmp in ((0, 0), (1, 2), (255, 0)):
        label = f"(navg {navg}, nsmp {nsmp})"
        await bench.reset()
        await bench.write(navg, nsmp)
        await bench.idle(3)
        total = (navg + 1) * (nsmp + 1)
        start = len(bench.trace)
        seen = await bench.strobes(total + 3)
        for number, obs in enumerate(seen, start=1):
            expected_avg = int(number <= total and number % (navg + 1) == 0)
            expected_all = int(number == total)
            expected_actv = int(number <= total)
            assert (obs.avgD, obs.allD, obs.actv) == (expected_avg, expected_all, expected_actv), (
                f"{label}: strobe {number} shows avgD {obs.avgD} allD {obs.allD} actv {obs.actv}, "
                f"expected avgD {expected_avg} allD {expected_all} actv {expected_actv}"
            )
        strobe_cycles = {obs.cycle for obs in seen}
        for obs in bench.trace[start:]:
            if obs.cycle not in strobe_cycles:
                assert quiet(obs), f"{label}: output moved without a strobe at cycle {obs.cycle}: {obs}"
        assert sum(obs.allD for obs in bench.trace[start:]) == 1, f"{label}: allD not exactly once"
        # after allD the definition is idle until it is written again
        assert sum(obs.init for obs in bench.trace[start:]) == 0, f"{label}: init pulsed while counting"
        if total == 6:
            await bench.write(navg, nsmp)
            await bench.idle(3)
            again = await bench.strobes(total)
            assert [obs.allD for obs in again] == [0] * (total - 1) + [1], f"{label}: restart did not complete again"
            assert [obs.avgD for obs in again] == [0, 1, 0, 1, 0, 1], f"{label}: restart avgD {[o.avgD for o in again]}"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def edef_cen_and_reset(dut):
    """cen low freezes the state, rst returns the block to idle with the configuration cleared.

    Propagation sampling: inputs are applied 2 ns after the edge, outputs read at the falling edge.
    """
    bench = Bench(dut)

    # a write with cen low is ignored; with cen back high and wrEn still high it loads
    await bench.reset()
    bench.cen = 0
    first = await bench.write(1, 2, slot=4, rate=5, repeat=4)
    await bench.idle(2)
    assert not any(obs.init for obs in bench.trace[first:]), "init pulsed with cen low"
    bench.cen = 1
    written = await bench.write(1, 2, slot=4, rate=5)
    seen = await bench.idle(2, strb=1)
    assert bench.trace[written + 1].init == 1, "init did not follow the write once cen returned"
    assert seen[-1].actv == 1, "definition not active after the delayed write"

    # strobes with cen low do not advance the state and are not consumed
    await bench.reset()
    await bench.write(1, 2, slot=4, rate=5)
    await bench.idle(3)
    first = await bench.strobes(1)
    assert first[0].avgD == 0 and first[0].actv == 1, "first strobe of (1, 2) should only count down"
    frozen = await bench.idle(10, cen=0, strb=1)
    assert all(obs.avgD == 1 and obs.actv == 1 and obs.allD == 0 for obs in frozen), (
        "with cen low the strobe gated outputs should keep following the strobe"
    )
    rest = await bench.strobes(5)
    # the frozen strobes were not consumed: avgD on strobes 1, 3, 5 after the freeze, allD on the 5th
    assert [obs.avgD for obs in rest] == [1, 0, 1, 0, 1], f"avgD after the freeze {[o.avgD for o in rest]}"
    assert [obs.allD for obs in rest] == [0, 0, 0, 0, 1], f"allD after the freeze {[o.allD for o in rest]}"

    # rst returns to idle and clears the configuration, even with cen low
    for cen in (1, 0):
        await bench.reset()
        await bench.write(1, 2, slot=4, rate=5, sevr=3)
        await bench.idle(3)
        await bench.strobes(1)
        await bench.idle(1, cen=cen, rst=1)
        after = await bench.idle(4, rst=0, cen=1, strb=1)
        assert all(quiet(obs) and not obs.init for obs in after), f"cen {cen}: definition still running after rst"
        assert all((obs.rate, obs.slot, obs.smin, obs.smaj) == (0, 0, 0, 0) for obs in after), (
            f"cen {cen}: configuration survived rst"
        )
        await bench.write(0, 0)
        await bench.idle(3)
        again = await bench.strobes(1)
        assert again[0].allD == 1, f"cen {cen}: a new write after rst did not start the definition"


@pytest.mark.parametrize("edef", [0, 15])
def test_TPGMiniEdef(edef):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.tpgminiedefwrapper",
        parameters={"EDEF_G": edef},
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
    )
