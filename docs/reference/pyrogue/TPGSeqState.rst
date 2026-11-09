.. _api-tpgseqstate:

TPGSeqState
===========

Source: :repo:`python/LclsTimingCore/TPGSeqState.py`. Register table: :ref:`TPGSeqState registers <register-map-tpgseqstate>`.

Rogue 6.16.0 rejects this class at ``root.start()``, so its tree cannot be built. The variables below are read from the source with ``ast``; the known issues name the declarations that Rogue refuses.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'TPGSeqState'``
   * - ``description``
     - ``'Timing pattern sequencer state'``
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
   * - ``SeqIndex[0..49]``
     - RemoteVariable
     - ``0x000`` + ``0x8`` * i
     - [31:0]
     - RO
     - UInt
     - none
     - Sequencer instruction at offset
   * - ``SeqCondACount[0..49]``
     - RemoteVariable
     - ``0x004`` + ``0x8`` * i
     - [7:0]
     - RO
     - UInt
     - none
     - BSA condition A counter
   * - ``SeqCondBCount[0..49]``
     - RemoteVariable
     - ``0x004`` + ``0x40`` * i
     - [7:0]
     - RO
     - UInt
     - none
     - BSA condition B counter
   * - ``SeqCondCCount[0..49]``
     - RemoteVariable
     - ``0x004`` + ``0x8`` * i
     - [7:0]
     - RO
     - UInt
     - none
     - BSA condition C counter
   * - ``SeqCondDCount[0..49]``
     - RemoteVariable
     - ``0x004`` + ``0x8`` * i
     - [7:0]
     - RO
     - UInt
     - none
     - BSA condition D counter

Known issues
------------

Each test is skipped unless ``RUN_KNOWN_ISSUE_TESTS=1`` is set, and fails while the issue stands.

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Test
     - What
     - Issue
   * - ``test_TPGSeqState_known_issue_overlap``
     - TPGSeqState.py declares SeqCondACount, SeqCondBCount, SeqCondCCount, and SeqCondDCount at the same bit of byte 4, so Rogue rejects the tree
     - :issue:`221`
