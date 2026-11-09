.. _register-map-gthrxaligncheck:

GthRxAlignCheck registers
=========================

Decode file: :repo:`LCLS-II/core/rtl/GthRxAlignCheck.vhd`. Python class: :repo:`python/LclsTimingCore/GthRxAlignCheck.py`. YAML map: :repo:`yaml/GthRxAlignCheck.yaml`.

Variant default
---------------

RTL generics: none. Python arguments: none.

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
     - ``PhaseCount[0]``
       RTL: ``sample[0]``
     - [7:0]
     - RW
     - ``0x00``
     - differs: bitSize :issue:`224`, mode :issue:`228`
       at 0x000 [31:0] RO
     - differs: mode :issue:`228`; differs from Python: bitSize :issue:`224`
       at 0x000 [7:0] RO
     - Timing frame phase
   * - ``0x000`` + ``8 bits`` * i
     - ``PhaseCount[1..39]``
       RTL: ``sample[1..39]``
     - [15:8]
     - RW
     - ``0x00``
     - differs: offset :issue:`224`, bitSize :issue:`224`, mode :issue:`228`
       at 0x004 [31:0] RO, step 0x4
     - differs: mode :issue:`228`; differs from Python: offset :issue:`224`, bitSize :issue:`224`
       at 0x000 [15:8] RO, step 8 bits
     - Timing frame phase
   * - ``0x0A0`` + ``0x4`` * i
     - ``PhaseCount[40..63]``
     - [31:0]
     - RO
     - not asserted
     - differs: missing-in-vhdl :issue:`224`
       at 0x0A0 [31:0] RO, step 0x4
     - absent :issue:`224`
     - Timing frame phase
   * - ``0x100``
     - ``PhaseTarget``
       RTL: ``tgt``
     - [6:0]
     - RW
     - ``0x10``
     - agrees
     - agrees
     - Timing frame phase lock target
   * - ``0x100``
     - ``Mask``
       RTL: ``mask``
       YAML: ``PhaseMask``
     - [14:8]
     - RW
     - ``0x7E``
     - agrees
     - agrees
     - Mask
   * - ``0x100``
     - ``ResetLen``
       RTL: ``rstlen``
     - [19:16]
     - RW
     - ``0x3``
     - agrees
     - agrees
     - Reset length
   * - ``0x104``
     - ``LastPhase``
       RTL: ``last``
     - [15:0]
     - RW
     - ``0x0000``
     - differs: bitSize :issue:`228`, mode :issue:`228`
       at 0x104 [6:0] RO
     - differs: bitSize :issue:`228`, mode :issue:`228`
       at 0x104 [6:0] RO
     - Last timing frame phase seen
   * - ``0x108``
     - ``TxClkFreqRaw``
       RTL: ``txClkFreq``
       YAML: ``TxClkFreq``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - no description in source
   * - ``0x10C``
     - ``RxClkFreqRaw``
       RTL: ``rxClkFreq``
       YAML: ``RxClkFreq``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - no description in source

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``LastPhase`` (bitSize): ``LastPhase python width 7 vs vhdl width 16`` :issue:`228`
   * ``LastPhase`` (mode): ``LastPhase python mode RO vs vhdl mode RW`` :issue:`228`
   * ``PhaseCount`` (bitSize): ``PhaseCount[0] python width 32 vs vhdl width 8 (first differing element 0 of 64, 40 differ)`` :issue:`224`
   * ``PhaseCount`` (missing-in-vhdl): ``PhaseCount[40] is in python at bit 1280 (width 32) but not in vhdl (first differing element 40 of 64, 24 differ)`` :issue:`224`
   * ``PhaseCount`` (missing-in-yaml): ``PhaseCount[40] is in python at bit 1280 (width 32) but not in yaml (first differing element 40 of 64, 24 differ)`` :issue:`224`
   * ``PhaseCount`` (mode): ``PhaseCount[0] python mode RO vs vhdl mode RW (first differing element 0 of 64, 40 differ)`` :issue:`228`
   * ``PhaseCount`` (offset): ``PhaseCount[1] python bit 32 (word 0x4 bit 0) vs vhdl bit 8 (word 0x0 bit 8) (first differing element 1 of 64, 39 differ)`` :issue:`224`
