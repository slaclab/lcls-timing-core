.. _register-map-tpgseqjump:

TPGSeqJump registers
====================

No RTL in repo: the firmware that implements this block lives outside this repository, so the tables show the PyRogue declarations and how the YAML map agrees with them.

Python class: :repo:`python/LclsTimingCore/TPGSeqJump.py`. YAML map: :repo:`yaml/TPGSeqJump.yaml`.

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
     - ``StartAddr[0..1023]``
     - [11:0]
     - RW
     - agrees
     - Sequence start offset
   * - ``0x000`` + ``0x4`` * i
     - ``Class[0..1023]``
     - [11:8]
     - RW
     - agrees
     - Sequence power class
   * - ``0x000`` + ``0x4`` * i
     - ``StartSync[0..1023]``
     - [31:16]
     - RW
     - agrees
     - Start synchronization condition

