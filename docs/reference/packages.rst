VHDL packages and records
=========================

Every VHDL package of the library with its records, types, constants, and subprograms, read from the package declarations by ``python -m tests.common.gen_docs``. A port of an entity whose type is one of these records links to its definition on the entity pages.

.. list-table::
   :header-rows: 1
   :widths: 15 30 10 45

   * - Package
     - File
     - Loaded by a ruckus.tcl
     - Purpose
   * - :ref:`EvrV1Pkg <package-evrv1pkg>`
     - :repo:`LCLS-I/evr/EvrV1Pkg.vhd`
     - yes
     - The EvrV1StatusType and EvrV1ConfigType records that connect EvrV1Reg to EvrV1EventReceiver. Status carries the time stamps, time stamp FIFO, event RAM read data, interrupt flags, and data buffer state out of the receiver, and config carries the pulse, output map, event RAM, interrupt, and data buffer controls into it. EVR_V1_CONFIG_INIT_C is the all-zero configuration.
   * - :ref:`TPGMiniEdefPkg <package-tpgminiedefpkg>`
     - :repo:`LCLS-II/core/rtl/TPGMiniEdefPkg.vhd`
     - yes
     - Declares the configuration record of one mini event definition (TPGMiniEdefConfigType with navg, nsmp, edef, slot, rate, sevr, and a write enable), its field subtypes and reset constant, and toSlv and fromSlv conversions to the packed register word. TPGMiniReg, TPGMiniCore, TPGMiniStream, and TPGMiniEdef use it.
   * - :ref:`TPGPkg <package-tpgpkg>`
     - :repo:`LCLS-II/core/rtl/TPGPkg.vhd`
     - yes
     - Declares the limits and records shared by the pattern generator blocks: the fixed rate, AC rate, and sequence depth constants, the BsaDefType and CtrDefType definition records, and the TPGConfigType and TPGStatusType records exchanged with the register block, with their reset constants. BsaControl, CtrControl, EventSelect, TPGMini, TPGMiniReg, and TPGMiniStream use it.
   * - :ref:`TimingPkg <package-timingpkg>`
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - yes
     - Declares the timing link definitions: the 8b10b character constants (the K28.5 comma, start and end of frame, K28.0, and K28.1), the 944 bit LCLS-II TimingMessageType, the 704 bit LCLS-I TimingStreamType with its 416 bit data buffer, the extension, bus, and PHY control records, and the functions that convert them to and from bit vectors. TimingCore, TimingRx, the serializers, and the EVR blocks use it.
   * - :ref:`TimingExtnPkg <package-timingextnpkg>`
     - :repo:`LCLS-II/core/rtl/default/TimingExtnPkg.vhd`
     - no
     - Default definition of the extension interface, which a downstream project can replace with its own package of the same name. It declares ExptMessageType (two 32 bit base-rate counters and a 256 bit IRIG time code, 320 bits on stream id 2), the stream count and word counts, and conversions between the bit vector and the record.
   * - :ref:`EvrV2Pkg <package-evrv2pkg>`
     - :repo:`LCLS-II/evr/rtl/EvrV2Pkg.vhd`
     - yes
     - Types and constants of the LCLS-II EVR: the EvrV2ChannelConfig record (81 bits as a vector) and the EvrV2TriggerConfigType record, with their init constants, array types, and conversion functions to and from bit vectors. It also holds the BSA, cache, and DMA record types and the tag constants, and the channel and trigger counts used by the fixed-size EVR.

.. _package-evrv1pkg:

EvrV1Pkg
--------

File: :repo:`LCLS-I/evr/EvrV1Pkg.vhd`

Loaded by a ruckus.tcl: yes.

The EvrV1StatusType and EvrV1ConfigType records that connect EvrV1Reg to EvrV1EventReceiver. Status carries the time stamps, time stamp FIFO, event RAM read data, interrupt flags, and data buffer state out of the receiver, and config carries the pulse, output map, event RAM, interrupt, and data buffer controls into it. EVR_V1_CONFIG_INIT_C is the all-zero configuration.

.. rubric:: Records

.. _type-evrv1statustype:

**EvrV1StatusType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``ts``
     - ``slv(63 downto 0)``
   * - ``secondsShift``
     - ``slv(31 downto 0)``
   * - ``tsLatch``
     - ``slv(63 downto 0)``
   * - ``tsFifoTsLow``
     - ``slv(31 downto 0)``
   * - ``tsFifoTsHigh``
     - ``slv(31 downto 0)``
   * - ``tsFifoEventCode``
     - ``slv(7 downto 0)``
   * - ``tsFifoValid``
     - ``sl``
   * - ``tsFifoNext``
     - ``sl``
   * - ``tsFifoWrCnt``
     - ``slv(8 downto 0)``
   * - ``eventRamReset``
     - ``Slv32Array(1 downto 0)``
   * - ``eventRamSet``
     - ``Slv32Array(1 downto 0)``
   * - ``eventRamPulse``
     - ``Slv32Array(1 downto 0)``
   * - ``eventRamInt``
     - ``Slv32Array(1 downto 0)``
   * - ``intFlag``
     - ``slv(31 downto 0)``
   * - ``dbrx``
     - ``sl``
   * - ``dbrdy``
     - ``sl``
   * - ``dbcs``
     - ``sl``
   * - ``rxSize``
     - ``slv(11 downto 0)``
   * - ``dbData``
     - ``slv(31 downto 0)``
   * - ``dbInt``
     - ``sl``
   * - ``dbIntEna``
     - ``sl``

.. _type-evrv1configtype:

**EvrV1ConfigType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``latchTs``
     - ``sl``
   * - ``pulseControl``
     - ``Slv32Array(11 downto 0)``
   * - ``pulsePrescale``
     - ``Slv32Array(11 downto 0)``
   * - ``pulseDelay``
     - ``Slv32Array(11 downto 0)``
   * - ``pulseWidth``
     - ``Slv32Array(11 downto 0)``
   * - ``tsFifoRdEna``
     - ``sl``
   * - ``eventRamData``
     - ``slv(31 downto 0)``
   * - ``eventRamCs``
     - ``Slv4Array(1 downto 0)``
   * - ``eventRamAddr``
     - ``slv(7 downto 0)``
   * - ``eventRamWe``
     - ``Slv4Array(1 downto 0)``
   * - ``mapRamPage``
     - ``sl``
   * - ``evrEnable``
     - ``sl``
   * - ``outputMap``
     - ``Slv16Array(11 downto 0)``
   * - ``uSecDivider``
     - ``slv(31 downto 0)``
   * - ``intControl``
     - ``slv(31 downto 0)``
   * - ``dbena``
     - ``sl``
   * - ``dbdis``
     - ``sl``
   * - ``dben``
     - ``sl``
   * - ``dbRdAddr``
     - ``slv(8 downto 0)``
   * - ``irqClr``
     - ``slv(31 downto 0)``
   * - ``intEventEn``
     - ``sl``
   * - ``extEventEn``
     - ``sl``
   * - ``intEventCode``
     - ``slv(7 downto 0)``
   * - ``extEventCode``
     - ``slv(7 downto 0)``
   * - ``intEventCount``
     - ``slv(31 downto 0)``

