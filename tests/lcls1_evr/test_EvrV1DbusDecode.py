#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""EvrV1DbusDecode data buffer decoder under Icarus Verilog.

The default run simulates a test-time patched copy of the production file
together with a behavioral Databuff model, not the production file itself.
Icarus rejects line 216 of LCLS-I/evr/EvrV1DbusDecode.v, ``rxSize <= {0,
iRxSize};``, at every language level because the concatenation contains an
unsized constant. The patched copy replaces that single text with
``{1'b0, iRxSize}``, which is the value Vivado computes after it truncates
the 32 bit constant concatenation to the 12 bit rxSize. The copy is written
under tests/sim_build/lcls1_evr/_patched/ at test time and is never tracked;
the production file is only ever opened for reading, and the helper fails
loudly if the replaced text is not found exactly once. The Databuff is the
test-only model in tests/lcls1_evr/models/, which the shared vector set pins
to the production RAM. The known-issue test compiles the production file
itself with the same model and asserts the intended behavior, so it fails at
compile time until the unsized constant is fixed.

Test methodology:
    Sweep: buffers of 8 bytes ended by K28.1 (0x3C) and by K28.5 (0xBC), a
        corrupted checksum in the low and in the high byte, sizes 1, 4, 5
        and 255 bytes, five seeded random payloads of 1 to 256 bytes with a
        random filler byte and a random end code, the control inputs dben,
        dbena and dbdis, and an 8 ns EventClock against a 10 ns Clock. The
        2048 byte buffer limit is not filled.
    Stimulus: both clocks run at 10 ns unless stated, and Reset is held for 4
        cycles. dben is raised and held for 6 cycles, then dbena is high for
        4 cycles and low for 4. A buffer is one K28.0 (0x1C) start cycle, then
        for each data byte one filler cycle followed by one data cycle, one
        end cycle (K28.1 or K28.5), then a filler, the checksum high byte, a
        filler, and the checksum low byte. The checksum is the complement of
        the sum of the data bytes, 16 bits wide, and the filler and K cycles
        do not count. Seeded payloads take their generator from make_rng and
        the seed is logged.
    Checks: rxSize equals the data byte count from the end cycle on and
        holds its previous value before it. dbrx is high for exactly 2 * n +
        1 cycles starting the cycle after the start code. dbrdy rises 2
        cycles after the end cycle. dbcs stays 0 for a correct checksum and
        rises 5 cycles after the end cycle for a wrong one, and the next
        dbena pulse clears it. The words read back through dbRdAddr equal the
        data bytes followed by the two stored checksum bytes, packed little
        endian (bytes 1 to 8 give 0x04030201 and 0x08070605), and the lanes
        after the checksum are not compared because a buffer reuses the
        memory. The control cases state what was observed: dben low blocks
        reception, a missing dbena pulse keeps dbrx low and stores nothing
        while rxSize and dbrdy still report the buffer, dbdis stops storing
        in the middle of a buffer, and dbena, dbdis and a low dben each
        clear dbrdy in the same cycle. The unrelated clock case also
        measures its results before asserting them.
    Timing: 10 ns Clock and 10 ns EventClock, 8 ns EventClock in the
        unrelated clock case; the Verilog has a 1 ns / 100 ps timescale.
    Propagation sampling: the module has no delayed assignments, so each
        sample settles through a ReadOnly phase after the rising edge and
        the stimulus moves one time step on before it drives again.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep
import pytest

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    TESTS_ROOT,
    run_icarus_verilog_test,
    sample_after_delta_cycles,
)

PRODUCTION_SOURCE = REPO_ROOT / "LCLS-I/evr/EvrV1DbusDecode.v"
PATCHED_DIR = TESTS_ROOT / "sim_build" / "lcls1_evr" / "_patched"
MODEL_SOURCE = REPO_ROOT / "tests/lcls1_evr/models/EvrV1Databuff_model.v"
ORIGINAL_TEXT = "{0, iRxSize}"
PATCHED_TEXT = "{1'b0, iRxSize}"

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

