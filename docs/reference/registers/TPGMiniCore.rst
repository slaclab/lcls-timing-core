TPGMiniCore registers
=====================

Decode file: :repo:`LCLS-II/core/rtl/TPGMiniReg.vhd`. Python class: :repo:`python/LclsTimingCore/TPGMiniCore.py`. YAML map: :repo:`yaml/TPGMiniCore.yaml`.

Variant default
---------------

RTL generics: ``NARRAYS_BSA`` = ``2``. Python arguments: none.

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
     - ``TxPolarity``
       RTL: ``txPolarity``
     - [1]
     - RW
     - not asserted
     - agrees
     - agrees
     - Invert transmit link polarity
   * - ``0x000``
     - ``TxLoopback``
       RTL: ``txLoopback``
     - [4:2]
     - RW
     - not asserted
     - agrees
     - agrees
     - Set transmit link loopback
   * - ``0x000``
     - ``TxInhibit``
       RTL: ``txInhibit``
     - [5]
     - RW
     - not asserted
     - agrees
     - agrees
     - Set transmit link inhibit
   * - ``0x004``
     - ``BaseControl``
       RTL: ``baseDivisor``
     - [15:0]
     - RW
     - not asserted
     - agrees
     - agrees
     - Base rate trigger divisor
   * - ``0x008``
     - ``PulseIdRd``
       RTL: ``pulseId@0x8``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Pulse ID read
   * - ``0x010``
     - ``TStampRd``
       RTL: ``timeStamp@0x10``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Time stamp read
   * - ``0x018`` + ``0x4`` * i
     - ``FixedRateDiv[0..9]``
       RTL: ``FixedRateDivisors[0..9]``
     - [19:0]
     - RW
     - not asserted
     - differs: bitSize :issue:`225`
       at 0x018 [31:0] RW, step 0x4
     - differs: bitSize :issue:`225`
       at 0x018 [31:0] RW, step 0x4
     - Fixed rate marker divisors
   * - ``0x040``
     - ``RateReload``
       RTL: ``FixedRateDivisors!write``
     - strobe
     - WO
     - not asserted
     - agrees
     - differs: mode :issue:`228`
       at 0x040 [0] RW
     - Loads cached fixed rate marker divisors
   * - ``0x050``
     - ``BsaCompleteRd``
       RTL: ``bsaComplete``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - BSA complete read
   * - ``0x050``
     - ``BsaCompleteWr``
       RTL: ``bsaClear``
     - [63:0]
     - WO
     - not asserted
     - agrees
     - differs: mode :issue:`228`
       at 0x050 [63:0] RW
     - BSA complete write
   * - ``0x058``
     - ``PulseIdWr``
       RTL: ``pulseId@0x58``
     - [63:0]
     - RW
     - not asserted
     - agrees
     - differs from Python: mode :issue:`228`
       at 0x058 [63:0] RW
     - Pulse ID write
   * - ``0x060``
     - ``TStampWr``
       RTL: ``timeStamp@0x60``
     - [63:0]
     - RW
     - not asserted
     - agrees
     - differs from Python: mode :issue:`228`
       at 0x060 [63:0] RW
     - Time stamp Write
   * - ``0x068``
     - ``TxReset``
       RTL: ``txReset``
     - [0]
     - WO
     - not asserted
     - agrees
     - differs: mode :issue:`228`
       at 0x068 [0] RW
     - Reset transmit link
   * - ``0x06C``
     - ``CountIntervalReset``
       RTL: ``intervalRst``
     - [0]
     - WO
     - not asserted
     - agrees
     - differs: mode :issue:`228`
       at 0x06C [0] RW
     - Count Interval Reset
   * - ``0x070``
     - ``PulseIdSet``
       RTL: ``pulseIdWrEn``
     - [0]
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x070 [0] RW
     - differs: mode :issue:`228`
       at 0x070 [0] RW
     - Activates PulseId register value
   * - ``0x074``
     - ``TStampSet``
       RTL: ``timeStampWrEn``
     - [0]
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x074 [0] RW
     - differs: mode :issue:`228`
       at 0x074 [0] RW
     - Activates Timestamp register value
   * - ``0x07C``
     - ``Lcls1BsaStart``
       RTL: ``wrEn!write``
     - strobe
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x07C [31:0] RW
     - differs: mode :issue:`228`
       at 0x07C [31:0] RW
     - Lcls-1 BSA Started by Writing any Value Here
   * - ``0x1FC``
     - ``BsaActive[0]``
       RTL: ``init[0]``
     - [0]
     - RW
     - not asserted
     - agrees
     - agrees
     - Activates/Deactivates BSA EDEF
   * - ``0x1FC``
     - ``BsaActive[1]``
       RTL: ``init[1]``
     - [1]
     - RW
     - not asserted
     - differs: bitOffset :issue:`223`
       at 0x1FC [8] RW
     - differs: bitOffset :issue:`223`
       at 0x1FC [8] RW
     - Activates/Deactivates BSA EDEF
   * - ``0x200`` + ``0x10`` * i
     - ``BsaRateSelMode[0..1]``
       RTL: ``bsadefRateMode[0..1]``
     - [1:0]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA def rate mode selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaFixedRate[0..1]``
       RTL: ``bsaDefFixedRate[0..1]``
     - [5:2]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA fixed rate mode selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaACRate[0..1]``
       RTL: ``bsaDefACRate[0..1]``
     - [8:6]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA AC rate mode selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaACTSMask[0..1]``
       RTL: ``bsaDefACTSMask[0..1]``
     - [14:9]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA AC timeslot mask selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaSequenceSelect[0..1]``
       RTL: ``bsaDefSeqSel[0..1]``
     - [19:15]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA sequencer selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaSequenceBitSelect[0..1]``
       RTL: ``bsaDefSeqBit[0..1]``
     - [23:20]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA sequencer bit selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaDestMode[0..1]``
       RTL: ``bsaDefDestMode[0..1]``
     - [25:24]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA destination mode
   * - ``0x204`` + ``0x10`` * i
     - ``BsaDestInclusiveMask[0..1]``
       RTL: ``bsadefDestInclM[0..1]``
     - [15:0]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA inclusive destination mask
   * - ``0x204`` + ``0x10`` * i
     - ``BsaDestExclusiveMask[0..1]``
       RTL: ``bsaDefDestExclM[0..1]``
     - [31:16]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA exclusive destination mask
   * - ``0x208`` + ``0x10`` * i
     - ``BsaNtoAvg[0..1]``
       RTL: ``bsadefNToAvg[0..1]``
     - [12:0]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA def num acquisitions to average
   * - ``0x208`` + ``0x10`` * i
     - ``BsaMaxSeverity[0..1]``
       RTL: ``bsaDefMaxSevr[0..1]``
     - [15:14]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA def max alarm severity
   * - ``0x208``
     - ``BsaAvgToWr[0]``
       RTL: ``bsaDefAvgToWr[0]``
     - [31:16]
     - RW
     - not asserted
     - agrees
     - agrees
     - BSA def num averages to record
   * - ``0x218``
     - ``BsaAvgToWr[1]``
       RTL: ``bsaDefAvgToWr[1]``
     - [31:16]
     - RW
     - not asserted
     - differs: offset :issue:`222`
       at 0x210 [31:16] RW
     - differs from Python: offset :issue:`222`
       at 0x218 [31:16] RW
     - BSA def num averages to record
   * - ``0x400`` + ``0x4`` * i
     - ``bsastatus[0..63]``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`228`
     - absent :issue:`228`
     - no description in source
   * - ``0x500``
     - ``PllCnt``
       RTL: ``pllChanged``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Count of PLL status changes
   * - ``0x504``
     - ``ClkCnt``
       RTL: ``count186M``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Count of local 186M clock
   * - ``0x508``
     - ``SyncErrCnt``
       RTL: ``countSyncE``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Count of 71k sync errors
   * - ``0x50C``
     - ``CountInterval``
       RTL: ``interval``
     - [31:0]
     - RW
     - not asserted
     - agrees
     - agrees
     - Interval counters update period
   * - ``0x510``
     - ``BaseRateCount``
       RTL: ``countBRT``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Count of base rate triggers

