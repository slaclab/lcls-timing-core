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
        alternating fixedRates patterns; AC mode with acTimeSlot 0 to 7, every
        index 0 to 7, the mask bit set, clear and set for another slot;
        event-code mode with every control word 0 to 17 and bit 0 to 15;
        reserved mode 11; destination modes 00, 01, 10 and 11 with
        beamRequest(0) 0 and 1, beamRequest(7:4) 0, 5 and 15, the mask bit set
        and clear and destSel(18) toggled; enabled and dmaEnabled gating; the
        boundary indices (fixed 9 and 10, AC 5 and 6, control word 17,
        destination mask bit 15); and a seeded random run of 2000 strobes over
        all four rate modes and all destination modes. The default runs keep
        rateSel(8:4) at 17 or below. With RUN_KNOWN_ISSUE_TESTS=1 one extra
        simulation sets it to 18 and the simulator stops on an index out of
        bounds.
    Stimulus: the 81-bit channel configuration and the 944-bit message are
        packed with tests.common.evr_model and tests.common.timing_model; the
        inputs change right after a rising edge and strobeIn is pulsed. The
        random run draws its seed from tests.common.timing_model.make_rng,
        logs it, and honors LCLS_TIMING_SEED.
    Checks: selectOut and dmaOut equal evr_model.EventSelectModel on every
        sampled clock, are resolvable on every sample, and each directed case
        also states the expected level from the bit rule it exercises. The
        outputs are registered one clock after strobeIn, and the control word
        is registered one clock before that. Behavior marked "observed, intent
        unconfirmed" is asserted as measured; the maintainers have not
        confirmed it as intended.
    Timing: 10 ns clk; inputs change right after a rising edge.
    Propagation sampling: registered outputs settle after TPD_G (1 ns), so
        every output is sampled 2 ns after the rising edge.
"""

import os
from pathlib import Path

import cocotb
import pytest
from cocotb.clock import Clock

from tests.common import evr_model, timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/evr/wrappers/EvrV2EventSelectWrapper.vhd"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
OVERFLOW_ENTRYPOINT = "select_control_index_overflow"

CLOCK_NS = 10
DEST_ALWAYS = 0b10 << 16
FIXED_MODE = 0 << 11
AC_MODE = 1 << 11
CONTROL_MODE = 2 << 11
RESERVED_MODE = 3 << 11
CONTROL_WORDS = 18
RATE_PATTERNS = (0x2AA, 0x155, 0x3FF, 0x000, *(1 << k for k in range(10)))
AC_PATTERNS = (0b101010, 0b010101, 0b111111, 0b000000, 0b000001, 0b100000)


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


class Cases:
    """A list of steps with the expected (selectOut, dmaOut) at each strobe step.

    Every case first applies its configuration and message with strobeIn low,
    so the registered control word has caught up, and then pulses strobeIn.
    """

    def __init__(self):
        self.steps = []
        self.checks = []

    def add(self, config, msg, select, dma=None, label=""):
        self.steps.append((config, 0, msg))
        self.steps.append((config, 1, msg))
        if dma is None:
            dma = select & config["dmaEnabled"]
        self.checks.append((len(self.steps) - 1, select, dma, label))

    def verify(self, seen):
        for index, select, dma, label in self.checks:
            assert seen[index] == (select, dma), (
                f"{label}: step {index} (selectOut, dmaOut) {seen[index]}, expected {(select, dma)}"
            )


async def run_cases(dut, cases):
    clock_task = await start_clock(dut)
    seen = await run_steps(dut, cases.steps, evr_model.EventSelectModel())
    cases.verify(seen)
    assert any(pair[0] for pair in seen) and not all(pair[0] for pair in seen), "the sweep never changed selectOut"
    clock_task.cancel()
    return seen


def bit(value, index):
    return (value >> index) & 1


def always(**fields):
    """An enabled channel with dma on and a destination that always selects."""
    return channel(enabled=1, dmaEnabled=1, destSel=DEST_ALWAYS, **fields)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_fixed_rate_modes(dut):
    """Fixed-rate indices 0 to 9 select fixedRates(i) and 10 to 15 select 0.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    cases = Cases()
    for pattern in RATE_PATTERNS:
        for index in range(16):
            expected = bit(pattern, index) if index < 10 else 0
            cases.add(always(rateSel=FIXED_MODE | index), message(fixedRates=pattern), expected,
                      label=f"fixedRates {pattern:#05x} index {index}")
    await run_cases(dut, cases)


