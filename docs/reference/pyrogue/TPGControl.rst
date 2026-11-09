.. _api-tpgcontrol:

TPGControl
==========

Source: :repo:`python/LclsTimingCore/TPGControl.py`. Register table: :ref:`TPGControl registers <register-map-tpgcontrol>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'TPGControl'``
   * - ``description``
     - ``'Timing pattern generator control'``
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
   * - ``NBeamSeq``
     - RemoteVariable
     - ``0x000``
     - [7:0]
     - RO
     - UInt
     - none
     - Number of beam control sequences
   * - ``NControlSeq``
     - RemoteVariable
     - ``0x000``
     - [15:8]
     - RO
     - UInt
     - none
     - Number of experiment control sequences
   * - ``NArraysBSA``
     - RemoteVariable
     - ``0x000``
     - [23:16]
     - RO
     - UInt
     - none
     - Number of BSA arrays
   * - ``SeqAddrLen``
     - RemoteVariable
     - ``0x000``
     - [27:24]
     - RO
     - UInt
     - none
     - Sequence instruction at offset bus width
   * - ``NAllowSeq``
     - RemoteVariable
     - ``0x000``
     - [31:28]
     - RO
     - UInt
     - none
     - Number of allow table sequences
   * - ``ClockPeriod``
     - RemoteVariable
     - ``0x004``
     - [31:0]
     - RW
     - UInt
     - none
     - Period of beam synchronous clock (ns/cycle)
   * - ``BaseControl``
     - RemoteVariable
     - ``0x008``
     - [15:0]
     - RW
     - UInt
     - none
     - Base rate control divisor
   * - ``ACDelay``
     - RemoteVariable
     - ``0x00C``
     - [31:0]
     - RW
     - UInt
     - none
     - Adjustable delay for power line crossing measurement
   * - ``PulseIdL``
     - RemoteVariable
     - ``0x010``
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse ID lower word
   * - ``PulseIdU``
     - RemoteVariable
     - ``0x014``
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse ID upper word
   * - ``TStampL``
     - RemoteVariable
     - ``0x018``
     - [31:0]
     - RW
     - UInt
     - none
     - Time stamp lower word
   * - ``TStampU``
     - RemoteVariable
     - ``0x01C``
     - [31:0]
     - RW
     - UInt
     - none
     - Time stamp upper word
   * - ``ACRateDiv[0..5]``
     - RemoteVariable
     - ``0x020`` + ``8 bits`` * i
     - [7:0]
     - RW
     - UInt
     - none
     - Power line synch rate marker divisors
   * - ``FixedRateDiv[0..9]``
     - RemoteVariable
     - ``0x040`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Fixed rate marker divisors
   * - ``RateReload``
     - RemoteVariable
     - ``0x068``
     - [0]
     - WO
     - UInt
     - none
     - Loads cached ac/fixed rate marker divisors
   * - ``Sync``
     - RemoteVariable
     - ``0x070``
     - [0]
     - RW
     - UInt
     - none
     - Sync status with 71kHz
   * - ``IrqFifoEnable``
     - RemoteVariable
     - ``0x074``
     - [0]
     - RW
     - UInt
     - none
     - Enable sequence checkpoint interrupt
   * - ``IrqIntvEnable``
     - RemoteVariable
     - ``0x074``
     - [1]
     - RW
     - UInt
     - none
     - Enable interval counter interrupt
   * - ``IrqBsaEnable``
     - RemoteVariable
     - ``0x074``
     - [2]
     - RW
     - UInt
     - none
     - Enable BSA complete interrupt
   * - ``IrqEnable``
     - RemoteVariable
     - ``0x074``
     - [31]
     - RW
     - UInt
     - none
     - Enable interrupts
   * - ``IrqIntvStatus``
     - RemoteVariable
     - ``0x078``
     - [0]
     - RW
     - UInt
     - none
     - Interval counters updated
   * - ``IrqBsaStatus``
     - RemoteVariable
     - ``0x078``
     - [1]
     - RO
     - UInt
     - none
     - BSA complete updated
   * - ``SeqFifoData``
     - RemoteVariable
     - ``0x07C``
     - [31:0]
     - RO
     - UInt
     - none
     - Sequence checkpoint data
   * - ``BeamSeqCntl[0..15]``
     - RemoteVariable
     - ``0x080`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Beam sequence arbitration control
   * - ``SeqResetL``
     - RemoteVariable
     - ``0x100``
     - [31:0]
     - WO
     - UInt
     - none
     - Sequence restart lower word
   * - ``SeqResetU``
     - RemoteVariable
     - ``0x104``
     - [31:0]
     - WO
     - UInt
     - none
     - Sequence restart upper word
   * - ``BeamEnergy[0..3]``
     - RemoteVariable
     - ``0x120`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Beam energy meta data
   * - ``BeamDiagCntl``
     - RemoteVariable
     - ``0x1E4``
     - [31:0]
     - WO
     - UInt
     - none
     - Beam diagnostic buffer control
   * - ``BeamDiagStat[0..3]``
     - RemoteVariable
     - ``0x1E8`` + ``0x4`` * i
     - [31:0]
     - RO
     - UInt
     - none
     - Beam diagnostic latched status
   * - ``BsaCompleteL``
     - RemoteVariable
     - ``0x1F8``
     - [31:0]
     - RW
     - UInt
     - none
     - Bsa buffers complete lower word
   * - ``BsaCompleteU``
     - RemoteVariable
     - ``0x1FC``
     - [31:0]
     - RW
     - UInt
     - none
     - Bsa buffers complete upper word
   * - ``BsaEventSel[0..63]``
     - RemoteVariable
     - ``0x200`` + ``0x8`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Bsa definition rate/destination selection
   * - ``BsaStatSel[0..63]``
     - RemoteVariable
     - ``0x204`` + ``0x8`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Bsa definition samples to average/acquire

Known issues
------------

none