.. rubric:: Types and subtypes

none

.. rubric:: Constants

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Name
     - Type
     - Value
   * - ``EVR_V1_CONFIG_INIT_C``
     - ``EvrV1ConfigType``
     - ``(latchTs => '0', pulseControl => (others => (others => '0')), pulsePrescale => (others => (others => '0')), pulseDelay => (others => (others => '0')), pulseWidth => (others => (others => '0')), tsFifoRdEna => '0', eventRamData => (others => '0'), eventRamCs => (others => (others => '0')), eventRamAddr => (others => '0'), eventRamWe => (others => (others => '0')), mapRamPage => '0', evrEnable => '0', outputMap => (others => (others => '0')), uSecDivider => (others => '0'), intControl => (others => '0'), dbena => '0', dbdis => '0', dben => '0', dbRdAddr => (others => '0'), irqClr => (others => '0'), intEventEn => '0', extEventEn => '0', intEventCode => (others => '0'), extEventCode => (others => '0'), intEventCount => (others => '0'))``

.. rubric:: Subprograms

none

.. _package-tpgminiedefpkg:

TPGMiniEdefPkg
--------------

File: :repo:`LCLS-II/core/rtl/TPGMiniEdefPkg.vhd`

Loaded by a ruckus.tcl: yes.

Declares the configuration record of one mini event definition (TPGMiniEdefConfigType with navg, nsmp, edef, slot, rate, sevr, and a write enable), its field subtypes and reset constant, and toSlv and fromSlv conversions to the packed register word. TPGMiniReg, TPGMiniCore, TPGMiniStream, and TPGMiniEdef use it.

.. rubric:: Records

.. _type-tpgminiedefconfigtype:

**TPGMiniEdefConfigType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``navg``
     - ``EdefNavgType``
   * - ``nsmp``
     - ``EdefNsmpType``
   * - ``edef``
     - ``EdefType``
   * - ``slot``
     - ``EdefTSType``
   * - ``rate``
     - ``EdefRateType``
   * - ``sevr``
     - ``EdefSevrType``
   * - ``wrEn``
     - ``sl``

.. rubric:: Types and subtypes

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Declaration
   * - ``EdefNavgType``
     - ``subtype of slv(7 downto 0)``
   * - ``EdefNsmpType``
     - ``subtype of slv(11 downto 0)``
   * - ``EdefType``
     - ``subtype of slv(3 downto 0)``
   * - ``EdefTSType``
     - ``subtype of slv(2 downto 0)``
   * - ``EdefRateType``
     - ``subtype of slv(2 downto 0)``
   * - ``EdefSevrType``
     - ``subtype of slv(1 downto 0)``

.. rubric:: Constants

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Name
     - Type
     - Value
   * - ``EDEF_NUM_BITS_C``
     - ``natural``
     - ``EdefNavgType'length + EdefNsmpType'length + EdefType'length + EdefTSType'length + EdefRateType'length + EdefSevrType'length``
   * - ``TPG_MINI_EDEF_CONFIG_INIT_C``
     - ``TPGMiniEdefConfigType``
     - ``(navg => (others => '0'), nsmp => (others => '0'), edef => (others => '0'), slot => (others => '0'), rate => (others => '0'), sevr => (others => '0'), wrEn => '0')``

.. rubric:: Subprograms

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Kind
     - Name
     - Signature
   * - function
     - ``toSlv``
     - ``function toSlv(cfg : TPGMiniEdefConfigType) return slv``
   * - function
     - ``fromSlv``
     - ``function fromSlv(v : slv; wen : sl) return TPGMiniEdefConfigType``

.. _package-tpgpkg:

TPGPkg
------

File: :repo:`LCLS-II/core/rtl/TPGPkg.vhd`

Loaded by a ruckus.tcl: yes.

Declares the limits and records shared by the pattern generator blocks: the fixed rate, AC rate, and sequence depth constants, the BsaDefType and CtrDefType definition records, and the TPGConfigType and TPGStatusType records exchanged with the register block, with their reset constants. BsaControl, CtrControl, EventSelect, TPGMini, TPGMiniReg, and TPGMiniStream use it.

.. rubric:: Records

.. _type-ctrdeftype:

**CtrDefType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``rateSel``
     - ``slv(12 downto 0)``
   * - ``destSel``
     - ``slv(18 downto 0)``

.. _type-bsadeftype:

**BsaDefType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``nToAvg``
     - ``slv(12 downto 0)``
   * - ``avgToWr``
     - ``slv(15 downto 0)``
   * - ``rateSel``
     - ``slv(12 downto 0)``
   * - ``destSel``
     - ``slv(18 downto 0)``
   * - ``maxSevr``
     - ``slv(1 downto 0)``
   * - ``noTmo``
     - ``sl``
   * - ``init``
     - ``sl``

.. _type-l1trigconfig:

**L1TrigConfig**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``evcode``
     - ``slv(7 downto 0)``
   * - ``delay``
     - ``slv(31 downto 0)``

.. _type-tpgjumpconfigtype:

**TPGJumpConfigType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``syncSel``
     - ``slv(15 downto 0)``
   * - ``syncJump``
     - ``SeqAddrType``
   * - ``syncClass``
     - ``slv(3 downto 0)``
   * - ``bcsJump``
     - ``SeqAddrType``
   * - ``bcsClass``
     - ``slv(3 downto 0)``
   * - ``mpsJump``
     - ``SeqAddrArray(0 to MPSCHAN - 1)``
   * - ``mpsClass``
     - ``Slv4Array(0 to MPSCHAN - 1)``

.. _type-sequencerstate:

**SequencerState**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``index``
     - ``SeqAddrType``
   * - ``count``
     - ``Slv8Array(SEQCOUNTDEPTH - 1 downto 0)``

.. _type-beamdiagstatustype:

**BeamDiagStatusType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``latch``
     - ``sl``
   * - ``buffered``
     - ``sl``
   * - ``index``
     - ``slv(1 downto 0)``
   * - ``buffers``
     - ``Slv32Array(3 downto 0)``
   * - ``count``
     - ``slv(31 downto 0)``

