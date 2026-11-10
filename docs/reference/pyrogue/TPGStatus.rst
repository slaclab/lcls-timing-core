.. _api-tpgstatus:

TPGStatus
=========

Source: :repo:`python/LclsTimingCore/TPGStatus.py`. Register table: :ref:`TPGStatus registers <register-map-tpgstatus>`.

Rogue 6.16.0 rejects this class at ``root.start()``, so its tree cannot be built. The variables below are read from the source with ``ast``; the known issues name the declarations that Rogue refuses.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'TPGStatus'``
   * - ``description``
     - ``'Timing pattern generator status'``
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
   * - ``BsaStat[0..63]``
     - RemoteVariable
     - ``0x000`` + ``0x4`` * i
     - [31:0]
     - RO
     - UInt
     - none
     - BSA status num averaged/written
   * - ``CountPLL``
     - RemoteVariable
     - ``0x100``
     - [31:0]
     - RO
     - UInt
     - none
     - PLL Status changes
   * - ``Count186M``
     - RemoteVariable
     - ``0x104``
     - [31:0]
     - RO
     - UInt
     - none
     - 186MHz clock counts / 16
   * - ``CountSyncE``
     - RemoteVariable
     - ``0x108``
     - [31:0]
     - RO
     - UInt
     - none
     - Sync error counts
   * - ``CountIntv``
     - RemoteVariable
     - ``0x10C``
     - [31:0]
     - RW
     - UInt
     - none
     - Interval timer
   * - ``CountBRT``
     - RemoteVariable
     - ``0x110``
     - [31:0]
     - RO
     - UInt
     - none
     - Base rate trigger count in interval
   * - ``CountTrig[0..11]``
     - RemoteVariable
     - ``0x114`` + ``0x4`` * i
     - [31:0]
     - RO
     - UInt
     - none
     - External trigger count in interval
   * - ``CountSeq[0..63]``
     - RemoteVariable
     - ``0x144`` + ``16 bits`` * i
     - [31:0]
     - RO
     - UInt
     - none
     - Sequence requests in interval
   * - ``CountRxClks``
     - RemoteVariable
     - ``0x248``
     - [31:0]
     - RW
     - UInt
     - none
     - Recovered clock count / 16
   * - ``CountRxDV``
     - RemoteVariable
     - ``0x24C``
     - [31:0]
     - RW
     - UInt
     - none
     - Received data valid count

Known issues
------------

Each test is skipped unless ``RUN_KNOWN_ISSUE_TESTS=1`` is set, and fails while the issue stands.

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Test
     - What
     - Issue
   * - ``test_TPGStatus_known_issue_overlap``
     - TPGStatus.py declares CountSeq with a stride of 2 bytes for 32 bit counters, so neighbouring elements overlap and Rogue rejects the tree
     - :issue:`290`
