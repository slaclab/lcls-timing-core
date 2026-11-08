#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""GthRxAlignCheck test: lock decision, retry loop, histogram and registers with an emulated DRP.

After resetDone rises the block reads one DRP register (a 32 bit read at
DRP_ADDR + 0x540 for GTHE3, + 0x940 for the other GT types) through its
AXI-Lite master. The low seven bits are the comma alignment latency. When
(value xor tgt) and mask is zero the block locks; otherwise it raises
resetOut, waits for resetDone to fall and rise, and reads again. Every read
increments one byte of a 40 entry histogram (registers 0x00 to 0x24, byte
i mod 4 of word i / 4), indexed by the seven bit value, and the last value is
kept in register 0x104. A write to register 0x100 (tgt bits 6:0, mask bits
14:8, rstlen bits 19:16) clears the histogram.

Frequency registers: 0x108 and 0x10C (txClkFreq and rxClkFreq) are only read
for an OKAY response and resolvable bits. Their accuracy is not verified,
because SyncClockFreq refreshes once per second (REFRESH_RATE_G is hard-coded
to 1 Hz in GthRxAlignCheck, with REF_CLK_FREQ_G 156.25 MHz), far beyond a
simulation window; this is not a limit of the wrapper.

Test methodology:
    Sweep: GT_TYPE_G in GTHE3 and GTYE4 (DRP_ADDR_G 0), one compiled
        simulation each. The out-of-range histogram probe has its own
        simulation and runs only when RUN_KNOWN_ISSUE_TESTS=1, because it ends
        the simulator. The generics are handed to the cocotb module through
        the environment because the test filter replaces the automatic export.
    Stimulus: register accesses use a cocotbext-axi AxiLiteMaster on S_AXI.
        The DRP is a cocotbext-axi AxiLiteRam on M_AXI whose word at the DRP
        offset holds the value under test. A Python transceiver stand-in
        drops resetDone for 24 clocks after every rise of resetOut, which is
        the response the state machine waits for. txClk is 6.4 ns, rxClk
        5.4 ns and axilClk 10 ns. Every entrypoint starts with a 5 cycle
        axilRst with resetDone low, so the state machine waits in its read
        state until the entrypoint raises resetDone.
    Checks: reset values; the DRP address observed on M_AXI_ARADDR; lock for
        values equal to the target under the mask and no lock otherwise; the
        number of resetOut pulses and the histogram counts for a scripted
        sequence of DRP values; resetOut length as a function of rstlen;
        resetIn and resetErr from the locked state; every register and its
        read-back. Every checked output is resolvable after reset release.
        Waits are bounded loops of clock cycles.
    Timing: with the stand-in answering at once, resetOut stays high for
        rstlen + 2 clocks.
    Propagation sampling: every sample waits 2 ns past the rising edge so the
        registered outputs, which settle TPD_G = 1 ns after the edge, are
        stable; inputs change at the same point.