.. _type-tpgstatustype:

**TPGStatusType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``nbeamseq``
     - ``slv(5 downto 0)``
   * - ``nexptseq``
     - ``slv(7 downto 0)``
   * - ``narraysbsa``
     - ``slv(7 downto 0)``
   * - ``seqaddrlen``
     - ``slv(3 downto 0)``
   * - ``nallowseq``
     - ``slv(5 downto 0)``
   * - ``pulseId``
     - ``slv(63 downto 0)``
   * - ``timeStamp``
     - ``slv(63 downto 0)``
   * - ``bsaComplete``
     - ``slv(63 downto 0)``
   * - ``inpDelay``
     - ``slv(8 downto 0)``
   * - ``outOfSync``
     - ``sl``
   * - ``irqFifoFull``
     - ``sl``
   * - ``irqFifoEmpty``
     - ``sl``
   * - ``irqFifoData``
     - ``slv(31 downto 0)``
   * - ``pllChanged``
     - ``slv(31 downto 0)``
   * - ``count186M``
     - ``slv(31 downto 0)``
   * - ``countSyncE``
     - ``slv(31 downto 0)``
   * - ``countBRT``
     - ``slv(31 downto 0)``
   * - ``countTrig``
     - ``Slv32Array(NTRIGGERSIN - 1 downto 0)``
   * - ``countSeq``
     - ``Slv128Array(MAXSEQDEPTH - 1 downto 0)``
   * - ``countUpdate``
     - ``sl``
   * - ``beamDiag``
     - :ref:`BeamDiagStatusType <type-beamdiagstatustype>`
   * - ``rxStatus``
     - ``slv(11 downto 0)``
   * - ``rxClkCnt``
     - ``slv(31 downto 0)``
   * - ``rxDVCnt``
     - ``slv(31 downto 0)``
   * - ``seqRdData``
     - ``Slv32Array(MAXSEQDEPTH - 1 downto 0)``
   * - ``ctrvalv``
     - ``Slv32Array(MAXCOUNTERS - 1 downto 0)``
   * - ``bsaStatus``
     - ``Slv32Array(63 downto 0)``
   * - ``seqState``
     - ``SequencerStateArray(MAXSEQDEPTH - 1 downto 0)``
   * - ``bcsFault``
     - ``slv(BCSWIDTH - 1 downto 0)``
   * - ``mpsLatch``
     - ``Slv4Array(15 downto 0)``
   * - ``mpsState``
     - ``Slv4Array(15 downto 0)``

.. _type-beamdiagcontroltype:

**BeamDiagControlType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``manfault``
     - ``sl``
   * - ``clear``
     - ``slv(30 downto 0)``
   * - ``holdoff``
     - ``slv(19 downto 0)``
   * - ``inhibit``
     - ``slv(29 downto 0)``

.. _type-tpgconfigtype:

**TPGConfigType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``clock_step``
     - ``slv(4 downto 0)``
   * - ``clock_remainder``
     - ``slv(7 downto 0)``
   * - ``clock_divisor``
     - ``slv(7 downto 0)``
   * - ``txPolarity``
     - ``sl``
   * - ``acMaster``
     - ``sl``
   * - ``acTS1``
     - ``slv(1 downto 0)``
   * - ``acPolarity``
     - ``sl``
   * - ``acDelay``
     - ``slv(12 downto 0)``
   * - ``inpDelay``
     - ``slv(8 downto 0)``
   * - ``inpDelayLd``
     - ``sl``
   * - ``baseDivisor``
     - ``slv(15 downto 0)``
   * - ``pulseId``
     - ``slv(63 downto 0)``
   * - ``pulseIdWrEn``
     - ``sl``
   * - ``timeStamp``
     - ``slv(63 downto 0)``
   * - ``timeStampWrEn``
     - ``sl``
   * - ``ACRateDivisors``
     - ``Slv8Array(5 downto 0)``
   * - ``FixedRateDivisors``
     - ``Slv20Array(9 downto 0)``
   * - ``RateReload``
     - ``sl``
   * - ``SeqRestart``
     - ``slv(MAXSEQDEPTH - 1 downto 0)``
   * - ``forceSync``
     - ``sl``
   * - ``seqDestn``
     - ``Slv4Array(MAXBEAMSEQDEPTH - 1 downto 0)``
   * - ``allowRequired``
     - ``Slv16Array(MAXBEAMSEQDEPTH - 1 downto 0)``
   * - ``destnControl``
     - ``Slv16Array(MAXBEAMSEQDEPTH - 1 downto 0)``
   * - ``beamCharge``
     - ``slv(15 downto 0)``
   * - ``beamChargeOverride``
     - ``sl``
   * - ``beamEnergy``
     - ``Slv16Array(0 to 3)``
   * - ``photonWavelen``
     - ``Slv16Array(0 to 1)``
   * - ``irqEnable``
     - ``sl``
   * - ``irqFifoEnable``
     - ``sl``
   * - ``irqIntvEnable``
     - ``sl``
   * - ``irqBsaEnable``
     - ``sl``
   * - ``irqFaultEnable``
     - ``sl``
   * - ``irqFifoRd``
     - ``sl``
   * - ``diagSeq``
     - ``slv(6 downto 0)``
   * - ``beamDiag``
     - :ref:`BeamDiagControlType <type-beamdiagcontroltype>`
   * - ``ctrlock``
     - ``sl``
   * - ``ctrdefv``
     - ``CtrDefArray(MAXCOUNTERS - 1 downto 0)``
   * - ``bsadefv``
     - ``BsaDefArray(MAXARRAYSBSA - 1 downto 0)``
   * - ``bsatmo``
     - ``slv(3 downto 0)``
   * - ``interval``
     - ``slv(31 downto 0)``
   * - ``intervalRst``
     - ``sl``
   * - ``seqAddr``
     - ``SeqAddrType``
   * - ``seqWrData``
     - ``slv(31 downto 0)``
   * - ``seqWrEn``
     - ``slv(MAXSEQDEPTH - 1 downto 0)``
   * - ``seqJumpConfig``
     - ``TPGJumpConfigArray(MAXSEQDEPTH - 1 downto 0)``

.. _type-externaltrigtype:

**ExternalTrigType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``strobe71k``
     - ``sl``
   * - ``strobe360``
     - ``sl``
   * - ``strobe60``
     - ``sl``
   * - ``strobe1Hz``
     - ``sl``
   * - ``strobe``
     - ``sl``

