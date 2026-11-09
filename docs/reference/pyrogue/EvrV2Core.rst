.. _api-evrv2core:

EvrV2Core
=========

Source: :repo:`python/LclsTimingCore/EvrV2Core.py`. Register table: :ref:`EvrV2Core registers <register-map-evrv2core>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'EvrV2Core'``
   * - ``description``
     - ``'LCLS-II Timing Receiver module'``
   * - ``**kwargs``
     - none

Arguments beyond the ``pr.Device`` defaults: none.

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
   * - ``IrqEnable``
     - RemoteVariable
     - ``0x000``
     - [0]
     - RW
     - UInt
     - none
     - Interrupt Enable
   * - ``IrqStatus``
     - RemoteVariable
     - ``0x004``
     - [0]
     - RO
     - UInt
     - none
     - Interrupt Pending
   * - ``gtxDebug``
     - RemoteVariable
     - ``0x00C``
     - [7:0]
     - RO
     - UInt
     - none
     - Debug bits from link
   * - ``CountReset``
     - RemoteVariable
     - ``0x010``
     - [0]
     - RW
     - UInt
     - none
     - Counter reset
   * - ``ModeSel``
     - RemoteVariable
     - ``0x014``
     - [0]
     - RW
     - UInt
     - none
     - Select LCLS-I/LCLS-II Trigger outputs (0/1)
   * - ``DmaFullThr``
     - RemoteVariable
     - ``0x018``
     - [23:0]
     - RW
     - UInt
     - none
     - Set threshold in bytes for asserting readout full
   * - ``ChannelEnable``
     - RemoteVariable
     - ``0x020``
     - [0]
     - RW
     - UInt
     - none
     - Enable readout channel
   * - ``ChannelBsaEnable[0..11]``
     - RemoteVariable
     - ``0x020`` + ``0x20`` * i
     - [1]
     - RW
     - UInt
     - none
     - Enable BSA channel
   * - ``ChannelDmaEnable[0..11]``
     - RemoteVariable
     - ``0x020`` + ``0x20`` * i
     - [2]
     - RW
     - UInt
     - none
     - no description in source
   * - ``ChannelRateSel``
     - RemoteVariable
     - ``0x024``
     - [12:0]
     - RW
     - UInt
     - none
     - no description in source
   * - ``ChannelDestSel[0..11]``
     - RemoteVariable
     - ``0x024`` + ``0x20`` * i
     - [30:13]
     - RW
     - UInt
     - none
     - Channel event destination selection
   * - ``ChannelEventCnt[0..11]``
     - RemoteVariable
     - ``0x028`` + ``0x20`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Channel event counts
   * - ``ChannelBsaDelay[0..11]``
     - RemoteVariable
     - ``0x02C`` + ``0x20`` * i
     - [19:0]
     - RW
     - UInt
     - none
     - Channel BSA active delay
   * - ``ChannelBsaSetup[0..11]``
     - RemoteVariable
     - ``0x02C`` + ``0x20`` * i
     - [31:20]
     - RW
     - UInt
     - none
     - Channel BSA active setup
   * - ``ChannelBsaWidth[0..11]``
     - RemoteVariable
     - ``0x030`` + ``0x20`` * i
     - [19:0]
     - RW
     - UInt
     - none
     - Channel BSA active width
   * - ``GlobalEventCnt``
     - RemoteVariable
     - ``0x1A8``
     - [31:0]
     - RW
     - UInt
     - none
     - Global Event count
   * - ``TriggerChannel[0..11]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [3:0]
     - RW
     - UInt
     - none
     - Channel used for event selection
   * - ``TriggerPolarity[0..11]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [16]
     - RW
     - UInt
     - none
     - Trigger polarity (0=negative, 1=positive)
   * - ``TriggerEnable[0..11]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [31]
     - RW
     - UInt
     - none
     - Trigger enable
   * - ``TriggerDelay[0..11]``
     - RemoteVariable
     - ``0x208`` + ``0x10`` * i
     - [27:0]
     - RW
     - UInt
     - none
     - Trigger width (186MHz clocks)
   * - ``TriggerFineDelay[0..11]``
     - RemoteVariable
     - ``0x20C`` + ``0x10`` * i
     - [5:0]
     - RW
     - UInt
     - none
     - Trigger fine delay (82.2 ps steps)

Known issues
------------

none