"""

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotbext.axi import AxiLiteBus, AxiLiteMaster, AxiLiteRam, AxiResp
import pytest

from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    cocotb_test_filter_excluding,
    run_lcls_vhdl_test,
    sample_after_tpd,
)

WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/GthRxAlignCheckWrapper.vhd"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"
KNOWN_ISSUE_ENTRYPOINT = "align_out_of_range_sample"

RESET_CYCLES = 5
SETTLE_CYCLES = 20
GT_HOLD_CYCLES = 24
LOCK_WAIT_CYCLES = 600
DRP_SIZE = 4096
RESET_RSTLEN = 3
RESET_TARGET = 16
RESET_MASK = 126
REG_CONFIG = 0x100
REG_LAST = 0x104
REG_TX_CLK_FREQ = 0x108
REG_RX_CLK_FREQ = 0x10C
HISTOGRAM_SLOTS = 40
S_AXI_OUTPUTS = (
    "S_AXI_AWREADY", "S_AXI_WREADY", "S_AXI_BRESP", "S_AXI_BVALID",
    "S_AXI_ARREADY", "S_AXI_RDATA", "S_AXI_RRESP", "S_AXI_RVALID",
)


def gt_type():
    return os.environ["GT_TYPE_G"]


def drp_offset():
    """DRP register offset the module reads: 0x540 for GTHE3, 0x940 for GTYE4."""
    return 0x540 if gt_type() == "GTHE3" else 0x940


def config_word(tgt=RESET_TARGET, mask=RESET_MASK, rstlen=RESET_RSTLEN):
    return tgt | (mask << 8) | (rstlen << 16)


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


async def wait_axil(dut, count):
    for _ in range(count):
        await sample_after_tpd(dut.axilClk, propagation_time=2)


async def start_up(dut, drp_value=RESET_TARGET):
    """Drive resets and inputs, build the AXI-Lite master and DRP RAM, then start the clocks (cocotbext-axi order)."""
    dut.axilRst.value = 1
    dut.resetIn.value = 0
    dut.resetErr.value = 0
    dut.resetDone.value = 0
    master = AxiLiteMaster(AxiLiteBus.from_prefix(dut, "S_AXI"), dut.axilClk, dut.axilRst, reset_active_level=True)
    ram = AxiLiteRam(
        AxiLiteBus.from_prefix(dut, "M_AXI"), dut.axilClk, dut.axilRst, reset_active_level=True, size=DRP_SIZE
    )
    set_drp(ram, drp_value)
    await Timer(1, unit="ns")
    clocks = [
        cocotb.start_soon(Clock(dut.txClk, 6.4, unit="ns").start(start_high=False)),
        cocotb.start_soon(Clock(dut.rxClk, 5.4, unit="ns").start(start_high=False)),
        cocotb.start_soon(Clock(dut.axilClk, 10, unit="ns").start(start_high=False)),
    ]
    await wait_axil(dut, RESET_CYCLES)
    dut.axilRst.value = 0
    await wait_axil(dut, SETTLE_CYCLES)
    return master, ram, clocks


def set_drp(ram, value):
    ram.write(drp_offset(), value.to_bytes(4, "little"))


class Transceiver:
    """Transceiver stand-in: every rise of resetOut is answered by a resetDone drop, then resetDone returns.

    ``on_reset(count)``, if set, runs on the cycle of the ``count``-th resetOut
    rise since ``clear``, so a script can change the DRP value for the next
    read. ``lengths`` collects the number of cycles each resetOut pulse stayed
    high.
    """

    def __init__(self, dut):
        self.dut = dut
        self.on_reset = None
        self.clear()

    def clear(self):
        self.resets = 0
        self.lengths = []

    async def run(self):
        """Lifetime agent: follow resetOut and drive resetDone until the test ends."""
        high = 0
        previous = 0
        low_left = 0
        while True:
            await sample_after_tpd(self.dut.axilClk, propagation_time=2)
            out = resolved_int(self.dut.resetOut)
            if out and not previous:
                self.resets += 1
                if self.on_reset is not None:
                    self.on_reset(self.resets)
            if out:
                high += 1
                if low_left == 0 and resolved_int(self.dut.resetDone) == 1:
                    self.dut.resetDone.value = 0
                    low_left = GT_HOLD_CYCLES
            elif previous:
                self.lengths.append(high)
                high = 0
            previous = out
            if low_left:
                low_left -= 1
                if low_left == 0:
                    self.dut.resetDone.value = 1


async def watch_drp_addresses(dut, addresses):
    """Lifetime agent: record M_AXI_ARADDR on every cycle with M_AXI_ARVALID high, until the test ends."""
    while True:
        await sample_after_tpd(dut.axilClk, propagation_time=2)
        if resolved_int(dut.M_AXI_ARVALID):
            addresses.append(resolved_int(dut.M_AXI_ARADDR))


async def read_reg(master, address):
    response = await master.read(address, 4)
    assert response.resp == AxiResp.OKAY, f"read 0x{address:03X} response {response.resp!r}"
    return int.from_bytes(response.data, "little")


async def write_reg(master, address, value):
    response = await master.write(address, value.to_bytes(4, "little"))
    assert response.resp == AxiResp.OKAY, f"write 0x{address:03X} response {response.resp!r}"


async def read_histogram(master):
    """The 40 histogram bytes: byte i mod 4 of register 4 * (i / 4)."""
    words = [await read_reg(master, 4 * index) for index in range(HISTOGRAM_SLOTS // 4)]
    return [(word >> (8 * byte)) & 0xFF for word in words for byte in range(4)]


async def wait_locked(dut, limit=LOCK_WAIT_CYCLES):
    """Wait up to ``limit`` axilClk cycles for locked; return the cycle count or None."""
    for cycle in range(limit):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
        if resolved_int(dut.locked):
            return cycle
    return None


async def watch_not_locked(dut, cycles):
    """locked stays low for ``cycles`` axilClk cycles."""
    for cycle in range(cycles):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
        assert resolved_int(dut.locked) == 0, f"locked went high on cycle {cycle}"


async def pulse_reset_in(dut):
    dut.resetIn.value = 1
    await wait_axil(dut, 1)
    dut.resetIn.value = 0


def cancel_all(tasks):
    for task in tasks:
        task.cancel()


def scripted_reads(ram, gt, values):
    """Make read k return ``values[k]``: the first is set now, each next one on the reset that follows the read before it.

    The first resetOut pulse comes from the reset input that restarts the state
    machine, so the ``count``-th pulse is followed by read ``count - 1``.
    """
    set_drp(ram, values[0])

    def on_reset(count):
        if count - 1 < len(values):
            set_drp(ram, values[count - 1])

    gt.on_reset = on_reset


async def run_script(dut, master, ram, gt, values):
    """Restart the state machine and return the histogram after it locked on the last scripted value."""
    await write_reg(master, REG_CONFIG, config_word())
    gt.clear()
    scripted_reads(ram, gt, values)
    await pulse_reset_in(dut)
    cycle = await wait_locked(dut)
    assert cycle is not None, f"no lock within {LOCK_WAIT_CYCLES} cycles for DRP values {values}"
    return await read_histogram(master)


@cocotb.test(timeout_time=300, timeout_unit="us")
async def align_reset_values(dut):
    """After reset the state machine waits for resetDone with the documented register values.

    With resetDone low, locked and resetOut are low, register 0x100 reads
    tgt 16, mask 126 and rstlen 3, the last-value register and the whole
    histogram read zero, and no DRP read has been issued. Every output is
    resolvable.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut)
    addresses = []
    watcher = cocotb.start_soon(watch_drp_addresses(dut, addresses))
    for _ in range(20):
        await sample_after_tpd(dut.axilClk, propagation_time=2)
        for name in ("locked", "resetOut", *S_AXI_OUTPUTS, "M_AXI_ARVALID", "M_AXI_RREADY"):
            assert getattr(dut, name).value.is_resolvable, f"{name} is {getattr(dut, name).value} after reset release"
        assert resolved_int(dut.locked) == 0, "locked is high before resetDone"
        assert resolved_int(dut.resetOut) == 0, "resetOut is high before resetDone"
    config = await read_reg(master, REG_CONFIG)
    assert config == config_word(), f"register 0x100 is 0x{config:08X} after reset"
    assert await read_reg(master, REG_LAST) == 0, "last-value register is nonzero after reset"
    assert await read_histogram(master) == [0] * HISTOGRAM_SLOTS, "histogram is nonzero after reset"
    assert not addresses, f"DRP reads {addresses} before resetDone"
    cancel_all([watcher, *clocks])


