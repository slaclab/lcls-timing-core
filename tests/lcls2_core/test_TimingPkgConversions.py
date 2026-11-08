#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TimingPkg and default TimingExtnPkg conversion functions against the model.

Test methodology:
    Sweep: all-zero, all-ones and 20 seeded random TimingMessageType values
        for the message encode and decode; a single one bit walked through
        every position of the 944-bit message, 704-bit stream, 416-bit data
        buffer and 320-bit ExptMessageType vectors; 20 seeded random
        streams (event-code bit 255 included) and 20 seeded random
        ExptMessageType values.
    Stimulus: the wrappers are combinational, so each case drives every
        input, waits 1 ns and reads every output. The encode side is driven
        field by field, the decode side with the vector the model packs.
    Checks: toSlv equals pack_message, toSlvNoBsa equals pack_message_no_bsa,
        the stream and data buffer vectors equal pack_stream and
        pack_databuff, and every decoded field equals the model dictionary;
        the walking bit lands in exactly the model field and bit, so no
        field overlaps or leaves a gap; the 13 unused bits (316 downto 304)
        are never set by toSlv and ignored by toTimingMessageType; every
        compared output is resolvable. A 672-bit vector decoded with
        toTimingMessageType leaves version, syncStatus, mpsValid, bcsFault
        and the four bsa fields unassigned, so those slices read back as
        unresolved bits while every assigned field equals the model
        (observed, intent unconfirmed).
    Timing: no clock; outputs settle within 1 ns of the inputs.
    Propagation sampling: combinational outputs are read 1 ns after the
        inputs change.
"""

from pathlib import Path

import cocotb
from cocotb.triggers import Timer

from tests.common import timing_model
from tests.common.regression_utils import (
    REPO_ROOT,
    cocotb_filtered_env,
    cocotb_test_filter,
    run_lcls_vhdl_test,
)

CONVERSIONS_WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingPkgConversionsWrapper.vhd"
EXTN_PKG = REPO_ROOT / "LCLS-II/core/rtl/default/TimingExtnPkg.vhd"
EXTN_WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingExtnPkgWrapper.vhd"

RANDOM_CASES = 20
SETTLE_NS = 1

MESSAGE_TABLE = tuple(entry for entry in timing_model.MESSAGE_FIELDS if entry[0] != "unused")
MESSAGE_LAYOUT = timing_model.field_layout(timing_model.MESSAGE_FIELDS)
UNUSED_LSB, UNUSED_WIDTH, _ = MESSAGE_LAYOUT["unused"]
UNASSIGNED_BY_NO_BSA = ("version", "syncStatus", "mpsValid", "bcsFault", "bsaInit", "bsaActive", "bsaAvgDone", "bsaDone")


def capitalized(name):
    return name[0].upper() + name[1:]


def resolved_int(handle):
    """Return the integer value of a handle, failing on any X, U or Z bit."""
    value = handle.value
    assert value.is_resolvable, f"{handle._name} carries unresolved bits: {value}"
    return int(value)


def flat(elements, width):
    """Pack array elements into one integer, element 0 in the lowest bits."""
    return sum(element << (width * index) for index, element in enumerate(elements))


def split(value, width, count):
    mask = (1 << width) - 1
    return [(value >> (width * index)) & mask for index in range(count)]


def drive_fields(dut, prefix, table, values):
    """Drive one flat input per field of ``table`` from a field dictionary."""
    for name, width, count in table:
        port = getattr(dut, prefix + capitalized(name))
        port.value = values[name] if count == 1 else flat(values[name], width)


def read_fields(dut, prefix, table):
    """Read one flat output per field of ``table`` into a field dictionary."""
    result = {}
    for name, width, count in table:
        value = resolved_int(getattr(dut, prefix + capitalized(name)))
        result[name] = value if count == 1 else split(value, width, count)
    return result


def uniform_message(fill_ones):
    message = {}
    for name, width, count in MESSAGE_TABLE:
        fill = (1 << width) - 1 if fill_ones else 0
        message[name] = fill if count == 1 else [fill] * count
    return message


def drive_message(dut, message):
    drive_fields(dut, "enc", MESSAGE_TABLE, message)


def read_decoded_message(dut):
    return read_fields(dut, "dec", MESSAGE_TABLE)


def zero_stream():
    return {"pulseId": 0, "eventCodes": 0, "dbuff": timing_model.unpack_databuff(0)}


def drive_stream(dut, stream):
    dut.encStreamPulseId.value = stream["pulseId"]
    dut.encStreamEventCodes.value = stream["eventCodes"]
    drive_fields(dut, "encDbuff", timing_model.DATABUFF_FIELDS, stream["dbuff"])


def read_decoded_stream(dut):
    return {
        "pulseId": resolved_int(dut.decStreamPulseId),
        "eventCodes": resolved_int(dut.decStreamEventCodes),
        "dbuff": read_fields(dut, "decDbuff", timing_model.DATABUFF_FIELDS),
    }


def zero_wrapper_inputs(dut):
    drive_message(dut, uniform_message(False))
    drive_stream(dut, zero_stream())
    dut.decMessage.value = 0
    dut.decMessageNoBsa.value = 0
    dut.decStream.value = 0


async def settle():
    await Timer(SETTLE_NS, unit="ns")


@cocotb.test(timeout_time=100, timeout_unit="us")
async def conversions_message_fields(dut):
    """toSlv, toSlvNoBsa and toTimingMessageType agree with the model on every field.

    Propagation sampling: combinational outputs are read 1 ns after the inputs change.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    messages = [uniform_message(False), uniform_message(True)]
    messages += [timing_model.random_message(rng) for _ in range(RANDOM_CASES)]
    unused_mask = ((1 << UNUSED_WIDTH) - 1) << UNUSED_LSB

    zero_wrapper_inputs(dut)
    for index, message in enumerate(messages):
        vector = timing_model.pack_message(message)

        drive_message(dut, message)
        dut.decMessage.value = vector
        await settle()
        assert resolved_int(dut.encMessage) == vector, f"case {index}: encMessage differs from pack_message"
        assert resolved_int(dut.encMessage) & unused_mask == 0, f"case {index}: toSlv set an unused bit"
        assert resolved_int(dut.encMessageNoBsa) == timing_model.pack_message_no_bsa(message), (
            f"case {index}: encMessageNoBsa differs from pack_message_no_bsa"
        )
        assert read_decoded_message(dut) == message, f"case {index}: decoded fields differ from the message"

        dut.decMessage.value = vector | unused_mask
        await settle()
        assert read_decoded_message(dut) == message, f"case {index}: the unused bits changed a decoded field"


