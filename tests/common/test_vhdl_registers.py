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

# Targets whose width the parser cannot resolve, per decode file, at default
# generics. An empty set means every width resolves; a parser change that
# resolves or loses one changes the set and fails the pin test.
UNRESOLVED_TARGETS = {
    TIMINGRX: frozenset(),
    GTHALIGN: frozenset(),
    EVRV2AXI: frozenset(),
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


def _parse(body="", declarations="", concurrent="", architecture="", generics=None):
    source = UNIT.format(body=body, declarations=declarations, concurrent=concurrent, architecture=architecture)
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
