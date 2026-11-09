.. _register-map-tpg:

TPG registers
=============

No RTL in repo: the firmware that implements this block lives outside this repository, so the tables show the PyRogue declarations and how the YAML map agrees with them.

Python class: :repo:`python/LclsTimingCore/TPG.py`. YAML map: :repo:`yaml/TPG.yaml`.

The class adds these child devices; their registers appear below with the child name in front.

.. list-table::
   :header-rows: 1
   :widths: 25 30 15 10 20

   * - Child
     - Class
     - Offset
     - Count
     - Stride
   * - ``TPGControl``
     - :ref:`TPGControl <register-map-tpgcontrol>`
     - ``0x0``
     - 1
     - none
   * - ``TPGStatus``
     - :ref:`TPGStatus <register-map-tpgstatus>`
     - ``0x400``
     - 1
     - none
   * - ``TPGSeqState``
     - :ref:`TPGSeqState <register-map-tpgseqstate>`
     - ``0x800``
     - 1
     - none
   * - ``TPGSeqJump``
     - :ref:`TPGSeqJump <register-map-tpgseqjump>`
     - ``0x400``
     - 1
     - none

Variant default
---------------

Python arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 30 55 15

   * - YAML map
     - Parse error
     - Issue
   * - :repo:`yaml/TPG.yaml`
     - ``ScannerError`` at line 69 of the text after the includes are spliced in: mapping values are not allowed here
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
     - ``TPGControl.NBeamSeq``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - Number of beam control sequences
   * - ``0x000``
     - ``TPGControl.NControlSeq``
     - [15:8]
     - RO
     - map does not parse :issue:`218`
     - Number of experiment control sequences
   * - ``0x000``
     - ``TPGControl.NArraysBSA``
     - [23:16]
     - RO
     - map does not parse :issue:`218`
     - Number of BSA arrays
   * - ``0x000``
     - ``TPGControl.SeqAddrLen``
     - [27:24]
     - RO
     - map does not parse :issue:`218`
     - Sequence instruction at offset bus width
   * - ``0x000``
     - ``TPGControl.NAllowSeq``
     - [31:28]
     - RO
     - map does not parse :issue:`218`
     - Number of allow table sequences
   * - ``0x004``
     - ``TPGControl.ClockPeriod``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Period of beam synchronous clock (ns/cycle)
   * - ``0x008``
     - ``TPGControl.BaseControl``
     - [15:0]
     - RW
     - map does not parse :issue:`218`
     - Base rate control divisor
   * - ``0x00C``
     - ``TPGControl.ACDelay``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Adjustable delay for power line crossing measurement
   * - ``0x010``
     - ``TPGControl.PulseIdL``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Pulse ID lower word
   * - ``0x014``
     - ``TPGControl.PulseIdU``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Pulse ID upper word
   * - ``0x018``
     - ``TPGControl.TStampL``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Time stamp lower word
   * - ``0x01C``
     - ``TPGControl.TStampU``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Time stamp upper word
   * - ``0x020`` + ``8 bits`` * i
     - ``TPGControl.ACRateDiv[0..5]``
     - [7:0]
     - RW
     - map does not parse :issue:`218`
     - Power line synch rate marker divisors
   * - ``0x040`` + ``0x4`` * i
     - ``TPGControl.FixedRateDiv[0..9]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Fixed rate marker divisors
   * - ``0x068``
     - ``TPGControl.RateReload``
     - [0]
     - WO
     - map does not parse :issue:`218`
     - Loads cached ac/fixed rate marker divisors
   * - ``0x070``
     - ``TPGControl.Sync``
     - [0]
     - RW
     - map does not parse :issue:`218`
     - Sync status with 71kHz
   * - ``0x074``
     - ``TPGControl.IrqFifoEnable``
     - [0]
     - RW
     - map does not parse :issue:`218`
     - Enable sequence checkpoint interrupt
   * - ``0x074``
     - ``TPGControl.IrqIntvEnable``
     - [1]
     - RW
     - map does not parse :issue:`218`
     - Enable interval counter interrupt
   * - ``0x074``
     - ``TPGControl.IrqBsaEnable``
     - [2]
     - RW
     - map does not parse :issue:`218`
     - Enable BSA complete interrupt
   * - ``0x074``
     - ``TPGControl.IrqEnable``
     - [31]
     - RW
     - map does not parse :issue:`218`
     - Enable interrupts
   * - ``0x078``
     - ``TPGControl.IrqIntvStatus``
     - [0]
     - RW
     - map does not parse :issue:`218`
     - Interval counters updated
   * - ``0x078``
     - ``TPGControl.IrqBsaStatus``
     - [1]
     - RO
     - map does not parse :issue:`218`
     - BSA complete updated
   * - ``0x07C``
     - ``TPGControl.SeqFifoData``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Sequence checkpoint data
   * - ``0x080`` + ``0x4`` * i
     - ``TPGControl.BeamSeqCntl[0..15]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Beam sequence arbitration control
   * - ``0x100``
     - ``TPGControl.SeqResetL``
     - [31:0]
     - WO
     - map does not parse :issue:`218`
     - Sequence restart lower word
   * - ``0x104``
     - ``TPGControl.SeqResetU``
     - [31:0]
     - WO
     - map does not parse :issue:`218`
     - Sequence restart upper word
   * - ``0x120`` + ``0x4`` * i
     - ``TPGControl.BeamEnergy[0..3]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Beam energy meta data
   * - ``0x1E4``
     - ``TPGControl.BeamDiagCntl``
     - [31:0]
     - WO
     - map does not parse :issue:`218`
     - Beam diagnostic buffer control
   * - ``0x1E8`` + ``0x4`` * i
     - ``TPGControl.BeamDiagStat[0..3]``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Beam diagnostic latched status
   * - ``0x1F8``
     - ``TPGControl.BsaCompleteL``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa buffers complete lower word
   * - ``0x1FC``
     - ``TPGControl.BsaCompleteU``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa buffers complete upper word
   * - ``0x200`` + ``0x8`` * i
     - ``TPGControl.BsaEventSel[0..63]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa definition rate/destination selection
   * - ``0x204`` + ``0x8`` * i
     - ``TPGControl.BsaStatSel[0..63]``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Bsa definition samples to average/acquire
   * - ``0x400`` + ``0x4`` * i
     - ``TPGSeqJump.StartAddr[0..1023]``
     - [11:0]
     - RW
     - map does not parse :issue:`218`
     - Sequence start offset
   * - ``0x400`` + ``0x4`` * i
     - ``TPGStatus.BsaStat[0..63]``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - BSA status num averaged/written
   * - ``0x400`` + ``0x4`` * i
     - ``TPGSeqJump.Class[0..1023]``
     - [11:8]
     - RW
     - map does not parse :issue:`218`
     - Sequence power class
   * - ``0x400`` + ``0x4`` * i
     - ``TPGSeqJump.StartSync[0..1023]``
     - [31:16]
     - RW
     - map does not parse :issue:`218`
     - Start synchronization condition
   * - ``0x500``
     - ``TPGStatus.CountPLL``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - PLL Status changes
   * - ``0x504``
     - ``TPGStatus.Count186M``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - 186MHz clock counts / 16
   * - ``0x508``
     - ``TPGStatus.CountSyncE``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Sync error counts
   * - ``0x50C``
     - ``TPGStatus.CountIntv``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Interval timer
   * - ``0x510``
     - ``TPGStatus.CountBRT``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Base rate trigger count in interval
   * - ``0x514`` + ``0x4`` * i
     - ``TPGStatus.CountTrig[0..11]``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - External trigger count in interval
   * - ``0x544`` + ``16 bits`` * i
     - ``TPGStatus.CountSeq[0..63]``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Sequence requests in interval
   * - ``0x648``
     - ``TPGStatus.CountRxClks``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Recovered clock count / 16
   * - ``0x64C``
     - ``TPGStatus.CountRxDV``
     - [31:0]
     - RW
     - map does not parse :issue:`218`
     - Received data valid count
   * - ``0x800`` + ``0x8`` * i
     - ``TPGSeqState.SeqIndex[0..49]``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Sequencer instruction at offset
   * - ``0x804`` + ``0x8`` * i
     - ``TPGSeqState.SeqCondACount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition A counter
   * - ``0x804`` + ``0x40`` * i
     - ``TPGSeqState.SeqCondBCount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition B counter
   * - ``0x804`` + ``0x8`` * i
     - ``TPGSeqState.SeqCondCCount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition C counter
   * - ``0x804`` + ``0x8`` * i
     - ``TPGSeqState.SeqCondDCount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition D counter

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``<yaml>`` (missing-in-yaml): ``TPG.yaml does not parse, so no field of TPG can be compared with it`` :issue:`218`
