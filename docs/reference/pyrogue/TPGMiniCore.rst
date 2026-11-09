.. _api-tpgminicore:

TPGMiniCore
===========

Source: :repo:`python/LclsTimingCore/TPGMiniCore.py`. Register table: :ref:`TPGMiniCore registers <register-map-tpgminicore>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'TPGMiniCore'``
   * - ``description``
     - ``'Embedded timing pattern generator'``
   * - ``NARRAYSBSA``
     - ``2``
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
   * - ``TxPolarity``
     - RemoteVariable
     - ``0x000``
     - [1]
     - RW
     - UInt
     - none
     - Invert transmit link polarity
   * - ``TxLoopback``
     - RemoteVariable
     - ``0x000``
     - [4:2]
     - RW
     - UInt
     - none
     - Set transmit link loopback
   * - ``TxInhibit``
     - RemoteVariable
     - ``0x000``
     - [5]
     - RW
     - UInt
     - none
     - Set transmit link inhibit
   * - ``BaseControl``
     - RemoteVariable
     - ``0x004``
     - [15:0]
     - RW
     - UInt
     - none
     - Base rate trigger divisor
   * - ``PulseIdRd``
     - RemoteVariable
     - ``0x008``
     - [63:0]
     - RO
     - UInt
     - none
     - Pulse ID read
   * - ``TStampRd``
     - RemoteVariable
     - ``0x010``
     - [63:0]
     - RO
     - UInt
     - none
     - Time stamp read
   * - ``FixedRateDiv[0..9]``
     - RemoteVariable
     - ``0x018`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Fixed rate marker divisors
   * - ``RateReload``
     - RemoteVariable
     - ``0x040``
     - [0]
     - WO
     - UInt
     - none
     - Loads cached fixed rate marker divisors
   * - ``NBeamSeq``
     - RemoteVariable
     - ``0x04C``
     - [5:0]
     - RO
     - UInt
     - none
     - Number of beam request engines
   * - ``NControlSeq``
     - RemoteVariable
     - ``0x04C``
     - [13:6]
     - RO
     - UInt
     - none
     - Number of control sequence engines
   * - ``NArraysBsa``
     - RemoteVariable
     - ``0x04C``
     - [21:14]
     - RO
     - UInt
     - none
     - Number of BSA arrays
   * - ``SeqAddrLen``
     - RemoteVariable
     - ``0x04C``
     - [25:22]
     - RO
     - UInt
     - none
     - Number of beam sequence engines
   * - ``NAllowSeq``
     - RemoteVariable
     - ``0x04C``
     - [31:26]
     - RO
     - UInt
     - none
     - Number of beam allow engines
   * - ``BsaCompleteRd``
     - RemoteVariable
     - ``0x050``
     - [63:0]
     - RO
     - UInt
     - none
     - BSA complete read
   * - ``BsaCompleteWr``
     - RemoteVariable
     - ``0x050``
     - [63:0]
     - WO
     - UInt
     - none
     - BSA complete write
   * - ``PulseIdWr``
     - RemoteVariable
     - ``0x058``
     - [63:0]
     - WO
     - UInt
     - none
     - Pulse ID write
   * - ``TStampWr``
     - RemoteVariable
     - ``0x060``
     - [63:0]
     - WO
     - UInt
     - none
     - Time stamp Write
   * - ``TxReset``
     - RemoteVariable
     - ``0x068``
     - [0]
     - WO
     - UInt
     - none
     - Reset transmit link
   * - ``CountIntervalReset``
     - RemoteVariable
     - ``0x06C``
     - [0]
     - WO
     - UInt
     - none
     - Count Interval Reset
   * - ``PulseIdSet``
     - RemoteVariable
     - ``0x070``
     - [0]
     - RW
     - UInt
     - none
     - Activates PulseId register value
   * - ``TStampSet``
     - RemoteVariable
     - ``0x074``
     - [0]
     - RW
     - UInt
     - none
     - Activates Timestamp register value
   * - ``Lcls1BsaNumSamples``
     - RemoteVariable
     - ``0x078``
     - [11:0]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Number of Samples - 1
   * - ``Lcls1BsaRate``
     - RemoteVariable
     - ``0x078``
     - [14:12]
     - RW
     - enum 0: 120Hz, 1: 60Hz, 2: 30Hz, 3: 10Hz, 4: 5Hz, 5: 1Hz, 6: 0.5Hz
     - none
     - Lcls-1 BSA Rate
   * - ``Lcls1BsaTimeSlot``
     - RemoteVariable
     - ``0x078``
     - [17:15]
     - RW
     - enum 0: TS1, 1: TS2, 2: TS3, 3: TS4, 4: TS5, 5: TS6
     - none
     - Lcls-1 BSA Time Slot
   * - ``Lcls1BsaSeverity``
     - RemoteVariable
     - ``0x078``
     - [19:18]
     - RW
     - enum 0: INVALID, 1: MAJOR, 2: MINOR
     - none
     - Lcls-1 BSA Rejection Severity Threshold
   * - ``Lcls1BsaEdefSlot``
     - RemoteVariable
     - ``0x078``
     - [23:20]
     - RW
     - UInt
     - none
     - Lcls-1 BSA EDEF Slot Number
   * - ``Lcls1BsaNumAvgs``
     - RemoteVariable
     - ``0x078``
     - [31:24]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Number of Values to Average per Sample - 1
   * - ``Lcls1BsaStart``
     - RemoteVariable
     - ``0x07C``
     - [31:0]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Started by Writing any Value Here
   * - ``BsaActive[0..1]``
     - RemoteVariable
     - ``0x1FC`` + ``8 bits`` * i
     - [0]
     - RW
     - UInt
     - none
     - Activates/Deactivates BSA EDEF
   * - ``BsaRateSelMode[0..1]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [1:0]
     - RW
     - enum 0: FixedRate, 1: ACRate, 2: Sequencer
     - none
     - BSA def rate mode selection
   * - ``BsaFixedRate[0..1]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [5:2]
     - RW
     - enum 0: 1MHz, 1: 71kHz, 2: 10kHz, 3: 1kHz, 4: 100Hz, 5: 10Hz, 6: 1Hz
     - none
     - BSA fixed rate mode selection
   * - ``BsaACRate[0..1]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [8:6]
     - RW
     - enum 0: 60Hz, 1: 30Hz, 2: 10Hz, 3: 5Hz, 4: 1Hz, 5: 0.5Hz
     - none
     - BSA AC rate mode selection
   * - ``BsaACTSMask[0..1]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [14:9]
     - RW
     - UInt
     - none
     - BSA AC timeslot mask selection
   * - ``BsaSequenceSelect[0..1]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [19:15]
     - RW
     - UInt
     - none
     - BSA sequencer selection
   * - ``BsaSequenceBitSelect[0..1]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [23:20]
     - RW
     - UInt
     - none
     - BSA sequencer bit selection
   * - ``BsaDestMode[0..1]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [25:24]
     - RW
     - enum 0: Dont_Care, 1: Inclusive, 2: Exclusive
     - none
     - BSA destination mode
   * - ``BsaDestInclusiveMask[0..1]``
     - RemoteVariable
     - ``0x204`` + ``0x10`` * i
     - [15:0]
     - RW
     - UInt
     - none
     - BSA inclusive destination mask
   * - ``BsaDestExclusiveMask[0..1]``
     - RemoteVariable
     - ``0x204`` + ``0x10`` * i
     - [31:16]
     - RW
     - UInt
     - none
     - BSA exclusive destination mask
   * - ``BsaNtoAvg[0..1]``
     - RemoteVariable
     - ``0x208`` + ``0x10`` * i
     - [12:0]
     - RW
     - UInt
     - none
     - BSA def num acquisitions to average
   * - ``BsaMaxSeverity[0..1]``
     - RemoteVariable
     - ``0x208`` + ``0x10`` * i
     - [15:14]
     - RW
     - enum 0: NoAlarm, 1: Minor, 2: Major, 3: Invalid
     - none
     - BSA def max alarm severity
   * - ``BsaAvgToWr[0..1]``
     - RemoteVariable
     - ``0x208`` + ``0x8`` * i
     - [31:16]
     - RW
     - UInt
     - none
     - BSA def num averages to record
   * - ``PllCnt``
     - RemoteVariable
     - ``0x500``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of PLL status changes
   * - ``ClkCnt``
     - RemoteVariable
     - ``0x504``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of local 186M clock
   * - ``SyncErrCnt``
     - RemoteVariable
     - ``0x508``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of 71k sync errors
   * - ``CountInterval``
     - RemoteVariable
     - ``0x50C``
     - [31:0]
     - RW
     - UInt
     - none
     - Interval counters update period
   * - ``BaseRateCount``
     - RemoteVariable
     - ``0x510``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of base rate triggers