.. rubric:: Types and subtypes

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Declaration
   * - ``CtrDefArray``
     - ``array (natural range <>) of CtrDefType``
   * - ``BsaDefArray``
     - ``array (natural range <>) of BsaDefType``
   * - ``SeqAddrType``
     - ``subtype of slv(SEQADDRLEN - 1 downto 0)``
   * - ``SeqAddrArray``
     - ``array (natural range <>) of SeqAddrType``
   * - ``L1TrigConfigArray``
     - ``array (natural range <>) of L1TrigConfig``
   * - ``TPGJumpConfigArray``
     - ``array (natural range <>) of TPGJumpConfigType``
   * - ``SequencerStateArray``
     - ``array (natural range <>) of SequencerState``
   * - ``TPGConfigArray``
     - ``array (natural range <>) of TPGConfigType``

.. rubric:: Constants

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Name
     - Type
     - Value
   * - ``FIXEDRATEDEPTH``
     - ``integer``
     - ``10``
   * - ``ACRATEDEPTH``
     - ``integer``
     - ``6``
   * - ``MAXALLOWSEQDEPTH``
     - ``natural``
     - ``16``
   * - ``MAXBEAMSEQDEPTH``
     - ``natural``
     - ``16``
   * - ``MAXEXPSEQDEPTH``
     - ``natural``
     - ``72``
   * - ``EXPPARTITIONS``
     - ``integer``
     - ``8``
   * - ``MAXSEQDEPTH``
     - ``integer``
     - ``MAXALLOWSEQDEPTH + MAXBEAMSEQDEPTH + MAXEXPSEQDEPTH``
   * - ``SEQADDRLEN``
     - ``integer``
     - ``11``
   * - ``SEQCOUNTDEPTH``
     - ``integer``
     - ``4``
   * - ``BCSWIDTH``
     - ``integer``
     - ``1``
   * - ``MPSDEPTH``
     - ``integer``
     - ``5``
   * - ``MAXCOUNTERS``
     - ``integer``
     - ``24``
   * - ``MAXARRAYSBSA``
     - ``integer``
     - ``50``
   * - ``NTRIGGERSIN``
     - ``integer``
     - ``12``
   * - ``MPSCHAN``
     - ``integer``
     - ``14``
   * - ``Allow``
     - ``slv(MAXALLOWSEQDEPTH - 1 downto 0)``
     - ``(others => '0')``
   * - ``Beam``
     - ``slv(Allow'left + MAXBEAMSEQDEPTH downto Allow'left + 1)``
     - ``(others => '0')``
   * - ``Expt``
     - ``slv(Beam'left + MAXEXPSEQDEPTH downto Beam'left + 1)``
     - ``(others => '0')``
   * - ``Seq``
     - ``slv(Expt'left downto Allow'right)``
     - ``(others => '0')``
   * - ``CTRDEF_INIT_C``
     - ``CtrDefType``
     - ``(rateSel => (others => '0'), destSel => (others => '0'))``
   * - ``BSADEF_INIT_C``
     - ``BsaDefType``
     - ``(nToAvg => (others => '0'), avgToWr => (others => '0'), rateSel => (others => '0'), destSel => (others => '0'), maxSevr => (others => '0'), noTmo => '0', init => '0')``
   * - ``L1TRIGCONFIG_INIT_C``
     - ``L1TrigConfig``
     - ``(evcode => (others => '1'), delay => (others => '1'))``
   * - ``TPG_JUMPCONFIG_INIT_C``
     - ``TPGJumpConfigType``
     - ``(syncSel => (others => '0'), syncJump => (others => '0'), syncClass => (others => '0'), bcsJump => (others => '0'), bcsClass => (others => '0'), mpsJump => (others => (others => '0')), mpsClass => (others => (others => '0')))``
   * - ``BEAM_DIAG_STATUS_INIT_C``
     - ``BeamDiagStatusType``
     - ``(latch => '0', buffered => '0', index => (others => '0'), buffers => (others => (others => '0')), count => (others => '0'))``
   * - ``SEQUENCER_STATE_INIT_C``
     - ``SequencerState``
     - ``(index => (others => '0'), count => (others => (others => '0')))``
   * - ``TPG_STATUS_INIT_C``
     - ``TPGStatusType``
     - ``(nbeamseq => (others => '0'), nexptseq => (others => '0'), narraysbsa => (others => '0'), seqaddrlen => (others => '0'), nallowseq => (others => '0'), pulseId => (others => '0'), timeStamp => (others => '0'), bsaComplete => (others => '0'), inpDelay => (others => '0'), outOfSync => '0', irqFifoFull => '0', irqFifoEmpty => '0', irqFifoData => (others => '0'), pllChanged => (others => '0'), count186M => (others => '0'), countSyncE => (others => '0'), countBRT => (others => '0'), countTrig => (others => (others => '0')), countSeq => (others => (others => '0')), countUpdate => '0', beamDiag => BEAM_DIAG_STATUS_INIT_C, rxStatus => (others => '0'), rxClkCnt => (others => '0'), rxDVCnt => (others => '0'), seqRdData => (others => (others => '0')), ctrvalv => (others => (others => '0')), bsaStatus => (others => (others => '0')), seqState => (others => SEQUENCER_STATE_INIT_C), bcsFault => (others => '0'), mpsLatch => (others => (others => '0')), mpsState => (others => (others => '0')))``
   * - ``BEAM_DIAG_CONTROL_INIT_C``
     - ``BeamDiagControlType``
     - ``(manfault => '0', clear => (others => '0'), holdoff => (others => '0'), inhibit => (others => '0'))``
   * - ``TPG_CONFIG_INIT_C``
     - ``TPGConfigType``
     - ``(clock_step => toSlv(5, 5), clock_remainder => toSlv(5, 8), clock_divisor => toSlv(13, 8), txPolarity => '0', baseDivisor => x"00C8", acMaster => '1', acTS1 => "00", acPolarity => '0', acDelay => toSlv(100, 13), inpDelay => (others => '0'), inpDelayLd => '0', pulseId => (others => '0'), pulseIdWrEn => '1', timeStamp => (others => '0'), timeStampWrEn => '0', ACRateDivisors => (x"00", x"3C", x"0C", x"06", x"02", x"01"), FixedRateDivisors => (x"00000", x"00000", x"00000", x"DE2B0", x"16378", x"0238C", x"0038E", x"0005B", x"0000D", x"00001"), RateReload => '0', SeqRestart => (others => '0'), forceSync => '0', seqDestn => (others => x"0"), allowRequired => (others => x"0000"), destnControl => (others => x"0000"), beamCharge => (others => '0'), beamChargeOverride => '0', beamEnergy => (others => (others => '0')), photonWavelen => (others => (others => '0')), irqEnable => '0', irqFifoEnable => '0', irqIntvEnable => '0', irqBsaEnable => '0', irqFaultEnable => '0', irqFifoRd => '0', diagSeq => (others => '1'), beamDiag => BEAM_DIAG_CONTROL_INIT_C, ctrlock => '0', ctrdefv => (others => CTRDEF_INIT_C), bsadefv => (others => BSADEF_INIT_C), bsatmo => toSlv(4, 4), interval => x"0000488b", intervalRst => '1', seqAddr => (others => '0'), seqWrData => (others => '0'), seqWrEn => (others => '0'), seqJumpConfig => (others => TPG_JUMPCONFIG_INIT_C))``
   * - ``EXTERNAL_TRIG_INIT_C``
     - ``ExternalTrigType``
     - ``(strobe71k => '0', strobe360 => '0', strobe60 => '0', strobe1Hz => '0', strobe => '0')``

