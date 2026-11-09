.. _register-map-tpgcontrol:

TPGControl registers
====================

No RTL in repo: the firmware that implements this block lives outside this repository, so the tables show the PyRogue declarations and how the YAML map agrees with them.

Python class: :repo:`python/LclsTimingCore/TPGControl.py`. YAML map: :repo:`yaml/TPGControl.yaml`.

Variant default
---------------

Python arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 30 55 15

   * - YAML map
     - Parse error
     - Issue
   * - :repo:`yaml/TPGControl.yaml`
     - ``ScannerError`` at line 58: mapping values are not allowed here
     - :issue:`218`

.. list-table::
   :header-rows: 1
   :widths: 10 22 8 7 23 30

   * - Offset
     - Field
     - Bits
     - Mode
     - YAML
     - Description
   * - ``0x000``
     - ``NBeamSeq``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - Number of beam control sequences
   * - ``0x000``
     - ``NControlSeq``
     - [15:8]
     - RO
     - map does not parse :issue:`218`
     - Number of experiment control sequences
   * - ``0x000``
     - ``NArraysBSA``
     - [23:16]
     - RO
     - map does not parse :issue:`218`
     - Number of BSA arrays
   * - ``0x000``
     - ``SeqAddrLen``
     - [27:24]
     - RO
     - map does not parse :issue:`218`
     - Sequence instruction at offset bus width
   * - ``0x000``
     - ``NAllowSeq``
     - [31:28]
     - RO
     - map does not parse :issue:`218`
     - Number of allow table sequences
   * - ``0x004``
     - ``ClockPeriod``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Period of beam synchronous clock (ns/cycle)
   * - ``0x008``
     - ``BaseControl``
     - [15:0]
     - RW
     - map does not parse :issue:`218`
     - Base rate control divisor
   * - ``0x00C``
     - ``ACDelay``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Adjustable delay for power line crossing measurement
   * - ``0x010``
     - ``PulseIdL``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Pulse ID lower word
   * - ``0x014``
     - ``PulseIdU``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Pulse ID upper word
   * - ``0x018``
     - ``TStampL``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Time stamp lower word
   * - ``0x01C``
     - ``TStampU``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Time stamp upper word
   * - ``0x020`` + ``8 bits`` * i
     - ``ACRateDiv[0..5]``
     - [7:0]
     - RW
     - map does not parse :issue:`218`
     - Power line synch rate marker divisors
   * - ``0x040`` + ``0x4`` * i
     - ``FixedRateDiv[0..9]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Fixed rate marker divisors
   * - ``0x068``
     - ``RateReload``
     - [0]
     - WO
     - map does not parse :issue:`218`
     - Loads cached ac/fixed rate marker divisors
   * - ``0x070``
     - ``Sync``
     - [0]
     - RW
     - map does not parse :issue:`218`
     - Sync status with 71kHz
   * - ``0x074``
     - ``IrqFifoEnable``
     - [0]
     - RW
     - map does not parse :issue:`218`
     - Enable sequence checkpoint interrupt
   * - ``0x074``
     - ``IrqIntvEnable``
     - [1]
     - RW
     - map does not parse :issue:`218`
     - Enable interval counter interrupt
   * - ``0x074``
     - ``IrqBsaEnable``
     - [2]
     - RW
     - map does not parse :issue:`218`
     - Enable BSA complete interrupt
   * - ``0x074``
     - ``IrqEnable``
     - [31]
     - RW
     - map does not parse :issue:`218`
     - Enable interrupts
   * - ``0x078``
     - ``IrqIntvStatus``
     - [0]
     - RW
     - map does not parse :issue:`218`
     - Interval counters updated
   * - ``0x078``
     - ``IrqBsaStatus``
     - [1]
     - RO
     - map does not parse :issue:`218`
     - BSA complete updated
   * - ``0x07C``
     - ``SeqFifoData``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Sequence checkpoint data
   * - ``0x080`` + ``0x4`` * i
     - ``BeamSeqCntl[0..15]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Beam sequence arbitration control
   * - ``0x100``
     - ``SeqResetL``
     - [31:0]
     - WO
     - map does not parse :issue:`218`
     - Sequence restart lower word
   * - ``0x104``
     - ``SeqResetU``
     - [31:0]
     - WO
     - map does not parse :issue:`218`
     - Sequence restart upper word
   * - ``0x120`` + ``0x4`` * i
     - ``BeamEnergy[0..3]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Beam energy meta data
   * - ``0x1E4``
     - ``BeamDiagCntl``
     - [31:0]
     - WO
     - map does not parse :issue:`218`
     - Beam diagnostic buffer control
   * - ``0x1E8`` + ``0x4`` * i
     - ``BeamDiagStat[0..3]``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Beam diagnostic latched status
   * - ``0x1F8``
     - ``BsaCompleteL``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa buffers complete lower word
   * - ``0x1FC``
     - ``BsaCompleteU``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa buffers complete upper word
   * - ``0x200`` + ``0x8`` * i
     - ``BsaEventSel[0..63]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa definition rate/destination selection
   * - ``0x204`` + ``0x8`` * i
     - ``BsaStatSel[0..63]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa definition samples to average/acquire

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``<yaml>`` (missing-in-yaml): ``TPGControl.yaml does not parse, so no field of TPGControl can be compared with it`` :issue:`218`