Arguments NARRAYSBSA1
~~~~~~~~~~~~~~~~~~~~~

Constructor arguments: ``NARRAYSBSA=1``.

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
   * - ``TxPolarity``
     - RemoteVariable
     - ``0x000``
     - [1]
     - RW
     - UInt
     - none
     - Invert transmit link polarity
   * - ``TxLoopback``
     - RemoteVariable
     - ``0x000``
     - [4:2]
     - RW
     - UInt
     - none
     - Set transmit link loopback
   * - ``TxInhibit``
     - RemoteVariable
     - ``0x000``
     - [5]
     - RW
     - UInt
     - none
     - Set transmit link inhibit
   * - ``BaseControl``
     - RemoteVariable
     - ``0x004``
     - [15:0]
     - RW
     - UInt
     - none
     - Base rate trigger divisor
   * - ``PulseIdRd``
     - RemoteVariable
     - ``0x008``
     - [63:0]
     - RO
     - UInt
     - none
     - Pulse ID read
   * - ``TStampRd``
     - RemoteVariable
     - ``0x010``
     - [63:0]
     - RO
     - UInt
     - none
     - Time stamp read
   * - ``FixedRateDiv[0..9]``
     - RemoteVariable
     - ``0x018`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Fixed rate marker divisors
   * - ``RateReload``
     - RemoteVariable
     - ``0x040``
     - [0]
     - WO
     - UInt
     - none
     - Loads cached fixed rate marker divisors
   * - ``NBeamSeq``
     - RemoteVariable
     - ``0x04C``
     - [5:0]
     - RO
     - UInt
     - none
     - Number of beam request engines
   * - ``NControlSeq``
     - RemoteVariable
     - ``0x04C``
     - [13:6]
     - RO
     - UInt
     - none
     - Number of control sequence engines
   * - ``NArraysBsa``
     - RemoteVariable
     - ``0x04C``
     - [21:14]
     - RO
     - UInt
     - none
     - Number of BSA arrays
   * - ``SeqAddrLen``
     - RemoteVariable
     - ``0x04C``
     - [25:22]
     - RO
     - UInt
     - none
     - Number of beam sequence engines
   * - ``NAllowSeq``
     - RemoteVariable
     - ``0x04C``
     - [31:26]
     - RO
     - UInt
     - none
     - Number of beam allow engines
   * - ``BsaCompleteRd``
     - RemoteVariable
     - ``0x050``
     - [63:0]
     - RO
     - UInt
     - none
     - BSA complete read
   * - ``BsaCompleteWr``
     - RemoteVariable
     - ``0x050``
     - [63:0]
     - WO
     - UInt
     - none
     - BSA complete write
   * - ``PulseIdWr``
     - RemoteVariable
     - ``0x058``
     - [63:0]
     - WO
     - UInt
     - none
     - Pulse ID write
   * - ``TStampWr``
     - RemoteVariable
     - ``0x060``
     - [63:0]
     - WO
     - UInt
     - none
     - Time stamp Write
   * - ``TxReset``
     - RemoteVariable
     - ``0x068``
     - [0]
     - WO
     - UInt
     - none
     - Reset transmit link
   * - ``CountIntervalReset``
     - RemoteVariable
     - ``0x06C``
     - [0]
     - WO
     - UInt
     - none
     - Count Interval Reset
   * - ``PulseIdSet``
     - RemoteVariable
     - ``0x070``
     - [0]
     - RW
     - UInt
     - none
     - Activates PulseId register value
   * - ``TStampSet``
     - RemoteVariable
     - ``0x074``
     - [0]
     - RW
     - UInt
     - none
     - Activates Timestamp register value
   * - ``Lcls1BsaNumSamples``
     - RemoteVariable
     - ``0x078``
     - [11:0]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Number of Samples - 1
   * - ``Lcls1BsaRate``
     - RemoteVariable
     - ``0x078``
     - [14:12]
     - RW
     - enum 0: 120Hz, 1: 60Hz, 2: 30Hz, 3: 10Hz, 4: 5Hz, 5: 1Hz, 6: 0.5Hz
     - none
     - Lcls-1 BSA Rate
   * - ``Lcls1BsaTimeSlot``
     - RemoteVariable
     - ``0x078``
     - [17:15]
     - RW
     - enum 0: TS1, 1: TS2, 2: TS3, 3: TS4, 4: TS5, 5: TS6
     - none
     - Lcls-1 BSA Time Slot
   * - ``Lcls1BsaSeverity``
     - RemoteVariable
     - ``0x078``
     - [19:18]
     - RW
     - enum 0: INVALID, 1: MAJOR, 2: MINOR
     - none
     - Lcls-1 BSA Rejection Severity Threshold
   * - ``Lcls1BsaEdefSlot``
     - RemoteVariable
     - ``0x078``
     - [23:20]
     - RW
     - UInt
     - none
     - Lcls-1 BSA EDEF Slot Number
   * - ``Lcls1BsaNumAvgs``
     - RemoteVariable
     - ``0x078``
     - [31:24]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Number of Values to Average per Sample - 1
   * - ``Lcls1BsaStart``
     - RemoteVariable
     - ``0x07C``
     - [31:0]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Started by Writing any Value Here
   * - ``BsaActive[0]``
     - RemoteVariable
     - ``0x1FC``
     - [0]
     - RW
     - UInt
     - none
     - Activates/Deactivates BSA EDEF
   * - ``BsaRateSelMode[0]``
     - RemoteVariable
     - ``0x200``
     - [1:0]
     - RW
     - enum 0: FixedRate, 1: ACRate, 2: Sequencer
     - none
     - BSA def rate mode selection
   * - ``BsaFixedRate[0]``
     - RemoteVariable
     - ``0x200``
     - [5:2]
     - RW
     - enum 0: 1MHz, 1: 71kHz, 2: 10kHz, 3: 1kHz, 4: 100Hz, 5: 10Hz, 6: 1Hz
     - none
     - BSA fixed rate mode selection
   * - ``BsaACRate[0]``
     - RemoteVariable
     - ``0x200``
     - [8:6]
     - RW
     - enum 0: 60Hz, 1: 30Hz, 2: 10Hz, 3: 5Hz, 4: 1Hz, 5: 0.5Hz
     - none
     - BSA AC rate mode selection
   * - ``BsaACTSMask[0]``
     - RemoteVariable
     - ``0x200``
     - [14:9]
     - RW
     - UInt
     - none
     - BSA AC timeslot mask selection
   * - ``BsaSequenceSelect[0]``
     - RemoteVariable
     - ``0x200``
     - [19:15]
     - RW
     - UInt
     - none
     - BSA sequencer selection
   * - ``BsaSequenceBitSelect[0]``
     - RemoteVariable
     - ``0x200``
     - [23:20]
     - RW
     - UInt
     - none
     - BSA sequencer bit selection
   * - ``BsaDestMode[0]``
     - RemoteVariable
     - ``0x200``
     - [25:24]
     - RW
     - enum 0: Dont_Care, 1: Inclusive, 2: Exclusive
     - none
     - BSA destination mode
   * - ``BsaDestInclusiveMask[0]``
     - RemoteVariable
     - ``0x204``
     - [15:0]
     - RW
     - UInt
     - none
     - BSA inclusive destination mask
   * - ``BsaDestExclusiveMask[0]``
     - RemoteVariable
     - ``0x204``
     - [31:16]
     - RW
     - UInt
     - none
     - BSA exclusive destination mask
   * - ``BsaNtoAvg[0]``
     - RemoteVariable
     - ``0x208``
     - [12:0]
     - RW
     - UInt
     - none
     - BSA def num acquisitions to average
   * - ``BsaMaxSeverity[0]``
     - RemoteVariable
     - ``0x208``
     - [15:14]
     - RW
     - enum 0: NoAlarm, 1: Minor, 2: Major, 3: Invalid
     - none
     - BSA def max alarm severity
   * - ``BsaAvgToWr[0]``
     - RemoteVariable
     - ``0x208``
     - [31:16]
     - RW
     - UInt
     - none
     - BSA def num averages to record
   * - ``PllCnt``
     - RemoteVariable
     - ``0x500``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of PLL status changes
   * - ``ClkCnt``
     - RemoteVariable
     - ``0x504``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of local 186M clock
   * - ``SyncErrCnt``
     - RemoteVariable
     - ``0x508``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of 71k sync errors
   * - ``CountInterval``
     - RemoteVariable
     - ``0x50C``
     - [31:0]
     - RW
     - UInt
     - none
     - Interval counters update period
   * - ``BaseRateCount``
     - RemoteVariable
     - ``0x510``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of base rate triggers

Arguments NARRAYSBSA4
~~~~~~~~~~~~~~~~~~~~~

Constructor arguments: ``NARRAYSBSA=4``.

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
   * - ``TxPolarity``
     - RemoteVariable
     - ``0x000``
     - [1]
     - RW
     - UInt
     - none
     - Invert transmit link polarity
   * - ``TxLoopback``
     - RemoteVariable
     - ``0x000``
     - [4:2]
     - RW
     - UInt
     - none
     - Set transmit link loopback
   * - ``TxInhibit``
     - RemoteVariable
     - ``0x000``
     - [5]
     - RW
     - UInt
     - none
     - Set transmit link inhibit
   * - ``BaseControl``
     - RemoteVariable
     - ``0x004``
     - [15:0]
     - RW
     - UInt
     - none
     - Base rate trigger divisor
   * - ``PulseIdRd``
     - RemoteVariable
     - ``0x008``
     - [63:0]
     - RO
     - UInt
     - none
     - Pulse ID read
   * - ``TStampRd``
     - RemoteVariable
     - ``0x010``
     - [63:0]
     - RO
     - UInt
     - none
     - Time stamp read
   * - ``FixedRateDiv[0..9]``
     - RemoteVariable
     - ``0x018`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Fixed rate marker divisors
   * - ``RateReload``
     - RemoteVariable
     - ``0x040``
     - [0]
     - WO
     - UInt
     - none
     - Loads cached fixed rate marker divisors
   * - ``NBeamSeq``
     - RemoteVariable
     - ``0x04C``
     - [5:0]
     - RO
     - UInt
     - none
     - Number of beam request engines
   * - ``NControlSeq``
     - RemoteVariable
     - ``0x04C``
     - [13:6]
     - RO
     - UInt
     - none
     - Number of control sequence engines
   * - ``NArraysBsa``
     - RemoteVariable
     - ``0x04C``
     - [21:14]
     - RO
     - UInt
     - none
     - Number of BSA arrays
   * - ``SeqAddrLen``
     - RemoteVariable
     - ``0x04C``
     - [25:22]
     - RO
     - UInt
     - none
     - Number of beam sequence engines
   * - ``NAllowSeq``
     - RemoteVariable
     - ``0x04C``
     - [31:26]
     - RO
     - UInt
     - none
     - Number of beam allow engines
   * - ``BsaCompleteRd``
     - RemoteVariable
     - ``0x050``
     - [63:0]
     - RO
     - UInt
     - none
     - BSA complete read
   * - ``BsaCompleteWr``
     - RemoteVariable
     - ``0x050``
     - [63:0]
     - WO
     - UInt
     - none
     - BSA complete write
   * - ``PulseIdWr``
     - RemoteVariable
     - ``0x058``
     - [63:0]
     - WO
     - UInt
     - none
     - Pulse ID write
   * - ``TStampWr``
     - RemoteVariable
     - ``0x060``
     - [63:0]
     - WO
     - UInt
     - none
     - Time stamp Write
   * - ``TxReset``
     - RemoteVariable
     - ``0x068``
     - [0]
     - WO
     - UInt
     - none
     - Reset transmit link
   * - ``CountIntervalReset``
     - RemoteVariable
     - ``0x06C``
     - [0]
     - WO
     - UInt
     - none
     - Count Interval Reset
   * - ``PulseIdSet``
     - RemoteVariable
     - ``0x070``
     - [0]
     - RW
     - UInt
     - none
     - Activates PulseId register value
   * - ``TStampSet``
     - RemoteVariable
     - ``0x074``
     - [0]
     - RW
     - UInt
     - none
     - Activates Timestamp register value
   * - ``Lcls1BsaNumSamples``
     - RemoteVariable
     - ``0x078``
     - [11:0]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Number of Samples - 1
   * - ``Lcls1BsaRate``
     - RemoteVariable
     - ``0x078``
     - [14:12]
     - RW
     - enum 0: 120Hz, 1: 60Hz, 2: 30Hz, 3: 10Hz, 4: 5Hz, 5: 1Hz, 6: 0.5Hz
     - none
     - Lcls-1 BSA Rate
   * - ``Lcls1BsaTimeSlot``
     - RemoteVariable
     - ``0x078``
     - [17:15]
     - RW
     - enum 0: TS1, 1: TS2, 2: TS3, 3: TS4, 4: TS5, 5: TS6
     - none
     - Lcls-1 BSA Time Slot
   * - ``Lcls1BsaSeverity``
     - RemoteVariable
     - ``0x078``
     - [19:18]
     - RW
     - enum 0: INVALID, 1: MAJOR, 2: MINOR
     - none
     - Lcls-1 BSA Rejection Severity Threshold
   * - ``Lcls1BsaEdefSlot``
     - RemoteVariable
     - ``0x078``
     - [23:20]
     - RW
     - UInt
     - none
     - Lcls-1 BSA EDEF Slot Number
   * - ``Lcls1BsaNumAvgs``
     - RemoteVariable
     - ``0x078``
     - [31:24]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Number of Values to Average per Sample - 1
   * - ``Lcls1BsaStart``
     - RemoteVariable
     - ``0x07C``
     - [31:0]
     - RW
     - UInt
     - none
     - Lcls-1 BSA Started by Writing any Value Here
   * - ``BsaActive[0..3]``
     - RemoteVariable
     - ``0x1FC`` + ``8 bits`` * i
     - [0]
     - RW
     - UInt
     - none
     - Activates/Deactivates BSA EDEF
   * - ``BsaRateSelMode[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [1:0]
     - RW
     - enum 0: FixedRate, 1: ACRate, 2: Sequencer
     - none
     - BSA def rate mode selection
   * - ``BsaFixedRate[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [5:2]
     - RW
     - enum 0: 1MHz, 1: 71kHz, 2: 10kHz, 3: 1kHz, 4: 100Hz, 5: 10Hz, 6: 1Hz
     - none
     - BSA fixed rate mode selection
   * - ``BsaACRate[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [8:6]
     - RW
     - enum 0: 60Hz, 1: 30Hz, 2: 10Hz, 3: 5Hz, 4: 1Hz, 5: 0.5Hz
     - none
     - BSA AC rate mode selection
   * - ``BsaACTSMask[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [14:9]
     - RW
     - UInt
     - none
     - BSA AC timeslot mask selection
   * - ``BsaSequenceSelect[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [19:15]
     - RW
     - UInt
     - none
     - BSA sequencer selection
   * - ``BsaSequenceBitSelect[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [23:20]
     - RW
     - UInt
     - none
     - BSA sequencer bit selection
   * - ``BsaDestMode[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x10`` * i
     - [25:24]
     - RW
     - enum 0: Dont_Care, 1: Inclusive, 2: Exclusive
     - none
     - BSA destination mode
   * - ``BsaDestInclusiveMask[0..3]``
     - RemoteVariable
     - ``0x204`` + ``0x10`` * i
     - [15:0]
     - RW
     - UInt
     - none
     - BSA inclusive destination mask
   * - ``BsaDestExclusiveMask[0..3]``
     - RemoteVariable
     - ``0x204`` + ``0x10`` * i
     - [31:16]
     - RW
     - UInt
     - none
     - BSA exclusive destination mask
   * - ``BsaNtoAvg[0..3]``
     - RemoteVariable
     - ``0x208`` + ``0x10`` * i
     - [12:0]
     - RW
     - UInt
     - none
     - BSA def num acquisitions to average
   * - ``BsaMaxSeverity[0..3]``
     - RemoteVariable
     - ``0x208`` + ``0x10`` * i
     - [15:14]
     - RW
     - enum 0: NoAlarm, 1: Minor, 2: Major, 3: Invalid
     - none
     - BSA def max alarm severity
   * - ``BsaAvgToWr[0..3]``
     - RemoteVariable
     - ``0x208`` + ``0x8`` * i
     - [31:16]
     - RW
     - UInt
     - none
     - BSA def num averages to record
   * - ``PllCnt``
     - RemoteVariable
     - ``0x500``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of PLL status changes
   * - ``ClkCnt``
     - RemoteVariable
     - ``0x504``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of local 186M clock
   * - ``SyncErrCnt``
     - RemoteVariable
     - ``0x508``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of 71k sync errors
   * - ``CountInterval``
     - RemoteVariable
     - ``0x50C``
     - [31:0]
     - RW
     - UInt
     - none
     - Interval counters update period
   * - ``BaseRateCount``
     - RemoteVariable
     - ``0x510``
     - [31:0]
     - RO
     - UInt
     - none
     - Count of base rate triggers

Known issues
------------

Each test is skipped unless ``RUN_KNOWN_ISSUE_TESTS=1`` is set, and fails while the issue stands.

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Test
     - What
     - Issue
   * - ``test_TPGMiniCore_known_issue_bsa_avg_to_wr_stride``
     - TPGMiniCore.py declares BsaAvgToWr with a stride of 8 where TPGMiniReg decodes 16 bytes per sequence
     - :issue:`222`
   * - ``test_TPGMiniCore_known_issue_narraysbsa_32``
     - TPGMiniCore.py declares BsaActive with a byte stride where TPGMiniReg decodes one bit per sequence, so NARRAYSBSA above 4 is rejected
     - :issue:`223`
