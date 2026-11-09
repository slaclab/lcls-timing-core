.. _api-timingframerx:

TimingFrameRx
=============

Source: :repo:`python/LclsTimingCore/TimingFrameRx.py`. Register table: :ref:`TimingFrameRx registers <register-map-timingframerx>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'TimingFrameRx'``
   * - ``description``
     - ``'Status of timing frame reception'``
   * - ``clkselMode``
     - ``'SELECT'``
   * - ``**kwargs``
     - none

Constructor checks
------------------

none

Sub-devices
-----------

none

Variables
---------

Arguments default
~~~~~~~~~~~~~~~~~

Constructor arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 17 11 12 7 6 14 10 23

   * - Name
     - Kind
     - Offset
     - Bits
     - Mode
     - Base or enum
     - Condition
     - Description
   * - ``sofCount``
     - RemoteVariable
     - ``0x000``
     - [31:0]
     - RO
     - UInt
     - none
     - Start of frame count
   * - ``eofCount``
     - RemoteVariable
     - ``0x004``
     - [31:0]
     - RO
     - UInt
     - none
     - End of frame count
   * - ``FidCount``
     - RemoteVariable
     - ``0x008``
     - [31:0]
     - RO
     - UInt
     - none
     - Valid frame count
   * - ``CrcErrCount``
     - RemoteVariable
     - ``0x00C``
     - [31:0]
     - RO
     - UInt
     - none
     - CRC error count
   * - ``RxClkCount``
     - RemoteVariable
     - ``0x010``
     - [31:0]
     - RO
     - UInt
     - none
     - Recovered clock count div 16
   * - ``RxRstCount``
     - RemoteVariable
     - ``0x014``
     - [31:0]
     - RO
     - UInt
     - none
     - Receive link reset count
   * - ``RxDecErrCount``
     - RemoteVariable
     - ``0x018``
     - [31:0]
     - RO
     - UInt
     - none
     - Receive 8b/10b decode error count
   * - ``RxDspErrCount``
     - RemoteVariable
     - ``0x01C``
     - [31:0]
     - RO
     - UInt
     - none
     - Receive disparity error count
   * - ``ClearRxCounters``
     - RemoteCommand
     - ``0x020``
     - [0]
     - WO
     - UInt
     - none
     - Reset receive counters
   * - ``RxLinkUp``
     - RemoteVariable
     - ``0x020``
     - [1]
     - RO
     - UInt
     - none
     - Receive link status
   * - ``RxPolarity``
     - RemoteVariable
     - ``0x020``
     - [2]
     - RW
     - UInt
     - none
     - Invert receive link polarity
   * - ``C_RxReset``
     - RemoteCommand
     - ``0x020``
     - [3]
     - WO
     - UInt
     - none
     - Reset receive link
   * - ``ClkSel``
     - RemoteVariable
     - ``0x020``
     - [4]
     - RW
     - enum 0: LCLS-I Clock, 1: LCLS-II Clock
     - ``clkselSelect``
     - Select LCLS-I/LCLS-II Timing
   * - ``RxDown``
     - RemoteVariable
     - ``0x020``
     - [5]
     - RW
     - UInt
     - none
     - Rx down latch status
   * - ``BypassRst``
     - RemoteVariable
     - ``0x020``
     - [6]
     - RW
     - UInt
     - none
     - Buffer bypass reset status
   * - ``RxPllReset``
     - RemoteVariable
     - ``0x020``
     - [7]
     - WO
     - UInt
     - none
     - Reset RX PLL
   * - ``ModeSel``
     - RemoteVariable
     - ``0x020``
     - [9]
     - RW
     - enum 0: Lcls1Protocol, 1: Lcls2Protocol
     - ``clkselSelect``
     - Select timing mode
   * - ``ModeSelEn``
     - RemoteVariable
     - ``0x020``
     - [10]
     - RW
     - enum 0: UseClkSel, 1: UseModeSel
     - ``clkselSelect``
     - Enable ModeSel register
   * - ``MsgDelay``
     - RemoteVariable
     - ``0x024``
     - [19:0]
     - RW
     - UInt
     - none
     - LCLS-II timing frame pipeline delay (186MHz clks)
   * - ``TxClkCount``
     - RemoteVariable
     - ``0x028``
     - [31:0]
     - RO
     - UInt
     - none
     - Transmit clock counter div 16
   * - ``BypassDoneCount``
     - RemoteVariable
     - ``0x02C``
     - [15:0]
     - RO
     - UInt
     - none
     - Buffer bypass done count
   * - ``BypassResetCount``
     - RemoteVariable
     - ``0x02C``
     - [31:16]
     - RO
     - UInt
     - none
     - Buffer bypass reset count

Arguments LCLSII
~~~~~~~~~~~~~~~~

Constructor arguments: ``clkselMode='LCLSII'``.

.. list-table::
   :header-rows: 1
   :widths: 17 11 12 7 6 14 10 23

   * - Name
     - Kind
     - Offset
     - Bits
     - Mode
     - Base or enum
     - Condition
     - Description
   * - ``sofCount``
     - RemoteVariable
     - ``0x000``
     - [31:0]
     - RO
     - UInt
     - none
     - Start of frame count
   * - ``eofCount``
     - RemoteVariable
     - ``0x004``
     - [31:0]
     - RO
     - UInt
     - none
     - End of frame count
   * - ``FidCount``
     - RemoteVariable
     - ``0x008``
     - [31:0]
     - RO
     - UInt
     - none
     - Valid frame count
   * - ``CrcErrCount``
     - RemoteVariable
     - ``0x00C``
     - [31:0]
     - RO
     - UInt
     - none
     - CRC error count
   * - ``RxClkCount``
     - RemoteVariable
     - ``0x010``
     - [31:0]
     - RO
     - UInt
     - none
     - Recovered clock count div 16
   * - ``RxRstCount``
     - RemoteVariable
     - ``0x014``
     - [31:0]
     - RO
     - UInt
     - none
     - Receive link reset count
   * - ``RxDecErrCount``
     - RemoteVariable
     - ``0x018``
     - [31:0]
     - RO
     - UInt
     - none
     - Receive 8b/10b decode error count
   * - ``RxDspErrCount``
     - RemoteVariable
     - ``0x01C``
     - [31:0]
     - RO
     - UInt
     - none
     - Receive disparity error count
   * - ``ClearRxCounters``
     - RemoteCommand
     - ``0x020``
     - [0]
     - WO
     - UInt
     - none
     - Reset receive counters
   * - ``RxLinkUp``
     - RemoteVariable
     - ``0x020``
     - [1]
     - RO
     - UInt
     - none
     - Receive link status
   * - ``RxPolarity``
     - RemoteVariable
     - ``0x020``
     - [2]
     - RW
     - UInt
     - none
     - Invert receive link polarity
   * - ``C_RxReset``
     - RemoteCommand
     - ``0x020``
     - [3]
     - WO
     - UInt
     - none
     - Reset receive link
   * - ``ClkSel``
     - RemoteVariable
     - ``0x020``
     - [4]
     - RO
     - enum 0: LCLS-I Clock, 1: LCLS-II Clock
     - ``clkselFixed``
     - Select LCLS-I/LCLS-II Timing
   * - ``RxDown``
     - RemoteVariable
     - ``0x020``
     - [5]
     - RW
     - UInt
     - none
     - Rx down latch status
   * - ``BypassRst``
     - RemoteVariable
     - ``0x020``
     - [6]
     - RW
     - UInt
     - none
     - Buffer bypass reset status
   * - ``RxPllReset``
     - RemoteVariable
     - ``0x020``
     - [7]
     - WO
     - UInt
     - none
     - Reset RX PLL
   * - ``ModeSel``
     - RemoteVariable
     - ``0x020``
     - [9]
     - RO
     - enum 0: Lcls1Protocol, 1: Lcls2Protocol
     - ``clkselFixed``
     - Select timing mode
   * - ``ModeSelEn``
     - RemoteVariable
     - ``0x020``
     - [10]
     - RO
     - enum 0: UseClkSel, 1: UseModeSel
     - ``clkselFixed``
     - Enable ModeSel register
   * - ``MsgDelay``
     - RemoteVariable
     - ``0x024``
     - [19:0]
     - RW
     - UInt
     - none
     - LCLS-II timing frame pipeline delay (186MHz clks)
   * - ``TxClkCount``
     - RemoteVariable
     - ``0x028``
     - [31:0]
     - RO
     - UInt
     - none
     - Transmit clock counter div 16
   * - ``BypassDoneCount``
     - RemoteVariable
     - ``0x02C``
     - [15:0]
     - RO
     - UInt
     - none
     - Buffer bypass done count
   * - ``BypassResetCount``
     - RemoteVariable
     - ``0x02C``
     - [31:16]
     - RO
     - UInt
     - none
     - Buffer bypass reset count

Known issues
------------

none
