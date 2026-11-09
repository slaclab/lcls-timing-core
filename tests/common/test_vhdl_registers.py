#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Pin the VHDL register decode parser to layouts measured on the running RTL.

Test methodology:
    Sweep: the generics that change the register layout of each decode file
        (trigger or channel count 1 and 3, the 256 byte and 4 kB group
        stride, and the tap or DMA gate), the clock select mode of
        TimingRx, the BSA sequence count of TPGMiniReg, and one synthetic
        VHDL fragment per statement form the parser handles.
    Stimulus: the repository VHDL files read as text and parsed, never
        analyzed or run; literal register tables read with ast out of the
        earlier cocotb test modules, which are never imported.
    Checks: the parser output equals the layout those tests measured on the
        simulated RTL, bit for bit; the exact set of targets whose width
        cannot be resolved, and the exact set of arms the parser cannot
        interpret, are pinned per file, so a parser change that resolves or
        loses one fails loudly.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import re
import time
from pathlib import Path

import pytest

from tests.common import ast_constants, vhdl_registers

WALK = "tests/lcls2_evr/register_walk.py"
FIELD_CALL = {"_field": (("name", "lsb", "width", "mode", "condition"), {"mode": "RW", "condition": None})}

TRIGREG = "LCLS-II/evr/rtl/EvrV2TrigReg.vhd"
CHANREG = "LCLS-II/evr/rtl/EvrV2ChannelReg.vhd"
ISR_CTRL = "LCLS-I/evr/EvrV1CoreIsrCtrl.vhd"

GENERIC_COMBOS = [(count, card, flag) for count in (1, 3) for card in (0, 1) for flag in (0, 1)]


def _mode(field):
    if field.readable and field.writable:
        return "RW"
    if field.readable:
        return "RO"
    return "WO"


def _observed(decode):
    return {(f.byte_offset, f.bit_offset, f.width, f.target, _mode(f)) for f in decode.fields}


def _layout_constants(*names):
    return ast_constants.read_constants(WALK, names, FIELD_CALL)


def _expected(layout, groups, stride, gate, enabled, base=0):
    """Expand a register walk layout into the same tuples the parser reports."""
    result = set()
    for group in range(groups):
        for word, fields in layout.items():
            for entry in fields:
                if entry["condition"] is not None and not (entry["condition"] == gate and enabled):
                    continue
                result.add((base + group * stride + word, entry["lsb"], entry["width"], entry["name"], entry["mode"]))
    return result


# ---------------------------------------------------------------------------
# The constant reader
# ---------------------------------------------------------------------------

def _write(tmp_path, text):
    path = tmp_path / "module.py"
    path.write_text(text, encoding="utf-8")
    return path


def test_read_constants_literals_and_range(tmp_path):
    path = _write(tmp_path, "A = (1, 2, *range(4, 7))\nB = [3, -4]\nC = {'x': 1}\n")
    assert ast_constants.read_constants(path, ["A", "B", "C"]) == {"A": (1, 2, 4, 5, 6), "B": [3, -4], "C": {"x": 1}}


def test_read_constants_name_keys_bound_earlier(tmp_path):
    path = _write(tmp_path, "BASE = 0x20\nTABLE = {BASE: ('a',), 4: BASE}\n")
    assert ast_constants.read_constants(path, ["TABLE"]) == {"TABLE": {0x20: ("a",), 4: 0x20}}


def test_read_constants_helper_call_defaults(tmp_path):
    path = _write(tmp_path, "T = (_field('a', 3, 1), _field('b', 4, 2, 'RO', condition='G'))\n")
    calls = {"_field": (("name", "lsb", "width", "mode", "condition"), {"mode": "RW", "condition": None})}
    value = ast_constants.read_constants(path, ["T"], calls)["T"]
    assert value == (
        {"name": "a", "lsb": 3, "width": 1, "mode": "RW", "condition": None},
        {"name": "b", "lsb": 4, "width": 2, "mode": "RO", "condition": "G"},
    )


@pytest.mark.parametrize(
    "text",
    [
        "X = int('3')\n",
        "X = [i for i in range(3)]\n",
        "X = 1 + 2\n",
        "X = open\n",
        "X = (*[1, 2],)\n",
        "X = Y\nY = X\n",
    ],
)
def test_read_constants_rejects_non_literals(tmp_path, text):
    with pytest.raises(ValueError, match="X"):
        ast_constants.read_constants(_write(tmp_path, text), ["X"])


def test_read_constants_missing_name(tmp_path):
    with pytest.raises(ValueError, match="NOPE"):
        ast_constants.read_constants(_write(tmp_path, "X = 1\n"), ["NOPE"])


