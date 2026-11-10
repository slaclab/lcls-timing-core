.. _api-evrv1reg:

EvrV1Reg
========

Source: :repo:`python/LclsTimingCore/EvrV1Reg.py`. Register table: :ref:`EvrV1Reg registers <register-map-evrv1reg>`.

Rogue 6.16.0 rejects this class at ``root.start()``, so its tree cannot be built. The variables below are read from the source with ``ast``; the known issues name the declarations that Rogue refuses.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'EvrV1Reg'``
   * - ``description``
     - ``'LCLS-I EVR Registers'``
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
   * - ``Status``
     - RemoteVariable
     - ``0x000``
     - [31:0]
     - RO
     - UInt
     - none
     - Status Register
   * - ``Control``
     - RemoteVariable
     - ``0x004``
     - [31:0]
     - RW
     - UInt
     - none
     - Control Register
   * - ``IrqFlagRd``
     - RemoteVariable
     - ``0x008``
     - [31:0]
     - RO
     - UInt
     - none
     - Interrupt Flag Register
   * - ``IrqFlagWr``
     - RemoteVariable
     - ``0x008``
     - [31:0]
     - WO
     - UInt
     - none
     - Interrupt Flag Register
   * - ``IrqEnable``
     - RemoteVariable
     - ``0x00C``
     - [31:0]
     - RW
     - UInt
     - none
     - Interrupt Enable Register
   * - ``PulseIrqMap``
     - RemoteVariable
     - ``0x010``
     - [31:0]
     - RW
     - UInt
     - none
     - Mapping register for pulse interrupt
   * - ``PcieIntEna``
     - RemoteVariable
     - ``0x014``
     - [31:0]
     - RW
     - UInt
     - none
     - PCIe interrupt Enable and state status
   * - ``FWVersion``
     - RemoteVariable
     - ``0x02C``
     - [31:0]
     - RO
     - UInt
     - none
     - Firmware Version Register
   * - ``FWVersionUnmasked``
     - RemoteVariable
     - ``0x030``
     - [31:0]
     - RO
     - UInt
     - none
     - Firmware Version without 0x1F mask and byte swapped
   * - ``UsecDivider``
     - RemoteVariable
     - ``0x04C``
     - [31:0]
     - RW
     - UInt
     - none
     - Divider to get from Event Clock to 1 MHz
   * - ``SecSR``
     - RemoteVariable
     - ``0x05C``
     - [31:0]
     - RO
     - UInt
     - none
     - Seconds Shift Register
   * - ``SecCounter``
     - RemoteVariable
     - ``0x060``
     - [31:0]
     - RO
     - UInt
     - none
     - Timestamp Seconds Counter
   * - ``EventCounter``
     - RemoteVariable
     - ``0x064``
     - [31:0]
     - RO
     - UInt
     - none
     - Timestamp Event Counter
   * - ``SecLatch``
     - RemoteVariable
     - ``0x068``
     - [31:0]
     - RO
     - UInt
     - none
     - Timestamp Seconds Counter Latch
   * - ``EvCntLatch``
     - RemoteVariable
     - ``0x06C``
     - [31:0]
     - RO
     - UInt
     - none
     - Timestamp Event Counter Latch
   * - ``IntEventEn``
     - RemoteVariable
     - ``0x0A0``
     - [31:0]
     - RW
     - UInt
     - none
     - Internal Event Enable
   * - ``IntEventCount``
     - RemoteVariable
     - ``0x0A4``
     - [0]
     - RW
     - UInt
     - none
     - Internal Event Count
   * - ``IntEventCode``
     - RemoteVariable
     - ``0x0A8``
     - [7:0]
     - RW
     - UInt
     - none
     - Internal Event Code
   * - ``ExtEventEn``
     - RemoteVariable
     - ``0x0AC``
     - [0]
     - RW
     - UInt
     - none
     - External Event Enable
   * - ``ExtEventCode``
     - RemoteVariable
     - ``0x0B0``
     - [7:0]
     - RW
     - UInt
     - none
     - External Event Code
   * - ``Pulse00[0..3]``
     - RemoteVariable
     - ``0x200`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 0 Registers
   * - ``Pulse01[0..3]``
     - RemoteVariable
     - ``0x210`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 1 Registers
   * - ``Pulse02[0..3]``
     - RemoteVariable
     - ``0x220`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 2 Registers
   * - ``Pulse03[0..3]``
     - RemoteVariable
     - ``0x230`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 3 Registers
   * - ``Pulse04[0..3]``
     - RemoteVariable
     - ``0x240`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 4 Registers
   * - ``Pulse05[0..3]``
     - RemoteVariable
     - ``0x250`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 5 Registers
   * - ``Pulse06[0..3]``
     - RemoteVariable
     - ``0x260`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 6 Registers
   * - ``Pulse07[0..3]``
     - RemoteVariable
     - ``0x270`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 7 Registers
   * - ``Pulse08[0..3]``
     - RemoteVariable
     - ``0x280`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 8 Registers
   * - ``Pulse09[0..3]``
     - RemoteVariable
     - ``0x290`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 9 Registers
   * - ``Pulse10[0..3]``
     - RemoteVariable
     - ``0x2A0`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 10 Registers
   * - ``Pulse11[0..3]``
     - RemoteVariable
     - ``0x2B0`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse 11 Registers
   * - ``OutputMap[0..11]``
     - RemoteVariable
     - ``0x440`` + ``0x4`` * i
     - [15:0]
     - RW
     - UInt
     - none
     - Front Panel Output Map Registers [11:0]

Known issues
------------

Each test is skipped unless ``RUN_KNOWN_ISSUE_TESTS=1`` is set, and fails while the issue stands.

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Test
     - What
     - Issue
   * - ``test_EvrV1Reg_known_issue_overlap``
     - EvrV1Reg.py declares IrqFlagWr and IrqFlagRd on the same bits of 0x08 without overlapEn, so Rogue rejects the tree
     - :issue:`285`