.. rubric:: Subprograms

none

.. _package-timingpkg:

TimingPkg
---------

File: :repo:`LCLS-II/core/rtl/TimingPkg.vhd`

Loaded by a ruckus.tcl: yes.

Declares the timing link definitions: the 8b10b character constants (the K28.5 comma, start and end of frame, K28.0, and K28.1), the 944 bit LCLS-II TimingMessageType, the 704 bit LCLS-I TimingStreamType with its 416 bit data buffer, the extension, bus, and PHY control records, and the functions that convert them to and from bit vectors. TimingCore, TimingRx, the serializers, and the EVR blocks use it.

.. rubric:: Records

.. _type-timingrxtype:

**TimingRxType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``data``
     - ``slv(15 downto 0)``
   * - ``dataK``
     - ``slv(1 downto 0)``
   * - ``decErr``
     - ``slv(1 downto 0)``
   * - ``dspErr``
     - ``slv(1 downto 0)``

.. _type-timingphycontroltype:

**TimingPhyControlType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``reset``
     - ``sl``
   * - ``inhibit``
     - ``sl``
   * - ``polarity``
     - ``sl``
   * - ``bufferByRst``
     - ``sl``
   * - ``pllReset``
     - ``sl``

.. _type-timingphystatustype:

**TimingPhyStatusType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``locked``
     - ``sl``
   * - ``resetDone``
     - ``sl``
   * - ``bufferByDone``
     - ``sl``
   * - ``bufferByErr``
     - ``sl``

.. _type-timingserialtype:

**TimingSerialType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``ready``
     - ``sl``
   * - ``data``
     - ``slv(15 downto 0)``
   * - ``offset``
     - ``slv(6 downto 0)``
   * - ``last``
     - ``sl``

.. _type-timingmessagetype:

**TimingMessageType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``version``
     - ``slv(15 downto 0)``
   * - ``pulseId``
     - ``slv(63 downto 0)``
   * - ``timeStamp``
     - ``slv(63 downto 0)``
   * - ``fixedRates``
     - ``slv(9 downto 0)``
   * - ``acRates``
     - ``slv(5 downto 0)``
   * - ``acTimeSlot``
     - ``slv(2 downto 0)``
   * - ``acTimeSlotPhase``
     - ``slv(11 downto 0)``
   * - ``resync``
     - ``sl``
   * - ``beamRequest``
     - ``slv(31 downto 0)``
   * - ``beamEnergy``
     - ``Slv16Array(0 to 3)``
   * - ``photonWavelen``
     - ``Slv16Array(0 to 1)``
   * - ``syncStatus``
     - ``sl``
   * - ``mpsValid``
     - ``sl``
   * - ``bcsFault``
     - ``slv(0 downto 0)``
   * - ``mpsLimit``
     - ``slv(15 downto 0)``
   * - ``mpsClass``
     - ``slv4Array(0 to 15)``
   * - ``bsaInit``
     - ``slv(63 downto 0)``
   * - ``bsaActive``
     - ``slv(63 downto 0)``
   * - ``bsaAvgDone``
     - ``slv(63 downto 0)``
   * - ``bsaDone``
     - ``slv(63 downto 0)``
   * - ``control``
     - ``slv16Array(0 to 17)``

.. _type-timingdatabufftype:

**TimingDataBuffType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``dtype``
     - ``slv(15 downto 0)``
   * - ``version``
     - ``slv(15 downto 0)``
   * - ``dmod``
     - ``slv(191 downto 0)``
   * - ``epicsTime``
     - ``slv(63 downto 0)``
   * - ``edefAvgDn``
     - ``slv(31 downto 0)``
   * - ``edefMinor``
     - ``slv(31 downto 0)``
   * - ``edefMajor``
     - ``slv(31 downto 0)``
   * - ``edefInit``
     - ``slv(31 downto 0)``

.. _type-timingstreamtype:

**TimingStreamType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``pulseId``
     - ``slv(31 downto 0)``
   * - ``eventCodes``
     - ``slv(255 downto 0)``
   * - ``dbuff``
     - :ref:`TimingDataBuffType <type-timingdatabufftype>`

.. _type-lclsv1timingdatatype:

**LclsV1TimingDataType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``linkUp``
     - ``sl``
   * - ``gtRxData``
     - ``slv(15 downto 0)``
   * - ``gtRxDataK``
     - ``slv(1 downto 0)``
   * - ``gtRxDispErr``
     - ``slv(1 downto 0)``
   * - ``gtRxDecErr``
     - ``slv(1 downto 0)``

.. _type-lclsv2timingdatatype:

**LclsV2TimingDataType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``linkUp``
     - ``sl``

.. _type-timingextensionmessagetype:

**TimingExtensionMessageType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``valid``
     - ``sl``
   * - ``data``
     - ``slv(TIMING_EXTENSION_MESSAGE_BITS_C - 1 downto 0)``

.. _type-timingbustype:

**TimingBusType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``strobe``
     - ``sl``
   * - ``valid``
     - ``sl``
   * - ``message``
     - :ref:`TimingMessageType <type-timingmessagetype>`
   * - ``stream``
     - :ref:`TimingStreamType <type-timingstreamtype>`
   * - ``v1``
     - :ref:`LclsV1TimingDataType <type-lclsv1timingdatatype>`
   * - ``v2``
     - :ref:`LclsV2TimingDataType <type-lclsv2timingdatatype>`
   * - ``modesel``
     - ``sl``
   * - ``extension``
     - ``TimingExtensionArray``

.. _type-timingphytype:

**TimingPhyType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``dataK``
     - ``slv(1 downto 0)``
   * - ``data``
     - ``slv(15 downto 0)``
   * - ``control``
     - :ref:`TimingPhyControlType <type-timingphycontroltype>`

