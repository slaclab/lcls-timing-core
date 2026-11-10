.. _register-map-timingframerx:

TimingFrameRx registers
=======================

Decode file: :repo:`LCLS-II/core/rtl/TimingRx.vhd`. Python class: :repo:`python/LclsTimingCore/TimingFrameRx.py`. YAML map: :repo:`yaml/TimingFrameRx.yaml`.

Variant SELECT
--------------

RTL generics: ``CLKSEL_MODE_G`` = ``SELECT``. Python arguments: ``clkselMode='SELECT'``.

.. list-table::
   :header-rows: 1
   :widths: 9 17 7 6 12 15 15 19

   * - Offset
     - Field
     - Bits
     - Mode
     - Reset
     - Python
     - YAML
     - Description
   * - ``0x000``
     - ``sofCount``
       RTL: ``axilStatusCounters12[0]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Start of frame count
   * - ``0x004``
     - ``eofCount``
       RTL: ``axilStatusCounters12[1]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - End of frame count
   * - ``0x008``
     - ``FidCount``
       RTL: ``axilStatusCounters12[2]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Valid frame count
   * - ``0x00C``
     - ``CrcErrCount``
       RTL: ``axilStatusCounters12[3]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - CRC error count
   * - ``0x010``
     - ``RxClkCount``
       RTL: ``axilStatusCounters3[0]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Recovered clock count div 16
   * - ``0x014``
     - ``RxRstCount``
       RTL: ``axilStatusCounters3[1]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Receive link reset count
   * - ``0x018``
     - ``RxDecErrCount``
       RTL: ``axilStatusCounters3[2]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Receive 8b/10b decode error count
   * - ``0x01C``
     - ``RxDspErrCount``
       RTL: ``axilStatusCounters3[3]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Receive disparity error count
   * - ``0x020``
     - ``ClearRxCounters``
       RTL: ``cntRst``
       YAML: ``RxCountReset``
     - [0]
     - RW
     - not asserted
     - agrees
     - differs from Python: mode :issue:`294`
       at 0x020 [0] RW
     - Reset receive counters
   * - ``0x020``
     - ``RxLinkUp``
       RTL: ``axilRxLinkUp``
     - [1]
     - RO
     - not asserted
     - agrees
     - agrees
     - Receive link status
   * - ``0x020``
     - ``RxPolarity``
       RTL: ``polarity``
     - [2]
     - RW
     - not asserted
     - agrees
     - agrees
     - Invert receive link polarity
   * - ``0x020``
     - ``C_RxReset``
       RTL: ``reset``
       YAML: ``RxReset``
     - [3]
     - RW
     - not asserted
     - agrees
     - differs from Python: mode :issue:`294`
       at 0x020 [3] RW
     - Reset receive link
   * - ``0x020``
     - ``ClkSel``
       RTL: ``clkSel``
     - [4]
     - RW
     - not asserted
     - agrees
     - agrees
     - Select LCLS-I/LCLS-II Timing
   * - ``0x020``
     - ``RxDown``
       RTL: ``rxDown``
     - [5]
     - RW
     - not asserted
     - agrees
     - agrees
     - Rx down latch status
   * - ``0x020``
     - ``BypassRst``
       RTL: ``bufferByRst``
     - [6]
     - RW
     - not asserted
     - agrees
     - agrees
     - Buffer bypass reset status
   * - ``0x020``
     - ``RxPllReset``
       RTL: ``pllReset``
       YAML: ``RxPLLReset``
     - [7]
     - RW
     - not asserted
     - agrees
     - differs from Python: mode :issue:`294`
       at 0x020 [7] RW
     - Reset RX PLL
   * - ``0x020``
     - ``VersionErr``
       RTL: ``axilVsnErr``
     - [8]
     - RO
     - not asserted
     - absent :issue:`298`
     - agrees
     - no description in source
   * - ``0x020``
     - ``ModeSel``
       RTL: ``modeSel``
     - [9]
     - RW
     - not asserted
     - agrees
     - agrees
     - Select timing mode
   * - ``0x020``
     - ``ModeSelEn``
       RTL: ``modeSelEn``
     - [10]
     - RW
     - not asserted
     - agrees
     - agrees
     - Enable ModeSel register
   * - ``0x020``
     - ``MsgNoDelay``
       RTL: ``streamNoDelay``
     - [24]
     - RW
     - not asserted
     - absent :issue:`298`
     - agrees
     - no description in source
   * - ``0x024``
     - ``MsgDelay``
       RTL: ``messageDelay``
     - [19:0]
     - RW
     - not asserted
     - agrees
     - agrees
     - LCLS-II timing frame pipeline delay (186MHz clks)
   * - ``0x024``
     - ``MsgDelayRst``
       RTL: ``messageDelayRst``
     - [31]
     - RW
     - not asserted
     - absent :issue:`298`
     - agrees
     - no description in source
   * - ``0x028``
     - ``TxClkCount``
       RTL: ``txClkCntS``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Transmit clock counter div 16
   * - ``0x02C``
     - ``BypassDoneCount``
       RTL: ``rxStatusCount[0]``
     - [15:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Buffer bypass done count
   * - ``0x02C``
     - ``BypassResetCount``
       RTL: ``rxStatusCount[1]``
     - [31:16]
     - RO
     - not asserted
     - agrees
     - agrees
     - Buffer bypass reset count
   * - ``0x030``
     - ``FrameVersion``
       RTL: ``axilVersion``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`298`
     - agrees
     - no description in source
   * - ``0x040``
     - ``timingTSEvCntGray_o``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`298`
     - absent :issue:`298`
     - no description in source

Variant LCLSII
--------------

RTL generics: ``CLKSEL_MODE_G`` = ``LCLSII``. Python arguments: ``clkselMode='LCLSII'``.

.. list-table::
   :header-rows: 1
   :widths: 9 17 7 6 12 15 15 19

   * - Offset
     - Field
     - Bits
     - Mode
     - Reset
     - Python
     - YAML
     - Description
   * - ``0x000``
     - ``sofCount``
       RTL: ``axilStatusCounters12[0]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Start of frame count
   * - ``0x004``
     - ``eofCount``
       RTL: ``axilStatusCounters12[1]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - End of frame count
   * - ``0x008``
     - ``FidCount``
       RTL: ``axilStatusCounters12[2]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Valid frame count
   * - ``0x00C``
     - ``CrcErrCount``
       RTL: ``axilStatusCounters12[3]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - CRC error count
   * - ``0x010``
     - ``RxClkCount``
       RTL: ``axilStatusCounters3[0]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Recovered clock count div 16
   * - ``0x014``
     - ``RxRstCount``
       RTL: ``axilStatusCounters3[1]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Receive link reset count
   * - ``0x018``
     - ``RxDecErrCount``
       RTL: ``axilStatusCounters3[2]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Receive 8b/10b decode error count
   * - ``0x01C``
     - ``RxDspErrCount``
       RTL: ``axilStatusCounters3[3]``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Receive disparity error count
   * - ``0x020``
     - ``ClearRxCounters``
       RTL: ``cntRst``
     - [0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Reset receive counters
   * - ``0x020``
     - ``RxLinkUp``
       RTL: ``axilRxLinkUp``
     - [1]
     - RO
     - not asserted
     - agrees
     - not compared
     - Receive link status
   * - ``0x020``
     - ``RxPolarity``
       RTL: ``polarity``
     - [2]
     - RW
     - not asserted
     - agrees
     - not compared
     - Invert receive link polarity
   * - ``0x020``
     - ``C_RxReset``
       RTL: ``reset``
     - [3]
     - RW
     - not asserted
     - agrees
     - not compared
     - Reset receive link
   * - ``0x020``
     - ``ClkSel``
       RTL: ``clkSel``
     - [4]
     - RO
     - not asserted
     - agrees
     - not compared
     - Select LCLS-I/LCLS-II Timing
   * - ``0x020``
     - ``RxDown``
       RTL: ``rxDown``
     - [5]
     - RW
     - not asserted
     - agrees
     - not compared
     - Rx down latch status
   * - ``0x020``
     - ``BypassRst``
       RTL: ``bufferByRst``
     - [6]
     - RW
     - not asserted
     - agrees
     - not compared
     - Buffer bypass reset status
   * - ``0x020``
     - ``RxPllReset``
       RTL: ``pllReset``
     - [7]
     - RW
     - not asserted
     - agrees
     - not compared
     - Reset RX PLL
   * - ``0x020``
     - ``VersionErr``
       RTL: ``axilVsnErr``
     - [8]
     - RO
     - not asserted
     - absent :issue:`298`
     - not compared
     - no description in source
   * - ``0x020``
     - ``ModeSel``
       RTL: ``modeSel``
     - [9]
     - RO
     - not asserted
     - agrees
     - not compared
     - Select timing mode
   * - ``0x020``
     - ``ModeSelEn``
       RTL: ``modeSelEn``
     - [10]
     - RO
     - not asserted
     - agrees
     - not compared
     - Enable ModeSel register
   * - ``0x020``
     - ``MsgNoDelay``
       RTL: ``streamNoDelay``
     - [24]
     - RW
     - not asserted
     - absent :issue:`298`
     - not compared
     - no description in source
   * - ``0x024``
     - ``MsgDelay``
       RTL: ``messageDelay``
     - [19:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - LCLS-II timing frame pipeline delay (186MHz clks)
   * - ``0x024``
     - ``MsgDelayRst``
       RTL: ``messageDelayRst``
     - [31]
     - RW
     - not asserted
     - absent :issue:`298`
     - not compared
     - no description in source
   * - ``0x028``
     - ``TxClkCount``
       RTL: ``txClkCntS``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Transmit clock counter div 16
   * - ``0x02C``
     - ``BypassDoneCount``
       RTL: ``rxStatusCount[0]``
     - [15:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Buffer bypass done count
   * - ``0x02C``
     - ``BypassResetCount``
       RTL: ``rxStatusCount[1]``
     - [31:16]
     - RO
     - not asserted
     - agrees
     - not compared
     - Buffer bypass reset count
   * - ``0x030``
     - ``FrameVersion``
       RTL: ``axilVersion``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`298`
     - not compared
     - no description in source
   * - ``0x040``
     - ``timingTSEvCntGray_o``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`298`
     - not compared
     - no description in source

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``C_RxReset`` (mode): ``C_RxReset python mode WO vs yaml mode RW`` :issue:`294`
   * ``ClearRxCounters`` (mode): ``ClearRxCounters python mode WO vs yaml mode RW`` :issue:`294`
   * ``FrameVersion`` (missing-in-python): ``axilVersion is in vhdl at bit 384 (width 32) but not in python`` :issue:`298`
   * ``MsgDelayRst`` (missing-in-python): ``messageDelayRst is in vhdl at bit 319 (width 1) but not in python`` :issue:`298`
   * ``MsgNoDelay`` (missing-in-python): ``streamNoDelay is in vhdl at bit 280 (width 1) but not in python`` :issue:`298`
   * ``RxPllReset`` (mode): ``RxPllReset python mode WO vs yaml mode RW`` :issue:`294`
   * ``VersionErr`` (missing-in-python): ``axilVsnErr is in vhdl at bit 264 (width 1) but not in python`` :issue:`298`
   * ``timingTSEvCntGray_o`` (missing-in-python): ``timingTSEvCntGray_o is in vhdl at bit 512 (width 32) but not in python`` :issue:`298`
   * ``timingTSEvCntGray_o`` (missing-in-yaml): ``timingTSEvCntGray_o is in vhdl at bit 512 (width 32) but not in yaml`` :issue:`298`