@cocotb.test(timeout_time=300, timeout_unit="us")
async def align_locks_on_target(dut):
    """DRP value 16 locks on the first read at the GT type's offset and stays locked.

    Once resetDone is high one read is issued at DRP_ADDR + 0x540 (GTHE3) or
    + 0x940 (GTYE4), observed on M_AXI_ARADDR. locked rises, resetOut never
    pulses, register 0x104 reads 16, histogram slot 16 (register 0x10 byte 0)
    reads 1 and no other slot counts, and no further read follows over 200
    cycles.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut, drp_value=16)
    addresses = []
    watcher = cocotb.start_soon(watch_drp_addresses(dut, addresses))
    gt = Transceiver(dut)
    gt_task = cocotb.start_soon(gt.run())
    dut.resetDone.value = 1
    cycle = await wait_locked(dut)
    assert cycle is not None, "locked never rose for DRP value 16"
    await wait_axil(dut, 200)
    assert resolved_int(dut.locked) == 1, "locked dropped again"
    assert gt.resets == 0, f"resetOut pulsed {gt.resets} times for a matching value"
    assert set(addresses) == {drp_offset()}, f"DRP read addresses {sorted(hex(a) for a in set(addresses))}"
    assert await read_reg(master, REG_LAST) == 16, "register 0x104 is not 16"
    histogram = await read_histogram(master)
    assert histogram[16] == 1 and sum(histogram) == 1, f"histogram {histogram}"
    assert await read_reg(master, 0x10) == 1, "register 0x10 byte 0 is not 1"
    cancel_all([watcher, gt_task, *clocks])


@cocotb.test(timeout_time=300, timeout_unit="us")
async def align_masked_lsb(dut):
    """Values that differ from the target only under the mask or above bit 6 lock.

    With the reset target 16 and mask 126, bit 0 of the value is ignored, so 17
    locks; bits above 6 never reach the compare, so 0x8010 and 0x0090 lock as
    16 and are counted in slot 16, while the full 16 bit value is kept in
    register 0x104. Values 18, 32 and 0 differ under the mask and do not lock.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut)
    gt = Transceiver(dut)
    gt_task = cocotb.start_soon(gt.run())
    dut.resetDone.value = 1
    assert await wait_locked(dut) is not None, "no initial lock"
    for value, slot in ((17, 17), (0x8010, 16), (0x0090, 16), (16, 16)):
        gt.clear()
        gt.on_reset = None
        await write_reg(master, REG_CONFIG, config_word())
        set_drp(ram, value)
        await pulse_reset_in(dut)
        assert await wait_locked(dut) is not None, f"DRP value 0x{value:X} did not lock"
        assert await read_reg(master, REG_LAST) == value, f"register 0x104 is not 0x{value:X}"
        histogram = await read_histogram(master)
        assert histogram[slot] == 1 and sum(histogram) == 1, f"DRP value 0x{value:X}: histogram {histogram}"
    for value in (18, 32, 0):
        gt.clear()
        await write_reg(master, REG_CONFIG, config_word())
        set_drp(ram, value)
        await pulse_reset_in(dut)
        await watch_not_locked(dut, 120)
        assert gt.resets >= 2, f"DRP value {value}: only {gt.resets} resets, expected a retry loop"
    cancel_all([gt_task, *clocks])


