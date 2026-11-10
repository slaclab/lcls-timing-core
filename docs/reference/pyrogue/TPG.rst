.. _api-tpg:

TPG
===

Source: :repo:`python/LclsTimingCore/TPG.py`. Register table: :ref:`TPG registers <register-map-tpg>`.

Rogue 6.16.0 rejects this class at ``root.start()``, so its tree cannot be built. The variables below are read from the source with ``ast``; the known issues name the declarations that Rogue refuses.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'TPG'``
   * - ``description``
     - ``'Timing generator module for AMC Carrier'``
   * - ``**kwargs``
     - none

Arguments beyond the ``pr.Device`` defaults: none.

Constructor checks
------------------

none

Sub-devices
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 30 15 15 15

   * - Name
     - Class
     - Offset
     - Count
     - Stride
   * - ``TPGControl``
     - :ref:`TPGControl <api-tpgcontrol>`
     - ``0x0``
     - 1
     - none
   * - ``TPGStatus``
     - :ref:`TPGStatus <api-tpgstatus>`
     - ``0x400``
     - 1
     - none
   * - ``TPGSeqState``
     - :ref:`TPGSeqState <api-tpgseqstate>`
     - ``0x800``
     - 1
     - none
   * - ``TPGSeqJump``
     - :ref:`TPGSeqJump <api-tpgseqjump>`
     - ``0x400``
     - 1
     - none

Variables
---------

none

Known issues
------------

Each test is skipped unless ``RUN_KNOWN_ISSUE_TESTS=1`` is set, and fails while the issue stands.

.. list-table::
   :header-rows: 1
   :widths: 35 45 20

   * - Test
     - What
     - Issue
   * - ``test_TPG_known_issue_overlap``
     - TPG.py inherits the TPGStatus CountSeq overlap (and the TPGSeqJump and TPGSeqState overlaps of issues 220 and 221), and also adds TPGStatus and TPGSeqJump both at 0x400, so Rogue rejects the tree
     - :issue:`292`
