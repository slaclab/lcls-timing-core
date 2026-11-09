#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1EventRAM256x32 leaf test under GHDL.

Test methodology:
    Sweep: all 256 addresses written on one port and read back on the other,
        in both directions; same-address read and write on each port;
        enable low on each port.
    Stimulus: no reset exists. clka runs at 10 ns and clkb at 7 ns, so the
        two ports never share an edge pattern. Inputs change just after a
        rising edge of the port's own clock. Data comes from the seeded
        generator in timing_model, and the seed is logged. The two ports
        are never active in the same step: a write on one port completes
        before the other port reads, because the memory is one shared
        variable and a same-time access from both clocks is not defined.
        Each run of operations on a port starts 2 ns after that port's own
        edge, so no input changes in the instant of an edge of its clock.
    Checks: every word read on the other port equals the word written, with
        one read per clock back to back. The read latency is one clock: the
        data for the address presented before an edge is visible after that
        edge. A write to an address that is read in the same cycle returns
        the old word on that port (read-first), and the next read returns
        the new word. With the enable low a write does not change the
        memory and a read leaves the data output unchanged.
    Timing: 10 ns clka, 7 ns clkb.
    Propagation sampling: the data outputs update ``after TPD_G`` (1 ns),
        so every sample is taken 2 ns after the rising edge.
"""

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tests.common import timing_model
from tests.common.regression_utils import run_lcls_vhdl_test, sample_after_tpd

CLKA_PERIOD_NS = 10
CLKB_PERIOD_NS = 7
DEPTH = 256
READ_FIRST_ADDRESSES = 16
ENABLE_ADDRESSES = 8
PORTS = ("a", "b")


class Port:
    """Handles for one RAM port, named by suffix (a or b)."""

    def __init__(self, dut, suffix):
        self.suffix = suffix
        self.clk = getattr(dut, f"clk{suffix}")
        self.en = getattr(dut, f"en{suffix}")
        self.we = getattr(dut, f"we{suffix}")
        self.addr = getattr(dut, f"addr{suffix}")
        self.din = getattr(dut, f"din{suffix}")
        self.dout = getattr(dut, f"dout{suffix}")

    def idle(self):
        # The enable is low so an idle port never reads while the other writes.
        self.en.value = 0
        self.we.value = 0
        self.addr.value = 0
        self.din.value = 0

    async def sample(self):
        """Wait for this port's next edge and return its data output.

        Propagation sampling: the sample is taken 2 ns after the edge, past
        the 1 ns ``after TPD_G`` delay.
        """
        await sample_after_tpd(self.clk, propagation_time=2)
        assert self.dout.value.is_resolvable, f"dout{self.suffix} is not resolvable"
        return int(self.dout.value)

    async def align(self):
        """Move to 2 ns after this port's own next edge before changing inputs.

        The two clocks are unrelated, so a step that ends on the other
        port's clock can coincide with this port's edge. Inputs changed in
        that instant race the edge, so every run of operations on a port
        starts here.
        """
        await self.sample()

    async def write(self, address, word, *, enable=1):
        """Present one write cycle; the next edge captures it."""
        self.en.value = enable
        self.we.value = 1
        self.addr.value = address
        self.din.value = word
        await self.sample()
        self.we.value = 0

    async def read(self, address):
        """Present one read address and return the word after the next edge."""
        self.en.value = 1
        self.we.value = 0
        self.addr.value = address
        return await self.sample()


async def start_ports(dut):
    ports = {suffix: Port(dut, suffix) for suffix in PORTS}
    for port in ports.values():
        port.idle()
    cocotb.start_soon(Clock(dut.clka, CLKA_PERIOD_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.clkb, CLKB_PERIOD_NS, unit="ns").start())
    await RisingEdge(dut.clka)
    await RisingEdge(dut.clkb)
    return ports


async def fill_and_read_back(dut, writer, reader):
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")
    words = [rng.getrandbits(32) for _ in range(DEPTH)]

    await writer.align()
    for address, word in enumerate(words):
        await writer.write(address, word)
    writer.idle()

    # One read per clock, back to back: the word for the address presented
    # before an edge appears after that edge, so the sample taken after
    # presenting address k is word k.
    await reader.align()
    for address in range(DEPTH):
        got = await reader.read(address)
        assert got == words[address], (
            f"port {reader.suffix} read {got:#010x} at {address:#04x}, "
            f"port {writer.suffix} wrote {words[address]:#010x}"
        )
    reader.idle()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def ram_port_a_to_b(dut):
    """Words written on port A read back on port B at every address.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` register delay.
    """
    ports = await start_ports(dut)
    await fill_and_read_back(dut, ports["a"], ports["b"])


@cocotb.test(timeout_time=500, timeout_unit="us")
async def ram_port_b_to_a(dut):
    """Words written on port B read back on port A at every address.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` delay.
    """
    ports = await start_ports(dut)
    await fill_and_read_back(dut, ports["b"], ports["a"])


@cocotb.test(timeout_time=500, timeout_unit="us")
async def ram_read_first(dut):
    """A write and a read of one address in one cycle returns the old word.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` delay.
    """
    ports = await start_ports(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")

    for suffix in PORTS:
        port = ports[suffix]
        await port.align()
        for address in range(READ_FIRST_ADDRESSES):
            old = rng.getrandbits(32)
            new = rng.getrandbits(32)
            await port.write(address, old)
            # The same-cycle write returns the word stored before the edge.
            await port.write(address, new)
            returned = int(port.dout.value)
            assert returned == old, (
                f"port {suffix} write with read at {address:#04x} returned {returned:#010x}, "
                f"expected the old word {old:#010x}"
            )
            # The next read sees the word the write stored.
            after = await port.read(address)
            assert after == new, f"port {suffix} read {after:#010x} after the write, expected {new:#010x}"
        port.idle()


@cocotb.test(timeout_time=500, timeout_unit="us")
async def ram_enables(dut):
    """A low enable blocks the write and holds the data output.

    Propagation sampling: samples are taken 2 ns after the edge, past the
    1 ns ``after TPD_G`` delay.
    """
    ports = await start_ports(dut)
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")

    for writer_suffix, reader_suffix in (("a", "b"), ("b", "a")):
        writer, reader = ports[writer_suffix], ports[reader_suffix]
        for address in range(ENABLE_ADDRESSES):
            stored = rng.getrandbits(32)
            blocked = rng.getrandbits(32)
            await writer.align()
            await writer.write(address, stored)
            # A write with the enable low leaves the stored word alone.
            await writer.write(address, blocked, enable=0)
            writer.idle()
            await reader.align()
            got = await reader.read(address)
            reader.idle()
            assert got == stored, (
                f"port {writer_suffix} write with en low changed {address:#04x} to {got:#010x}, "
                f"expected {stored:#010x}"
            )

        # A read with the enable low does not update the data output: the
        # output keeps the word of the last enabled read.
        await reader.align()
        held = await reader.read(0)
        reader.en.value = 0
        reader.addr.value = ENABLE_ADDRESSES - 1
        for _ in range(3):
            got = await reader.sample()
            assert got == held, (
                f"port {reader_suffix} output changed to {got:#010x} with en low, expected {held:#010x}"
            )
        reader.idle()
        writer.idle()


def test_EvrV1EventRAM256x32():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.evrv1eventram256x32",
    )
