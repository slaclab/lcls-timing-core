#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Compare one register block across its VHDL decode, PyRogue tree, and YAML map.

Every source is reduced to ``RegField`` records. ``compare`` matches fields by
exact name, then through the per-block name map, and reports the differences as
``Drift`` records keyed by (block, field, kind). Positions are compared as the
absolute bit position, byte offset * 8 + bit offset, so Rogue's word alignment
of offsets never shows up as drift: equal positions are no drift, a different
32-bit word is kind ``offset``, and the same word with a different bit is kind
``bitOffset``.

``verdict`` applies the allowlist contract: a drift that is not listed fails,
and a listed entry that no longer drifts fails, so the list shrinks when a
fix lands. Every allowlist value links an issue, or is the pending
placeholder until the finding behind it is filed. ``compare_block`` and
``format_report`` describe what was compared and write the drift report. The
module uses only the standard library, so the engine runs without Rogue.
"""

import os
import re
import tempfile
from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Optional, Tuple

BITS_PER_BYTE = 8
WORD_BITS = 32

KINDS = (
    "offset",
    "bitOffset",
    "bitSize",
    "mode",
    "missing-in-vhdl",
    "missing-in-python",
    "missing-in-yaml",
)

SOURCES = ("python", "vhdl", "yaml")

# A block-level finding stands in for field comparisons against a source that
# cannot be read (a YAML map that does not parse): the field is one of these
# keys and the kind is the value.
BLOCK_SENTINELS = {"<yaml>": "missing-in-yaml", "<vhdl>": "missing-in-vhdl"}

STROBE_SUFFIXES = ("!write", "!read")

INDEX_GROUP_RE = re.compile(r"\[(\d+)\]")
# Several index groups in one path (a child array holding an array) combine as
# outer * INDEX_RADIX + inner; the radix exceeds every array length in the maps.
INDEX_RADIX = 4096

ISSUE_URL_RE = re.compile(r"^https://github\.com/slaclab/lcls-timing-core/issues/\d+$")
PENDING_ISSUE = "pending"
REQUIRE_FILED_ISSUES = True


@dataclass(frozen=True)
class RegField:
    block: str
    name: str
    index: Optional[int]
    byte_offset: int
    bit_offset: int
    bit_size: Optional[int]
    mode: str
    source: str
    line: int
    readable: bool
    writable: bool

    @property
    def abs_bit(self) -> int:
        return self.byte_offset * BITS_PER_BYTE + self.bit_offset

    @property
    def word_byte(self) -> int:
        return (self.abs_bit // WORD_BITS) * 4

    @property
    def bit_in_word(self) -> int:
        return self.abs_bit % WORD_BITS


def split_index(path: str) -> Tuple[str, Optional[int]]:
    """Return (name without index groups, element index) for a variable path.

    ``Name[3]`` is ("Name", 3) and ``Group[2].Name`` is ("Group.Name", 2), so
    the allowlist key names a field once however many elements drift.
    """
    groups = INDEX_GROUP_RE.findall(path)
    index: Optional[int] = None
    for group in groups:
        index = int(group) if index is None else index * INDEX_RADIX + int(group)
    return INDEX_GROUP_RE.sub("", path), index


class Drift(NamedTuple):
    block: str
    field: str
    kind: str
    detail: str


@dataclass(frozen=True)
class Variant:
    id: str
    python_args: dict
    generics: dict
    compare_yaml: bool


@dataclass(frozen=True)
class Block:
    name: str
    vhdl: Optional[str]
    yaml: Optional[str]
    variants: Tuple[Variant, ...]
    vhdl_window: Optional[Tuple[int, int]] = None
    python_source: str = "tree"


def _single(generics: dict, python_args: Optional[dict] = None, compare_yaml: bool = True) -> Tuple[Variant, ...]:
    return (Variant("default", python_args or {}, generics, compare_yaml),)


# Each block names one variant that is compared with the YAML map: the one
# whose arguments enable every optional register, because the map has no
# conditional fields.
BLOCKS = {
    "EvrV2TriggerReg": Block(
        "EvrV2TriggerReg",
        "LCLS-II/evr/rtl/EvrV2TrigReg.vhd",
        "EvrV2TriggerReg.yaml",
        (
            Variant("default", {}, {"TRIGGERS_C": 1, "USE_TAP_C": False, "EVR_CARD_G": False}, False),
            Variant("useTap", {"useTap": True}, {"TRIGGERS_C": 1, "USE_TAP_C": True, "EVR_CARD_G": False}, True),
        ),
    ),
    "EvrV2ChannelReg": Block(
        "EvrV2ChannelReg",
        "LCLS-II/evr/rtl/EvrV2ChannelReg.vhd",
        "EvrV2ChannelReg.yaml",
        (
            Variant("default", {}, {"NCHANNELS_G": 1, "EVR_CARD_G": False, "DMA_ENABLE_G": False}, False),
            Variant("dmaEnable", {"dmaEnable": True},
                    {"NCHANNELS_G": 1, "EVR_CARD_G": False, "DMA_ENABLE_G": True}, True),
        ),
    ),
    # The Python class declares twelve channels, and the RTL decodes only the
    # control and channel words below 0x200; the trigger section at 0x200 has
    # no RTL in this repository.
    "EvrV2Core": Block(
        "EvrV2Core",
        "LCLS-II/evr/rtl/EvrV2Axi.vhd",
        "EvrV2Core.yaml",
        _single({"DMA_ENABLE_G": True, "CHANNELS_C": 12}),
        vhdl_window=(0x000, 0x1FF),
    ),
    "EvrV1Isr": Block(
        "EvrV1Isr", "LCLS-I/evr/EvrV1CoreIsrCtrl.vhd", "EvrV1Isr.yaml", _single({}),
    ),
    "GthRxAlignCheck": Block(
        "GthRxAlignCheck", "LCLS-II/core/rtl/GthRxAlignCheck.vhd", "GthRxAlignCheck.yaml", _single({}),
    ),
    # The RW or RO mode of three registers follows the clock select mode, and
    # the YAML map describes the selectable one.
    "TimingFrameRx": Block(
        "TimingFrameRx",
        "LCLS-II/core/rtl/TimingRx.vhd",
        "TimingFrameRx.yaml",
        (
            Variant("SELECT", {"clkselMode": "SELECT"}, {"CLKSEL_MODE_G": "SELECT"}, True),
            Variant("LCLSII", {"clkselMode": "LCLSII"}, {"CLKSEL_MODE_G": "LCLSII"}, False),
        ),
    ),
    # The default of two BSA arrays is the count the YAML map anchors.
    "TPGMiniCore": Block(
        "TPGMiniCore",
        "LCLS-II/core/rtl/TPGMiniReg.vhd",
        "TPGMiniCore.yaml",
        (
            Variant("default", {}, {"NARRAYS_BSA": 2}, True),
            Variant("narrays1", {"NARRAYSBSA": 1}, {"NARRAYS_BSA": 1}, False),
            Variant("narrays4", {"NARRAYSBSA": 4}, {"NARRAYS_BSA": 4}, False),
        ),
    ),
    "TPGControl": Block("TPGControl", None, "TPGControl.yaml", _single({})),
    "LclsTriggerPulse": Block("LclsTriggerPulse", None, "LclsTriggerPulse.yaml", _single({})),
    # Sixteen trigger and channel groups, the count the YAML map anchors, with
    # every optional register of the groups present.
    "EvrV2CoreTriggers": Block(
        "EvrV2CoreTriggers",
        None,
        "EvrV2CoreTriggers.yaml",
        _single({}, {"numTrig": 16, "dmaEnable": True, "useTap": True}),
    ),
    # Rogue rejects these five classes (or cannot build their composite), so
    # their declarations are read from source instead of a built tree.
    "EvrV1Reg": Block(
        "EvrV1Reg", "LCLS-I/evr/EvrV1Reg.vhd", "EvrV1Reg.yaml", _single({}), python_source="ast",
    ),
    "TPGStatus": Block("TPGStatus", None, "TPGStatus.yaml", _single({}), python_source="ast"),
    "TPGSeqJump": Block("TPGSeqJump", None, "TPGSeqJump.yaml", _single({}), python_source="ast"),
    "TPGSeqState": Block("TPGSeqState", None, "TPGSeqState.yaml", _single({}), python_source="ast"),
    "TPG": Block("TPG", None, "TPG.yaml", _single({}), python_source="ast"),
}

# Classes with no map or decode file of their own: every register they hold
# belongs to a child class that is compared directly.
COVERED_BY_LEAVES = {
    "EvrV2CoreChannels": "no YAML map and no decode file; its only child EvrV2ChannelReg is compared directly",
}

# python name -> {"vhdl": name, "yaml": name}; a missing source key means the
# name is the same in that source. A VHDL name such as "eventCount[12]" pairs
# one element of an RTL array with a single Python variable, and a name such
# as "pulseId@0x58" is one of several decodes of the same RTL target. A key
# that is no Python variable (VersionErr) names a register only the YAML map
# and the RTL carry, so it can be paired with its RTL name.
NAME_MAPS: Dict[str, Dict[str, Dict[str, str]]] = {
    "EvrV2TriggerReg": {
        # The RTL record names the trigger enable "enabled" and the source
        # select "channel"; the CPSW map calls the trigger enable "Enable".
        "EnableTrig": {"vhdl": "enabled", "yaml": "Enable"},
        "Source": {"vhdl": "channel"},
        "Polarity": {"vhdl": "polarity"},
        "ComplEn": {"vhdl": "complEn"},
        "ComplAnd": {"vhdl": "complAnd"},
        "Delay": {"vhdl": "delay"},
        "Width": {"vhdl": "width"},
        "DelayTap": {"vhdl": "delayTap"},
        "DelayTapReadback": {"vhdl": "delay_rd"},
    },
    "EvrV2ChannelReg": {
        "EnableReg": {"vhdl": "enabled", "yaml": "Enable"},
        "BsaEnabled": {"vhdl": "bsaEnabled"},
        "dmaEnabled": {"vhdl": "dmaEnabled", "yaml": "DmaEnabled"},
        # Python splits the RTL rate select into RateSel and RateType and the
        # destination select into DestSel and DestType. The first name listed
        # owns the RTL field; the type variables are the extra high bits.
        "RateSel": {"vhdl": "rateSel"},
        "RateType": {"vhdl": "rateSel"},
        "DestSel": {"vhdl": "destSel"},
        "DestType": {"vhdl": "destSel"},
        "Count": {"vhdl": "eventCount"},
        "BsaWindowDelay": {"vhdl": "bsaActiveDelay"},
        "BsaWindowSetup": {"vhdl": "bsaActiveSetup"},
        "BsaWindowWidth": {"vhdl": "bsaActiveWidth"},
    },
    "EvrV2Core": {
        "IrqEnable": {"vhdl": "irqEnable"},
        # The decode reports the interrupt request through its local register
        # "sReg"; the testbench signal for it is irqReq.
        "IrqStatus": {"vhdl": "sReg"},
        "gtxDebug": {"yaml": "GtxDebug"},
        "CountReset": {"vhdl": "countReset"},
        "ModeSel": {"vhdl": "trigSel"},
        "DmaFullThr": {"vhdl": "dmaFullThr"},
        "ChannelEnable": {"vhdl": "enabled"},
        "ChannelBsaEnable": {"vhdl": "bsaEnabled"},
        "ChannelDmaEnable": {"vhdl": "dmaEnabled"},
        "ChannelRateSel": {"vhdl": "rateSel"},
        "ChannelDestSel": {"vhdl": "destSel"},
        "ChannelEventCnt": {"vhdl": "eventCount"},
        "ChannelBsaDelay": {"vhdl": "bsaActiveDelay"},
        "ChannelBsaSetup": {"vhdl": "bsaActiveSetup"},
        "ChannelBsaWidth": {"vhdl": "bsaActiveWidth"},
        # The global count is the thirteenth entry of the RTL event count mux.
        "GlobalEventCnt": {"vhdl": "eventCount[12]"},
        # The trigger section has no RTL in this repository; these are the
        # EvrV2TrigReg names the earlier testbench paired with it.
        "TriggerChannel": {"vhdl": "channel"},
        "TriggerPolarity": {"vhdl": "polarity"},
        "TriggerEnable": {"vhdl": "enabled"},
        "TriggerDelay": {"vhdl": "delay"},
        "TriggerFineDelay": {"vhdl": "delayTap"},
    },
    "EvrV1Isr": {
        "IsrSelect": {"vhdl": "isrSelect"},
    },
    "GthRxAlignCheck": {
        # The RTL stores 40 phase samples of 8 bits; the YAML map keeps the
        # Python name for them.
        "PhaseCount": {"vhdl": "sample"},
        "PhaseTarget": {"vhdl": "tgt"},
        "Mask": {"vhdl": "mask", "yaml": "PhaseMask"},
        "ResetLen": {"vhdl": "rstlen"},
        "LastPhase": {"vhdl": "last"},
        # Python declares the raw counters; TxClkFreq and RxClkFreq are
        # LinkVariables that convert them, and the YAML map holds the raw
        # register under the converted name.
        "TxClkFreqRaw": {"vhdl": "txClkFreq", "yaml": "TxClkFreq"},
        "RxClkFreqRaw": {"vhdl": "rxClkFreq", "yaml": "RxClkFreq"},
    },
    "TimingFrameRx": {
        "sofCount": {"vhdl": "axilStatusCounters12[0]"},
        "eofCount": {"vhdl": "axilStatusCounters12[1]"},
        "FidCount": {"vhdl": "axilStatusCounters12[2]"},
        "CrcErrCount": {"vhdl": "axilStatusCounters12[3]"},
        "RxClkCount": {"vhdl": "axilStatusCounters3[0]"},
        "RxRstCount": {"vhdl": "axilStatusCounters3[1]"},
        "RxDecErrCount": {"vhdl": "axilStatusCounters3[2]"},
        "RxDspErrCount": {"vhdl": "axilStatusCounters3[3]"},
        "BypassDoneCount": {"vhdl": "rxStatusCount[0]"},
        "BypassResetCount": {"vhdl": "rxStatusCount[1]"},
        "TxClkCount": {"vhdl": "txClkCntS"},
        "ClearRxCounters": {"vhdl": "cntRst", "yaml": "RxCountReset"},
        "RxLinkUp": {"vhdl": "axilRxLinkUp"},
        "RxPolarity": {"vhdl": "polarity"},
        "C_RxReset": {"vhdl": "reset", "yaml": "RxReset"},
        "ClkSel": {"vhdl": "clkSel"},
        "RxDown": {"vhdl": "rxDown"},
        "BypassRst": {"vhdl": "bufferByRst"},
        "RxPllReset": {"vhdl": "pllReset", "yaml": "RxPLLReset"},
        "ModeSel": {"vhdl": "modeSel"},
        "ModeSelEn": {"vhdl": "modeSelEn"},
        "MsgDelay": {"vhdl": "messageDelay"},
        # Registers the YAML map and the RTL carry and Python does not.
        "VersionErr": {"vhdl": "axilVsnErr"},
        "MsgNoDelay": {"vhdl": "streamNoDelay"},
        "MsgDelayRst": {"vhdl": "messageDelayRst"},
        "FrameVersion": {"vhdl": "axilVersion"},
    },
    "TPGMiniCore": {
        "TxPolarity": {"vhdl": "txPolarity"},
        "TxLoopback": {"vhdl": "txLoopback"},
        "TxInhibit": {"vhdl": "txInhibit"},
        "BaseControl": {"vhdl": "baseDivisor"},
        # The RTL reads the 64 bit pulse id and time stamp as two words.
        "PulseIdRd": {"vhdl": "pulseId@0x8"},
        "TStampRd": {"vhdl": "timeStamp@0x10"},
        "FixedRateDiv": {"vhdl": "FixedRateDivisors"},
        "RateReload": {"vhdl": "FixedRateDivisors!write"},
        "BsaCompleteWr": {"vhdl": "bsaClear"},
        "BsaCompleteRd": {"vhdl": "bsaComplete"},
        "PulseIdWr": {"vhdl": "pulseId@0x58"},
        "TStampWr": {"vhdl": "timeStamp@0x60"},
        "TxReset": {"vhdl": "txReset"},
        "CountIntervalReset": {"vhdl": "intervalRst"},
        "PulseIdSet": {"vhdl": "pulseIdWrEn"},
        "TStampSet": {"vhdl": "timeStampWrEn"},
        # The first write of the Lcls1 BSA block raises the RTL edef strobe.
        "Lcls1BsaStart": {"vhdl": "wrEn!write"},
        # The RTL spells these bsaDef targets with mixed case in the case
        # decode (bsadefRateMode, bsadefDestInclM, bsadefNToAvg).
        "BsaActive": {"vhdl": "init"},
        "BsaRateSelMode": {"vhdl": "bsadefRateMode"},
        "BsaFixedRate": {"vhdl": "bsaDefFixedRate"},
        "BsaACRate": {"vhdl": "bsaDefACRate"},
        "BsaACTSMask": {"vhdl": "bsaDefACTSMask"},
        "BsaSequenceSelect": {"vhdl": "bsaDefSeqSel"},
        "BsaSequenceBitSelect": {"vhdl": "bsaDefSeqBit"},
        "BsaDestMode": {"vhdl": "bsaDefDestMode"},
        "BsaDestInclusiveMask": {"vhdl": "bsadefDestInclM"},
        "BsaDestExclusiveMask": {"vhdl": "bsaDefDestExclM"},
        "BsaNtoAvg": {"vhdl": "bsadefNToAvg"},
        "BsaMaxSeverity": {"vhdl": "bsaDefMaxSevr"},
        "BsaAvgToWr": {"vhdl": "bsaDefAvgToWr"},
        "ClkCnt": {"vhdl": "count186M"},
        "SyncErrCnt": {"vhdl": "countSyncE"},
        "PllCnt": {"vhdl": "pllChanged"},
        "CountInterval": {"vhdl": "interval"},
        "BaseRateCount": {"vhdl": "countBRT"},
    },
    "EvrV1Reg": {
        "Status": {"vhdl": "statusReg"},
        "Control": {"vhdl": "controlReg"},
        # The interrupt flag word at 0x08 is written as irqClr1 and read as
        # intFlag; the YAML map has one read-write IrqFlag for both.
        "IrqFlagWr": {"vhdl": "irqClr1", "yaml": "IrqFlag"},
        "IrqFlagRd": {"vhdl": "intFlag"},
        "IrqEnable": {"vhdl": "intControl"},
        "PulseIrqMap": {"vhdl": "hardwareInt"},
        # The word at 0x14 is written whole and read as three slices, with the
        # interrupt active flag in bit 1.
        "PcieIntEna": {"vhdl_pieces": ["pcieIntEna@0x14.0", "pcieIntEna", "irqActive", "pcieIntEna@0x14.2"]},
        "FWVersion": {"vhdl": "fwVersion@0x2c"},
        # The word at 0x30 is the firmware version with its four bytes swapped.
        "FWVersionUnmasked": {
            "vhdl_pieces": ["fwVersion@0x30.0", "fwVersion@0x30.8", "fwVersion@0x30.16", "fwVersion@0x30.24"]
        },
        "UsecDivider": {"vhdl": "uSecDivider"},
        "SecSR": {"vhdl": "secondsShift"},
        # The 64 bit time stamp is read as two words, seconds then counter.
        "SecCounter": {"vhdl": "ts@0x60"},
        "EventCounter": {"vhdl": "ts@0x64"},
        "SecLatch": {"vhdl": "tsLatch@0x68"},
        "EvCntLatch": {"vhdl": "tsLatch@0x6c"},
        "IntEventEn": {"vhdl": "intEventEn"},
        "IntEventCount": {"vhdl": "intEventCount"},
        "IntEventCode": {"vhdl": "intEventCode"},
        "ExtEventEn": {"vhdl": "extEventEn"},
        "ExtEventCode": {"vhdl": "extEventCode"},
        "OutputMap": {"vhdl": "outputMap"},
        # Each pulse generator is four words: control, prescale, delay, width.
        **{
            f"Pulse{pulse:02d}": {
                "vhdl_elements": [f"{word}[{pulse}]" for word in
                                  ("pulseControl", "pulsePrescale", "pulseDelay", "pulseWidth")]
            }
            for pulse in range(12)
        },
        # Registers only the RTL decodes, joined into one field each: the
        # data buffer control word at 0x20 and the time stamp FIFO at 0x70.
        "DataBufferControl": {"vhdl_pieces": ["rxSize", "dben", "dbcs", "dbdis", "dbrdy", "dbena", "dbrx"]},
        "TimestampFifo": {"vhdl_pieces": ["tsFifoTsLow", "tsFifoTsHigh", "tsFifoEventCode"]},
    },
    "EvrV2CoreTriggers": {
        "EvrV2ChannelReg.EnableReg": {"yaml": "EvrV2ChannelReg.Enable"},
        "EvrV2ChannelReg.dmaEnabled": {"yaml": "EvrV2ChannelReg.DmaEnabled"},
        "EvrV2TriggerReg.EnableTrig": {"yaml": "EvrV2TriggerReg.Enable"},
    },
}

# (block, field, kind) -> issue link. field has the [i] index stripped, and a
# field of a child group carries the group name (EvrV2ChannelReg.RateSel).
# Every entry links a filed issue, or the placeholder PENDING_ISSUE until the
# finding behind it is filed. The list is reviewed by hand and shrinks when a
# fix lands; it is never generated by a test.
_ISSUE_214 = "https://github.com/slaclab/lcls-timing-core/issues/214"
_ISSUE_215 = "https://github.com/slaclab/lcls-timing-core/issues/215"
_ISSUE_217 = "https://github.com/slaclab/lcls-timing-core/issues/217"
_ISSUE_218 = "https://github.com/slaclab/lcls-timing-core/issues/218"
_ISSUE_222 = "https://github.com/slaclab/lcls-timing-core/issues/222"
_ISSUE_223 = "https://github.com/slaclab/lcls-timing-core/issues/223"
_ISSUE_224 = "https://github.com/slaclab/lcls-timing-core/issues/224"
_ISSUE_225 = "https://github.com/slaclab/lcls-timing-core/issues/225"
_ISSUE_226 = "https://github.com/slaclab/lcls-timing-core/issues/226"
_ISSUE_227 = "https://github.com/slaclab/lcls-timing-core/issues/227"
_ISSUE_228 = "https://github.com/slaclab/lcls-timing-core/issues/228"

ALLOWLIST: Dict[Tuple[str, str, str], str] = {
    # EvrV2TriggerReg: the Python variables sit one bit above the RTL decode
    # and the YAML map.
    ("EvrV2TriggerReg", "ComplEn", "bitOffset"): _ISSUE_214,
    ("EvrV2TriggerReg", "ComplAnd", "bitOffset"): _ISSUE_214,
    # EvrV2CoreTriggers repeats the same two variables for each trigger group.
    ("EvrV2CoreTriggers", "EvrV2TriggerReg.ComplEn", "bitOffset"): _ISSUE_214,
    ("EvrV2CoreTriggers", "EvrV2TriggerReg.ComplAnd", "bitOffset"): _ISSUE_214,

    # EvrV2ChannelReg: Python declares the rate select as 11 bits plus a 2 bit
    # type and the destination select as 16 bits plus a 2 bit type, where the
    # RTL decode and the YAML map hold one 13 bit and one 19 bit field. The
    # two type variables have no counterpart of their own.
    ("EvrV2ChannelReg", "RateSel", "bitSize"): _ISSUE_215,
    ("EvrV2ChannelReg", "DestSel", "bitSize"): _ISSUE_215,
    ("EvrV2ChannelReg", "RateType", "missing-in-vhdl"): _ISSUE_215,
    ("EvrV2ChannelReg", "RateType", "missing-in-yaml"): _ISSUE_215,
    ("EvrV2ChannelReg", "DestType", "missing-in-vhdl"): _ISSUE_215,
    ("EvrV2ChannelReg", "DestType", "missing-in-yaml"): _ISSUE_215,
    # EvrV2CoreTriggers repeats the same variables for each channel group.
    ("EvrV2CoreTriggers", "EvrV2ChannelReg.RateSel", "bitSize"): _ISSUE_215,
    ("EvrV2CoreTriggers", "EvrV2ChannelReg.DestSel", "bitSize"): _ISSUE_215,
    ("EvrV2CoreTriggers", "EvrV2ChannelReg.RateType", "missing-in-yaml"): _ISSUE_215,
    ("EvrV2CoreTriggers", "EvrV2ChannelReg.DestType", "missing-in-yaml"): _ISSUE_215,

    # EvrV2Core: channel field widths and channel count differ from the RTL
    # decode and the YAML map. ChannelEnable and ChannelRateSel are declared
    # for channel 0 only, so channels 1 to 11 are missing in Python.
    ("EvrV2Core", "ChannelBsaSetup", "bitSize"): _ISSUE_215,
    ("EvrV2Core", "ChannelDestSel", "bitSize"): _ISSUE_215,
    ("EvrV2Core", "ChannelEnable", "missing-in-python"): _ISSUE_215,
    ("EvrV2Core", "ChannelRateSel", "missing-in-python"): _ISSUE_215,
    # EvrV2Core questions: the event counts are read-write in Python and
    # read-only in the RTL; the YAML map has a LinkAddr register at 0x08 that
    # Python comments out and the RTL does not decode; the YAML map puts the
    # trigger delay at 0x204 and a trigger width at 0x208, while Python puts
    # the trigger delay at 0x208 and has no width (no RTL in this repository
    # decodes the trigger section).
    ("EvrV2Core", "ChannelEventCnt", "mode"): _ISSUE_217,
    ("EvrV2Core", "GlobalEventCnt", "mode"): _ISSUE_217,
    ("EvrV2Core", "LinkAddr", "missing-in-python"): _ISSUE_228,
    ("EvrV2Core", "LinkAddr", "missing-in-vhdl"): _ISSUE_228,
    ("EvrV2Core", "TriggerDelay", "offset"): _ISSUE_217,
    ("EvrV2Core", "TriggerWidth", "missing-in-python"): _ISSUE_217,

    # GthRxAlignCheck: Python declares 64 phase counters of 32 bits at a
    # stride of 4 bytes, read only, while the RTL and the YAML map hold 40
    # samples of 8 bits packed four to a word.
    ("GthRxAlignCheck", "PhaseCount", "offset"): _ISSUE_224,
    ("GthRxAlignCheck", "PhaseCount", "bitSize"): _ISSUE_224,
    ("GthRxAlignCheck", "PhaseCount", "mode"): _ISSUE_228,
    ("GthRxAlignCheck", "PhaseCount", "missing-in-vhdl"): _ISSUE_224,
    ("GthRxAlignCheck", "PhaseCount", "missing-in-yaml"): _ISSUE_224,
    # GthRxAlignCheck question: Python and the YAML map show the last phase as
    # a 7 bit read-only field, the RTL stores 16 bits behind a read-write
    # decode.
    ("GthRxAlignCheck", "LastPhase", "bitSize"): _ISSUE_228,
    ("GthRxAlignCheck", "LastPhase", "mode"): _ISSUE_228,

    # TimingFrameRx questions: the YAML map has no write-only mode, so three
    # Python write-only strobes read read-write there; and four registers
    # that the RTL decodes and the YAML map lists (the frame version and the
    # message delay controls) have no Python variable, as does the gray coded
    # time stamp event counter at 0x40 that only the RTL decodes.
    ("TimingFrameRx", "C_RxReset", "mode"): _ISSUE_228,
    ("TimingFrameRx", "ClearRxCounters", "mode"): _ISSUE_228,
    ("TimingFrameRx", "RxPllReset", "mode"): _ISSUE_228,
    ("TimingFrameRx", "FrameVersion", "missing-in-python"): _ISSUE_228,
    ("TimingFrameRx", "MsgDelayRst", "missing-in-python"): _ISSUE_228,
    ("TimingFrameRx", "MsgNoDelay", "missing-in-python"): _ISSUE_228,
    ("TimingFrameRx", "VersionErr", "missing-in-python"): _ISSUE_228,
    ("TimingFrameRx", "timingTSEvCntGray_o", "missing-in-python"): _ISSUE_228,
    ("TimingFrameRx", "timingTSEvCntGray_o", "missing-in-yaml"): _ISSUE_228,

    # TPGMiniCore defects: BsaActive uses a one byte stride where the RTL has
    # one bit per sequence in a single word, and BsaAvgToWr uses a stride of 8
    # bytes where every other field of the BSA definition uses 16. The fixed
    # rate divisors are 32 bits in Python and the YAML map and 20 bits in the
    # RTL.
    ("TPGMiniCore", "BsaActive", "bitOffset"): _ISSUE_223,
    ("TPGMiniCore", "BsaAvgToWr", "offset"): _ISSUE_222,
    ("TPGMiniCore", "FixedRateDiv", "bitSize"): _ISSUE_225,
    # TPGMiniCore questions: six Python write-only variables read read-write
    # in the YAML map (it has no write-only mode); three Python read-write
    # strobes are write-only in the RTL; and the 64 BSA status words at 0x400
    # that the RTL reads have no Python variable and no YAML entry.
    ("TPGMiniCore", "BsaCompleteWr", "mode"): _ISSUE_228,
    ("TPGMiniCore", "CountIntervalReset", "mode"): _ISSUE_228,
    ("TPGMiniCore", "PulseIdWr", "mode"): _ISSUE_228,
    ("TPGMiniCore", "RateReload", "mode"): _ISSUE_228,
    ("TPGMiniCore", "TStampWr", "mode"): _ISSUE_228,
    ("TPGMiniCore", "TxReset", "mode"): _ISSUE_228,
    ("TPGMiniCore", "Lcls1BsaStart", "mode"): _ISSUE_228,
    ("TPGMiniCore", "PulseIdSet", "mode"): _ISSUE_228,
    ("TPGMiniCore", "TStampSet", "mode"): _ISSUE_228,
    ("TPGMiniCore", "bsastatus", "missing-in-python"): _ISSUE_228,
    ("TPGMiniCore", "bsastatus", "missing-in-yaml"): _ISSUE_228,

    # EvrV1Reg: the interrupt flag word at 0x08 is declared as a write-only
    # IrqFlagWr and a read-only IrqFlagRd on the same bits, where the YAML map
    # has one read-write IrqFlag.
    ("EvrV1Reg", "IrqFlagWr", "mode"): _ISSUE_217,
    ("EvrV1Reg", "IrqFlagRd", "missing-in-yaml"): _ISSUE_217,
    # EvrV1Reg question: the RTL reads bit 31 of that word as zero (31 bits).
    ("EvrV1Reg", "IrqFlagRd", "bitSize"): _ISSUE_217,
    # EvrV1Reg defects: the internal event enable is 32 bits in Python and the
    # YAML map and 1 bit in the RTL, and the internal event count is 1 bit
    # against 32 (the widths look swapped); the output map is one 16 bit entry
    # per word in Python, while the RTL packs two entries per word, the lower
    # numbered entry in the upper half.
    ("EvrV1Reg", "IntEventEn", "bitSize"): _ISSUE_226,
    ("EvrV1Reg", "IntEventCount", "bitSize"): _ISSUE_226,
    ("EvrV1Reg", "OutputMap", "offset"): _ISSUE_227,
    ("EvrV1Reg", "OutputMap", "bitOffset"): _ISSUE_227,
    # EvrV1Reg question: sixteen arrays in the YAML map give a number of
    # elements and no stride (twelve pulse generators, the output map, and the
    # two map RAMs), so every element sits at the first address; the CPSW
    # default stride is not known here.
    **{("EvrV1Reg", f"Pulse{pulse:02d}", "offset"): _ISSUE_228 for pulse in range(12)},
    # EvrV1Reg questions: the YAML map lists two map RAMs that Python leaves
    # out and the RTL decodes as memory windows (the second RAM is at 0x6000 in
    # the map and at 0x5000 in the RTL); the RTL decodes a data buffer control
    # word at 0x20 and a time stamp FIFO at 0x70 that neither Python nor the
    # YAML map declare.
    ("EvrV1Reg", "MapRam1", "missing-in-python"): _ISSUE_228,
    ("EvrV1Reg", "MapRam1", "missing-in-vhdl"): _ISSUE_228,
    ("EvrV1Reg", "MapRam2", "missing-in-python"): _ISSUE_228,
    ("EvrV1Reg", "MapRam2", "missing-in-vhdl"): _ISSUE_228,
    ("EvrV1Reg", "DataBufferControl", "missing-in-python"): _ISSUE_228,
    ("EvrV1Reg", "DataBufferControl", "missing-in-yaml"): _ISSUE_228,
    ("EvrV1Reg", "TimestampFifo", "missing-in-python"): _ISSUE_228,
    ("EvrV1Reg", "TimestampFifo", "missing-in-yaml"): _ISSUE_228,

    # TPGStatus question: the YAML map gives the trigger counts a misspelled
    # stride key, so its elements all sit at the first address.
    ("TPGStatus", "CountTrig", "offset"): _ISSUE_228,

    # The YAML maps that do not parse: nothing in these blocks can be
    # compared with them.
    ("TPGControl", "<yaml>", "missing-in-yaml"): _ISSUE_218,
    ("TPGSeqState", "<yaml>", "missing-in-yaml"): _ISSUE_218,
    ("TPG", "<yaml>", "missing-in-yaml"): _ISSUE_218,
}


def _mode(readable: bool, writable: bool) -> str:
    if readable and writable:
        return "RW"
    return "RO" if readable else "WO"


def _merge_words(fields):
    """Join the 32 bit words of one target that sit back to back.

    A 64 bit register read as two words is one register, so it is one field
    of twice the width. Only the same target and element, the same access, and
    a full word before the join qualify.
    """
    merged = []
    for field in sorted(fields, key=lambda f: (f.target, -1 if f.index is None else f.index,
                                               f.byte_offset * BITS_PER_BYTE + f.bit_offset)):
        previous = merged[-1] if merged else None
        if (
            previous is not None
            and previous.target == field.target
            and previous.index == field.index
            and previous.readable == field.readable
            and previous.writable == field.writable
            and previous.width % WORD_BITS == 0
            and field.width == WORD_BITS
            and field.bit_offset == 0
            and previous.bit_offset == 0
            and (field.target_low == 0 == previous.target_low or field.target_low == previous.target_low + previous.width)
            and field.byte_offset * BITS_PER_BYTE + field.bit_offset
            == previous.byte_offset * BITS_PER_BYTE + previous.bit_offset + previous.width
        ):
            merged[-1] = previous._replace(width=previous.width + field.width)
        else:
            merged.append(field)
    return merged


def from_vhdl(decode, block: str) -> List[RegField]:
    """Adapt a vhdl_registers.Decode into RegFields.

    Words of one target that sit back to back are one wider field. Fields
    that still share a target and element are named ``target@0xADDR``, with
    ``.BIT`` added when two share an address, so each keeps its own place. A loop index is kept as the element index only when
    the same target is decoded more than once, so a one-trigger decode lines
    up with scalar Python variables and a many-element decode lines up with
    Name[i]. A write or read strobe becomes a field named ``target!write`` or
    ``target!read`` with no width; a strobe nothing else names is a side
    effect of an access, not a register, and is never reported on its own.
    """
    fields = _merge_words(decode.fields)
    seen: Dict[Tuple[str, Optional[int]], int] = {}
    for field in fields:
        seen[(field.target, field.index)] = seen.get((field.target, field.index), 0) + 1
    names = {}
    for field in fields:
        if seen[(field.target, field.index)] == 1:
            names[id(field)] = field.target
        else:
            names[id(field)] = f"{field.target}@{field.byte_offset:#x}"
    taken: Dict[str, int] = {}
    for field in fields:
        taken[names[id(field)]] = taken.get(names[id(field)], 0) + 1
    for field in fields:
        if taken[names[id(field)]] > 1 and seen[(field.target, field.index)] > 1:
            names[id(field)] = f"{names[id(field)]}.{field.bit_offset}"
    counts: Dict[str, int] = {}
    for field in fields:
        counts[names[id(field)]] = counts.get(names[id(field)], 0) + 1
    adapted = [
        RegField(
            block=block,
            name=names[id(field)],
            index=field.index if counts[names[id(field)]] > 1 else None,
            byte_offset=field.byte_offset,
            bit_offset=field.bit_offset,
            bit_size=field.width,
            mode=_mode(field.readable, field.writable),
            source="vhdl",
            line=field.line,
            readable=field.readable,
            writable=field.writable,
        )
        for field in fields
    ]
    strobes: Dict[str, int] = {}
    for strobe in decode.strobes:
        label = f"{strobe.target}!{strobe.kind}"
        strobes[label] = strobes.get(label, 0) + 1
    for strobe in decode.strobes:
        label = f"{strobe.target}!{strobe.kind}"
        writable = strobe.kind == "write"
        adapted.append(
            RegField(
                block=block,
                name=label,
                index=strobe.index if strobes[label] > 1 else None,
                byte_offset=strobe.byte_offset,
                bit_offset=0,
                bit_size=None,
                mode=_mode(not writable, writable),
                source="vhdl",
                line=strobe.line,
                readable=not writable,
                writable=writable,
            )
        )
    return adapted


def from_yaml(fields, block: str) -> List[RegField]:
    """Adapt yaml_maps.YamlField records into RegFields.

    A group index in the path (``EvrV2ChannelReg[3].RateSel``) becomes the
    element index, the same way the Python side splits its paths.
    """
    adapted = []
    for field in fields:
        path = field.name if field.index is None else f"{field.name}[{field.index}]"
        name, index = split_index(path)
        adapted.append(
            RegField(
                block=block,
                name=name,
                index=index,
                byte_offset=field.byte_offset,
                bit_offset=field.bit_offset,
                bit_size=field.bit_size,
                mode=field.mode,
                source="yaml",
                line=0,
                readable=True,
                writable=field.mode == "RW",
            )
        )
    return adapted


def mode_agrees(declared: RegField, vhdl: RegField) -> bool:
    """Capability rule between a declared access mode and the RTL decode.

    RW needs the RTL readable and writable, RO needs it readable and not
    writable, and WO needs it writable. Two non-RTL sources (Python against
    YAML) compare by plain equality.
    """
    if declared.source != "vhdl" and vhdl.source != "vhdl":
        return declared.mode == vhdl.mode
    if declared.source == "vhdl":
        declared, vhdl = vhdl, declared
    if declared.mode == "RW":
        return vhdl.readable and vhdl.writable
    if declared.mode == "RO":
        return vhdl.readable and not vhdl.writable
    return vhdl.writable


def _label(field: RegField) -> str:
    return field.name if field.index is None else f"{field.name}[{field.index}]"


def _element(field: RegField) -> int:
    return field.index or 0


def _join(first: RegField, second: RegField) -> RegField:
    """Return the field that spans two pieces of one register."""
    start = min(first.abs_bit, second.abs_bit)
    sizes = (first.bit_size, second.bit_size)
    end = max(first.abs_bit + (first.bit_size or 0), second.abs_bit + (second.bit_size or 0))
    readable = first.readable or second.readable
    writable = first.writable or second.writable
    return RegField(
        block=first.block, name=first.name, index=first.index,
        byte_offset=start // BITS_PER_BYTE, bit_offset=start % BITS_PER_BYTE,
        bit_size=None if None in sizes else end - start, mode=_mode(readable, writable),
        source=first.source, line=first.line, readable=readable, writable=writable,
    )


def _routes(name_map):
    """Build the lookup from a source's own names to (Python name, element).

    A plain entry pairs one name (or one ``name[i]`` element label) with the
    Python variable. ``vhdl_elements`` lists the labels of the RTL elements
    that are the successive elements of a Python array, and ``vhdl_pieces``
    lists the RTL names that together make up one Python variable. The first
    Python variable that names an RTL name owns it.
    """
    route: Dict[str, Dict[str, Tuple[str, Optional[int]]]] = {"vhdl": {}, "yaml": {}}
    pieces = set()
    for python_name, names in name_map.items():
        for key, value in names.items():
            source = key.split("_")[0]
            if key in ("vhdl", "yaml"):
                element = 0 if value.endswith("]") else None
                route[source].setdefault(value, (python_name, element))
            elif key == "vhdl_elements":
                for element, label in enumerate(value):
                    route[source].setdefault(label, (python_name, element))
            elif key == "vhdl_pieces":
                pieces.add(python_name)
                for piece in value:
                    route[source].setdefault(piece, (python_name, None))
            else:
                raise ValueError(f"name map entry {python_name!r} has unknown key {key!r}")
    return route, pieces


def _position_kind(a: RegField, b: RegField) -> Optional[str]:
    if a.abs_bit == b.abs_bit:
        return None
    return "offset" if a.word_byte != b.word_byte else "bitOffset"


def pair_kinds(a: RegField, b: RegField) -> List[str]:
    """Return the kinds that separate two fields of one register, in report order.

    The position kind (offset or bitOffset), then bitSize, then mode: the
    same three predicates the drift comparison applies to every pair.
    """
    kinds = []
    position = _position_kind(a, b)
    if position is not None:
        kinds.append(position)
    if a.bit_size is not None and b.bit_size is not None and a.bit_size != b.bit_size:
        kinds.append("bitSize")
    if not mode_agrees(a, b):
        kinds.append("mode")
    return kinds


def group_fields(python, vhdl, yaml, name_map: Dict[str, Dict[str, object]]):
    """Pair the fields of the sources that are present.

    Returns {Python name: {source: {element: RegField}}}. A field of the RTL
    or the YAML map joins the Python variable the name map routes it to, and
    a field no route names keeps its own name. An RTL strobe that no other
    source names is a side effect, not a register, and is left out.
    """
    sources = {"python": python, "vhdl": vhdl, "yaml": yaml}
    present = [s for s in SOURCES if sources[s] is not None]
    python_names = {f.name for f in (python or [])}
    route, pieces = _routes(name_map)

    grouped: Dict[str, Dict[str, Dict[int, RegField]]] = {}
    for source in present:
        for field in sources[source]:
            canonical, element = field.name, _element(field)
            if source != "python":
                label = _label(field)
                if field.index is not None and label in route[source]:
                    canonical, element = route[source][label]
                elif field.name not in python_names and field.name in route[source]:
                    canonical, element = route[source][field.name]
                if element is None:
                    element = _element(field)
            slot = grouped.setdefault(canonical, {}).setdefault(source, {})
            if canonical in pieces and source != "python" and element in slot:
                slot[element] = _join(slot[element], field)
            else:
                slot[element] = field

    for canonical in [c for c, by in grouped.items()
                      if set(by) == {"vhdl"} and c.endswith(STROBE_SUFFIXES)]:
        del grouped[canonical]
    return grouped


def _compare(block: str, python, vhdl, yaml, name_map: Dict[str, Dict[str, object]]) -> List[Drift]:
    """Return the drifts between the sources that are present.

    None means the source is not compared; an empty list means it is compared
    and holds nothing, so every field of the other sources is missing there.
    """
    sources = {"python": python, "vhdl": vhdl, "yaml": yaml}
    present = [s for s in SOURCES if sources[s] is not None]
    grouped = group_fields(python, vhdl, yaml, name_map)

    # Fields that exist in one source only, used to hint at an unmapped rename.
    lonely: Dict[str, List[RegField]] = {s: [] for s in present}
    for canonical, by_source in grouped.items():
        if len(by_source) == 1:
            source = next(iter(by_source))
            lonely[source].extend(by_source[source].values())

    found: Dict[Tuple[str, str], List[Tuple[int, str, str]]] = {}

    def record(field: str, kind: str, element: int, detail: str, total: int) -> None:
        found.setdefault((field, kind), []).append((element, detail, total))

    for canonical, by_source in grouped.items():
        elements = sorted({e for per in by_source.values() for e in per})
        for element in elements:
            have = {s: by_source[s][element] for s in present if s in by_source and element in by_source[s]}
            for source in present:
                if source in have:
                    continue
                other = next(iter(have.values()))
                hint = ""
                for candidate in lonely[source]:
                    if (candidate.abs_bit == other.abs_bit and candidate.bit_size == other.bit_size
                            and candidate.source != other.source):
                        hint = (
                            f"; same position as {_label(candidate)}: add a name-map entry "
                            "if this is the same register"
                        )
                        break
                record(
                    canonical,
                    f"missing-in-{source}",
                    element,
                    f"{_label(other)} is in {other.source} at bit {other.abs_bit} "
                    f"(width {other.bit_size}) but not in {source}{hint}",
                    len(elements),
                )
            names = sorted(have)
            for i, first in enumerate(names):
                for second in names[i + 1:]:
                    a, b = have[first], have[second]
                    kind = _position_kind(a, b)
                    if kind is not None:
                        record(canonical, kind, element,
                               f"{_label(a)} {first} bit {a.abs_bit} (word {a.word_byte:#x} bit {a.bit_in_word}) "
                               f"vs {second} bit {b.abs_bit} (word {b.word_byte:#x} bit {b.bit_in_word})",
                               len(elements))
                    if a.bit_size is not None and b.bit_size is not None and a.bit_size != b.bit_size:
                        record(canonical, "bitSize", element,
                               f"{_label(a)} {first} width {a.bit_size} vs {second} width {b.bit_size}",
                               len(elements))
                    if not mode_agrees(a, b):
                        record(canonical, "mode", element,
                               f"{_label(a)} {first} mode {a.mode} vs {second} mode {b.mode}",
                               len(elements))

    drifts = []
    for (field, kind), entries in found.items():
        element, detail, total = sorted(entries)[0]
        differing = len({e for e, _, _ in entries})
        suffix = f" (first differing element {element} of {total}, {differing} differ)" if total > 1 else ""
        drifts.append(Drift(block, field, kind, detail + suffix))
    return sorted(drifts, key=lambda d: (d.block, d.field, d.kind))


UNRESOLVED_RE = re.compile(r"^(?:read|write) 0x([0-9A-Fa-f]+):")


def unresolved_words(unresolved) -> frozenset:
    """Return the byte addresses of the RTL arms the parser could not read.

    ``unresolved`` is Decode.unresolved, entries such as
    ``read 0x4C: concatenation``. The RTL of those words is not compared.
    """
    words = set()
    for entry in unresolved:
        match = UNRESOLVED_RE.match(entry)
        if match is None:
            raise ValueError(f"unresolved decode entry {entry!r} does not name an address")
        words.add(int(match.group(1), 16) // 4 * 4)
    return frozenset(words)


def coverage_split(fields, vhdl_window: Optional[Tuple[int, int]] = None, vhdl_skip: frozenset = frozenset()):
    """Return (fields the RTL decode covers, fields it does not) for one source.

    A field is covered when its byte address lies inside vhdl_window (first
    and last byte, inclusive; None means the whole map) and its word is not
    one of vhdl_skip (word byte addresses whose RTL arm could not be parsed).
    None in gives (None, None) out.
    """
    if fields is None:
        return None, None

    def covered(field: RegField) -> bool:
        if vhdl_window is not None and not vhdl_window[0] <= field.abs_bit // BITS_PER_BYTE <= vhdl_window[1]:
            return False
        return field.word_byte not in vhdl_skip

    return [f for f in fields if covered(f)], [f for f in fields if not covered(f)]


def compare(block: str, python, vhdl, yaml, name_map: Dict[str, Dict[str, str]],
            vhdl_window: Optional[Tuple[int, int]] = None,
            vhdl_skip: frozenset = frozenset()) -> List[Drift]:
    """Return the drifts between the sources that are present.

    With vhdl_window (first and last byte, inclusive) or vhdl_skip (word byte
    addresses whose RTL arm could not be parsed) the RTL is compared only with
    the Python and YAML fields it covers; the other fields are compared with
    each other alone, because no readable RTL decodes those addresses.
    """
    if vhdl is None or (vhdl_window is None and not vhdl_skip):
        return _compare(block, python, vhdl, yaml, name_map)

    inside_py, outside_py = coverage_split(python, vhdl_window, vhdl_skip)
    inside_ya, outside_ya = coverage_split(yaml, vhdl_window, vhdl_skip)
    drifts = _compare(block, inside_py, coverage_split(vhdl, vhdl_window, vhdl_skip)[0], inside_ya, name_map)
    drifts += _compare(block, outside_py, None, outside_ya, name_map)
    return sorted(drifts, key=lambda d: (d.block, d.field, d.kind))


class BlockResult(NamedTuple):
    """The outcome of comparing one block variant."""

    block: str
    variant: str
    drifts: List[Drift]
    sources: Tuple[str, ...]
    no_rtl: int
    unparsed: int = 0


def compare_block(block: Block, variant: Variant, python, vhdl, yaml, name_map,
                  yaml_unreadable: bool = False, vhdl_skip: frozenset = frozenset()) -> BlockResult:
    """Compare one variant of a block and describe what was compared.

    yaml_unreadable marks a map that does not parse: it is reported as one
    block-level finding and no field of the block is compared at all.
    """
    if yaml_unreadable:
        sources = ("python",) + (("vhdl",) if vhdl is not None else ())
        sentinel = Drift(block.name, "<yaml>", "missing-in-yaml",
                         f"{block.yaml} does not parse, so no field of {block.name} can be compared with it")
        return BlockResult(block.name, variant.id, [sentinel], sources,
                           len(python) if vhdl is None else 0)
    drifts = compare(block.name, python, vhdl, yaml, name_map, block.vhdl_window, vhdl_skip)
    sources = tuple(s for s, f in (("python", python), ("vhdl", vhdl), ("yaml", yaml)) if f is not None)
    no_rtl = unparsed = 0
    for field in python:
        if vhdl is None or (
            block.vhdl_window is not None
            and not block.vhdl_window[0] <= field.abs_bit // BITS_PER_BYTE <= block.vhdl_window[1]
        ):
            no_rtl += 1
        elif field.word_byte in vhdl_skip:
            unparsed += 1
    return BlockResult(block.name, variant.id, drifts, sources, no_rtl, unparsed)


def validate_allowlist(allowlist, require_filed: bool = REQUIRE_FILED_ISSUES) -> None:
    """Reject entries that could not prove a specific, linked drift."""
    for key, value in allowlist.items():
        if not (isinstance(key, tuple) and len(key) == 3 and all(isinstance(k, str) for k in key)):
            raise ValueError(f"allowlist key {key!r} must be (block, field, kind)")
        block, field, kind = key
        if not block or not field:
            raise ValueError(f"allowlist key {key!r} needs a block and a field")
        if kind not in KINDS:
            raise ValueError(f"allowlist key {key!r} has kind {kind!r}, expected one of {KINDS}")
        if field.startswith("<") and BLOCK_SENTINELS.get(field) != kind:
            raise ValueError(f"allowlist key {key!r}: block-level field {field!r} must have kind "
                             f"{BLOCK_SENTINELS.get(field)!r}")
        if value == PENDING_ISSUE:
            if require_filed:
                raise ValueError(f"allowlist entry {key!r} is still {PENDING_ISSUE}; link a filed issue")
            continue
        if not isinstance(value, str) or not ISSUE_URL_RE.match(value):
            raise ValueError(f"allowlist entry {key!r} must link a slaclab/lcls-timing-core issue, got {value!r}")


def verdict(drifts, allowlist, blocks=None) -> List[str]:
    """Return the reasons the drifts fail the allowlist; empty means pass.

    The stale direction is judged only over blocks (all blocks of the
    allowlist when None), so a per-block run never reports another block's
    entry as stale.
    """
    reasons = []
    seen = set()
    for drift in drifts:
        key = (drift.block, drift.field, drift.kind)
        seen.add(key)
        if key not in allowlist:
            reasons.append(f"unlisted drift: {key}: {drift.detail}")
    for key in sorted(allowlist):
        if blocks is not None and key[0] not in blocks:
            continue
        if key not in seen:
            reasons.append(f"listed in ALLOWLIST but no longer drifts; remove the entry: {key}")
    return reasons


def format_report(results, allowlist) -> str:
    """Return a plain-text drift report for BlockResult records.

    One line per drift (block, variant, field, kind, the allowlist link or
    ``unlisted``, and the detail), then one line per block and variant that
    names the sources compared, how many Python fields have no RTL in the
    repository to compare with, and how many sit in an RTL arm the parser
    could not read. Entries of the allowlist that no result
    drifts for are listed last. The text depends only on its arguments, so
    two calls on the same results are equal.
    """
    lines = ["# register drift report", ""]
    seen = set()
    for result in sorted(results, key=lambda r: (r.block, r.variant)):
        for drift in result.drifts:
            key = (drift.block, drift.field, drift.kind)
            seen.add(key)
            link = allowlist.get(key, "unlisted")
            lines.append(f"drift {drift.block} {result.variant} {drift.field} {drift.kind} {link}: {drift.detail}")
    lines.append("")
    for result in sorted(results, key=lambda r: (r.block, r.variant)):
        note = f"; {result.no_rtl} fields: no RTL in repo" if result.no_rtl else ""
        if result.unparsed:
            note += f"; {result.unparsed} fields: RTL arm not parsed"
        lines.append(f"block {result.block} variant {result.variant}: compared {', '.join(result.sources)}{note}")
    blocks = {r.block for r in results}
    stale = sorted(k for k in allowlist if k[0] in blocks and k not in seen)
    if stale:
        lines.append("")
        lines.extend(f"stale {key}: listed in ALLOWLIST but no longer drifts" for key in stale)
    return "\n".join(lines) + "\n"


def write_report(path, text: str) -> None:
    """Write text to path so a reader never sees a partial file.

    The text goes to a temporary file in the same directory and replaces the
    target in one step, so a second run replaces the report instead of
    appending to it and an interrupted run leaves the old report intact.
    """
    directory = os.path.dirname(os.path.abspath(path))
    handle, temporary = tempfile.mkstemp(dir=directory, prefix=".drift-report-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