@cocotb.test(timeout_time=300, timeout_unit="us")
async def align_retry_and_histogram(dut):
    """A mismatching value raises resetOut and retries; every read is counted; rstlen sets the pulse length.

    The DRP returns 18 four times and then 16. resetOut pulses four times,
    each read counts in its histogram slot (slot 18, register 0x10 byte 2,
    reads 4; slot 16 reads 1), register 0x104 ends at 16 and the state machine
    locks. With the stand-in answering at once, resetOut stays high for rstlen
    + 2 clocks, checked for rstlen 0, 3, 6 and 15 (the 4 bit maximum).

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut)
    gt = Transceiver(dut)
    gt_task = cocotb.start_soon(gt.run())
    dut.resetDone.value = 1
    assert await wait_locked(dut) is not None, "no initial lock"

    histogram = await run_script(dut, master, ram, gt, [18, 18, 18, 18, 16])
    assert gt.resets == 5, f"{gt.resets} resetOut pulses, expected the reset input plus 4 retries"
    assert histogram[18] == 4 and histogram[16] == 1 and sum(histogram) == 5, f"histogram {histogram}"
    assert await read_reg(master, 0x10) == 0x00040001, "register 0x10 does not hold slot 16 = 1 and slot 18 = 4"
    assert await read_reg(master, REG_LAST) == 16, "register 0x104 is not the last value 16"
    assert gt.lengths == [RESET_RSTLEN + 2] * 5, f"resetOut lengths {gt.lengths} for rstlen {RESET_RSTLEN}"

    for rstlen in (0, 6, 15):
        await write_reg(master, REG_CONFIG, config_word(rstlen=rstlen))
        gt.clear()
        scripted_reads(ram, gt, [18, 18, 16])
        await pulse_reset_in(dut)
        assert await wait_locked(dut) is not None, f"no lock for rstlen {rstlen}"
        assert gt.lengths == [rstlen + 2] * 3, f"rstlen {rstlen}: resetOut lengths {gt.lengths}, expected {rstlen + 2}"
    cancel_all([gt_task, *clocks])


@cocotb.test(timeout_time=300, timeout_unit="us")
async def align_highest_slot(dut):
    """The highest in-range value 39 counts in byte 3 of register 0x24; value 0 counts in byte 0 of register 0x00.

    The DRP returns 39 three times, then 0 twice, then 16. Slot 39 reads 3
    (register 0x24 bits 31:24), slot 0 reads 2 (register 0x00 bits 7:0) and
    slot 16 reads 1. The out-of-range value 40 is probed in
    align_out_of_range_sample, which has its own simulation.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut)
    gt = Transceiver(dut)
    gt_task = cocotb.start_soon(gt.run())
    dut.resetDone.value = 1
    assert await wait_locked(dut) is not None, "no initial lock"
    histogram = await run_script(dut, master, ram, gt, [39, 39, 39, 0, 0, 16])
    assert histogram[39] == 3 and histogram[0] == 2 and histogram[16] == 1 and sum(histogram) == 6, (
        f"histogram {histogram}"
    )
    assert await read_reg(master, 0x24) == 0x03000000, "register 0x24 does not hold slot 39 = 3 in byte 3"
    assert await read_reg(master, 0x00) == 0x00000002, "register 0x00 does not hold slot 0 = 2 in byte 0"
    cancel_all([gt_task, *clocks])