CLOCK_NS = 10
EVENT_CLOCK_UNRELATED_NS = 8
RESET_CYCLES = 4
DBEN_SETTLE_CYCLES = 6
DBENA_HIGH_CYCLES = 4
DBENA_LOW_CYCLES = 4
SETTLE_CYCLES = 10

START_CODE = 0x1C
END_K281 = 0x3C
END_K285 = 0xBC

# Measured latencies, in cycles after the end code cycle.
DBRDY_RISE_AFTER_END = 2
DBCS_RISE_AFTER_END = 5

BYTE_PATTERN_SIZES = (1, 4, 5, 255)
RANDOM_BUFFERS = 5
CONTROL_PAYLOAD_SIZE = 12
DBDIS_PAIR = 3


def patched_dbus_decode_source(directory: Path = PATCHED_DIR) -> Path:
    """Return the path of the test-time patched copy of EvrV1DbusDecode.v.

    The production file is read, never written. The replaced text must occur
    exactly once so an upstream edit makes the test fail instead of silently
    simulating something else. The copy is replaced atomically and only when
    its content differs, so parallel workers can call this at the same time.
    """
    text = PRODUCTION_SOURCE.read_text(encoding="utf-8")
    assert text.count(ORIGINAL_TEXT) == 1, (
        f"expected exactly one {ORIGINAL_TEXT!r} in {PRODUCTION_SOURCE.name}, "
        f"found {text.count(ORIGINAL_TEXT)}"
    )
    patched = text.replace(ORIGINAL_TEXT, PATCHED_TEXT)

    sim_build_root = (TESTS_ROOT / "sim_build").resolve()
    assert directory.resolve().is_relative_to(sim_build_root), (
        f"{directory} is not under {sim_build_root}"
    )
    directory.mkdir(parents=True, exist_ok=True)

    destination = directory / PRODUCTION_SOURCE.name
    if destination.is_file() and destination.read_text(encoding="utf-8") == patched:
        return destination

    descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(patched)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def checksum_of(payload):
    """The 16 bit complement of the sum of the data bytes."""
    return (~sum(payload)) & 0xFFFF


def unpack_words(words):
    return [(word >> (8 * lane)) & 0xFF for word in words for lane in range(4)]


class Snapshot:
    """Decoder outputs after one rising edge."""

    def __init__(self, dut):
        for name in ("rxSize", "dbrx", "dbrdy", "dbcs"):
            assert getattr(dut, name).value.is_resolvable, f"{name} is not resolvable"
        self.rx_size = int(dut.rxSize.value)
        self.dbrx = int(dut.dbrx.value)
        self.dbrdy = int(dut.dbrdy.value)
        self.dbcs = int(dut.dbcs.value)

    def __repr__(self):
        return f"(rxSize={self.rx_size}, dbrx={self.dbrx}, dbrdy={self.dbrdy}, dbcs={self.dbcs})"