def test_read_constants_does_not_execute(tmp_path):
    marker = tmp_path / "ran"
    path = _write(tmp_path, f"import pathlib\npathlib.Path({str(marker)!r}).write_text('x')\nX = 1\n")
    assert ast_constants.read_constants(path, ["X"]) == {"X": 1}
    assert not marker.exists()


# ---------------------------------------------------------------------------
# EVR V2 trigger and channel registers, and the LCLS-I ISR control
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "count, card, tap",
    GENERIC_COMBOS,
    ids=[f"n{count}-card{card}-tap{tap}" for count, card, tap in GENERIC_COMBOS],
)
def test_trigreg_matches_layout(count, card, tap):
    layout = _layout_constants("TRIGREG_LAYOUT", "TRIGGER_GROUP_TIGHT", "TRIGGER_GROUP_CARD")
    stride = layout["TRIGGER_GROUP_CARD" if card else "TRIGGER_GROUP_TIGHT"]
    decode = vhdl_registers.read_decode(
        TRIGREG, generics={"TRIGGERS_C": count, "EVR_CARD_G": bool(card), "USE_TAP_C": bool(tap)}
    )
    assert decode.unresolved == []
    assert _observed(decode) == _expected(layout["TRIGREG_LAYOUT"], count, stride, "USE_TAP", bool(tap))


@pytest.mark.parametrize(
    "count, card, dma",
    GENERIC_COMBOS,
    ids=[f"n{count}-card{card}-dma{dma}" for count, card, dma in GENERIC_COMBOS],
)
def test_chanreg_matches_layout(count, card, dma):
    layout = _layout_constants("CHANREG_LAYOUT", "TRIGGER_GROUP_TIGHT", "TRIGGER_GROUP_CARD")
    stride = layout["TRIGGER_GROUP_CARD" if card else "TRIGGER_GROUP_TIGHT"]
    decode = vhdl_registers.read_decode(
        CHANREG, generics={"NCHANNELS_G": count, "EVR_CARD_G": bool(card), "DMA_ENABLE_G": bool(dma)}
    )
    assert decode.unresolved == []
    assert _observed(decode) == _expected(layout["CHANREG_LAYOUT"], count, stride, "DMA_ENABLE", bool(dma))


def test_trigreg_strobes():
    stride_of = {0: 256, 1: 4096}
    for count, card, tap in GENERIC_COMBOS:
        decode = vhdl_registers.read_decode(
            TRIGREG, generics={"TRIGGERS_C": count, "EVR_CARD_G": bool(card), "USE_TAP_C": bool(tap)}
        )
        seen = sorted((s.target, s.byte_offset, s.kind) for s in decode.strobes)
        want = [("loadShift", group * stride_of[card] + 0x0C, "write") for group in range(count)] if tap else []
        assert seen == want, (count, card, tap)


def test_isr_ctrl_single_field():
    decode = vhdl_registers.read_decode(ISR_CTRL)
    assert [(f.target, f.byte_offset, f.bit_offset, f.width, f.readable, f.writable) for f in decode.fields] == [
        ("isrSelect", 0x0, 0, 1, True, True)
    ]
    assert decode.strobes == []
    assert decode.unresolved == []


# ---------------------------------------------------------------------------
# TimingRx, GthRxAlignCheck, and EvrV2Axi
# ---------------------------------------------------------------------------

TIMINGRX = "LCLS-II/core/rtl/TimingRx.vhd"
GTHALIGN = "LCLS-II/core/rtl/GthRxAlignCheck.vhd"
EVRV2AXI = "LCLS-II/evr/rtl/EvrV2Axi.vhd"
TIMINGRX_TEST = "tests/lcls2_core/test_TimingRx.py"
GTHALIGN_TEST = "tests/lcls2_core/test_GthRxAlignCheck.py"

EVRV1REG = "LCLS-I/evr/EvrV1Reg.vhd"
EVRV1REG_TEST = "tests/lcls1_evr/test_EvrV1Reg.py"
TPGMINIREG = "LCLS-II/core/rtl/TPGMiniReg.vhd"

# Entries of Decode.unresolved per decode file, at default generics: targets
# whose width the parser cannot resolve, and read or write arms it cannot
# interpret. An empty set means everything resolves and is interpreted; a
# parser change that resolves or loses one changes the set and fails the pin
# test. The three TPGMiniReg entries are the concatenation that builds the
# resources word, and the two functions of the BSA event definition word.
UNRESOLVED_TARGETS = {
    ISR_CTRL: frozenset(),
    EVRV1REG: frozenset(),
    GTHALIGN: frozenset(),
    TIMINGRX: frozenset(),
    TPGMINIREG: frozenset({
        "read 0x4C: concatenation",
        "read 0x78: function call",
        "write 0x78: expression of the write data",
    }),
    EVRV2AXI: frozenset(),
    CHANREG: frozenset(),
    TRIGREG: frozenset(),
}