Not decoded: the parser could not interpret these RTL arms, so the Python and YAML registers of their words are compared with each other only.

* ``read 0x4C: concatenation``
* ``read 0x78: function call``
* ``write 0x78: expression of the write data``

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
   * - ``0x04C``
     - ``NBeamSeq``
     - [5:0]
     - RO
     - agrees
     - Number of beam request engines
   * - ``0x04C``
     - ``NControlSeq``
     - [13:6]
     - RO
     - agrees
     - Number of control sequence engines
   * - ``0x04C``
     - ``NArraysBsa``
     - [21:14]
     - RO
     - agrees
     - Number of BSA arrays
   * - ``0x04C``
     - ``SeqAddrLen``
     - [25:22]
     - RO
     - agrees
     - Number of beam sequence engines
   * - ``0x04C``
     - ``NAllowSeq``
     - [31:26]
     - RO
     - agrees
     - Number of beam allow engines
   * - ``0x078``
     - ``Lcls1BsaNumSamples``
     - [11:0]
     - RW
     - agrees
     - Lcls-1 BSA Number of Samples - 1
   * - ``0x078``
     - ``Lcls1BsaRate``
     - [14:12]
     - RW
     - agrees
     - Lcls-1 BSA Rate
   * - ``0x078``
     - ``Lcls1BsaTimeSlot``
     - [17:15]
     - RW
     - agrees
     - Lcls-1 BSA Time Slot
   * - ``0x078``
     - ``Lcls1BsaSeverity``
     - [19:18]
     - RW
     - agrees
     - Lcls-1 BSA Rejection Severity Threshold
   * - ``0x078``
     - ``Lcls1BsaEdefSlot``
     - [23:20]
     - RW
     - agrees
     - Lcls-1 BSA EDEF Slot Number
   * - ``0x078``
     - ``Lcls1BsaNumAvgs``
     - [31:24]
     - RW
     - agrees
     - Lcls-1 BSA Number of Values to Average per Sample - 1

