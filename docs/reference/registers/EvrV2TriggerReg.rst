EvrV2TriggerReg registers
=========================

Decode file: :repo:`LCLS-II/evr/rtl/EvrV2TrigReg.vhd`. Python class: :repo:`python/LclsTimingCore/EvrV2TriggerReg.py`. YAML map: :repo:`yaml/EvrV2TriggerReg.yaml`.

Variant default
---------------

RTL generics: ``TRIGGERS_C`` = ``1``, ``USE_TAP_C`` = ``False``, ``EVR_CARD_G`` = ``False``. Python arguments: none.

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
     - ``Source``
       RTL: ``channel``
     - [3:0]
     - RW
     - ``0x0``
     - agrees
     - not compared
     - Source mask
   * - ``0x000``
     - ``Polarity``
       RTL: ``polarity``
     - [16]
     - RW
     - ``0x1``
     - agrees
     - not compared
     - Signal polarity
   * - ``0x000``
     - ``ComplEn``
       RTL: ``complEn``
     - [28]
     - RW
     - ``0x0``
     - differs: bitOffset :issue:`214`
       at 0x000 [29] RW
     - not compared
     - Enable complementary trigger outputs
   * - ``0x000``
     - ``ComplAnd``
       RTL: ``complAnd``
     - [29]
     - RW
     - ``0x0``
     - differs: bitOffset :issue:`214`
       at 0x000 [30] RW
     - not compared
     - Complementary trigger logic
   * - ``0x000``
     - ``EnableTrig``
       RTL: ``enabled``
     - [31]
     - RW
     - ``0x0``
     - agrees
     - not compared
     - Trigger Enable
   * - ``0x004``
     - ``Delay``
       RTL: ``delay``
     - [27:0]
     - RW
     - ``0x0000000``
     - agrees
     - not compared
     - Delay in ticks
   * - ``0x008``
     - ``Width``
       RTL: ``width``
     - [27:0]
     - RW
     - ``0x0000001``
     - agrees
     - not compared
     - Width in ticks


Variant useTap
--------------

RTL generics: ``TRIGGERS_C`` = ``1``, ``USE_TAP_C`` = ``True``, ``EVR_CARD_G`` = ``False``. Python arguments: ``useTap=True``.

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
     - ``Source``
       RTL: ``channel``
     - [3:0]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Source mask
   * - ``0x000``
     - ``Polarity``
       RTL: ``polarity``
     - [16]
     - RW
     - ``0x1``
     - agrees
     - agrees
     - Signal polarity
   * - ``0x000``
     - ``ComplEn``
       RTL: ``complEn``
     - [28]
     - RW
     - ``0x0``
     - differs: bitOffset :issue:`214`
       at 0x000 [29] RW
     - agrees
     - Enable complementary trigger outputs
   * - ``0x000``
     - ``ComplAnd``
       RTL: ``complAnd``
     - [29]
     - RW
     - ``0x0``
     - differs: bitOffset :issue:`214`
       at 0x000 [30] RW
     - agrees
     - Complementary trigger logic
   * - ``0x000``
     - ``EnableTrig``
       RTL: ``enabled``
       YAML: ``Enable``
     - [31]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Trigger Enable
   * - ``0x004``
     - ``Delay``
       RTL: ``delay``
     - [27:0]
     - RW
     - ``0x0000000``
     - agrees
     - agrees
     - Delay in ticks
   * - ``0x008``
     - ``Width``
       RTL: ``width``
     - [27:0]
     - RW
     - ``0x0000001``
     - agrees
     - agrees
     - Width in ticks
   * - ``0x00C``
     - ``DelayTap``
       RTL: ``delayTap``
     - [5:0]
     - RW
     - ``0x00``
     - agrees
     - agrees
     - Delay tpa in ticks/64 (Only valid register is USE_TAP_C=true)
   * - ``0x00C``
     - ``DelayTapReadback``
       RTL: ``delay_rd``
     - [21:16]
     - RO
     - ``0x00``
     - agrees
     - agrees
     - Delay tap readback in ticks/64 (Only valid register is USE_TAP_C=true)

Access strobes carry no data and are not registers: a write of 0x00C pulses ``loadShift``.

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``ComplAnd`` (bitOffset): ``ComplAnd python bit 30 (word 0x0 bit 30) vs vhdl bit 29 (word 0x0 bit 29)`` :issue:`214`
   * ``ComplEn`` (bitOffset): ``ComplEn python bit 29 (word 0x0 bit 29) vs vhdl bit 28 (word 0x0 bit 28)`` :issue:`214`