def _position(field):
    return (field.byte_offset, field.bit_offset, field.target, _mode(field))


@pytest.mark.parametrize("mode", ["SELECT", "LCLSII"])
def test_timingrx_matches_constants(mode):
    c = ast_constants.read_constants(
        TIMINGRX_TEST,
        [
            "REG_CONTROL", "BIT_CLK_SEL", "BIT_MODE_SEL", "BIT_MODE_SEL_EN", "REG_COUNTER_RX_CLK",
            "REG_MESSAGE_DELAY", "REG_TX_CLK_COUNTER", "REG_VERSION", "REG_TS_EVENT_COUNTER",
            "BIT_CNT_RST", "BIT_LINK_UP", "BIT_POLARITY", "BIT_RESET", "BIT_RX_DOWN", "BIT_BUFFER_BY_RST",
            "BIT_PLL_RESET", "BIT_VERSION_ERROR", "BIT_STREAM_NO_DELAY",
        ],
    )
    select = "RW" if mode == "SELECT" else "RO"
    control = c["REG_CONTROL"]
    expected = {
        (control, c["BIT_CNT_RST"], "cntRst", "RW"),
        (control, c["BIT_LINK_UP"], "axilRxLinkUp", "RO"),
        (control, c["BIT_POLARITY"], "polarity", "RW"),
        (control, c["BIT_RESET"], "reset", "RW"),
        (control, c["BIT_CLK_SEL"], "clkSel", select),
        (control, c["BIT_RX_DOWN"], "rxDown", "RW"),
        (control, c["BIT_BUFFER_BY_RST"], "bufferByRst", "RW"),
        (control, c["BIT_PLL_RESET"], "pllReset", "RW"),
        (control, c["BIT_VERSION_ERROR"], "axilVsnErr", "RO"),
        (control, c["BIT_MODE_SEL"], "modeSel", select),
        (control, c["BIT_MODE_SEL_EN"], "modeSelEn", select),
        (control, c["BIT_STREAM_NO_DELAY"], "streamNoDelay", "RW"),
        (c["REG_MESSAGE_DELAY"], 0, "messageDelay", "RW"),
        (c["REG_MESSAGE_DELAY"], 31, "messageDelayRst", "RW"),
        (c["REG_TX_CLK_COUNTER"], 0, "txClkCntS", "RO"),
        (0x2C, 0, "rxStatusCount", "RO"),
        (0x2C, 16, "rxStatusCount", "RO"),
        (c["REG_VERSION"], 0, "axilVersion", "RO"),
        (c["REG_TS_EVENT_COUNTER"], 0, "timingTSEvCntGray_o", "RO"),
    }
    # Status counters: words 0x00 to 0x1C, the word at 0x10 being REG_COUNTER_RX_CLK.
    expected |= {(0x00, 0, "axilStatusCounters12", "RO"), (0x04, 0, "axilStatusCounters12", "RO"),
                 (0x08, 0, "axilStatusCounters12", "RO"), (0x0C, 0, "axilStatusCounters12", "RO"),
                 (c["REG_COUNTER_RX_CLK"], 0, "axilStatusCounters3", "RO"),
                 (0x14, 0, "axilStatusCounters3", "RO"), (0x18, 0, "axilStatusCounters3", "RO"),
                 (0x1C, 0, "axilStatusCounters3", "RO")}
    decode = vhdl_registers.read_decode(TIMINGRX, generics={"CLKSEL_MODE_G": mode})
    assert {_position(f) for f in decode.fields} == expected
    assert frozenset(decode.unresolved) == UNRESOLVED_TARGETS[TIMINGRX]
    mux = {(f.target, f.index, f.width) for f in decode.fields if f.target.startswith(("axilStatusCounters", "rxStatus"))}
    assert mux == {("axilStatusCounters12", k, 32) for k in range(4)} | {
        ("axilStatusCounters3", k, 32) for k in range(4)} | {("rxStatusCount", k, 16) for k in range(2)}


