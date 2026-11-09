.. _api-tpgseqjump:

TPGSeqJump
==========

Source: :repo:`python/LclsTimingCore/TPGSeqJump.py`. Register table: :ref:`TPGSeqJump registers <register-map-tpgseqjump>`.

Rogue 6.16.0 rejects this class at ``root.start()``, so its tree cannot be built. The variables below are read from the source with ``ast``; the known issues name the declarations that Rogue refuses.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'TPGSeqJump'``
   * - ``description``
     - ``'Timing pattern sequencer jump programming'``
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
   * - ``StartAddr[0..1023]``
     - RemoteVariable
     - ``0x000`` + ``0x4`` * i
     - [11:0]
     - RW
     - UInt
     - none
     - Sequence start offset
   * - ``Class[0..1023]``
     - RemoteVariable
     - ``0x000`` + ``0x4`` * i
     - [11:8]
     - RW
     - UInt
     - none
     - Sequence power class
   * - ``StartSync[0..1023]``
     - RemoteVariable
     - ``0x000`` + ``0x4`` * i
     - [31:16]
     - RW
     - UInt
     - none
     - Start synchronization condition

Known issues
------------

Each test is skipped unless ``RUN_KNOWN_ISSUE_TESTS=1`` is set, and fails while the issue stands.

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Test
     - What
     - Issue
   * - ``test_TPGSeqJump_known_issue_overlap``
     - TPGSeqJump.py declares Class at byte 1 bit 0, overlapping bits 8 to 11 of StartAddr, so Rogue rejects the tree
     - :issue:`220`
