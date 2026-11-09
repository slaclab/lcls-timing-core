LCLS-I EVR
==========

:repo:`LCLS-I/ruckus.tcl` loads these sources into the ``lcls_timing_core`` library; a file that is not loaded says so in the Status column.

.. list-table::
   :header-rows: 1
   :widths: 20 40 25 15

   * - Entity
     - File
     - Status
     - Issues
   * - :ref:`EvrV1TimeStampGenerator <entity-lcls-i-evr-evrv1timestampgenerator-v>`
     - :repo:`LCLS-I/evr/EvrV1TimeStampGenerator.v`
     - simulated
     - issue pending

.. _entity-lcls-i-evr-evrv1timestampgenerator-v:

EvrV1TimeStampGenerator
-----------------------

File: :repo:`LCLS-I/evr/EvrV1TimeStampGenerator.v`

Free-running 64-bit time stamp for the LCLS-I EVR in a single Clock domain. TimeStamp counts up by 1 on every Clock, and every 330556 clocks a reload puts the seconds counter in bits 63:32 and clears the low word while the seconds counter increments. Reset clears the seconds counter, the reload counter, and TimeStamp.

Status: simulated; a cocotb test runs the module in Icarus Verilog

.. rubric:: Generics

none

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``Clock``
     - in
     - ``wire``
   * - ``Reset``
     - in
     - ``wire``
   * - ``TimeStamp``
     - out
     - ``[63:0]``

Issues: issue pending