Variant narrays1
----------------

RTL generics: ``NARRAYS_BSA`` = ``1``. Python arguments: ``NARRAYSBSA=1``.

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
     - ``TxPolarity``
       RTL: ``txPolarity``
     - [1]
     - RW
     - not asserted
     - agrees
     - not compared
     - Invert transmit link polarity
   * - ``0x000``
     - ``TxLoopback``
       RTL: ``txLoopback``
     - [4:2]
     - RW
     - not asserted
     - agrees
     - not compared
     - Set transmit link loopback
   * - ``0x000``
     - ``TxInhibit``
       RTL: ``txInhibit``
     - [5]
     - RW
     - not asserted
     - agrees
     - not compared
     - Set transmit link inhibit
   * - ``0x004``
     - ``BaseControl``
       RTL: ``baseDivisor``
     - [15:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Base rate trigger divisor
   * - ``0x008``
     - ``PulseIdRd``
       RTL: ``pulseId@0x8``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Pulse ID read
   * - ``0x010``
     - ``TStampRd``
       RTL: ``timeStamp@0x10``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Time stamp read
   * - ``0x018`` + ``0x4`` * i
     - ``FixedRateDiv[0..9]``
       RTL: ``FixedRateDivisors[0..9]``
     - [19:0]
     - RW
     - not asserted
     - differs: bitSize :issue:`225`
       at 0x018 [31:0] RW, step 0x4
     - not compared
     - Fixed rate marker divisors
   * - ``0x040``
     - ``RateReload``
       RTL: ``FixedRateDivisors!write``
     - strobe
     - WO
     - not asserted
     - agrees
     - not compared
     - Loads cached fixed rate marker divisors
   * - ``0x050``
     - ``BsaCompleteRd``
       RTL: ``bsaComplete``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - BSA complete read
   * - ``0x050``
     - ``BsaCompleteWr``
       RTL: ``bsaClear``
     - [63:0]
     - WO
     - not asserted
     - agrees
     - not compared
     - BSA complete write
   * - ``0x058``
     - ``PulseIdWr``
       RTL: ``pulseId@0x58``
     - [63:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Pulse ID write
   * - ``0x060``
     - ``TStampWr``
       RTL: ``timeStamp@0x60``
     - [63:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Time stamp Write
   * - ``0x068``
     - ``TxReset``
       RTL: ``txReset``
     - [0]
     - WO
     - not asserted
     - agrees
     - not compared
     - Reset transmit link
   * - ``0x06C``
     - ``CountIntervalReset``
       RTL: ``intervalRst``
     - [0]
     - WO
     - not asserted
     - agrees
     - not compared
     - Count Interval Reset
   * - ``0x070``
     - ``PulseIdSet``
       RTL: ``pulseIdWrEn``
     - [0]
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x070 [0] RW
     - not compared
     - Activates PulseId register value
   * - ``0x074``
     - ``TStampSet``
       RTL: ``timeStampWrEn``
     - [0]
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x074 [0] RW
     - not compared
     - Activates Timestamp register value
   * - ``0x07C``
     - ``Lcls1BsaStart``
       RTL: ``wrEn!write``
     - strobe
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x07C [31:0] RW
     - not compared
     - Lcls-1 BSA Started by Writing any Value Here
   * - ``0x1FC``
     - ``BsaActive[0]``
       RTL: ``init``
     - [0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Activates/Deactivates BSA EDEF
   * - ``0x200``
     - ``BsaRateSelMode[0]``
       RTL: ``bsadefRateMode``
     - [1:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def rate mode selection
   * - ``0x200``
     - ``BsaFixedRate[0]``
       RTL: ``bsaDefFixedRate``
     - [5:2]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA fixed rate mode selection
   * - ``0x200``
     - ``BsaACRate[0]``
       RTL: ``bsaDefACRate``
     - [8:6]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA AC rate mode selection
   * - ``0x200``
     - ``BsaACTSMask[0]``
       RTL: ``bsaDefACTSMask``
     - [14:9]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA AC timeslot mask selection
   * - ``0x200``
     - ``BsaSequenceSelect[0]``
       RTL: ``bsaDefSeqSel``
     - [19:15]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA sequencer selection
   * - ``0x200``
     - ``BsaSequenceBitSelect[0]``
       RTL: ``bsaDefSeqBit``
     - [23:20]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA sequencer bit selection
   * - ``0x200``
     - ``BsaDestMode[0]``
       RTL: ``bsaDefDestMode``
     - [25:24]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA destination mode
   * - ``0x204``
     - ``BsaDestInclusiveMask[0]``
       RTL: ``bsadefDestInclM``
     - [15:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA inclusive destination mask
   * - ``0x204``
     - ``BsaDestExclusiveMask[0]``
       RTL: ``bsaDefDestExclM``
     - [31:16]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA exclusive destination mask
   * - ``0x208``
     - ``BsaNtoAvg[0]``
       RTL: ``bsadefNToAvg``
     - [12:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def num acquisitions to average
   * - ``0x208``
     - ``BsaMaxSeverity[0]``
       RTL: ``bsaDefMaxSevr``
     - [15:14]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def max alarm severity
   * - ``0x208``
     - ``BsaAvgToWr[0]``
       RTL: ``bsaDefAvgToWr``
     - [31:16]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def num averages to record
   * - ``0x400`` + ``0x4`` * i
     - ``bsastatus[0..63]``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`228`
     - not compared
     - no description in source
   * - ``0x500``
     - ``PllCnt``
       RTL: ``pllChanged``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of PLL status changes
   * - ``0x504``
     - ``ClkCnt``
       RTL: ``count186M``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of local 186M clock
   * - ``0x508``
     - ``SyncErrCnt``
       RTL: ``countSyncE``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of 71k sync errors
   * - ``0x50C``
     - ``CountInterval``
       RTL: ``interval``
     - [31:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Interval counters update period
   * - ``0x510``
     - ``BaseRateCount``
       RTL: ``countBRT``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of base rate triggers

Not decoded: the parser could not interpret these RTL arms, so the Python and YAML registers of their words are compared with each other only.

* ``read 0x4C: concatenation``
* ``read 0x78: function call``
* ``write 0x78: expression of the write data``

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
   * - ``0x04C``
     - ``NBeamSeq``
     - [5:0]
     - RO
     - not compared
     - Number of beam request engines
   * - ``0x04C``
     - ``NControlSeq``
     - [13:6]
     - RO
     - not compared
     - Number of control sequence engines
   * - ``0x04C``
     - ``NArraysBsa``
     - [21:14]
     - RO
     - not compared
     - Number of BSA arrays
   * - ``0x04C``
     - ``SeqAddrLen``
     - [25:22]
     - RO
     - not compared
     - Number of beam sequence engines
   * - ``0x04C``
     - ``NAllowSeq``
     - [31:26]
     - RO
     - not compared
     - Number of beam allow engines
   * - ``0x078``
     - ``Lcls1BsaNumSamples``
     - [11:0]
     - RW
     - not compared
     - Lcls-1 BSA Number of Samples - 1
   * - ``0x078``
     - ``Lcls1BsaRate``
     - [14:12]
     - RW
     - not compared
     - Lcls-1 BSA Rate
   * - ``0x078``
     - ``Lcls1BsaTimeSlot``
     - [17:15]
     - RW
     - not compared
     - Lcls-1 BSA Time Slot
   * - ``0x078``
     - ``Lcls1BsaSeverity``
     - [19:18]
     - RW
     - not compared
     - Lcls-1 BSA Rejection Severity Threshold
   * - ``0x078``
     - ``Lcls1BsaEdefSlot``
     - [23:20]
     - RW
     - not compared
     - Lcls-1 BSA EDEF Slot Number
   * - ``0x078``
     - ``Lcls1BsaNumAvgs``
     - [31:24]
     - RW
     - not compared
     - Lcls-1 BSA Number of Values to Average per Sample - 1

Variant narrays4
----------------

RTL generics: ``NARRAYS_BSA`` = ``4``. Python arguments: ``NARRAYSBSA=4``.

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
     - ``TxPolarity``
       RTL: ``txPolarity``
     - [1]
     - RW
     - not asserted
     - agrees
     - not compared
     - Invert transmit link polarity
   * - ``0x000``
     - ``TxLoopback``
       RTL: ``txLoopback``
     - [4:2]
     - RW
     - not asserted
     - agrees
     - not compared
     - Set transmit link loopback
   * - ``0x000``
     - ``TxInhibit``
       RTL: ``txInhibit``
     - [5]
     - RW
     - not asserted
     - agrees
     - not compared
     - Set transmit link inhibit
   * - ``0x004``
     - ``BaseControl``
       RTL: ``baseDivisor``
     - [15:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Base rate trigger divisor
   * - ``0x008``
     - ``PulseIdRd``
       RTL: ``pulseId@0x8``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Pulse ID read
   * - ``0x010``
     - ``TStampRd``
       RTL: ``timeStamp@0x10``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Time stamp read
   * - ``0x018`` + ``0x4`` * i
     - ``FixedRateDiv[0..9]``
       RTL: ``FixedRateDivisors[0..9]``
     - [19:0]
     - RW
     - not asserted
     - differs: bitSize :issue:`225`
       at 0x018 [31:0] RW, step 0x4
     - not compared
     - Fixed rate marker divisors
   * - ``0x040``
     - ``RateReload``
       RTL: ``FixedRateDivisors!write``
     - strobe
     - WO
     - not asserted
     - agrees
     - not compared
     - Loads cached fixed rate marker divisors
   * - ``0x050``
     - ``BsaCompleteRd``
       RTL: ``bsaComplete``
     - [63:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - BSA complete read
   * - ``0x050``
     - ``BsaCompleteWr``
       RTL: ``bsaClear``
     - [63:0]
     - WO
     - not asserted
     - agrees
     - not compared
     - BSA complete write
   * - ``0x058``
     - ``PulseIdWr``
       RTL: ``pulseId@0x58``
     - [63:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Pulse ID write
   * - ``0x060``
     - ``TStampWr``
       RTL: ``timeStamp@0x60``
     - [63:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Time stamp Write
   * - ``0x068``
     - ``TxReset``
       RTL: ``txReset``
     - [0]
     - WO
     - not asserted
     - agrees
     - not compared
     - Reset transmit link
   * - ``0x06C``
     - ``CountIntervalReset``
       RTL: ``intervalRst``
     - [0]
     - WO
     - not asserted
     - agrees
     - not compared
     - Count Interval Reset
   * - ``0x070``
     - ``PulseIdSet``
       RTL: ``pulseIdWrEn``
     - [0]
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x070 [0] RW
     - not compared
     - Activates PulseId register value
   * - ``0x074``
     - ``TStampSet``
       RTL: ``timeStampWrEn``
     - [0]
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x074 [0] RW
     - not compared
     - Activates Timestamp register value
   * - ``0x07C``
     - ``Lcls1BsaStart``
       RTL: ``wrEn!write``
     - strobe
     - WO
     - not asserted
     - differs: mode :issue:`228`
       at 0x07C [31:0] RW
     - not compared
     - Lcls-1 BSA Started by Writing any Value Here
   * - ``0x1FC``
     - ``BsaActive[0]``
       RTL: ``init[0]``
     - [0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Activates/Deactivates BSA EDEF
   * - ``0x1FC`` + ``1 bits`` * i
     - ``BsaActive[1..3]``
       RTL: ``init[1..3]``
     - [1]
     - RW
     - not asserted
     - differs: bitOffset :issue:`223`
       at 0x1FC [8] RW, step 8 bits
     - not compared
     - Activates/Deactivates BSA EDEF
   * - ``0x200`` + ``0x10`` * i
     - ``BsaRateSelMode[0..3]``
       RTL: ``bsadefRateMode[0..3]``
     - [1:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def rate mode selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaFixedRate[0..3]``
       RTL: ``bsaDefFixedRate[0..3]``
     - [5:2]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA fixed rate mode selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaACRate[0..3]``
       RTL: ``bsaDefACRate[0..3]``
     - [8:6]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA AC rate mode selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaACTSMask[0..3]``
       RTL: ``bsaDefACTSMask[0..3]``
     - [14:9]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA AC timeslot mask selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaSequenceSelect[0..3]``
       RTL: ``bsaDefSeqSel[0..3]``
     - [19:15]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA sequencer selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaSequenceBitSelect[0..3]``
       RTL: ``bsaDefSeqBit[0..3]``
     - [23:20]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA sequencer bit selection
   * - ``0x200`` + ``0x10`` * i
     - ``BsaDestMode[0..3]``
       RTL: ``bsaDefDestMode[0..3]``
     - [25:24]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA destination mode
   * - ``0x204`` + ``0x10`` * i
     - ``BsaDestInclusiveMask[0..3]``
       RTL: ``bsadefDestInclM[0..3]``
     - [15:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA inclusive destination mask
   * - ``0x204`` + ``0x10`` * i
     - ``BsaDestExclusiveMask[0..3]``
       RTL: ``bsaDefDestExclM[0..3]``
     - [31:16]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA exclusive destination mask
   * - ``0x208`` + ``0x10`` * i
     - ``BsaNtoAvg[0..3]``
       RTL: ``bsadefNToAvg[0..3]``
     - [12:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def num acquisitions to average
   * - ``0x208`` + ``0x10`` * i
     - ``BsaMaxSeverity[0..3]``
       RTL: ``bsaDefMaxSevr[0..3]``
     - [15:14]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def max alarm severity
   * - ``0x208``
     - ``BsaAvgToWr[0]``
       RTL: ``bsaDefAvgToWr[0]``
     - [31:16]
     - RW
     - not asserted
     - agrees
     - not compared
     - BSA def num averages to record
   * - ``0x218`` + ``0x10`` * i
     - ``BsaAvgToWr[1..3]``
       RTL: ``bsaDefAvgToWr[1..3]``
     - [31:16]
     - RW
     - not asserted
     - differs: offset :issue:`222`
       at 0x210 [31:16] RW, step 0x8
     - not compared
     - BSA def num averages to record
   * - ``0x400`` + ``0x4`` * i
     - ``bsastatus[0..63]``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`228`
     - not compared
     - no description in source
   * - ``0x500``
     - ``PllCnt``
       RTL: ``pllChanged``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of PLL status changes
   * - ``0x504``
     - ``ClkCnt``
       RTL: ``count186M``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of local 186M clock
   * - ``0x508``
     - ``SyncErrCnt``
       RTL: ``countSyncE``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of 71k sync errors
   * - ``0x50C``
     - ``CountInterval``
       RTL: ``interval``
     - [31:0]
     - RW
     - not asserted
     - agrees
     - not compared
     - Interval counters update period
   * - ``0x510``
     - ``BaseRateCount``
       RTL: ``countBRT``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - not compared
     - Count of base rate triggers

Not decoded: the parser could not interpret these RTL arms, so the Python and YAML registers of their words are compared with each other only.

* ``read 0x4C: concatenation``
* ``read 0x78: function call``
* ``write 0x78: expression of the write data``

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
   * - ``0x04C``
     - ``NBeamSeq``
     - [5:0]
     - RO
     - not compared
     - Number of beam request engines
   * - ``0x04C``
     - ``NControlSeq``
     - [13:6]
     - RO
     - not compared
     - Number of control sequence engines
   * - ``0x04C``
     - ``NArraysBsa``
     - [21:14]
     - RO
     - not compared
     - Number of BSA arrays
   * - ``0x04C``
     - ``SeqAddrLen``
     - [25:22]
     - RO
     - not compared
     - Number of beam sequence engines
   * - ``0x04C``
     - ``NAllowSeq``
     - [31:26]
     - RO
     - not compared
     - Number of beam allow engines
   * - ``0x078``
     - ``Lcls1BsaNumSamples``
     - [11:0]
     - RW
     - not compared
     - Lcls-1 BSA Number of Samples - 1
   * - ``0x078``
     - ``Lcls1BsaRate``
     - [14:12]
     - RW
     - not compared
     - Lcls-1 BSA Rate
   * - ``0x078``
     - ``Lcls1BsaTimeSlot``
     - [17:15]
     - RW
     - not compared
     - Lcls-1 BSA Time Slot
   * - ``0x078``
     - ``Lcls1BsaSeverity``
     - [19:18]
     - RW
     - not compared
     - Lcls-1 BSA Rejection Severity Threshold
   * - ``0x078``
     - ``Lcls1BsaEdefSlot``
     - [23:20]
     - RW
     - not compared
     - Lcls-1 BSA EDEF Slot Number
   * - ``0x078``
     - ``Lcls1BsaNumAvgs``
     - [31:24]
     - RW
     - not compared
     - Lcls-1 BSA Number of Values to Average per Sample - 1

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``BsaActive`` (bitOffset): ``BsaActive[1] python bit 4072 (word 0x1fc bit 8) vs vhdl bit 4065 (word 0x1fc bit 1) (first differing element 1 of 2, 1 differ)`` :issue:`223`
   * ``BsaAvgToWr`` (offset): ``BsaAvgToWr[1] python bit 4240 (word 0x210 bit 16) vs vhdl bit 4304 (word 0x218 bit 16) (first differing element 1 of 2, 1 differ)`` :issue:`222`
   * ``BsaCompleteWr`` (mode): ``BsaCompleteWr python mode WO vs yaml mode RW`` :issue:`228`
   * ``CountIntervalReset`` (mode): ``CountIntervalReset python mode WO vs yaml mode RW`` :issue:`228`
   * ``FixedRateDiv`` (bitSize): ``FixedRateDiv[0] python width 32 vs vhdl width 20 (first differing element 0 of 10, 10 differ)`` :issue:`225`
   * ``Lcls1BsaStart`` (mode): ``Lcls1BsaStart python mode RW vs vhdl mode WO`` :issue:`228`
   * ``PulseIdSet`` (mode): ``PulseIdSet python mode RW vs vhdl mode WO`` :issue:`228`
   * ``PulseIdWr`` (mode): ``PulseIdWr python mode WO vs yaml mode RW`` :issue:`228`
   * ``RateReload`` (mode): ``FixedRateDivisors!write vhdl mode WO vs yaml mode RW`` :issue:`228`
   * ``TStampSet`` (mode): ``TStampSet python mode RW vs vhdl mode WO`` :issue:`228`
   * ``TStampWr`` (mode): ``TStampWr python mode WO vs yaml mode RW`` :issue:`228`
   * ``TxReset`` (mode): ``TxReset python mode WO vs yaml mode RW`` :issue:`228`
   * ``bsastatus`` (missing-in-python): ``bsastatus[0] is in vhdl at bit 8192 (width 32) but not in python (first differing element 0 of 64, 64 differ)`` :issue:`228`
   * ``bsastatus`` (missing-in-yaml): ``bsastatus[0] is in vhdl at bit 8192 (width 32) but not in yaml (first differing element 0 of 64, 64 differ)`` :issue:`228`