@cocotb.test(timeout_time=300, timeout_unit="us")
async def align_reset_inputs(dut):
    """resetIn and resetErr with resetDone high take the state machine out of the locked state.

    From the locked state a one cycle resetIn drops locked, raises resetOut and
    the state machine locks again after the stand-in answers; the second read
    brings slot 16 to 2. resetErr with resetDone high does the same (slot 16 at
    3). resetErr while resetDone is low leaves the lock in place.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut, drp_value=16)
    gt = Transceiver(dut)
    gt_task = cocotb.start_soon(gt.run())
    dut.resetDone.value = 1
    assert await wait_locked(dut) is not None, "no initial lock"

    await pulse_reset_in(dut)
    await wait_axil(dut, 2)
    assert resolved_int(dut.locked) == 0, "locked still high after resetIn"
    assert await wait_locked(dut) is not None, "no lock after resetIn"
    assert gt.resets == 1, f"{gt.resets} resetOut pulses after one resetIn"
    assert (await read_histogram(master))[16] == 2, "slot 16 is not 2 after the second read"

    dut.resetErr.value = 1
    await wait_axil(dut, 1)
    dut.resetErr.value = 0
    await wait_axil(dut, 2)
    assert resolved_int(dut.locked) == 0, "locked still high after resetErr with resetDone high"
    assert await wait_locked(dut) is not None, "no lock after resetErr"
    assert gt.resets == 2, f"{gt.resets} resetOut pulses after resetIn and resetErr"
    assert (await read_histogram(master))[16] == 3, "slot 16 is not 3 after the third read"

    dut.resetDone.value = 0
    dut.resetErr.value = 1
    await wait_axil(dut, 3)
    dut.resetErr.value = 0
    await wait_axil(dut, 20)
    assert resolved_int(dut.locked) == 1, "resetErr with resetDone low dropped the lock"
    assert gt.resets == 2, "resetErr with resetDone low raised resetOut"
    cancel_all([gt_task, *clocks])


@cocotb.test(timeout_time=600, timeout_unit="us")
async def align_registers(dut):
    """Register map: configuration read-back, lock decision for other targets and masks, and the plain registers.

    Register 0x100 reads back tgt, mask and rstlen. A target of 20 does not
    lock on 16 and locks on 20 and 21; mask 127 locks on 16 but not on 17;
    mask 0 locks on any value. The last-value register 0x104 and the histogram
    bytes read back what is written (observed, intent unconfirmed). Writing
    0x100 clears the histogram. The frequency registers 0x108 and 0x10C answer
    OKAY with resolvable bits, their value is not checked (see the module
    docstring), and an unmapped address answers OKAY with zero data (observed,
    intent unconfirmed).

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut)
    gt = Transceiver(dut)
    gt_task = cocotb.start_soon(gt.run())
    dut.resetDone.value = 1
    assert await wait_locked(dut) is not None, "no initial lock"

    for word in (config_word(20, 127, 5), config_word(1, 2, 15), config_word(127, 0, 0)):
        await write_reg(master, REG_CONFIG, word)
        assert await read_reg(master, REG_CONFIG) == word, f"register 0x100 does not read back 0x{word:08X}"

    cases = (
        (20, RESET_MASK, 16, False),
        (20, RESET_MASK, 20, True),
        (20, RESET_MASK, 21, True),
        (16, 127, 17, False),
        (16, 127, 16, True),
        (16, 0, 18, True),
        (16, 0, 5, True),
    )
    for tgt, mask, value, expect_lock in cases:
        await write_reg(master, REG_CONFIG, config_word(tgt, mask))
        set_drp(ram, value)
        gt.clear()
        await pulse_reset_in(dut)
        if expect_lock:
            assert await wait_locked(dut) is not None, f"tgt {tgt} mask {mask} did not lock on {value}"
        else:
            await watch_not_locked(dut, 120)
            assert gt.resets >= 2, f"tgt {tgt} mask {mask} value {value}: no retry loop"

    await write_reg(master, REG_CONFIG, config_word())
    set_drp(ram, 16)
    await pulse_reset_in(dut)
    assert await wait_locked(dut) is not None, "no lock to settle the state machine"
    await write_reg(master, REG_LAST, 0xBEEF)
    assert await read_reg(master, REG_LAST) == 0xBEEF, "register 0x104 does not read back a write"
    await write_reg(master, 0x00, 0x04030201)
    assert await read_reg(master, 0x00) == 0x04030201, "histogram word 0 does not read back a write"
    await write_reg(master, REG_CONFIG, config_word())
    assert await read_histogram(master) == [0] * HISTOGRAM_SLOTS, "a write to register 0x100 did not clear the histogram"

    for address in (REG_TX_CLK_FREQ, REG_RX_CLK_FREQ):
        await read_reg(master, address)
        assert dut.S_AXI_RDATA.value.is_resolvable, f"read data of 0x{address:03X} is unresolved"
    response = await master.read(0x1F0, 4)
    assert response.resp == AxiResp.OKAY and int.from_bytes(response.data, "little") == 0, (
        f"unmapped read answered {response.resp!r} with {response.data!r}"
    )
    cancel_all([gt_task, *clocks])


