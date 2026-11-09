Entities
========

The VHDL entities of the library, with their purpose, generics, ports, and the way the regression covers it. The pages are generated from the sources by ``python -m tests.common.gen_docs``; the purposes are authored.

Each entity has one of five verification statuses:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Status
     - Meaning
   * - ``simulated``
     - A cocotb test runs the entity (or its testbench wrapper) in the GHDL leg of the regression.
   * - ``baseline-excluded``
     - GHDL cannot analyze the file today. The regression records the exact GHDL message and fails if it changes or disappears; the issues column links the report.
   * - ``Vivado-only``
     - A transceiver wrapper for one device family. It instantiates a vendor primitive, so only Vivado builds it and the regression does not.
   * - ``not simulated``
     - The file analyzes cleanly but no test simulates the entity; the entity page gives the reason.
   * - ``not simulated: not loaded by any ruckus.tcl``
     - The file is tracked in the repository but no ruckus.tcl loads it, so no build includes it.

.. toctree::
   :maxdepth: 1

   core