def test_gthrxaligncheck_matches_constants():
    c = ast_constants.read_constants(
        GTHALIGN_TEST, ["REG_CONFIG", "REG_LAST", "REG_TX_CLK_FREQ", "REG_RX_CLK_FREQ", "HISTOGRAM_SLOTS"]
    )
    decode = vhdl_registers.read_decode(GTHALIGN)
    samples = sorted((f.index, f.byte_offset, f.bit_offset, f.width) for f in decode.fields if f.target == "sample")
    slots = c["HISTOGRAM_SLOTS"]
    assert samples == [(i, 4 * (i // 4), 8 * (i % 4), 8) for i in range(slots)]
    fixed = {(f.target, f.byte_offset, f.bit_offset, f.width, _mode(f)) for f in decode.fields if f.target != "sample"}
    assert fixed == {
        ("tgt", c["REG_CONFIG"], 0, 7, "RW"),
        ("mask", c["REG_CONFIG"], 8, 7, "RW"),
        ("rstlen", c["REG_CONFIG"], 16, 4, "RW"),
        ("last", c["REG_LAST"], 0, 16, "RW"),
        ("txClkFreq", c["REG_TX_CLK_FREQ"], 0, 32, "RO"),
        ("rxClkFreq", c["REG_RX_CLK_FREQ"], 0, 32, "RO"),
    }
    assert frozenset(decode.unresolved) == UNRESOLVED_TARGETS[GTHALIGN]


@pytest.mark.parametrize(
    "count, dma",
    [(1, 0), (1, 1), (3, 0), (3, 1)],
    ids=[f"n{count}-dma{dma}" for count, dma in [(1, 0), (1, 1), (3, 0), (3, 1)]],
)
def test_evrv2axi_matches_layout(count, dma):
    c = _layout_constants("AXI_LAYOUT", "CHANREG_LAYOUT", "AXI_CHANNEL_BASE", "AXI_CHANNEL_STRIDE", "AXI_GLOBAL_COUNT")
    decode = vhdl_registers.read_decode(EVRV2AXI, generics={"DMA_ENABLE_G": bool(dma), "CHANNELS_C": count})
    assert frozenset(decode.unresolved) == UNRESOLVED_TARGETS[EVRV2AXI]
    # The register block names two words after the signal that feeds them.
    aliases = {"sReg": "irqReq"}
    observed = set()
    for item in _observed(decode):
        offset, bit, width, target, mode = item
        if target == "eventCount" and offset == c["AXI_GLOBAL_COUNT"]:
            target = "globalCount"
        observed.add((offset, bit, width, aliases.get(target, target), mode))
    expected = _expected(c["AXI_LAYOUT"], 1, 0, "DMA_ENABLE", bool(dma))
    expected |= _expected(
        c["CHANREG_LAYOUT"], count, c["AXI_CHANNEL_STRIDE"], "DMA_ENABLE", bool(dma), base=c["AXI_CHANNEL_BASE"]
    )
    assert observed == expected


# ---------------------------------------------------------------------------
# Synthetic statement forms
# ---------------------------------------------------------------------------

UNIT = """
library surf;
use surf.StdRtlPkg.all;
use surf.AxiLitePkg.all;
entity T is
   generic (
      TPD_G  : time    := 1 ns;
      N_G    : integer := 3;
      MODE_G : string  := "A");
   port (clk : in sl);
end T;
architecture rtl of T is
   type RegType is record
      s : Slv8Array(7 downto 0);
      f : slv(11 downto 0);
      g : sl;
{extra_fields}
   end record;
   signal r : RegType;
{architecture}
begin
{concurrent}
   comb : process (r) is
      variable v  : RegType;
      variable ep : AxiLiteEndpointType;
{declarations}
   begin
{body}
   end process comb;
end rtl;
"""


def _parse(body="", declarations="", concurrent="", architecture="", generics=None, extra_fields=""):
    source = UNIT.format(
        body=body, declarations=declarations, concurrent=concurrent, architecture=architecture,
        extra_fields=extra_fields,
    )
    return vhdl_registers.parse_decode(source, "synthetic.vhd", generics)


def _rows(decode):
    return [(f.target, f.index, f.byte_offset, f.bit_offset, f.width, _mode(f)) for f in decode.fields]


def test_loop_with_division_and_modulo_evaluates_every_value():
    decode = _parse(
        "for i in 0 to 7 loop\n"
        "   axiSlaveRegister(ep, toSlv(4*(i/4), 9), 8*(i mod 4), v.s(i));\n"
        "end loop;"
    )
    assert [(f.byte_offset, f.bit_offset) for f in decode.fields] == [
        (0, 0), (0, 8), (0, 16), (0, 24), (4, 0), (4, 8), (4, 16), (4, 24)
    ]
    assert [f.index for f in decode.fields] == list(range(8))
    assert {f.width for f in decode.fields} == {8}


def test_array_length_attribute_bounds_a_loop():
    decode = _parse(
        "for i in 0 to r.s'length-1 loop\n"
        "   axiSlaveRegister(ep, toSlv(4*i, 9), 0, v.s(i));\n"
        "end loop;"
    )
    assert [f.byte_offset for f in decode.fields] == [4 * i for i in range(8)]


def test_if_generate_is_not_an_if_then_branch():
    concurrent = (
        'G_A : if (MODE_G = "A") generate\n'
        "   p1 : process (r) is\n"
        "   begin\n"
        "      axiSlaveRegister(ep, X\"00\", 0, v.g);\n"
        "   end process p1;\n"
        "end generate G_A;\n"
        'G_B : if (MODE_G = "B") generate\n'
        "   p2 : process (r) is\n"
        "   begin\n"
        "      axiSlaveRegister(ep, X\"04\", 0, v.g);\n"
        "   end process p2;\n"
        "end generate G_B;\n"
    )
    body = "if (N_G = 3) then\n   axiSlaveRegister(ep, X\"08\", 0, v.g);\nend if;\naxiSlaveRegister(ep, X\"0C\", 0, v.g);"
    decode = _parse(body=body, concurrent=concurrent)
    assert [(f.byte_offset, f.condition) for f in decode.fields] == [
        (0x00, '( MODE_G = "A" )'), (0x08, "( N_G = 3 )"), (0x0C, None)
    ]
    other = _parse(body=body, concurrent=concurrent, generics={"MODE_G": "B"})
    assert [f.byte_offset for f in other.fields] == [0x04, 0x08, 0x0C]


def test_string_condition_on_a_generic_selects_the_branch():
    body = (
        'if (MODE_G = "A") then\n'
        "   axiSlaveRegister(ep, X\"00\", 0, v.g);\n"
        "else\n"
        "   axiSlaveRegisterR(ep, X\"00\", 0, r.g);\n"
        "end if;"
    )
    assert [_mode(f) for f in _parse(body=body).fields] == ["RW"]
    assert [_mode(f) for f in _parse(body=body, generics={"MODE_G": "other"}).fields] == ["RO"]


def test_local_wrapper_procedure_is_mapped_and_its_declaration_is_not_a_call():
    declarations = (
        "procedure p (addr : in slv; reg : in slv) is\n"
        "begin\n"
        "   axiSlaveRegister(ep, addr, 0, reg);\n"
        "end procedure;\n"
    )
    decode = _parse(body='p(X"10", v.f);', declarations=declarations)
    assert _rows(decode) == [("f", None, 0x10, 0, 12, "RW")]
    assert _parse(body="null;", declarations=declarations).fields == []


def test_wrapper_procedures_by_argument_count():
    declarations = (
        "procedure wr (addr : in slv; offset : in integer; reg : inout slv) is\n"
        "begin\n"
        "   axiSlaveRegister(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave,\n"
        "                    axilStatus, addr, offset, reg);\n"
        "end procedure;\n"
        "procedure rd (addr : in slv; reg : in slv) is\n"
        "begin\n"
        "   axiSlaveRegister(axilReadMaster, v.axilReadSlave, axilStatus, addr, 0, reg);\n"
        "end procedure;\n"
        "procedure rd (addr : in slv; reg : in slv; ack : out sl) is\n"
        "begin\n"
        "   if (axilStatus.readEnable = '1') then\n"
        "      if (std_match(axilReadMaster.araddr(addr'length-1 downto 0), addr)) then\n"
        "         v.axilReadSlave.rdata(reg'range) := reg;\n"
        "         ack := '1';\n"
        "      end if;\n"
        "   end if;\n"
        "end procedure;\n"
    )
    body = 'wr(X"00", 4, v.f);\nrd(X"04", r.f);\nrd(X"08", r.f, ack);'
    assert _rows(_parse(body=body, declarations=declarations)) == [
        ("f", None, 0, 4, 12, "RW"), ("f", None, 4, 0, 12, "RO"), ("f", None, 8, 0, 12, "RO"),
    ]


def test_wrapper_call_with_an_unknown_argument_count_is_unsupported():
    declarations = (
        "procedure rd (addr : in slv; reg : in slv) is\n"
        "begin\n"
        "   axiSlaveRegister(axilReadMaster, v.axilReadSlave, axilStatus, addr, 0, reg);\n"
        "end procedure;\n"
    )
    with pytest.raises(vhdl_registers.UnsupportedStatement, match=r"synthetic\.vhd:\d+"):
        _parse(body='rd(X"04");', declarations=declarations)


def test_unsupported_register_form_names_file_and_line():
    with pytest.raises(vhdl_registers.UnsupportedStatement, match=r"synthetic\.vhd:\d+"):
        _parse(body='axiSlaveRegister(ep, X"00", v.regs);')


# ---------------------------------------------------------------------------
# Case decodes: EvrV1Reg and TPGMiniReg
# ---------------------------------------------------------------------------

def test_evrv1reg_matches_constants():
    c = ast_constants.read_constants(
        EVRV1REG_TEST, ["WRITE_WORDS", "READ_WORDS", "READ_RANGES", "STATUS_WORD_FIELDS"]
    )
    decode = vhdl_registers.read_decode(EVRV1REG)
    assert frozenset(decode.unresolved) == UNRESOLVED_TARGETS[EVRV1REG]
    assert decode.strobes == []
    assert {f.byte_offset // 4 for f in decode.fields if f.writable} == set(c["WRITE_WORDS"])
    assert {f.byte_offset // 4 for f in decode.fields if f.readable} == set(c["READ_WORDS"])
    assert sorted((w.first_byte // 4, w.last_byte // 4) for w in decode.windows) == sorted(c["READ_RANGES"])
    assert all(w.readable and not w.writable for w in decode.windows)
    words = {entry[0] for entry in c["STATUS_WORD_FIELDS"]}
    observed = {
        (f.byte_offset // 4, "status" + f.target[0].upper() + f.target[1:], f.target_low, f.width)
        for f in decode.fields if f.readable and f.byte_offset // 4 in words
    }
    assert observed == set(c["STATUS_WORD_FIELDS"])
    # Every status slice starts at bit 0 of its word.
    assert {f.bit_offset for f in decode.fields if f.byte_offset // 4 in words} == {0}


BSADEF_WORDS = {
    0: [(0, 2), (2, 4), (6, 3), (9, 6), (15, 5), (20, 4), (24, 2)],
    1: [(0, 16), (16, 16)],
    2: [(0, 13), (14, 2), (16, 16)],
}


@pytest.mark.parametrize("count", [1, 2, 4, 32], ids=["1", "2", "4", "32"])
def test_tpgminireg_matches_slices(count):
    decode = vhdl_registers.read_decode(TPGMINIREG, generics={"NARRAYS_BSA": count})
    assert frozenset(decode.unresolved) == UNRESOLVED_TARGETS[TPGMINIREG]
    sequence = {
        (f.index, f.byte_offset, f.bit_offset, f.width)
        for f in decode.fields if f.target.lower().startswith("bsadef")
    }
    assert sequence == {
        (i, 0x200 + 16 * i + 4 * word, bit, width)
        for i in range(count) for word, slices in BSADEF_WORDS.items() for bit, width in slices
    }
    assert all(f.readable and f.writable for f in decode.fields if f.target.lower().startswith("bsadef"))
    by_target = {(f.target, f.byte_offset): f for f in decode.fields}
    pulse = by_target[("pulseId", 0x58)]
    assert (pulse.bit_offset, pulse.width, pulse.target_low, pulse.readable, pulse.writable) == (0, 64, 0, True, True)
    assert ("pulseId", 0x5C) not in by_target
    # BSACMPLL: the write decodes bsaClear and the read decodes bsaComplete, one 64 bit field each.
    clear, complete = by_target[("bsaClear", 0x50)], by_target[("bsaComplete", 0x50)]
    assert (clear.width, clear.readable, clear.writable) == (64, False, True)
    assert (complete.width, complete.readable, complete.writable) == (64, True, False)
    init = sorted((f.index, f.bit_offset) for f in decode.fields if f.target == "init")
    assert init == [(i, i) for i in range(count)]
    assert [f.byte_offset for f in decode.fields if f.target == "bsastatus"] == [0x400 + 4 * i for i in range(64)]
    assert sorted((s.target, s.byte_offset, s.kind) for s in decode.strobes) == [
        ("FixedRateDivisors", 0x40, "write"), ("wrEn", 0x7C, "write")
    ]
    assert decode.windows == ()


def test_every_decode_file_parses():
    decodes = vhdl_registers.read_all()
    assert sorted(decodes) == sorted(vhdl_registers.DECODE_FILES)
    assert all(decode.fields for decode in decodes.values())
    assert {path: frozenset(decode.unresolved) for path, decode in decodes.items()} == UNRESOLVED_TARGETS


def test_decode_files_name_the_eight_blocks():
    assert len(vhdl_registers.DECODE_FILES) == 8
    assert sorted(vhdl_registers.DECODE_FILES.values()) == sorted([
        "EvrV1Isr", "EvrV1Reg", "GthRxAlignCheck", "TimingFrameRx", "TPGMiniCore", "EvrV2Core",
        "EvrV2ChannelReg", "EvrV2TriggerReg",
    ])
    assert all((vhdl_registers.REPO_ROOT / path).is_file() for path in vhdl_registers.DECODE_FILES)


# ---------------------------------------------------------------------------
# Synthetic case decodes
# ---------------------------------------------------------------------------

POINTERS = (
    "wrPntr := conv_integer(axiWriteMaster.awaddr(14 downto 2));\n"
    "rdPntr := conv_integer(axiReadMaster.araddr(14 downto 2));\n"
)
POINTER_DECLARATIONS = "variable wrPntr : natural;\nvariable rdPntr : natural;\nvariable i : natural;\n"
WIDE_FIELDS = "      a : slv(7 downto 0);\n      b : slv(31 downto 0);\n      x : Slv16Array(N_G-1 downto 0);\n      y : slv(63 downto 0);\n"


def _case(body, constants="constant K : integer := 4;\nconstant B : integer := 128;\n"
          "constant B_END : integer := B + 4*N_G;\n", **kwargs):
    return _parse(
        body=POINTERS + body, declarations=POINTER_DECLARATIONS, architecture=constants,
        extra_fields=WIDE_FIELDS, **kwargs
    )


def _cases(decode):
    return sorted((f.target, f.index, f.byte_offset, f.bit_offset, f.width, f.target_low, _mode(f)) for f in decode.fields)


def test_case_arms_integer_constant_sum_range_and_others():
    decode = _case(
        "case wrPntr is\n"
        "   when 3 => v.a := regWrData(7 downto 0);\n"
        "   when K+1 => v.b := regWrData;\n"
        "   when 8 to 11 => null;\n"
        "   when others => null;\n"
        "end case;"
    )
    assert _cases(decode) == [("a", None, 12, 0, 8, 0, "WO"), ("b", None, 20, 0, 32, 0, "WO")]
    assert [(w.first_byte, w.last_byte, w.target, w.writable) for w in decode.windows] == [(32, 47, None, True)]


def test_case_read_arm_slices_the_read_data():
    decode = _case("case rdPntr is\n   when 2 => v.axiReadSlave.rdata(15 downto 8) := s;\nend case;")
    assert _cases(decode) == [("s", None, 8, 8, 8, 0, "RO")]


def test_case_arm_with_several_statements_and_choices():
    decode = _case(
        "case wrPntr is\n"
        "   when 1 | 2 =>\n"
        "      v.a := regWrData(3 downto 0);\n"
        "      v.b := regWrData(31 downto 16);\n"
        "end case;"
    )
    assert _cases(decode) == [
        ("a", None, 4, 0, 4, 0, "WO"), ("a", None, 8, 0, 4, 0, "WO"),
        ("b", None, 4, 16, 16, 0, "WO"), ("b", None, 8, 16, 16, 0, "WO"),
    ]


def test_nested_case_on_address_bits_indexes_the_sequences():
    body = (
        "regAddr := axiWriteMaster.awaddr(regAddr'range);\n"
        "case wrPntr is\n"
        "   when B to B_END =>\n"
        "      i := conv_integer(regAddr(8 downto 4));\n"
        "      case regAddr(3 downto 2) is\n"
        "         when \"01\" => v.x(i) := regWrData(31 downto 16);\n"
        "         when others => null;\n"
        "      end case;\n"
        "end case;"
    )
    decode = _parse(
        body=POINTERS + body, declarations=POINTER_DECLARATIONS + "variable regAddr : slv(31 downto 2);\n",
        architecture="constant B : integer := 128;\nconstant B_END : integer := B + 4*N_G;\n",
        extra_fields=WIDE_FIELDS,
    )
    assert _cases(decode) == [("x", i, 0x200 + 16 * i + 4, 16, 16, 0, "WO") for i in range(3)]
    assert decode.windows == ()


def test_write_slices_merge_little_endian_only():
    forward = _case(
        "case wrPntr is\n"
        "   when 5 => v.y(31 downto 0) := regWrData;\n"
        "   when 6 => v.y(63 downto 32) := regWrData;\n"
        "end case;"
    )
    assert _cases(forward) == [("y", None, 20, 0, 64, 0, "WO")]
    reverse = _case(
        "case wrPntr is\n"
        "   when 5 => v.y(63 downto 32) := regWrData;\n"
        "   when 6 => v.y(31 downto 0) := regWrData;\n"
        "end case;"
    )
    assert _cases(reverse) == [("y", None, 20, 0, 32, 32, "WO"), ("y", None, 24, 0, 32, 0, "WO")]


def test_read_and_write_arms_of_one_target_become_one_field():
    decode = _case(
        "case wrPntr is\n   when 1 => v.b := regWrData;\n   when 2 => v.a := regWrData(7 downto 0);\nend case;\n"
        "case rdPntr is\n   when 1 => v.axiReadSlave.rdata := r.b;\n   when 2 => v.axiReadSlave.rdata(7 downto 0) := r.y(7 downto 0);\n"
        "end case;"
    )
    assert _cases(decode) == [
        ("a", None, 8, 0, 8, 0, "WO"),
        ("b", None, 4, 0, 32, 0, "RW"),
        ("y", None, 8, 0, 8, 0, "RO"),
    ]


def test_arm_without_data_is_a_strobe_and_a_concatenation_is_unresolved():
    decode = _case(
        "case wrPntr is\n   when 7 => v.g := '1';\nend case;\n"
        "case rdPntr is\n   when 9 => v.axiReadSlave.rdata := r.a & r.b;\n"
        "   when 10 => v.axiReadSlave.rdata := toSlv(r.a);\n"
        "   when 11 => v.axiReadSlave.rdata := x\"DEADBEEF\";\nend case;"
    )
    assert [(s.target, s.byte_offset, s.kind) for s in decode.strobes] == [("g", 28, "write")]
    assert decode.fields == []
    assert sorted(decode.unresolved) == ["read 0x24: concatenation", "read 0x28: function call"]


def test_if_inside_an_arm_takes_the_branch_a_generic_selects():
    body = (
        "case wrPntr is\n"
        "   when 3 =>\n"
        "      if (MODE_G = \"A\") then\n"
        "         v.a := regWrData(7 downto 0);\n"
        "      else\n"
        "         v.b := regWrData;\n"
        "      end if;\n"
        "   when 4 =>\n"
        "      if (regWrData /= x\"FFFFFFFF\") then\n"
        "         v.b := regWrData;\n"
        "      end if;\n"
        "end case;"
    )
    assert [f.target for f in _case(body).fields] == ["a", "b"]
    assert [f.target for f in _case(body, generics={"MODE_G": "B"}).fields] == ["b", "b"]


def test_for_loop_inside_an_arm_evaluates_every_value():
    decode = _case(
        "case wrPntr is\n"
        "   when 127 =>\n"
        "      for j in 0 to N_G-1 loop\n"
        "         v.x(j) := regWrData(j);\n"
        "      end loop;\n"
        "end case;"
    )
    assert _cases(decode) == [("x", j, 0x1FC, j, 1, 0, "WO") for j in range(3)]


# ---------------------------------------------------------------------------
# Evaluator and widths
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("number, expected", [(0, 1), (1, 1), (2, 2), (16, 5), (17, 5)])
def test_bit_size_follows_the_surf_definition(number, expected):
    assert vhdl_registers.bit_size(number) == expected
    tokens = vhdl_registers.tokenize(f"bitSize({number})")
    assert vhdl_registers.evaluate(tokens, {}) == expected


def test_unresolved_width_is_listed_for_an_undeclared_target():
    decode = _parse(body='axiSlaveRegister(ep, X"00", 0, v.mystery);\naxiSlaveRegister(ep, X"04", 0, v.g);')
    assert [(f.target, f.width) for f in decode.fields] == [("mystery", None), ("g", 1)]
    assert decode.unresolved == ["mystery"]


def test_two_disagreeing_declarations_leave_the_width_unresolved():
    decode = _parse(
        body='axiSlaveRegister(ep, X"00", 0, v.twice);',
        architecture="type A is record twice : slv(3 downto 0); end record;\n"
                     "type B is record twice : slv(7 downto 0); end record;\n",
    )
    assert [(f.target, f.width) for f in decode.fields] == [("twice", None)]
    assert decode.unresolved == ["twice"]


def test_evaluator_never_runs_text():
    with pytest.raises(vhdl_registers.EvalError):
        vhdl_registers.evaluate(vhdl_registers.tokenize('__import__("os").system("true")'), {})
    with pytest.raises(vhdl_registers.EvalError):
        vhdl_registers.evaluate(vhdl_registers.tokenize("open(1)"), {})
    source = Path(vhdl_registers.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\b(eval|exec)\(", source)


def test_tokenizing_is_linear_on_hostile_text():
    started = time.monotonic()
    for text in ('"' * 4001, "'" * 4000, "a" * 100000, "-- " + "x" * 100000, 'x"' + "1" * 50000):
        try:
            vhdl_registers.tokenize(text)
        except ValueError:
            pass
    assert time.monotonic() - started < 5
