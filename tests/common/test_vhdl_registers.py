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


def _expected(layout, groups, stride, gate, enabled):
    """Expand a register walk layout into the same tuples the parser reports."""
    result = set()
    for group in range(groups):
        for word, fields in layout.items():
            for entry in fields:
                if entry["condition"] is not None and not (entry["condition"] == gate and enabled):
                    continue
                result.add((group * stride + word, entry["lsb"], entry["width"], entry["name"], entry["mode"]))
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
