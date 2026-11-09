.. _register-map-evrv1reg:

EvrV1Reg registers
==================

Decode file: :repo:`LCLS-I/evr/EvrV1Reg.vhd`. Python class: :repo:`python/LclsTimingCore/EvrV1Reg.py`. YAML map: :repo:`yaml/EvrV1Reg.yaml`.

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
     - ``Status``
       RTL: ``statusReg``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Status Register
   * - ``0x004``
     - ``Control``
       RTL: ``controlReg``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Control Register
   * - ``0x008``
     - ``IrqFlagRd``
       RTL: ``intFlag``
     - [30:0]
     - RO
     - ``0x00000000``
     - differs: bitSize :issue:`217`
       at 0x008 [31:0] RO
     - absent :issue:`217`
     - Interrupt Flag Register
   * - ``0x008``
     - ``IrqFlagWr``
       RTL: ``irqClr1``
       YAML: ``IrqFlag``
     - [31:0]
     - WO
     - ``0x00000000``
     - agrees
     - differs: mode :issue:`217`
       at 0x008 [31:0] RW
     - Interrupt Flag Register
   * - ``0x00C``
     - ``IrqEnable``
       RTL: ``intControl``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Interrupt Enable Register
   * - ``0x010``
     - ``PulseIrqMap``
       RTL: ``hardwareInt``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Mapping register for pulse interrupt
   * - ``0x014``
     - ``PcieIntEna``
       RTL: ``irqActive``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - PCIe interrupt Enable and state status
   * - ``0x020``
     - ``DataBufferControl``
       RTL: ``dbcs``
     - [15:0]
     - RW
     - ``0x0000``
     - absent :issue:`228`
     - absent :issue:`228`
     - no description in source
   * - ``0x02C``
     - ``FWVersion``
       RTL: ``fwVersion@0x2c``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Firmware Version Register
   * - ``0x030``
     - ``FWVersionUnmasked``
       RTL: ``fwVersion@0x30.0``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Firmware Version without 0x1F mask and byte swapped
   * - ``0x04C``
     - ``UsecDivider``
       RTL: ``uSecDivider``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Divider to get from Event Clock to 1 MHz
   * - ``0x05C``
     - ``SecSR``
       RTL: ``secondsShift``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Seconds Shift Register
   * - ``0x060``
     - ``SecCounter``
       RTL: ``ts@0x60``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Timestamp Seconds Counter
   * - ``0x064``
     - ``EventCounter``
       RTL: ``ts@0x64``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Timestamp Event Counter
   * - ``0x068``
     - ``SecLatch``
       RTL: ``tsLatch@0x68``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Timestamp Seconds Counter Latch
   * - ``0x06C``
     - ``EvCntLatch``
       RTL: ``tsLatch@0x6c``
     - [31:0]
     - RO
     - not asserted
     - agrees
     - agrees
     - Timestamp Event Counter Latch
   * - ``0x070``
     - ``TimestampFifo``
       RTL: ``tsFifoEventCode``
     - [71:0]
     - RO
     - not asserted
     - absent :issue:`228`
     - absent :issue:`228`
     - no description in source
   * - ``0x0A0``
     - ``IntEventEn``
       RTL: ``intEventEn``
     - [0]
     - RW
     - ``0x0``
     - differs: bitSize :issue:`226`
       at 0x0A0 [31:0] RW
     - differs: bitSize :issue:`226`
       at 0x0A0 [31:0] RW
     - Internal Event Enable
   * - ``0x0A4``
     - ``IntEventCount``
       RTL: ``intEventCount``
     - [31:0]
     - RW
     - ``0x00000000``
     - differs: bitSize :issue:`226`
       at 0x0A4 [0] RW
     - differs: bitSize :issue:`226`
       at 0x0A4 [0] RW
     - Internal Event Count
   * - ``0x0A8``
     - ``IntEventCode``
       RTL: ``intEventCode``
     - [7:0]
     - RW
     - ``0x00``
     - agrees
     - agrees
     - Internal Event Code
   * - ``0x0AC``
     - ``ExtEventEn``
       RTL: ``extEventEn``
     - [0]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - External Event Enable
   * - ``0x0B0``
     - ``ExtEventCode``
       RTL: ``extEventCode``
     - [7:0]
     - RW
     - ``0x00``
     - agrees
     - agrees
     - External Event Code
   * - ``0x200``
     - ``Pulse00[0]``
       RTL: ``pulseControl[0]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 0 Registers
   * - ``0x204`` + ``0x4`` * i
     - ``Pulse00[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x200 [31:0] RW
     - Pulse 0 Registers
   * - ``0x210``
     - ``Pulse01[0]``
       RTL: ``pulseControl[1]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 1 Registers
   * - ``0x214`` + ``0x4`` * i
     - ``Pulse01[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x210 [31:0] RW
     - Pulse 1 Registers
   * - ``0x220``
     - ``Pulse02[0]``
       RTL: ``pulseControl[2]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 2 Registers
   * - ``0x224`` + ``0x4`` * i
     - ``Pulse02[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x220 [31:0] RW
     - Pulse 2 Registers
   * - ``0x230``
     - ``Pulse03[0]``
       RTL: ``pulseControl[3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 3 Registers
   * - ``0x234`` + ``0x4`` * i
     - ``Pulse03[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x230 [31:0] RW
     - Pulse 3 Registers
   * - ``0x240``
     - ``Pulse04[0]``
       RTL: ``pulseControl[4]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 4 Registers
   * - ``0x244`` + ``0x4`` * i
     - ``Pulse04[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x240 [31:0] RW
     - Pulse 4 Registers
   * - ``0x250``
     - ``Pulse05[0]``
       RTL: ``pulseControl[5]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 5 Registers
   * - ``0x254`` + ``0x4`` * i
     - ``Pulse05[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x250 [31:0] RW
     - Pulse 5 Registers
   * - ``0x260``
     - ``Pulse06[0]``
       RTL: ``pulseControl[6]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 6 Registers
   * - ``0x264`` + ``0x4`` * i
     - ``Pulse06[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x260 [31:0] RW
     - Pulse 6 Registers
   * - ``0x270``
     - ``Pulse07[0]``
       RTL: ``pulseControl[7]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 7 Registers
   * - ``0x274`` + ``0x4`` * i
     - ``Pulse07[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x270 [31:0] RW
     - Pulse 7 Registers
   * - ``0x280``
     - ``Pulse08[0]``
       RTL: ``pulseControl[8]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 8 Registers
   * - ``0x284`` + ``0x4`` * i
     - ``Pulse08[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x280 [31:0] RW
     - Pulse 8 Registers
   * - ``0x290``
     - ``Pulse09[0]``
       RTL: ``pulseControl[9]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 9 Registers
   * - ``0x294`` + ``0x4`` * i
     - ``Pulse09[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x290 [31:0] RW
     - Pulse 9 Registers
   * - ``0x2A0``
     - ``Pulse10[0]``
       RTL: ``pulseControl[10]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 10 Registers
   * - ``0x2A4`` + ``0x4`` * i
     - ``Pulse10[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x2A0 [31:0] RW
     - Pulse 10 Registers
   * - ``0x2B0``
     - ``Pulse11[0]``
       RTL: ``pulseControl[11]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - agrees
     - Pulse 11 Registers
   * - ``0x2B4`` + ``0x4`` * i
     - ``Pulse11[1..3]``
       RTL: ``pulsePrescale[1..3]``
     - [31:0]
     - RW
     - ``0x00000000``
     - agrees
     - differs: offset :issue:`228`
       at 0x2B0 [31:0] RW
     - Pulse 11 Registers
   * - ``0x440``
     - ``OutputMap[1]``
       RTL: ``outputMap[1]``
     - [15:0]
     - RW
     - ``0x0000``
     - differs: offset :issue:`227`
       at 0x444 [15:0] RW
     - differs from Python: offset :issue:`227`
       at 0x440 [15:0] RW
     - Front Panel Output Map Registers [11:0]
   * - ``0x440``
     - ``OutputMap[0]``
       RTL: ``outputMap[0]``
     - [31:16]
     - RW
     - ``0x0000``
     - differs: bitOffset :issue:`227`
       at 0x440 [15:0] RW
     - differs: bitOffset :issue:`227`
       at 0x440 [15:0] RW
     - Front Panel Output Map Registers [11:0]
   * - ``0x444`` + ``-16 bits`` * i
     - ``OutputMap[2..3]``
       RTL: ``outputMap[2..3]``
     - [31:16]
     - RW
     - ``0x0000``
     - differs: offset :issue:`227`
       at 0x448 [15:0] RW, step 0x4
     - differs: offset :issue:`227`
       at 0x440 [15:0] RW
     - Front Panel Output Map Registers [11:0]
   * - ``0x448`` + ``-16 bits`` * i
     - ``OutputMap[4..5]``
       RTL: ``outputMap[4..5]``
     - [31:16]
     - RW
     - ``0x0000``
     - differs: offset :issue:`227`
       at 0x450 [15:0] RW, step 0x4
     - differs: offset :issue:`227`
       at 0x440 [15:0] RW
     - Front Panel Output Map Registers [11:0]
   * - ``0x44C`` + ``-16 bits`` * i
     - ``OutputMap[6..7]``
       RTL: ``outputMap[6..7]``
     - [31:16]
     - RW
     - ``0x0000``
     - differs: offset :issue:`227`
       at 0x458 [15:0] RW, step 0x4
     - differs: offset :issue:`227`
       at 0x440 [15:0] RW
     - Front Panel Output Map Registers [11:0]
   * - ``0x450`` + ``-16 bits`` * i
     - ``OutputMap[8..9]``
       RTL: ``outputMap[8..9]``
     - [31:16]
     - RW
     - ``0x0000``
     - differs: offset :issue:`227`
       at 0x460 [15:0] RW, step 0x4
     - differs: offset :issue:`227`
       at 0x440 [15:0] RW
     - Front Panel Output Map Registers [11:0]
   * - ``0x454`` + ``-16 bits`` * i
     - ``OutputMap[10..11]``
       RTL: ``outputMap[10..11]``
     - [31:16]
     - RW
     - ``0x0000``
     - differs: offset :issue:`227`
       at 0x468 [15:0] RW, step 0x4
     - differs: offset :issue:`227`
       at 0x440 [15:0] RW
     - Front Panel Output Map Registers [11:0]
   * - ``0x4000`` + ``0x0`` * i
     - ``MapRam1[0..1023]``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`228`
     - differs: missing-in-vhdl :issue:`228`
       at 0x4000 [31:0] RO
     - no description in source
   * - ``0x6000`` + ``0x0`` * i
     - ``MapRam2[0..1023]``
     - [31:0]
     - RO
     - not asserted
     - absent :issue:`228`
     - differs: missing-in-vhdl :issue:`228`
       at 0x6000 [31:0] RO
     - no description in source

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``DataBufferControl`` (missing-in-python): ``dbcs is in vhdl at bit 256 (width 16) but not in python`` :issue:`228`
   * ``DataBufferControl`` (missing-in-yaml): ``dbcs is in vhdl at bit 256 (width 16) but not in yaml`` :issue:`228`
   * ``IntEventCount`` (bitSize): ``IntEventCount python width 1 vs vhdl width 32`` :issue:`226`
   * ``IntEventEn`` (bitSize): ``IntEventEn python width 32 vs vhdl width 1`` :issue:`226`
   * ``IrqFlagRd`` (bitSize): ``IrqFlagRd python width 32 vs vhdl width 31`` :issue:`217`
   * ``IrqFlagRd`` (missing-in-yaml): ``IrqFlagRd is in python at bit 64 (width 32) but not in yaml`` :issue:`217`
   * ``IrqFlagWr`` (mode): ``IrqFlagWr python mode WO vs yaml mode RW`` :issue:`217`
   * ``MapRam1`` (missing-in-python): ``MapRam1[0] is in yaml at bit 131072 (width 32) but not in python (first differing element 0 of 1024, 1024 differ)`` :issue:`228`
   * ``MapRam1`` (missing-in-vhdl): ``MapRam1[0] is in yaml at bit 131072 (width 32) but not in vhdl (first differing element 0 of 1024, 1024 differ)`` :issue:`228`
   * ``MapRam2`` (missing-in-python): ``MapRam2[0] is in yaml at bit 196608 (width 32) but not in python (first differing element 0 of 1024, 1024 differ)`` :issue:`228`
   * ``MapRam2`` (missing-in-vhdl): ``MapRam2[0] is in yaml at bit 196608 (width 32) but not in vhdl (first differing element 0 of 1024, 1024 differ)`` :issue:`228`
   * ``OutputMap`` (bitOffset): ``OutputMap[0] python bit 8704 (word 0x440 bit 0) vs vhdl bit 8720 (word 0x440 bit 16) (first differing element 0 of 12, 1 differ)`` :issue:`227`
   * ``OutputMap`` (offset): ``OutputMap[1] python bit 8736 (word 0x444 bit 0) vs vhdl bit 8704 (word 0x440 bit 0) (first differing element 1 of 12, 11 differ)`` :issue:`227`
   * ``Pulse00`` (offset): ``Pulse00[1] python bit 4128 (word 0x204 bit 0) vs yaml bit 4096 (word 0x200 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse01`` (offset): ``Pulse01[1] python bit 4256 (word 0x214 bit 0) vs yaml bit 4224 (word 0x210 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse02`` (offset): ``Pulse02[1] python bit 4384 (word 0x224 bit 0) vs yaml bit 4352 (word 0x220 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse03`` (offset): ``Pulse03[1] python bit 4512 (word 0x234 bit 0) vs yaml bit 4480 (word 0x230 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse04`` (offset): ``Pulse04[1] python bit 4640 (word 0x244 bit 0) vs yaml bit 4608 (word 0x240 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse05`` (offset): ``Pulse05[1] python bit 4768 (word 0x254 bit 0) vs yaml bit 4736 (word 0x250 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse06`` (offset): ``Pulse06[1] python bit 4896 (word 0x264 bit 0) vs yaml bit 4864 (word 0x260 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse07`` (offset): ``Pulse07[1] python bit 5024 (word 0x274 bit 0) vs yaml bit 4992 (word 0x270 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse08`` (offset): ``Pulse08[1] python bit 5152 (word 0x284 bit 0) vs yaml bit 5120 (word 0x280 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse09`` (offset): ``Pulse09[1] python bit 5280 (word 0x294 bit 0) vs yaml bit 5248 (word 0x290 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse10`` (offset): ``Pulse10[1] python bit 5408 (word 0x2a4 bit 0) vs yaml bit 5376 (word 0x2a0 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``Pulse11`` (offset): ``Pulse11[1] python bit 5536 (word 0x2b4 bit 0) vs yaml bit 5504 (word 0x2b0 bit 0) (first differing element 1 of 4, 3 differ)`` :issue:`228`
   * ``TimestampFifo`` (missing-in-python): ``tsFifoEventCode is in vhdl at bit 896 (width 72) but not in python`` :issue:`228`
   * ``TimestampFifo`` (missing-in-yaml): ``tsFifoEventCode is in vhdl at bit 896 (width 72) but not in yaml`` :issue:`228`