@cocotb.test(timeout_time=100, timeout_unit="us")
async def conversions_bit_walk(dut):
    """A single one bit lands in exactly the model field and bit for every vector.

    Propagation sampling: combinational outputs are read 1 ns after the inputs change.
    """
    zero_wrapper_inputs(dut)

    for bit in range(timing_model.TIMING_MESSAGE_BITS):
        in_unused = UNUSED_LSB <= bit < UNUSED_LSB + UNUSED_WIDTH
        vector = 1 << bit
        expected = timing_model.unpack_message(vector)
        drive_message(dut, expected)
        dut.decMessage.value = vector
        await settle()
        assert resolved_int(dut.encMessage) == (0 if in_unused else vector), f"message bit {bit}: encode"
        assert read_decoded_message(dut) == expected, f"message bit {bit}: decode"

    for bit in range(timing_model.TIMING_STREAM_BITS):
        vector = 1 << bit
        expected = timing_model.unpack_stream(vector)
        drive_stream(dut, expected)
        dut.decStream.value = vector
        await settle()
        assert resolved_int(dut.encStream) == vector, f"stream bit {bit}: encode"
        assert resolved_int(dut.encDbuff) == timing_model.pack_databuff(expected["dbuff"]), f"stream bit {bit}: dbuff"
        assert read_decoded_stream(dut) == expected, f"stream bit {bit}: decode"

    drive_stream(dut, zero_stream())
    for bit in range(timing_model.TIMING_DATABUFF_BITS):
        vector = 1 << bit
        dbuff = timing_model.unpack_databuff(vector)
        drive_stream(dut, {"pulseId": 0, "eventCodes": 0, "dbuff": dbuff})
        await settle()
        assert resolved_int(dut.encDbuff) == vector, f"data buffer bit {bit}: encode"
        assert resolved_int(dut.encStream) == vector << 288, f"data buffer bit {bit}: placement in the stream"


def slice_text(text, lsb, width):
    """Return the bits lsb+width-1 downto lsb of an MSB-first bit string."""
    return text[len(text) - lsb - width:len(text) - lsb]


