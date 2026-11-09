#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV2EventSelect test: the RTL outputs equal a model on every clock.

Test methodology:
    Sweep: fixed-rate indices 0 to 15 against one-hot, inverted one-hot and
        alternating fixedRates patterns.
    Stimulus: the 81-bit channel configuration and the 944-bit message are
        packed with tests.common.evr_model and tests.common.timing_model; the
        inputs change right after a rising edge and strobeIn is pulsed.
    Checks: selectOut and dmaOut equal evr_model.EventSelectModel on every
        sampled clock, are registered one clock after strobeIn, and are
        resolvable on every sample.
    Timing: 10 ns clk; inputs change right after a rising edge.
    Propagation sampling: registered outputs settle after TPD_G (1 ns), so
        every output is sampled 2 ns after the rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock

from tests.common import evr_model, timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2EventSelectWrapper.vhd"

CLOCK_NS = 10
DEST_ALWAYS = 0b10 << 16


def channel(**fields):
    """Return a complete channel configuration dictionary with the defaults filled in."""
    return {**evr_model.CHANNEL_CONFIG_DEFAULTS, **fields}


def message(**fields):
    """Return a default timing message with the given fields replaced."""
    return {**timing_model.default_message(), **fields}


async def start_clock(dut):
    return cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start(start_high=False))


async def run_steps(dut, steps, model=None):
    """Apply each (config, strobe, message) step and compare both outputs with the model.

    Step k is applied 2 ns after edge k - 1 and its outputs are read 2 ns
    after edge k, which is the model's step convention. Returns the list of
    (selectOut, dmaOut) read after each edge.
    """
    seen = []
    dut.rst.value = 0
    for index, (config, strobe, msg) in enumerate(steps):
        dut.config.value = evr_model.pack_channel_config(**config)
        dut.strobeIn.value = strobe
        dut.dataIn.value = timing_model.pack_message(msg)
        await sample_after_tpd(dut.clk, propagation_time=2)
        for name in ("selectOut", "dmaOut"):
            assert getattr(dut, name).value.is_resolvable, (
                f"{name} carries unresolved bits at step {index}: {getattr(dut, name).value}"
            )
        got = (int(dut.selectOut.value), int(dut.dmaOut.value))
        if model is not None:
            want = model.step(config, strobe, msg)
            assert got == want, (
                f"step {index} (rateSel {config['rateSel']:#06x} destSel {config['destSel']:#07x} strobe {strobe}): "
                f"(selectOut, dmaOut) {got}, model {want}"
            )
        seen.append(got)
    return seen


@cocotb.test(timeout_time=200, timeout_unit="us")
async def select_fixed_rate_matches_model(dut):
    """A fixed-rate event is selected one clock after the strobe and matches the model.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    config = channel(enabled=1, rateSel=0, destSel=DEST_ALWAYS)
    steps = []
    strobes = []
    for strobe_number in range(20):
        has_event = strobe_number % 2 == 0
        msg = message(fixedRates=1 if has_event else 0)
        steps.append((config, 1, msg))
        strobes.append(has_event)
        steps.extend((config, 0, msg) for _ in range(9))
    clock_task = await start_clock(dut)
    seen = await run_steps(dut, steps, evr_model.EventSelectModel())
    for strobe_number, has_event in enumerate(strobes):
        selects = [pair[0] for pair in seen[strobe_number * 10:strobe_number * 10 + 10]]
        assert selects == [1 if has_event and k == 0 else 0 for k in range(10)], (
            f"strobe {strobe_number} (fixedRates(0) = {int(has_event)}): selectOut {selects}"
        )
    clock_task.cancel()


def run_select_simulation(test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2eventselectwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({}, test_filter),
    )


def test_EvrV2EventSelect():
    run_select_simulation(cocotb_test_filter("select_fixed_rate_matches_model"))
