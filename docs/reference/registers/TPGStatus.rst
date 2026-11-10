.. _register-map-tpgstatus:

TPGStatus registers
===================

No RTL in repo: the firmware that implements this block lives outside this repository, so the tables show the PyRogue declarations and how the YAML map agrees with them.

Python class: :repo:`python/LclsTimingCore/TPGStatus.py`. YAML map: :repo:`yaml/TPGStatus.yaml`.

Variant default
---------------

Python arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 10 22 8 7 23 30

   * - Offset
     - Field
     - Bits
     - Mode
     - YAML
     - Description
   * - ``0x000`` + ``0x4`` * i
     - ``BsaStat[0..63]``
     - [31:0]
     - RO
     - agrees
     - BSA status num averaged/written
   * - ``0x100``
     - ``CountPLL``
     - [31:0]
     - RO
     - agrees
     - PLL Status changes
   * - ``0x104``
     - ``Count186M``
     - [31:0]
     - RO
     - agrees
     - 186MHz clock counts / 16
   * - ``0x108``
     - ``CountSyncE``
     - [31:0]
     - RO
     - agrees
     - Sync error counts
   * - ``0x10C``
     - ``CountIntv``
     - [31:0]
     - RW
     - agrees
     - Interval timer
   * - ``0x110``
     - ``CountBRT``
     - [31:0]
     - RO
     - agrees
     - Base rate trigger count in interval
   * - ``0x114``
     - ``CountTrig[0]``
     - [31:0]
     - RO
     - agrees
     - External trigger count in interval
   * - ``0x118`` + ``0x4`` * i
     - ``CountTrig[1..11]``
     - [31:0]
     - RO
     - differs: offset :issue:`293`
       at 0x114 [31:0] RO
     - External trigger count in interval
   * - ``0x144`` + ``16 bits`` * i
     - ``CountSeq[0..63]``
     - [31:0]
     - RO
     - agrees
     - Sequence requests in interval
   * - ``0x248``
     - ``CountRxClks``
     - [31:0]
     - RW
     - agrees
     - Recovered clock count / 16
   * - ``0x24C``
     - ``CountRxDV``
     - [31:0]
     - RW
     - agrees
     - Received data valid count

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``CountTrig`` (offset): ``CountTrig[1] python bit 2240 (word 0x118 bit 0) vs yaml bit 2208 (word 0x114 bit 0) (first differing element 1 of 12, 11 differ)`` :issue:`293`