@cocotb.test(timeout_time=100, timeout_unit="us")
async def conversions_no_bsa_vector(dut):
    """A 672-bit vector decodes every assigned field and leaves the other fields unassigned.

    The unassigned slices read back as unresolved bits through toSlv. This is
    observed, intent unconfirmed.

    Propagation sampling: combinational outputs are read 1 ns after the inputs change.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    messages = [uniform_message(False), uniform_message(True)]
    messages += [timing_model.random_message(rng) for _ in range(RANDOM_CASES)]
    assigned = [name for name, _, _ in MESSAGE_TABLE if name not in UNASSIGNED_BY_NO_BSA]

    zero_wrapper_inputs(dut)
    for index, message in enumerate(messages):
        dut.decMessageNoBsa.value = timing_model.pack_message_no_bsa(message)
        await settle()
        text = str(dut.nbRoundTrip.value)
        assert len(text) == timing_model.TIMING_MESSAGE_BITS
        modeled = timing_model.unpack_message_no_bsa(timing_model.pack_message_no_bsa(message))

        for name in assigned:
            lsb, width, count = MESSAGE_LAYOUT[name]
            piece = slice_text(text, lsb, width * count)
            assert set(piece) <= {"0", "1"}, f"case {index}: assigned field {name} is unresolved: {piece}"
            value = int(piece, 2)
            decoded = value if count == 1 else split(value, width, count)
            assert decoded == message[name], f"case {index}: field {name} differs from the message"
            assert decoded == modeled[name], f"case {index}: field {name} differs from the model decode"
        for name in UNASSIGNED_BY_NO_BSA:
            lsb, width, count = MESSAGE_LAYOUT[name]
            piece = slice_text(text, lsb, width * count)
            assert not set(piece) <= {"0", "1"}, f"case {index}: unassigned field {name} is resolved: {piece}"
        unused = slice_text(text, UNUSED_LSB, UNUSED_WIDTH)
        assert unused == "0" * UNUSED_WIDTH, f"case {index}: the unused bits are not zero: {unused}"


@cocotb.test(timeout_time=200, timeout_unit="us")
async def conversions_stream_fields(dut):
    """toSlv and toTimingStreamType agree with the model for seeded random streams.

    Propagation sampling: combinational outputs are read 1 ns after the inputs change.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    streams = [timing_model.random_stream(rng, allow_code_255=True) for _ in range(RANDOM_CASES)]
    streams[0]["eventCodes"] |= 1 << 255
    ones = {
        "pulseId": (1 << 32) - 1,
        "eventCodes": (1 << 256) - 1,
        "dbuff": timing_model.unpack_databuff((1 << timing_model.TIMING_DATABUFF_BITS) - 1),
    }
    streams.append(ones)

    zero_wrapper_inputs(dut)
    for index, stream in enumerate(streams):
        vector = timing_model.pack_stream(stream)
        drive_stream(dut, stream)
        dut.decStream.value = vector
        await settle()
        assert resolved_int(dut.encStream) == vector, f"stream {index}: encStream differs from pack_stream"
        assert resolved_int(dut.encDbuff) == timing_model.pack_databuff(stream["dbuff"]), (
            f"stream {index}: encDbuff differs from pack_databuff"
        )
        assert read_decoded_stream(dut) == stream, f"stream {index}: decoded fields differ from the stream"


EXPT_PORTS = tuple(timing_model.EXPT_FIELDS)


def random_expt(rng):
    return {name: rng.getrandbits(width) for name, width, _ in EXPT_PORTS}


def drive_expt(dut, values):
    drive_fields(dut, "enc", EXPT_PORTS, values)


def read_decoded_expt(dut):
    return read_fields(dut, "dec", EXPT_PORTS)


@cocotb.test(timeout_time=500, timeout_unit="us")
async def conversions_expt_fields(dut):
    """The default ExptMessageType conversions agree with pack_expt and unpack_expt.

    Propagation sampling: combinational outputs are read 1 ns after the inputs change.
    """
    rng, seed = timing_model.make_rng()
    dut._log.info(f"random seed {seed}")
    values = [random_expt(rng) for _ in range(RANDOM_CASES)]
    values.append({name: (1 << width) - 1 for name, width, _ in EXPT_PORTS})

    drive_expt(dut, values[0])
    dut.decExpt.value = 0
    await settle()
    assert resolved_int(dut.exptStreamId) == timing_model.EXPT_STREAM_ID == 2

    for index, expt in enumerate(values):
        vector = timing_model.pack_expt(expt)
        drive_expt(dut, expt)
        dut.decExpt.value = vector
        await settle()
        assert resolved_int(dut.encExpt) == vector, f"case {index}: encExpt differs from pack_expt"
        assert read_decoded_expt(dut) == expt, f"case {index}: decoded fields differ"
        assert read_decoded_expt(dut) == timing_model.unpack_expt(vector)

    for bit in range(timing_model.EXPT_MESSAGE_BITS):
        vector = 1 << bit
        expected = timing_model.unpack_expt(vector)
        drive_expt(dut, expected)
        dut.decExpt.value = vector
        await settle()
        assert resolved_int(dut.encExpt) == vector, f"expt bit {bit}: encode"
        assert read_decoded_expt(dut) == expected, f"expt bit {bit}: decode"


def test_TimingPkgConversions():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingpkgconversionswrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(CONVERSIONS_WRAPPER)]},
        extra_env=cocotb_filtered_env(
            {},
            cocotb_test_filter(
                "conversions_message_fields",
                "conversions_bit_walk",
                "conversions_no_bsa_vector",
                "conversions_stream_fields",
            ),
        ),
    )


def test_ExptMessageConversions():
    run_lcls_vhdl_test(
        test_file=Path(__file__),
        toplevel="lcls_timing_core.timingextnpkgwrapper",
        extra_vhdl_sources={"lcls_timing_core": [str(EXTN_PKG), str(EXTN_WRAPPER)]},
        extra_env=cocotb_filtered_env({}, cocotb_test_filter("conversions_expt_fields")),
    )
