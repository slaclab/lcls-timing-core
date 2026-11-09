Register maps
=============

One page per register block. Each table of a block with RTL is read from the RTL address decode, one table per generic or argument variant. Offset is the byte address of the 32-bit word and Bits the position inside it. Mode is read-write (RW), read-only (RO), or write-only (WO) as the RTL decodes it. Reset is the slice of the word that a simulation asserts after reset, or ``not asserted`` when no test checks it; a word that mixes in a bit the testbench drives from an input is not listed. The Python and YAML columns compare the PyRogue declaration and the CPSW map with the RTL field. Description is the ``description`` text of the Python variable. A block with no RTL here is shown from its Python declarations, and the YAML column compares the map with them.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Agreement
     - Meaning
   * - ``agrees``
     - the source holds the same position, width, and mode as the RTL field
   * - ``differs: <kind>``
     - the source disagrees; each kind links the issue that records it
   * - ``differs from Python: <kind>``
     - the YAML field differs from the Python variable in that kind
   * - ``absent``
     - the source has no field for this register
   * - ``not compared``
     - the variant does not compare this source (the YAML map describes one variant)
   * - ``map does not parse``
     - the YAML map cannot be read, so none of its fields are compared

Classes that hold no registers of their own are covered by their children:

* ``EvrV2CoreChannels``: no YAML map and no decode file; its only child EvrV2ChannelReg is compared directly.

.. toctree::
   :maxdepth: 1
   :caption: Blocks with RTL in this repository

   EvrV2TriggerReg
   EvrV2ChannelReg
   EvrV2Core
   EvrV1Isr
   GthRxAlignCheck
   TimingFrameRx
   TPGMiniCore
   EvrV1Reg

.. toctree::
   :maxdepth: 1
   :caption: Blocks implemented outside this repository

   TPGControl
   LclsTriggerPulse
   EvrV2CoreTriggers
   TPGStatus
   TPGSeqJump
   TPGSeqState
   TPG

.. toctree::
   :maxdepth: 1
   :caption: YAML maps with no Python class

   yaml_only
