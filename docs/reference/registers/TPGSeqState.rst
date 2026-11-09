.. _register-map-tpgseqstate:

TPGSeqState registers
=====================

No RTL in repo: the firmware that implements this block lives outside this repository, so the tables show the PyRogue declarations and how the YAML map agrees with them.

Python class: :repo:`python/LclsTimingCore/TPGSeqState.py`. YAML map: :repo:`yaml/TPGSeqState.yaml`.

Variant default
---------------

Python arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 30 55 15

   * - YAML map
     - Parse error
     - Issue
   * - :repo:`yaml/TPGSeqState.yaml`
     - ``ScannerError`` at line 27: mapping values are not allowed here
     - :issue:`218`

.. list-table::
   :header-rows: 1
   :widths: 10 22 8 7 23 30

   * - Offset
     - Field
     - Bits
     - Mode
     - YAML
     - Description
   * - ``0x000`` + ``0x8`` * i
     - ``SeqIndex[0..49]``
     - [31:0]
     - RO
     - map does not parse :issue:`218`
     - Sequencer instruction at offset
   * - ``0x004`` + ``0x8`` * i
     - ``SeqCondACount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition A counter
   * - ``0x004`` + ``0x40`` * i
     - ``SeqCondBCount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition B counter
   * - ``0x004`` + ``0x8`` * i
     - ``SeqCondCCount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition C counter
   * - ``0x004`` + ``0x8`` * i
     - ``SeqCondDCount[0..49]``
     - [7:0]
     - RO
     - map does not parse :issue:`218`
     - BSA condition D counter

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``<yaml>`` (missing-in-yaml): ``TPGSeqState.yaml does not parse, so no field of TPGSeqState can be compared with it`` :issue:`218`