.. _type-timingtrigtype:

**TimingTrigType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``trigPulse``
     - ``slv(15 downto 0)``
   * - ``timeStamp``
     - ``slv(63 downto 0)``
   * - ``bsa``
     - ``slv(127 downto 0)``
   * - ``dmod``
     - ``slv(191 downto 0)``

.. rubric:: Types and subtypes

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Declaration
   * - ``TimingRxArray``
     - ``array (natural range <>) of TimingRxType``
   * - ``TimingPhyControlArray``
     - ``array (natural range <>) of TimingPhyControlType``
   * - ``TimingPhyStatusArray``
     - ``array (natural range <>) of TimingPhyStatusType``
   * - ``TimingSerialArray``
     - ``array (natural range <>) of TimingSerialType``
   * - ``TimingMessageArray``
     - ``array (natural range <>) of TimingMessageType``
   * - ``TimingDataBuffArray``
     - ``array (natural range <>) of TimingDataBuffType``
   * - ``TimingStreamArray``
     - ``array (natural range <>) of TimingStreamType``
   * - ``LclsV1TimingDataArray``
     - ``array (natural range <>) of LclsV1TimingDataType``
   * - ``LclsV2TimingDataArray``
     - ``array (natural range <>) of LclsV2TimingDataType``
   * - ``TimingExtensionArray``
     - ``array (15 downto 1) of TimingExtensionMessageType``
   * - ``TimingBusArray``
     - ``array (integer range <>) of TimingBusType``
   * - ``TimingPhyArray``
     - ``array (integer range <>) of TimingPhyType``

.. rubric:: Constants

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Name
     - Type
     - Value
   * - ``D_102_C``
     - ``slv(7 downto 0)``
     - ``"01001010"``
   * - ``D_215_C``
     - ``slv(7 downto 0)``
     - ``"10110101"``
   * - ``K_COM_C``
     - ``slv(7 downto 0)``
     - ``"10111100"``
   * - ``K_SOF_C``
     - ``slv(7 downto 0)``
     - ``"11110111"``
   * - ``K_EOF_C``
     - ``slv(7 downto 0)``
     - ``"11111101"``
   * - ``K_280_C``
     - ``slv(7 downto 0)``
     - ``"00011100"``
   * - ``K_281_C``
     - ``slv(7 downto 0)``
     - ``"00111100"``
   * - ``K_EOS_C``
     - ``slv(7 downto 0)``
     - ``K_280_C``
   * - ``TIMING_MESSAGE_BITS_C``
     - ``integer``
     - ``944``
   * - ``TIMING_MESSAGE_BITS_NO_BSA_C``
     - ``integer``
     - ``TIMING_MESSAGE_BITS_C - 256 - 16``
   * - ``TIMING_MESSAGE_WORDS_C``
     - ``integer``
     - ``TIMING_MESSAGE_BITS_C / 16``
   * - ``TIMING_MESSAGE_VERSION_C``
     - ``slv(15 downto 0)``
     - ``x"0001"``
   * - ``TIMING_STREAM_ID_C``
     - ``slv(3 downto 0)``
     - ``x"0"``
   * - ``TIMING_RX_INIT_C``
     - ``TimingRxType``
     - ``(data => x"0000", dataK => "00", decErr => "00", dspErr => "00")``
   * - ``TIMING_PHY_CONTROL_INIT_C``
     - ``TimingPhyControlType``
     - ``(reset => '0', inhibit => '0', polarity => '0', bufferByRst => '0', pllReset => '0')``
   * - ``TIMING_PHY_CONTROL_INHIBIT_C``
     - ``TimingPhyControlType``
     - ``(reset => '0', inhibit => '1', polarity => '0', bufferByRst => '0', pllReset => '0')``
   * - ``TIMING_PHY_STATUS_INIT_C``
     - ``TimingPhyStatusType``
     - ``(locked => '0', resetDone => '0', bufferByDone => '0', bufferByErr => '0')``
   * - ``TIMING_PHY_STATUS_FORCE_C``
     - ``TimingPhyStatusType``
     - ``(locked => '1', resetDone => '1', bufferByDone => '0', bufferByErr => '0')``
   * - ``TIMING_SERIAL_INIT_C``
     - ``TimingSerialType``
     - ``(ready => '0', data => x"0000", offset => (others => '0'), last => '0')``
   * - ``TIMING_MESSAGE_INIT_C``
     - ``TimingMessageType``
     - ``(version => TIMING_MESSAGE_VERSION_C, pulseId => (others => '0'), timeStamp => (others => '0'), fixedRates => (others => '0'), acRates => (others => '0'), acTimeSlot => (others => '0'), acTimeSlotPhase => (others => '0'), resync => '0', beamRequest => (others => '0'), beamEnergy => (others => (others => '0')), photonWavelen => (others => (others => '0')), syncStatus => '0', mpsValid => '0', bcsFault => (others => '0'), mpsLimit => (others => '0'), mpsClass => (others => (others => '1')), bsaInit => (others => '0'), bsaActive => (others => '0'), bsaAvgDone => (others => '0'), bsaDone => (others => '0'), control => (others => (others => '0')))``
   * - ``TIMING_DATABUFF_BITS_C``
     - ``integer``
     - ``416``
   * - ``TIMING_STREAM_BITS_C``
     - ``integer``
     - ``704``
   * - ``TIMING_DATA_BUFF_INIT_C``
     - ``TimingDataBuffType``
     - ``(dtype => (others => '0'), version => (others => '0'), dmod => (others => '0'), epicsTime => (others => '0'), edefAvgDn => (others => '0'), edefMinor => (others => '0'), edefMajor => (others => '0'), edefInit => (others => '0'))``
   * - ``TIMING_STREAM_INIT_C``
     - ``TimingStreamType``
     - ``(pulseId => (others => '0'), eventCodes => (others => '0'), dbuff => TIMING_DATA_BUFF_INIT_C)``
   * - ``LCLS_V1_TIMING_DATA_INIT_C``
     - ``LclsV1TimingDataType``
     - ``(linkUp => '0', gtRxData => (others => '0'), gtRxDataK => (others => '0'), gtRxDispErr => (others => '0'), gtRxDecErr => (others => '0'))``
   * - ``LCLS_V2_TIMING_DATA_INIT_C``
     - ``LclsV2TimingDataType``
     - ``(linkUp => '0')``
   * - ``TIMING_EXTENSION_MESSAGE_BITS_C``
     - ``integer``
     - ``512``
   * - ``TIMING_EXTENSION_MESSAGE_INIT_C``
     - ``TimingExtensionMessageType``
     - ``(valid => '0', data => (others => '0'))``
   * - ``TIMING_BUS_INIT_C``
     - ``TimingBusType``
     - ``(strobe => '0', valid => '0', message => TIMING_MESSAGE_INIT_C, stream => TIMING_STREAM_INIT_C, v1 => LCLS_V1_TIMING_DATA_INIT_C, v2 => LCLS_V2_TIMING_DATA_INIT_C, modesel => '0', extension => (others => TIMING_EXTENSION_MESSAGE_INIT_C))``
   * - ``TIMING_PHY_INIT_C``
     - ``TimingPhyType``
     - ``(dataK => "00", data => x"0000", control => TIMING_PHY_CONTROL_INIT_C)``
   * - ``TIMING_TRIG_INIT_C``
     - ``TimingTrigType``
     - ``(trigPulse => (others => '0'), timeStamp => (others => '0'), bsa => (others => '0'), dmod => (others => '0'))``