class Bench:
    """Drives the decoder one EventClock cycle at a time and reads its buffer."""

    def __init__(self, dut, event_clock_ns=CLOCK_NS, clock_ns=CLOCK_NS):
        self.dut = dut
        self.event_clock_ns = event_clock_ns
        self.clock_ns = clock_ns
        self.checking = False

    async def step(self, dbus=0, isK=0):
        """Drive one cycle, wait for the edge that captures it, and sample.

        Propagation sampling: the sample settles through a ReadOnly phase
        after the edge; the next drive happens one time step later.
        """
        self.dut.dbus.value = dbus
        self.dut.isK.value = isK
        await sample_after_delta_cycles(self.dut.EventClock)
        snapshot = Snapshot(self.dut) if self.checking else None
        await NextTimeStep()
        return snapshot

    async def reset(self):
        """Hold Reset with every control low, then release it."""
        self.checking = False
        self.dut.Reset.value = 1
        self.dut.dben.value = 0
        self.dut.dbena.value = 0
        self.dut.dbdis.value = 0
        self.dut.dbRdAddr.value = 0
        for _ in range(RESET_CYCLES):
            await self.step()
        self.dut.Reset.value = 0
        self.checking = True
        snapshot = await self.step()
        assert snapshot.rx_size == 0, f"rxSize is {snapshot.rx_size} after reset"
        assert not (snapshot.dbrx or snapshot.dbrdy or snapshot.dbcs), (
            f"outputs after reset: {snapshot}"
        )

    async def start(self):
        """Start both clocks and reset the decoder."""
        for name in ("dbus", "isK"):
            getattr(self.dut, name).value = 0
        cocotb.start_soon(Clock(self.dut.Clock, self.clock_ns, unit="ns").start())
        cocotb.start_soon(Clock(self.dut.EventClock, self.event_clock_ns, unit="ns").start())
        await self.reset()

    async def enable(self):
        """Raise dben and let its synchronizer settle."""
        self.dut.dben.value = 1
        for _ in range(DBEN_SETTLE_CYCLES):
            await self.step()

    async def arm(self):
        """Pulse dbena: high for 4 cycles, then low for 4."""
        self.dut.dbena.value = 1
        for _ in range(DBENA_HIGH_CYCLES):
            await self.step()
        self.dut.dbena.value = 0
        for _ in range(DBENA_LOW_CYCLES):
            await self.step()

    async def send(self, payload, *, end_code=END_K281, checksum=None, filler=None,
                   dbdis_pair=None, settle=SETTLE_CYCLES):
        """Send one buffer and return the snapshots from the start cycle on.

        Index 0 is the start cycle and index ``2 * len(payload) + 1`` is the
        end cycle. ``filler`` is a function that returns the next filler
        byte (default 0), and ``dbdis_pair`` raises dbdis for the filler cycle
        of that data byte.
        """
        if checksum is None:
            checksum = checksum_of(payload)
        next_filler = filler if filler is not None else (lambda: 0)
        trace = [await self.step(START_CODE, 1)]
        for index, value in enumerate(payload):
            self.dut.dbdis.value = 1 if index == dbdis_pair else 0
            trace.append(await self.step(next_filler()))
            self.dut.dbdis.value = 0
            trace.append(await self.step(value))
        trace.append(await self.step(end_code, 1))
        trace.append(await self.step(next_filler()))
        trace.append(await self.step(checksum >> 8))
        trace.append(await self.step(next_filler()))
        trace.append(await self.step(checksum & 0xFF))
        for _ in range(settle):
            trace.append(await self.step())
        return trace

    async def read_word(self, address):
        """Present a read address and return the word after the next Clock edge."""
        self.dut.dbRdAddr.value = address
        await sample_after_delta_cycles(self.dut.Clock)
        assert self.dut.dataBuffOut.value.is_resolvable, (
            f"dataBuffOut at word {address} is not resolvable"
        )
        word = int(self.dut.dataBuffOut.value)
        await NextTimeStep()
        return word

    async def read_words(self, count):
        return [await self.read_word(address) for address in range(count)]

    async def read_bytes(self, count):
        words = await self.read_words(-(-count // 4))
        return unpack_words(words)[:count]


def expected_stored_bytes(payload, checksum=None):
    """The bytes the memory holds after a buffer: the data, then the checksum."""
    if checksum is None:
        checksum = checksum_of(payload)
    return list(payload) + [checksum >> 8, checksum & 0xFF]


def check_reception(trace, payload, previous_rx_size, *, checksum_error=False):
    """Assert rxSize, dbrx, dbrdy and dbcs against the measured latencies."""
    size = len(payload)
    end = 2 * size + 1
    for index, snapshot in enumerate(trace):
        rx_expected = size if index >= end else previous_rx_size
        assert snapshot.rx_size == rx_expected, (
            f"{size} bytes: rxSize is {snapshot.rx_size} in cycle {index}, expected {rx_expected}"
        )
        dbrx_expected = 1 if 1 <= index <= end else 0
        assert snapshot.dbrx == dbrx_expected, (
            f"{size} bytes: dbrx is {snapshot.dbrx} in cycle {index}, expected {dbrx_expected}"
        )
        dbrdy_expected = 1 if index >= end + DBRDY_RISE_AFTER_END else 0
        assert snapshot.dbrdy == dbrdy_expected, (
            f"{size} bytes: dbrdy is {snapshot.dbrdy} in cycle {index}, expected {dbrdy_expected}"
        )
        dbcs_expected = 1 if checksum_error and index >= end + DBCS_RISE_AFTER_END else 0
        assert snapshot.dbcs == dbcs_expected, (
            f"{size} bytes: dbcs is {snapshot.dbcs} in cycle {index}, expected {dbcs_expected}"
        )


async def receive_and_check(bench, payload, previous_rx_size, *, end_code=END_K281,
                            checksum=None, filler=None, rearm=True):
    """Arm the decoder, send one buffer, then check the outputs and the stored bytes."""
    if rearm:
        await bench.arm()
    trace = await bench.send(payload, end_code=end_code, checksum=checksum, filler=filler)
    wrong_checksum = checksum is not None and checksum != checksum_of(payload)
    check_reception(trace, payload, previous_rx_size, checksum_error=wrong_checksum)
    stored = await bench.read_bytes(len(payload) + 2)
    assert stored == expected_stored_bytes(payload, checksum), (
        f"{len(payload)} bytes: stored {stored}, expected {expected_stored_bytes(payload, checksum)}"
    )
    return trace[-1].rx_size


# Pure helper tests, no simulator.

def test_patched_copy_replaces_one_occurrence():
    production = PRODUCTION_SOURCE.read_text(encoding="utf-8")
    patched = patched_dbus_decode_source().read_text(encoding="utf-8")
    assert production.count(ORIGINAL_TEXT) == 1
    assert patched.count(ORIGINAL_TEXT) == 0
    assert patched.count(PATCHED_TEXT) == 1
    assert patched.replace(PATCHED_TEXT, ORIGINAL_TEXT) == production


def test_patched_copy_is_idempotent():
    # A private directory keeps parallel workers from replacing the shared copy
    # between the two calls.
    scratch = PATCHED_DIR / f"scratch-{os.getpid()}"
    try:
        first = patched_dbus_decode_source(scratch)
        stamp = first.stat().st_mtime_ns
        second = patched_dbus_decode_source(scratch)
        assert second == first
        assert second.stat().st_mtime_ns == stamp, "an unchanged patched copy was rewritten"
        assert not list(scratch.glob("*.tmp")), "a temporary file was left behind"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_patched_copy_stays_under_sim_build():
    destination = patched_dbus_decode_source()
    assert destination.resolve().is_relative_to((TESTS_ROOT / "sim_build").resolve())
    with pytest.raises(AssertionError):
        patched_dbus_decode_source(REPO_ROOT / "LCLS-I" / "evr")


def test_production_file_unchanged():
    patched_dbus_decode_source()
    relative = PRODUCTION_SOURCE.relative_to(REPO_ROOT)
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(relative)],
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, f"{relative} differs from HEAD"


# cocotb entrypoints. In the default run they simulate the patched copy
# together with the Databuff model.

@cocotb.test(timeout_time=500, timeout_unit="us")
async def dbus_patched_receives_buffer(dut):
    """Bytes 1 to 8 ended by K28.1 are stored little endian with rxSize 8.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the rising edge.
    """
    bench = Bench(dut)
    await bench.start()
    await bench.enable()
    payload = list(range(1, 9))
    await receive_and_check(bench, payload, 0)
    words = await bench.read_words(3)
    assert words[0] == 0x04030201, f"word 0 is {words[0]:#010x}"
    assert words[1] == 0x08070605, f"word 1 is {words[1]:#010x}"
    checksum = checksum_of(payload)
    expected_checksum_word = (checksum >> 8) | ((checksum & 0xFF) << 8)
    assert words[2] & 0xFFFF == expected_checksum_word, (
        f"word 2 is {words[2]:#010x}, expected the checksum bytes high byte first"
    )


@cocotb.test(timeout_time=500, timeout_unit="us")
async def dbus_patched_checksum_error(dut):
    """A flipped checksum bit raises dbcs, and the next dbena pulse clears it.

    Propagation sampling: each sample settles through a ReadOnly phase.
    """
    bench = Bench(dut)
    await bench.start()
    await bench.enable()
    payload = list(range(1, 9))
    good = checksum_of(payload)
    rx_size = 0
    for flipped in (good ^ 0x0001, good ^ 0x0100, good ^ 0x8000):
        rx_size = await receive_and_check(bench, payload, rx_size, checksum=flipped)
    rx_size = await receive_and_check(bench, payload, rx_size)
    assert rx_size == 8


@cocotb.test(timeout_time=500, timeout_unit="us")
async def dbus_patched_end_with_k285(dut):
    """K28.5 (0xBC) ends a buffer exactly like K28.1 (0x3C).

    Propagation sampling: each sample settles through a ReadOnly phase.
    """
    bench = Bench(dut)
    await bench.start()
    await bench.enable()
    payload = list(range(1, 9))
    rx_size = await receive_and_check(bench, payload, 0, end_code=END_K285)
    rx_size = await receive_and_check(bench, payload[:5], rx_size, end_code=END_K285)
    assert rx_size == 5


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def dbus_patched_sizes(dut):
    """Buffers of 1, 4, 5 and 255 bytes: size, stored bytes and dbrx length.

    Propagation sampling: each sample settles through a ReadOnly phase.
    """
    bench = Bench(dut)
    await bench.start()
    await bench.enable()
    rx_size = 0
    for size in BYTE_PATTERN_SIZES:
        payload = [(index * 7 + 3) & 0xFF for index in range(size)]
        rx_size = await receive_and_check(bench, payload, rx_size)


@cocotb.test(timeout_time=5, timeout_unit="ms")
async def dbus_patched_random_payloads(dut):
    """Seeded random payloads of 1 to 256 bytes round-trip, with random fillers.

    Propagation sampling: each sample settles through a ReadOnly phase.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"seed {seed}")
    bench = Bench(dut)
    await bench.start()
    await bench.enable()
    rx_size = 0
    for _ in range(RANDOM_BUFFERS):
        size = rng.randint(1, 256)
        payload = [rng.getrandbits(8) for _ in range(size)]
        end_code = rng.choice((END_K281, END_K285))
        rx_size = await receive_and_check(
            bench, payload, rx_size, end_code=end_code,
            filler=lambda: rng.getrandbits(8),
        )
        dut._log.info(f"{size} bytes, end code {end_code:#04x}")


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def dbus_patched_enable_controls(dut):
    """dben, dbena and dbdis gate reception as observed, intent unconfirmed.

    Propagation sampling: each sample settles through a ReadOnly phase.
    """
    bench = Bench(dut)
    await bench.start()
    payload = [0x41 + index for index in range(CONTROL_PAYLOAD_SIZE)]
    size = len(payload)
    end = 2 * size + 1

    # dben low: pulsing dbena does not receive anything, and no output moves.
    before = await bench.read_words(CONTROL_PAYLOAD_SIZE // 4 + 1)
    await bench.arm()
    trace = await bench.send(payload)
    for index, snapshot in enumerate(trace):
        assert (snapshot.rx_size, snapshot.dbrx, snapshot.dbrdy, snapshot.dbcs) == (0, 0, 0, 0), (
            f"dben low: outputs {snapshot} in cycle {index}"
        )
    assert await bench.read_words(len(before)) == before, "dben low: the memory changed"

    # dben raised without a new dbena pulse: the earlier pulse is still
    # latched, so the next buffer is received in full.
    await bench.enable()
    trace = await bench.send(payload)
    check_reception(trace, payload, 0)
    assert await bench.read_bytes(size + 2) == expected_stored_bytes(payload), (
        "dben raised after dbena: the buffer was not stored"
    )

    # With no dbena pulse after reset nothing is stored and dbrx stays low,
    # but rxSize and dbrdy still report the buffer.
    await bench.reset()
    await bench.enable()
    before = await bench.read_words(CONTROL_PAYLOAD_SIZE // 4 + 1)
    other = [0x61 + index for index in range(size - 2)]
    trace = await bench.send(other)
    for index, snapshot in enumerate(trace):
        assert snapshot.dbrx == 0 and snapshot.dbcs == 0, f"no dbena: outputs {snapshot} in cycle {index}"
    other_end = 2 * len(other) + 1
    assert trace[-1].rx_size == len(other), f"no dbena: rxSize is {trace[-1].rx_size}"
    assert trace[other_end + DBRDY_RISE_AFTER_END].dbrdy == 1, "no dbena: dbrdy did not rise"
    assert await bench.read_words(len(before)) == before, "no dbena: the memory changed"

    # dbdis in the middle of a buffer: dbrx drops and storing stops after the
    # data byte of the pair that carried the pulse; rxSize and dbrdy still
    # report the whole buffer.
    await bench.reset()
    await bench.enable()
    await bench.arm()
    before = await bench.read_words(CONTROL_PAYLOAD_SIZE // 4 + 1)
    trace = await bench.send(payload, dbdis_pair=DBDIS_PAIR)
    dbrx_cycles = sum(snapshot.dbrx for snapshot in trace)
    assert dbrx_cycles == 2 * DBDIS_PAIR + 3, f"dbdis: dbrx was high {dbrx_cycles} cycles"
    assert trace[end].rx_size == size and trace[end + DBRDY_RISE_AFTER_END].dbrdy == 1, (
        "dbdis: rxSize or dbrdy did not report the buffer"
    )
    after = await bench.read_bytes(size + 2)
    stored = DBDIS_PAIR + 1
    assert after[:stored] == payload[:stored], f"dbdis: stored {after[:stored]}"
    unchanged = unpack_words(before)[stored:size + 2]
    assert after[stored:] == unchanged, "dbdis: bytes after the pulse were stored"

    # dbena, dbdis and a low dben each clear dbrdy in the cycle they appear.
    for control in ("dbena", "dbdis", "dben"):
        await bench.reset()
        await bench.enable()
        await bench.arm()
        trace = await bench.send(payload)
        assert trace[-1].dbrdy == 1, f"{control}: dbrdy was not set before the control"
        getattr(dut, control).value = 0 if control == "dben" else 1
        snapshot = await bench.step()
        assert snapshot.dbrdy == 0, f"{control}: dbrdy still high in the cycle of the control"
        getattr(dut, control).value = 1 if control == "dben" else 0


@cocotb.test(timeout_time=2, timeout_unit="ms")
async def dbus_patched_unrelated_clocks(dut):
    """An 8 ns EventClock against a 10 ns Clock gives the same buffer results.

    Propagation sampling: each sample settles through a ReadOnly phase after
    the EventClock edge; the Clock domain outputs are read after the stimulus
    stops and they settle.
    """
    bench = Bench(dut, event_clock_ns=EVENT_CLOCK_UNRELATED_NS, clock_ns=CLOCK_NS)
    await bench.start()
    await bench.enable()
    for size in (8, 1, 33, 255):
        await bench.arm()
        payload = [(index * 5 + size) & 0xFF for index in range(size)]
        trace = await bench.send(payload)
        assert trace[-1].rx_size == size, f"{size} bytes: rxSize is {trace[-1].rx_size}"
        assert any(snapshot.dbrx for snapshot in trace), f"{size} bytes: dbrx never rose"
        assert trace[-1].dbrx == 0 and trace[-1].dbrdy == 1 and trace[-1].dbcs == 0, (
            f"{size} bytes: final outputs {trace[-1]}"
        )
        stored = await bench.read_bytes(size + 2)
        assert stored == expected_stored_bytes(payload), f"{size} bytes: stored bytes differ"
    await bench.arm()
    payload = list(range(1, 9))
    trace = await bench.send(payload, checksum=checksum_of(payload) ^ 0x0001)
    assert trace[-1].dbcs == 1, "a wrong checksum did not raise dbcs"


def test_EvrV1DbusDecode_patched_copy():
    run_icarus_verilog_test(
        test_file=Path(__file__),
        toplevel="EvrV1DbusDecode",
        verilog_sources=[str(patched_dbus_decode_source()), str(MODEL_SOURCE)],
    )


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: EvrV1DbusDecode.v has an unsized constant in a concatenation that Icarus rejects; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_EvrV1DbusDecode_known_issue_unpatched():
    run_icarus_verilog_test(
        test_file=Path(__file__),
        toplevel="EvrV1DbusDecode",
        verilog_sources=[str(PRODUCTION_SOURCE), str(MODEL_SOURCE)],
        extra_env={"EVR_DBUS_SOURCE": "production"},
    )