@cocotb.test(timeout_time=300, timeout_unit="us")
async def align_out_of_range_sample(dut):
    """A DRP value of 40 or more indexes past the 40 entry histogram (known issue, gated).

    The histogram index is the seven bit DRP value, 0 to 127, into a 40 entry
    array. Value 40 is read once; the state machine is expected to carry on
    with its retry loop, resetOut pulsing again and no slot counting. On the
    current RTL the simulator may stop on the out-of-range index instead.

    Propagation sampling: samples are taken 2 ns after the edge.
    """
    master, ram, clocks = await start_up(dut, drp_value=40)
    gt = Transceiver(dut)
    gt_task = cocotb.start_soon(gt.run())
    dut.resetDone.value = 1
    await wait_axil(dut, 200)
    assert gt.resets >= 2, f"{gt.resets} resetOut pulses after a DRP value of 40, expected a retry loop"
    assert sum(await read_histogram(master)) == 0, "a histogram slot counted the out-of-range value"
    cancel_all([gt_task, *clocks])


def run_case(gt_type_value, test_filter):
    generics = {"GT_TYPE_G": gt_type_value, "DRP_ADDR_G": 0}
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.gthrxaligncheckwrapper",
        parameters=generics,
        extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
        extra_env=cocotb_filtered_env(generics, test_filter),
    )


@pytest.mark.parametrize("gt_type_value", ["GTHE3", "GTYE4"])
def test_GthRxAlignCheck(gt_type_value):
    run_case(gt_type_value, cocotb_test_filter_excluding(KNOWN_ISSUE_ENTRYPOINT))


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason="known issue: GthRxAlignCheck indexes a 40-entry histogram with a 7-bit DRP value; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce",
)
def test_GthRxAlignCheck_known_issue_sample_index():
    run_case("GTHE3", cocotb_test_filter(KNOWN_ISSUE_ENTRYPOINT))