.. rubric:: Subprograms

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Kind
     - Name
     - Signature
   * - function
     - ``toSlv``
     - ``function toSlv(message : TimingMessageType) return slv``
   * - function
     - ``toSlv32``
     - ``function toSlv32(vector : slv) return Slv32Array``
   * - function
     - ``toSlvNoBsa``
     - ``function toSlvNoBsa(message : TimingMessageType) return slv``
   * - function
     - ``toTimingMessageType``
     - ``function toTimingMessageType(vector : slv) return TimingMessageType``
   * - function
     - ``toTimingDataBuffType``
     - ``function toTimingDataBuffType(vector : slv) return TimingDataBuffType``
   * - function
     - ``toTimingStreamType``
     - ``function toTimingStreamType(vector : slv) return TimingStreamType``
   * - function
     - ``toSlv``
     - ``function toSlv(stream : TimingStreamType) return slv``
   * - function
     - ``toSlv``
     - ``function toSlv(dbuff : TimingDataBuffType) return slv``

.. _package-timingextnpkg:

TimingExtnPkg
-------------

File: :repo:`LCLS-II/core/rtl/default/TimingExtnPkg.vhd`

Loaded by a ruckus.tcl: no (default TimingExtnPkg; LCLS-II/core/ruckus.tcl lists no file from rtl/default, and only the test wrapper TimingExtnPkgWrapper.vhd uses the package).

Default definition of the extension interface, which a downstream project can replace with its own package of the same name. It declares ExptMessageType (two 32 bit base-rate counters and a 256 bit IRIG time code, 320 bits on stream id 2), the stream count and word counts, and conversions between the bit vector and the record.

.. rubric:: Records

.. _type-exptmessagetype:

**ExptMessageType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``baseRateSince1Hz``
     - ``slv(31 downto 0)``
   * - ``baseRateSinceTM``
     - ``slv(31 downto 0)``
   * - ``irigTimeCode``
     - ``slv(255 downto 0)``

.. rubric:: Types and subtypes

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Declaration
   * - ``TimingExtnType``
     - ``subtype of ExptMessageType``

.. rubric:: Constants

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Name
     - Type
     - Value
   * - ``EXPT_STREAM_ID``
     - ``slv(3 downto 0)``
     - ``x"2"``
   * - ``EXPT_MESSAGE_BITS_C``
     - ``integer``
     - ``320``
   * - ``EXPT_MESSAGE_INIT_C``
     - ``ExptMessageType``
     - ``(baseRateSince1Hz => (others => '1'), baseRateSinceTM => (others => '1'), irigTimeCode => (others => '1'))``
   * - ``TIMING_EXTN_INIT_C``
     - ``ExptMessageType``
     - ``EXPT_MESSAGE_INIT_C``
   * - ``TIMING_EXTN_BITS_C``
     - ``integer``
     - ``EXPT_MESSAGE_BITS_C``
   * - ``TIMING_EXTN_STREAMS_C``
     - ``integer``
     - ``2``
   * - ``TIMING_EXTN_WORDS_C``
     - ``IntegerArray(1 downto 0)``
     - ``(1, EXPT_MESSAGE_BITS_C / 16)``

.. rubric:: Subprograms

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Kind
     - Name
     - Signature
   * - function
     - ``toSlv``
     - ``function toSlv(message : ExptMessageType) return slv``
   * - function
     - ``toExptMessageType``
     - ``function toExptMessageType(vector : slv) return ExptMessageType``
   * - function
     - ``toTimingExtnType``
     - ``function toTimingExtnType(vector : slv) return TimingExtnType``
   * - procedure
     - ``toTimingExtnType``
     - ``procedure toTimingExtnType(stream : in integer; vector : in slv; validi : in sl; extn : inout TimingExtnType; valido : inout sl)``

.. _package-evrv2pkg:

EvrV2Pkg
--------

File: :repo:`LCLS-II/evr/rtl/EvrV2Pkg.vhd`

Loaded by a ruckus.tcl: yes.

Types and constants of the LCLS-II EVR: the EvrV2ChannelConfig record (81 bits as a vector) and the EvrV2TriggerConfigType record, with their init constants, array types, and conversion functions to and from bit vectors. It also holds the BSA, cache, and DMA record types and the tag constants, and the channel and trigger counts used by the fixed-size EVR.

.. rubric:: Records

.. _type-evrv2channelconfig:

**EvrV2ChannelConfig**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``enabled``
     - ``sl``
   * - ``rateSel``
     - ``slv(12 downto 0)``
   * - ``destSel``
     - ``slv(18 downto 0)``
   * - ``bsaEnabled``
     - ``sl``
   * - ``bsaActiveSetup``
     - ``slv(5 downto 0)``
   * - ``bsaActiveDelay``
     - ``slv(19 downto 0)``
   * - ``bsaActiveWidth``
     - ``slv(19 downto 0)``
   * - ``dmaEnabled``
     - ``sl``

.. _type-evrv2triggerconfigtype:

**EvrV2TriggerConfigType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``enabled``
     - ``sl``
   * - ``polarity``
     - ``sl``
   * - ``complEn``
     - ``sl``
   * - ``complAnd``
     - ``sl``
   * - ``delay``
     - ``slv(EVRV2_TRIG_WIDTH_C - 1 downto 0)``
   * - ``width``
     - ``slv(EVRV2_TRIG_WIDTH_C - 1 downto 0)``
   * - ``channel``
     - ``slv(3 downto 0)``
   * - ``channels``
     - ``slv(15 downto 0)``
   * - ``delayTap``
     - ``slv(5 downto 0)``
   * - ``loadTap``
     - ``sl``

