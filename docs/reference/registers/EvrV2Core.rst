EvrV2Core registers
===================

Decode file: :repo:`LCLS-II/evr/rtl/EvrV2Axi.vhd`. Python class: :repo:`python/LclsTimingCore/EvrV2Core.py`. YAML map: :repo:`yaml/EvrV2Core.yaml`.

Variant default
---------------

RTL generics: ``DMA_ENABLE_G`` = ``True``, ``CHANNELS_C`` = ``12``. Python arguments: none.

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
     - ``IrqEnable``
       RTL: ``irqEnable``
     - [0]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Interrupt Enable
   * - ``0x004``
     - ``IrqStatus``
       RTL: ``sReg``
     - [0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Interrupt Pending
   * - ``0x008``
     - ``LinkAddr``
     - [15:0]
     - RO
     - not asserted
     - absent :issue:`228`
     - differs: missing-in-vhdl :issue:`228`
       at 0x008 [15:0] RO
     - no description in source
   * - ``0x00C``
     - ``gtxDebug``
       YAML: ``GtxDebug``
     - [7:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Debug bits from link
   * - ``0x010``
     - ``CountReset``
       RTL: ``countReset``
     - [0]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Counter reset
   * - ``0x014``
     - ``ModeSel``
       RTL: ``trigSel``
     - [0]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Select LCLS-I/LCLS-II Trigger outputs (0/1)
   * - ``0x018``
     - ``DmaFullThr``
       RTL: ``dmaFullThr``
     - [23:0]
     - RW
     - ``0xFFFFFF``
     - agrees
     - agrees
     - Set threshold in bytes for asserting readout full
   * - ``0x020``
     - ``ChannelEnable``
       RTL: ``enabled[0]``
     - [0]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Enable readout channel
   * - ``0x020`` + ``0x20`` * i
     - ``ChannelBsaEnable[0..11]``
       RTL: ``bsaEnabled[0..11]``
     - [1]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Enable BSA channel
   * - ``0x020`` + ``0x20`` * i
     - ``ChannelDmaEnable[0..11]``
       RTL: ``dmaEnabled[0..11]``
     - [2]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - no description in source
   * - ``0x024``
     - ``ChannelRateSel``
       RTL: ``rateSel[0]``
     - [12:0]
     - RW
     - ``0x0000``
     - agrees
     - agrees
     - no description in source
   * - ``0x024`` + ``0x20`` * i
     - ``ChannelDestSel[0..11]``
       RTL: ``destSel[0..11]``
     - [31:13]
     - RW
     - ``0x00000``
     - differs: bitSize :issue:`215`
       at 0x024 [30:13] RW, step 0x20
     - differs: bitSize :issue:`215`
       at 0x024 [30:13] RW, step 0x20
     - Channel event destination selection
   * - ``0x028`` + ``0x20`` * i
     - ``ChannelEventCnt[0..11]``
       RTL: ``eventCount[0..11]``
     - [31:0]
     - RO
     - not asserted
     - differs: mode :issue:`217`
       at 0x028 [31:0] RW, step 0x20
     - differs: mode :issue:`217`
       at 0x028 [31:0] RW, step 0x20
     - Channel event counts
   * - ``0x02C`` + ``0x20`` * i
     - ``ChannelBsaDelay[0..11]``
       RTL: ``bsaActiveDelay[0..11]``
     - [19:0]
     - RW
     - ``0x00000``
     - agrees
     - agrees
     - Channel BSA active delay
   * - ``0x02C`` + ``0x20`` * i
     - ``ChannelBsaSetup[0..11]``
       RTL: ``bsaActiveSetup[0..11]``
     - [25:20]
     - RW
     - ``0x00``
     - differs: bitSize :issue:`215`
       at 0x02C [31:20] RW, step 0x20
     - differs: bitSize :issue:`215`
       at 0x02C [31:20] RW, step 0x20
     - Channel BSA active setup
   * - ``0x030`` + ``0x20`` * i
     - ``ChannelBsaWidth[0..11]``
       RTL: ``bsaActiveWidth[0..11]``
     - [19:0]
     - RW
     - ``0x00001``
     - agrees
     - agrees
     - Channel BSA active width
   * - ``0x040`` + ``0x20`` * i
     - ``ChannelEnable[1..11]``
       RTL: ``enabled[1..11]``
     - [0]
     - RW
     - ``0x0``
     - absent :issue:`215`
     - agrees
     - no description in source
   * - ``0x044`` + ``0x20`` * i
     - ``ChannelRateSel[1..11]``
       RTL: ``rateSel[1..11]``
     - [12:0]
     - RW
     - ``0x0000``
     - absent :issue:`215`
     - agrees
     - no description in source
   * - ``0x1A8``
     - ``GlobalEventCnt``
       RTL: ``eventCount[12]``
     - [31:0]
     - RO
     - not asserted
     - differs: mode :issue:`217`
       at 0x1A8 [31:0] RW
     - differs: mode :issue:`217`
       at 0x1A8 [31:0] RW
     - Global Event count

The RTL decodes the words from 0x000 to 0x1FF only; the words above it have no RTL in this repository, so they are listed in the table of registers without RTL below.

Registers without RTL in the repository (the Python view, with the YAML agreement):

.. list-table::
   :header-rows: 1
   :widths: 10 22 8 7 23 30

   * - Offset
     - Field
     - Bits
     - Mode
     - YAML
     - Description
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerChannel[0..11]``
     - [3:0]
     - RW
     - agrees
     - Channel used for event selection
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerPolarity[0..11]``
     - [16]
     - RW
     - agrees
     - Trigger polarity (0=negative, 1=positive)
   * - ``0x200`` + ``0x10`` * i
     - ``TriggerEnable[0..11]``
     - [31]
     - RW
     - agrees
     - Trigger enable
   * - ``0x208`` + ``0x10`` * i
     - ``TriggerDelay[0..11]``
     - [27:0]
     - RW
     - differs: offset :issue:`217`
       at 0x204 [27:0] RW, step 0x10
     - Trigger width (186MHz clocks)
   * - ``0x208`` + ``0x10`` * i
     - ``TriggerWidth[0..11]``
     - [27:0]
     - RW
     - differs: missing-in-python :issue:`217`
       at 0x208 [27:0] RW, step 0x10
     - no description in source
   * - ``0x20C`` + ``0x10`` * i
     - ``TriggerFineDelay[0..11]``
     - [5:0]
     - RW
     - agrees
     - Trigger fine delay (82.2 ps steps)

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``ChannelBsaSetup`` (bitSize): ``ChannelBsaSetup[0] python width 12 vs vhdl width 6 (first differing element 0 of 12, 12 differ)`` :issue:`215`
   * ``ChannelDestSel`` (bitSize): ``ChannelDestSel[0] python width 18 vs vhdl width 19 (first differing element 0 of 12, 12 differ)`` :issue:`215`
   * ``ChannelEnable`` (missing-in-python): ``enabled[1] is in vhdl at bit 512 (width 1) but not in python (first differing element 1 of 12, 11 differ)`` :issue:`215`
   * ``ChannelEventCnt`` (mode): ``ChannelEventCnt[0] python mode RW vs vhdl mode RO (first differing element 0 of 12, 12 differ)`` :issue:`217`
   * ``ChannelRateSel`` (missing-in-python): ``rateSel[1] is in vhdl at bit 544 (width 13) but not in python (first differing element 1 of 12, 11 differ)`` :issue:`215`
   * ``GlobalEventCnt`` (mode): ``GlobalEventCnt python mode RW vs vhdl mode RO`` :issue:`217`
   * ``LinkAddr`` (missing-in-python): ``LinkAddr is in yaml at bit 64 (width 16) but not in python`` :issue:`228`
   * ``LinkAddr`` (missing-in-vhdl): ``LinkAddr is in yaml at bit 64 (width 16) but not in vhdl`` :issue:`228`
   * ``TriggerDelay`` (offset): ``TriggerDelay[0] python bit 4160 (word 0x208 bit 0) vs yaml bit 4128 (word 0x204 bit 0) (first differing element 0 of 12, 12 differ)`` :issue:`217`
   * ``TriggerWidth`` (missing-in-python): ``TriggerWidth[0] is in yaml at bit 4160 (width 28) but not in python (first differing element 0 of 12, 12 differ)`` :issue:`217`