def legal_control_index(rate_sel):
    """True when rateSel(8:4) stays inside the 18-word control array."""
    return ((rate_sel >> 4) & 0x1F) < CONTROL_WORDS


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_ac_modes(dut):
    """AC mode selects acRates(i) for index 0 to 5 when the slot mask bit is set, else 0.

    The mask bit of acTimeSlot is rateSel(acTimeSlot + 2). acTimeSlot 0 (bit
    2, which is also the top bit of the index) and 7 (bit 9) are asserted as
    observed, intent unconfirmed.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    cases = Cases()
    for slot in range(8):
        for pattern in AC_PATTERNS:
            for index in range(8):
                for mask in (1 << (slot + 2), 0, 1 << ((slot + 1) % 8 + 2)):
                    rate_sel = AC_MODE | mask | index
                    if not legal_control_index(rate_sel):
                        continue
                    used = rate_sel & 0x7
                    expected = bit(pattern, used) if bit(rate_sel, slot + 2) and used < 6 else 0
                    cases.add(always(rateSel=rate_sel), message(acRates=pattern, acTimeSlot=slot), expected,
                              label=f"acRates {pattern:#04x} slot {slot} rateSel {rate_sel:#06x}")
    await run_cases(dut, cases)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_control_word_modes(dut):
    """Event-code mode outputs bit rateSel(3:0) of control(rateSel(8:4)), registered one clock early.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    cases = Cases()
    for word in range(CONTROL_WORDS):
        for index in range(16):
            for polarity in (1, 0):
                hot = 1 << index
                control = [hot if polarity == 0 else 0xFFFF ^ hot] * CONTROL_WORDS
                control[word] = hot if polarity else 0xFFFF ^ hot
                cases.add(always(rateSel=CONTROL_MODE | (word << 4) | index), message(control=control), polarity,
                          label=f"control word {word} bit {index} polarity {polarity}")
    # The word is registered one clock before the output: a strobe in the same
    # step that changes the message still sees the old word.
    config = always(rateSel=CONTROL_MODE | (5 << 4) | 3)
    old = message(control=[0] * 5 + [0x0008] + [0] * 12)
    new = message(control=[0] * CONTROL_WORDS)
    cases.steps += [(config, 0, old), (config, 1, new), (config, 1, new)]
    cases.checks.append((len(cases.steps) - 2, 1, 1, "strobe in the step that clears the word"))
    cases.checks.append((len(cases.steps) - 1, 0, 0, "strobe one clock after the word is cleared"))
    await run_cases(dut, cases)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_reserved_mode(dut):
    """Rate mode 11 never selects whatever the message holds.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    cases = Cases()
    full = message(fixedRates=0x3FF, acRates=0x3F, acTimeSlot=3, control=[0xFFFF] * CONTROL_WORDS)
    for low in (0x000, 0x001, 0x00F, 0x00A, 0x108, 0x100):
        cases.add(always(rateSel=RESERVED_MODE | low), full, 0, label=f"reserved mode low bits {low:#05x}")
    # A selecting config proves the message itself would have selected.
    cases.add(always(rateSel=FIXED_MODE | 0), full, 1, label="fixed rate control case")
    await run_cases(dut, cases)


def destination_expected(mode, beam_request, mask):
    if mode == 2:
        return 1
    if mode == 3:
        return 0
    requested = bit(beam_request, 0) and bit(mask, (beam_request >> 4) & 0xF)
    return int(bool(requested)) if mode == 0 else int(not requested)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_destination_modes(dut):
    """destSel(17:16) 10 always selects, 01 unless the beam is requested at a masked destination, 00 only then.

    Mode 11 never selects and destSel(18) changes nothing: both observed,
    intent unconfirmed.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    cases = Cases()
    for mode in range(4):
        for beam_bit in (0, 1):
            for destination in (0, 5, 15):
                for mask_set in (True, False):
                    for bit18 in (0, 1):
                        mask = (1 << destination) if mask_set else (0xFFFF ^ (1 << destination))
                        dest_sel = (bit18 << 18) | (mode << 16) | mask
                        beam_request = (destination << 4) | beam_bit
                        expected = destination_expected(mode, beam_request, mask)
                        cases.add(channel(enabled=1, dmaEnabled=1, rateSel=0, destSel=dest_sel),
                                  message(fixedRates=1, beamRequest=beam_request), expected,
                                  label=f"destSel {dest_sel:#07x} beamRequest {beam_request:#04x}")
    await run_cases(dut, cases)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_enable_and_dma(dut):
    """selectOut needs enabled and strobeIn; dmaOut also needs dmaEnabled.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    steps = []
    expected = []
    for enabled in (0, 1):
        for dma in (0, 1):
            for strobe in (0, 1):
                config = channel(enabled=enabled, dmaEnabled=dma, rateSel=0, destSel=DEST_ALWAYS)
                steps += [(config, strobe, message(fixedRates=1))] * 2
                expected += [(enabled & strobe, enabled & strobe & dma)] * 2
    clock_task = await start_clock(dut)
    seen = await run_steps(dut, steps, evr_model.EventSelectModel())
    assert seen == expected, f"enable and dma gating: got {seen}, expected {expected}"
    clock_task.cancel()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_boundaries(dut):
    """The last valid index of every rate mode selects and the first invalid one does not.

    Fixed 9 selects and 10 does not, AC 5 selects and 6 does not, control
    word 17 selects without an abort, and destination mask bit 15 is reachable.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    cases = Cases()
    cases.add(always(rateSel=FIXED_MODE | 9), message(fixedRates=0x3FF), 1, label="fixed index 9")
    cases.add(always(rateSel=FIXED_MODE | 10), message(fixedRates=0x3FF), 0, label="fixed index 10")
    ac = message(acRates=0x3F, acTimeSlot=1)
    cases.add(always(rateSel=AC_MODE | (1 << 3) | 5), ac, 1, label="AC index 5")
    cases.add(always(rateSel=AC_MODE | (1 << 3) | 6), ac, 0, label="AC index 6")
    control = [0] * CONTROL_WORDS
    control[17] = 0x8000
    cases.add(always(rateSel=CONTROL_MODE | (17 << 4) | 15), message(control=control), 1, label="control word 17")
    dest = channel(enabled=1, dmaEnabled=1, rateSel=0, destSel=1 << 15)
    cases.add(dest, message(fixedRates=1, beamRequest=0xF1), 1, label="destination mask bit 15 set")
    cases.add(dest, message(fixedRates=1, beamRequest=0xE1), 0, label="destination mask bit 14 clear")
    await run_cases(dut, cases)