.. _type-evrv2bsacontroltype:

**EvrV2BsaControlType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``timeStamp``
     - ``slv(63 downto 0)``
   * - ``bsaInit``
     - ``slv(63 downto 0)``
   * - ``bsaDone``
     - ``slv(63 downto 0)``

.. _type-evrv2bsachanneltype:

**EvrV2BsaChannelType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``pulseId``
     - ``slv(63 downto 0)``
   * - ``bsaActive``
     - ``slv(63 downto 0)``
   * - ``avgDoneId``
     - ``slv(63 downto 0)``
   * - ``bsaAvgDone``
     - ``slv(63 downto 0)``
   * - ``bsaDone``
     - ``slv(63 downto 0)``

.. _type-evrv2datatype:

**EvrV2DataType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``strobe``
     - ``sl``
   * - ``timingFrame``
     - :ref:`TimingMessageType <type-timingmessagetype>`

.. _type-evrv2cachecontroltype:

**EvrV2CacheControlType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``reset``
     - ``sl``
   * - ``rdclk``
     - ``sl``
   * - ``advance``
     - ``sl``

.. _type-evrv2cachedatatype:

**EvrV2CacheDataType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``empty``
     - ``sl``
   * - ``count``
     - ``slv(31 downto 0)``
   * - ``data``
     - ``slv(31 downto 0)``

.. _type-evrv2dmacontroltype:

**EvrV2DmaControlType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``ready``
     - ``sl``
   * - ``testData``
     - ``slv(23 downto 0)``
   * - ``fullThr``
     - ``slv(23 downto 0)``

.. _type-evrv2dmadatatype:

**EvrV2DmaDataType**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Type
   * - ``tValid``
     - ``sl``
   * - ``tData``
     - ``slv(31 downto 0)``

.. rubric:: Types and subtypes

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Name
     - Declaration
   * - ``EvrV2ChannelConfigArray``
     - ``array (natural range <>) of EvrV2ChannelConfig``
   * - ``EvrV2TriggerConfigArray``
     - ``array (natural range <>) of EvrV2TriggerConfigType``
   * - ``EvrV2BsaChannelArray``
     - ``array (natural range <>) of EvrV2BsaChannelType``
   * - ``EvrV2CacheControlArray``
     - ``array (natural range <>) of EvrV2CacheControlType``
   * - ``EvrV2CacheDataArray``
     - ``array (natural range <>) of EvrV2CacheDataType``
   * - ``EvrV2DmaControlArray``
     - ``array (natural range <>) of EvrV2DmaControlType``
   * - ``EvrV2DmaDataArray``
     - ``array (natural range <>) of EvrV2DmaDataType``

.. rubric:: Constants

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Name
     - Type
     - Value
   * - ``TriggerOutputs``
     - ``integer``
     - ``12``
   * - ``ReadoutChannels``
     - ``integer``
     - ``12``
   * - ``EVRV2_CHANNEL_CONFIG_BITS_C``
     - ``integer``
     - ``81``
   * - ``EVRV2_CHANNEL_CONFIG_INIT_C``
     - ``EvrV2ChannelConfig``
     - ``(enabled => '0', rateSel => (others => '0'), destSel => (others => '0'), bsaEnabled => '0', bsaActiveSetup => (others => '0'), bsaActiveDelay => (others => '0'), bsaActiveWidth => toSlv(1, 20), dmaEnabled => '0')``
   * - ``EVRV2_TRIG_WIDTH_C``
     - ``integer``
     - ``28``
   * - ``EVRV2_TRIGGER_CONFIG_BITS_C``
     - ``integer``
     - ``31 + 2 * EVRV2_TRIG_WIDTH_C``
   * - ``EVRV2_TRIGGER_CONFIG_INIT_C``
     - ``EvrV2TriggerConfigType``
     - ``(enabled => '0', polarity => '1', complEn => '0', complAnd => '0', delay => (others => '0'), width => toSlv(1, EVRV2_TRIG_WIDTH_C), channel => (others => '0'), channels => (others => '0'), delayTap => (others => '0'), loadTap => '0')``
   * - ``EVRV2_BSA_CONTROL_INIT_C``
     - ``EvrV2BsaControlType``
     - ``(timeStamp => (others => '0'), bsaInit => (others => '0'), bsaDone => (others => '0'))``
   * - ``EVRV2_BSA_CHANNEL_INIT_C``
     - ``EvrV2BsaChannelType``
     - ``(pulseId => (others => '0'), bsaActive => (others => '0'), avgDoneId => (others => '0'), bsaAvgDone => (others => '0'), bsaDone => (others => '0'))``
   * - ``EVRV2_CACHE_CONTROL_INIT_C``
     - ``EvrV2CacheControlType``
     - ``(reset => '0', rdclk => '0', advance => '0')``
   * - ``EVRV2_CACHE_DATA_INIT_C``
     - ``EvrV2CacheDataType``
     - ``(empty => '0', count => (others => '0'), data => (others => '0'))``
   * - ``EVRV2_DMA_CONTROL_INIT_C``
     - ``EvrV2DmaControlType``
     - ``(ready => '0', testData => (others => '0'), fullThr => (others => '1'))``
   * - ``EVRV2_DMA_DATA_INIT_C``
     - ``EvrV2DmaDataType``
     - ``(tValid => '0', tData => (others => '0'))``
   * - ``EVRV2_EVENT_TAG``
     - ``slv(15 downto 0)``
     - ``x"0000"``
   * - ``EVRV2_BSA_CONTROL_TAG``
     - ``slv(15 downto 0)``
     - ``x"0001"``
   * - ``EVRV2_BSA_CHANNEL_TAG``
     - ``slv(15 downto 0)``
     - ``x"0002"``
   * - ``EVRV2_END_TAG``
     - ``slv(15 downto 0)``
     - ``x"000F"``
   * - ``EVRV2_LCLS_TAG_BIT``
     - ``integer``
     - ``6``
   * - ``EVRV2_DROP_TAG_BIT``
     - ``integer``
     - ``7``

.. rubric:: Subprograms

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Kind
     - Name
     - Signature
   * - function
     - ``toSlv``
     - ``function toSlv(cfg : EvrV2ChannelConfig) return slv``
   * - function
     - ``toSlv``
     - ``function toSlv(cfg : EvrV2TriggerConfigType) return slv``
   * - function
     - ``toChannelConfig``
     - ``function toChannelConfig(vector : slv) return EvrV2ChannelConfig``
   * - function
     - ``toTriggerConfig``
     - ``function toTriggerConfig(vector : slv) return EvrV2TriggerConfigType``
