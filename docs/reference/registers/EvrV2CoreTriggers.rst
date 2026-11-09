.. _register-map-evrv2coretriggers:

EvrV2CoreTriggers registers
===========================

No RTL in repo: the firmware that implements this block lives outside this repository, so the tables show the PyRogue declarations and how the YAML map agrees with them.

Python class: :repo:`python/LclsTimingCore/EvrV2CoreTriggers.py`. YAML map: :repo:`yaml/EvrV2CoreTriggers.yaml`.

The class adds these child devices; their registers appear below with the child name in front.

.. list-table::
   :header-rows: 1
   :widths: 25 30 15 10 20

   * - Child
     - Class
     - Offset
     - Count
     - Stride
   * - ``EvrV2ChannelReg``
     - :ref:`EvrV2ChannelReg <register-map-evrv2channelreg>`
     - ``0x0``
     - 16
     - ``0x100``
   * - ``EvrV2TriggerReg``
     - :ref:`EvrV2TriggerReg <register-map-evrv2triggerreg>`
     - ``0x1000``
     - 16
     - ``0x100``

Variant default
---------------

Python arguments: ``numTrig=16``, ``dmaEnable=True``, ``useTap=True``.

.. list-table::
   :header-rows: 1
   :widths: 10 22 8 7 23 30

   * - Offset
     - Field
     - Bits
     - Mode
     - YAML
     - Description
   * - ``0x000`` + ``0x100`` * i
     - ``EvrV2ChannelReg.EnableReg[0..15]``
       YAML: ``EvrV2ChannelReg.Enable[0..15]``
     - [0]
     - RW
     - agrees
     - Enable Register
   * - ``0x000`` + ``0x100`` * i
     - ``EvrV2ChannelReg.BsaEnabled[0..15]``
     - [1]
     - RW
     - agrees
     - BSA Enable register (Only valid register is DMA_ENABLE_G=true)
   * - ``0x000`` + ``0x100`` * i
     - ``EvrV2ChannelReg.dmaEnabled[0..15]``
       YAML: ``EvrV2ChannelReg.DmaEnabled[0..15]``
     - [2]
     - RW
     - agrees
     - DMA Enable register (Only valid register is DMA_ENABLE_G=true)
   * - ``0x004`` + ``0x100`` * i
     - ``EvrV2ChannelReg.RateSel[0..15]``
     - [10:0]
     - RW
     - differs: bitSize :issue:`215`
       at 0x004 [12:0] RW, step 0x100
     - Rate select
   * - ``0x004`` + ``0x100`` * i
     - ``EvrV2ChannelReg.RateType[0..15]``
     - [12:11]
     - RW
     - absent :issue:`215`
     - no description in source
   * - ``0x004`` + ``0x100`` * i
     - ``EvrV2ChannelReg.DestSel[0..15]``
     - [28:13]
     - RW
     - differs: bitSize :issue:`215`
       at 0x004 [31:13] RW, step 0x100
     - Destination select
   * - ``0x004`` + ``0x100`` * i
     - ``EvrV2ChannelReg.DestType[0..15]``
     - [30:29]
     - RW
     - absent :issue:`215`
     - no description in source
   * - ``0x008`` + ``0x100`` * i
     - ``EvrV2ChannelReg.Count[0..15]``
     - [31:0]
     - RO
     - agrees
     - Counts
   * - ``0x00C`` + ``0x100`` * i
     - ``EvrV2ChannelReg.BsaWindowDelay[0..15]``
     - [19:0]
     - RW
     - agrees
     - Start of BSA sensitivity window following trigger (Only valid register is DMA_ENABLE_G=true)
   * - ``0x00C`` + ``0x100`` * i
     - ``EvrV2ChannelReg.BsaWindowSetup[0..15]``
     - [25:20]
     - RW
     - agrees
     - Start of BSA sensitivity window before trigger (Only valid register is DMA_ENABLE_G=true)
   * - ``0x010`` + ``0x100`` * i
     - ``EvrV2ChannelReg.BsaWindowWidth[0..15]``
     - [19:0]
     - RW
     - agrees
     - Width of BSA sensitivity window (Only valid register is DMA_ENABLE_G=true)
   * - ``0x1000`` + ``0x100`` * i
     - ``EvrV2TriggerReg.Source[0..15]``
     - [3:0]
     - RW
     - agrees
     - Source mask
   * - ``0x1000`` + ``0x100`` * i
     - ``EvrV2TriggerReg.Polarity[0..15]``
     - [16]
     - RW
     - agrees
     - Signal polarity
   * - ``0x1000`` + ``0x100`` * i
     - ``EvrV2TriggerReg.ComplEn[0..15]``
     - [29]
     - RW
     - differs: bitOffset :issue:`214`
       at 0x1000 [28] RW, step 0x100
     - Enable complementary trigger outputs
   * - ``0x1000`` + ``0x100`` * i
     - ``EvrV2TriggerReg.ComplAnd[0..15]``
     - [30]
     - RW
     - differs: bitOffset :issue:`214`
       at 0x1000 [29] RW, step 0x100
     - Complementary trigger logic
   * - ``0x1000`` + ``0x100`` * i
     - ``EvrV2TriggerReg.EnableTrig[0..15]``
       YAML: ``EvrV2TriggerReg.Enable[0..15]``
     - [31]
     - RW
     - agrees
     - Trigger Enable
   * - ``0x1004`` + ``0x100`` * i
     - ``EvrV2TriggerReg.Delay[0..15]``
     - [27:0]
     - RW
     - agrees
     - Delay in ticks
   * - ``0x1008`` + ``0x100`` * i
     - ``EvrV2TriggerReg.Width[0..15]``
     - [27:0]
     - RW
     - agrees
     - Width in ticks
   * - ``0x100C`` + ``0x100`` * i
     - ``EvrV2TriggerReg.DelayTap[0..15]``
     - [5:0]
     - RW
     - agrees
     - Delay tpa in ticks/64 (Only valid register is USE_TAP_C=true)
   * - ``0x100C`` + ``0x100`` * i
     - ``EvrV2TriggerReg.DelayTapReadback[0..15]``
     - [21:16]
     - RO
     - agrees
     - Delay tap readback in ticks/64 (Only valid register is USE_TAP_C=true)

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``EvrV2ChannelReg.DestSel`` (bitSize): ``EvrV2ChannelReg.DestSel[0] python width 16 vs yaml width 19 (first differing element 0 of 16, 16 differ)`` :issue:`215`
   * ``EvrV2ChannelReg.DestType`` (missing-in-yaml): ``EvrV2ChannelReg.DestType[0] is in python at bit 61 (width 2) but not in yaml (first differing element 0 of 16, 16 differ)`` :issue:`215`
   * ``EvrV2ChannelReg.RateSel`` (bitSize): ``EvrV2ChannelReg.RateSel[0] python width 11 vs yaml width 13 (first differing element 0 of 16, 16 differ)`` :issue:`215`
   * ``EvrV2ChannelReg.RateType`` (missing-in-yaml): ``EvrV2ChannelReg.RateType[0] is in python at bit 43 (width 2) but not in yaml (first differing element 0 of 16, 16 differ)`` :issue:`215`
   * ``EvrV2TriggerReg.ComplAnd`` (bitOffset): ``EvrV2TriggerReg.ComplAnd[0] python bit 32798 (word 0x1000 bit 30) vs yaml bit 32797 (word 0x1000 bit 29) (first differing element 0 of 16, 16 differ)`` :issue:`214`
   * ``EvrV2TriggerReg.ComplEn`` (bitOffset): ``EvrV2TriggerReg.ComplEn[0] python bit 32797 (word 0x1000 bit 29) vs yaml bit 32796 (word 0x1000 bit 28) (first differing element 0 of 16, 16 differ)`` :issue:`214`
