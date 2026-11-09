YAML-only register maps
=======================

These CPSW maps describe no PyRogue class and no RTL decode in this repository, so they are listed as the YAML states them: the byte address of the word, the bits inside it, the mode, and the description. An array is one row with its element step.

AmcCarrierDRAM.yaml
-------------------

YAML map: :repo:`yaml/AmcCarrierDRAM.yaml`.

.. list-table::
   :header-rows: 1
   :widths: 18 22 10 8 42

   * - Offset
     - Field
     - Bits
     - Mode
     - Description
   * - ``0x000`` + ``0x8`` * i
     - ``dram[0..536870911]``
     - [63:0]
     - RW
     - DRAM

BldAxiStream.yaml
-----------------

YAML map: :repo:`yaml/BldAxiStream.yaml`.

.. list-table::
   :header-rows: 1
   :widths: 18 22 10 8 42

   * - Offset
     - Field
     - Bits
     - Mode
     - Description
   * - ``0x000``
     - ``PacketSize``
     - [11:0]
     - RW
     - BLD max packet size in words
   * - ``0x000``
     - ``Enable``
     - [31]
     - RW
     - Enable BLD packet streaming
   * - ``0x004``
     - ``ChannelMask``
     - [30:0]
     - RW
     - BLD diagnostic channel selection
   * - ``0x008``
     - ``ChannelSevr``
     - [61:0]
     - RW
     - BLD diagnostic channel severity limit
   * - ``0x010``
     - ``WordCount``
     - [11:0]
     - RO
     - current BLD packet word count
   * - ``0x010``
     - ``TxState``
     - [19:16]
     - RO
     - BLD Tx State
   * - ``0x014``
     - ``PulseIdL``
     - [19:0]
     - RO
     - BLD PulseID latch
   * - ``0x018``
     - ``TimeStampL``
     - [31:0]
     - RO
     - BLD TimeStamp latch
   * - ``0x01C``
     - ``Delta``
     - [31:0]
     - RO
     - BLD Pulse Delta
   * - ``0x020``
     - ``PacketCount``
     - [19:0]
     - RO
     - BLD Packet Count
   * - ``0x020``
     - ``Paused``
     - [31]
     - RO
     - BLD Paused

EvrV2Module.yaml
----------------

YAML map: :repo:`yaml/EvrV2Module.yaml`.

The registers cannot be listed: ``EvrV2Module.yaml has no top-level key 'EvrV2Module'``

EvrV2PulsegenRegs.yaml
----------------------

YAML map: :repo:`yaml/EvrV2PulsegenRegs.yaml`.

.. list-table::
   :header-rows: 1
   :widths: 18 22 10 8 42

   * - Offset
     - Field
     - Bits
     - Mode
     - Description
   * - ``0x008``
     - ``LinkAddr``
     - [15:0]
     - RO
     - Physical link address
   * - ``0x00C``
     - ``GtxDebug``
     - [7:0]
     - RO
     - Debug bits from link
   * - ``0x010``
     - ``CountReset``
     - [0]
     - RW
     - Counter reset
   * - ``0x014``
     - ``ModeSel``
     - [0]
     - RW
     - Select LCLS-I/LCLS-II Trigger outputs (0/1)
   * - ``0x020`` + ``0x20`` * i
     - ``ChannelEnable[0..11]``
     - [0]
     - RW
     - Enable readout channel
   * - ``0x024`` + ``0x20`` * i
     - ``ChannelRateSel[0..11]``
     - [12:0]
     - RW
     - none
   * - ``0x024`` + ``0x20`` * i
     - ``ChannelDestSel[0..11]``
     - [30:13]
     - RW
     - Channel event destination selection
   * - ``0x028`` + ``0x20`` * i
     - ``ChannelEventCnt[0..11]``
     - [31:0]
     - RW
     - Channel event counts
   * - ``0x1A8``
     - ``GlobalEventCnt``
     - [31:0]
     - RW
     - Global Event count
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerChannel[0..11]``
     - [3:0]
     - RW
     - Channel used for event selection
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerPolarity[0..11]``
     - [16]
     - RW
     - Trigger polarity (0=negative, 1=positive)
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerEnable[0..11]``
     - [31]
     - RW
     - Trigger enable
   * - ``0x204`` + ``0x10`` * i
     - ``TriggerDelay[0..11]``
     - [27:0]
     - RW
     - Trigger delay (186MHz clocks)
   * - ``0x208`` + ``0x10`` * i
     - ``TriggerWidth[0..11]``
     - [27:0]
     - RW
     - Trigger width (186MHz clocks)
   * - ``0x20C`` + ``0x10`` * i
     - ``TriggerFineDelay[0..11]``
     - [5:0]
     - RW
     - Trigger fine delay (82.2 ps steps)

EvrV2TriggerPulse.yaml
----------------------

YAML map: :repo:`yaml/EvrV2TriggerPulse.yaml`.

.. list-table::
   :header-rows: 1
   :widths: 18 22 10 8 42

   * - Offset
     - Field
     - Bits
     - Mode
     - Description
   * - ``0x008``
     - ``LinkAddr``
     - [15:0]
     - RO
     - Physical link address
   * - ``0x00C``
     - ``GtxDebug``
     - [7:0]
     - RO
     - Debug bits from link
   * - ``0x010``
     - ``CountReset``
     - [0]
     - RW
     - Counter reset
   * - ``0x014``
     - ``ModeSel``
     - [0]
     - RW
     - Select LCLS-I/LCLS-II Trigger outputs (0/1)
   * - ``0x020`` + ``0x20`` * i
     - ``ChannelEnable[0..11]``
     - [0]
     - RW
     - Enable readout channel
   * - ``0x024`` + ``0x20`` * i
     - ``ChannelRateSel[0..11]``
     - [12:0]
     - RW
     - none
   * - ``0x024`` + ``0x20`` * i
     - ``ChannelDestSel[0..11]``
     - [30:13]
     - RW
     - Channel event destination selection
   * - ``0x028`` + ``0x20`` * i
     - ``ChannelEventCnt[0..11]``
     - [31:0]
     - RW
     - Channel event counts
   * - ``0x1A8``
     - ``GlobalEventCnt``
     - [31:0]
     - RW
     - Global Event count
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerChannel[0..11]``
     - [3:0]
     - RW
     - Channel used for event selection
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerPolarity[0..11]``
     - [16]
     - RW
     - Trigger polarity (0=negative, 1=positive)
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerEnable[0..11]``
     - [31]
     - RW
     - Trigger enable
   * - ``0x204`` + ``0x10`` * i
     - ``TriggerDelay[0..11]``
     - [27:0]
     - RW
     - Trigger delay (186MHz clocks)
   * - ``0x208`` + ``0x10`` * i
     - ``TriggerWidth[0..11]``
     - [27:0]
     - RW
     - Trigger width (186MHz clocks)
   * - ``0x20C`` + ``0x10`` * i
     - ``TriggerFineDelay[0..11]``
     - [5:0]
     - RW
     - Trigger fine delay (82.2 ps steps)