def random_channel(rng):
    """Return a random configuration whose rateSel(8:4) stays inside the control array."""
    rate_sel = rng.getrandbits(13)
    if not legal_control_index(rate_sel):
        # Fold an index of 18 to 31 back into 2 to 15 by clearing its top bit, rateSel(8).
        rate_sel &= ~(1 << 8) & 0x1FFF
    return channel(
        enabled=1 if rng.random() < 0.9 else 0,
        rateSel=rate_sel,
        destSel=rng.getrandbits(19),
        dmaEnabled=rng.getrandbits(1),
    )


@cocotb.test(timeout_time=500, timeout_unit="us")
async def select_random(dut):
    """2000 seeded random strobes over all rate and destination modes match the model.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"select_random seed {seed}")
    steps = []
    for _ in range(2000):
        config = random_channel(rng)
        msg = timing_model.random_message(rng)
        steps.append((config, 0, msg))
        steps.append((config, 1, msg))
    clock_task = await start_clock(dut)
    seen = await run_steps(dut, steps, evr_model.EventSelectModel())
    assert sum(pair[0] for pair in seen) > 50, "the random run barely selected anything"
    assert sum(pair[1] for pair in seen) > 20, "the random run barely produced dma"
    clock_task.cancel()


@cocotb.test(timeout_time=100, timeout_unit="us")
async def select_control_index_overflow(dut):
    """A control index of 18 must not abort the simulation.

    Known issue entrypoint: rateSel(8:4) = 18 indexes past the 18-word
    control array and the simulator reports an index out of bounds in
    EvrV2EventSelect.vhd and stops.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    config = always(rateSel=FIXED_MODE | (18 << 4))
    steps = [(config, 0, message()), (config, 1, message())]
    clock_task = await start_clock(dut)
    await run_steps(dut, steps)
    clock_task.cancel()


def run_select_simulation(test_filter):
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv2eventselectwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env({}, test_filter),
    )


def test_EvrV2EventSelect():
    run_select_simulation(cocotb_test_filter_excluding(OVERFLOW_ENTRYPOINT))


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV2EventSelect indexes the 18-word control array with rateSel(8:4) up to 31 "
        "and GHDL aborts at 18; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV2EventSelect_known_issue_control_index():
    run_select_simulation(cocotb_test_filter(OVERFLOW_ENTRYPOINT))
