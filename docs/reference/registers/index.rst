Register maps
=============

One page per register block. Each table is read from the RTL address decode, one table per generic or argument variant. Offset is the byte address of the 32-bit word and Bits the position inside it. Mode is read-write (RW), read-only (RO), or write-only (WO) as the RTL decodes it. Reset is the slice of the word that a simulation asserts after reset, or ``not asserted`` when no test checks it. The Python and YAML columns compare the PyRogue declaration and the CPSW map with the RTL field. Description is the ``description`` text of the Python variable.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Agreement
     - Meaning
   * - ``agrees``
     - the source holds the same position, width, and mode as the RTL field
   * - ``differs: <kind>``
     - the source disagrees; each kind links the issue that records it
   * - ``absent``
     - the source has no field for this register
   * - ``not compared``
     - the variant does not compare this source (the YAML map describes one variant)
   * - ``map does not parse``
     - the YAML map cannot be read, so none of its fields are compared

.. toctree::
   :maxdepth: 1

   EvrV2TriggerReg
