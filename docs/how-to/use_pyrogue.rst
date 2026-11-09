Use the PyRogue devices
=======================

``python/LclsTimingCore/`` holds one ``pr.Device`` class per register block of
the firmware. This page shows how to get the package on the Python path, how
to add a device to a Rogue root, and which classes Rogue refuses to build today.
The register maps themselves are written three times, in the VHDL decode, in
these classes, and in the YAML maps under ``yaml/``; the regression compares
them.

Get the package on the path
---------------------------

Put the repository's ``python/`` directory on ``PYTHONPATH``, or install the
package from the conda recipe. Do not run ``setup.py`` or ``pip install`` on the
working tree: the build appends a ``__version__`` line to a tracked file, and it
imports ``distutils``, which Python 3.12 removed.

.. code-block:: bash

   export PYTHONPATH=$PWD/python

The package imports ``pyrogue`` and nothing else outside itself, so Rogue is its only run-time requirement.

Add a device to a root
----------------------

Import the package, create each device with the memory interface it talks
through (``memBase``) and the byte address of its block (``offset``), and add it
to the root. ``offset`` is the AXI-Lite address of the block in the firmware:
for the timing core that is the ``AXIL_BASE_ADDR_G`` of ``TimingCore`` plus the
window of the block (see :doc:`instantiate_timing_core`), and for the trigger
composite it is its ``AXIL_BASEADDR_G`` (see :doc:`instantiate_evr`).

The example uses a Rogue memory emulator so that it runs without hardware; on a
board, ``memBase`` is the memory-mapped interface of your transport.

.. code-block:: python

   import pyrogue as pr
   import rogue.interfaces.memory as rim
   import LclsTimingCore as lclsTiming

   root = pr.Root(name='root', pollEn=False)
   memory = rim.Emulate(4, 0x100000)
   root.addInterface(memory)

   root.add(lclsTiming.TimingFrameRx(
       name='TimingFrameRx',
       memBase=memory,
       offset=0x00000,
       expand=True,
   ))

   root.add(lclsTiming.EvrV2CoreTriggers(
       name='EvrTriggers',
       memBase=memory,
       offset=0x80000,
       numTrig=4,
   ))

   root.start()
   try:
       print(root.TimingFrameRx.sofCount.get())
       print(root.EvrTriggers.EvrV2TriggerReg[3].path)
   finally:
       root.stop()

``TimingFrameRx`` maps the receive status of ``TimingRx``; its ``clkselMode``
argument takes the same values as ``CLKSEL_MODE_G``. ``EvrV2CoreTriggers`` takes
``numTrig`` from 1 to 16 and raises ``ValueError`` outside that range; it adds
``numTrig`` channel groups and ``numTrig`` trigger groups named
``EvrV2ChannelReg[i]`` and ``EvrV2TriggerReg[i]``. ``EvrV2CoreChannels`` has the
same arguments and adds the channel groups only.

Other blocks follow the same pattern: ``TPGMiniCore`` for the embedded pattern
generator at ``0x30000`` of the timing core, ``GthRxAlignCheck`` for the phase
lock check, and ``EvrV2Core`` and ``EvrV1Reg`` for the two EVR generations.

Classes that Rogue rejects today
--------------------------------

Five classes cannot be built under Rogue 6.16.0 because they declare variables
that overlap, which Rogue refuses when the root starts. The regression pins each
one with the exact Rogue message and keeps a gated test that expects the build to
succeed once the overlap is fixed:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Class
     - Why Rogue rejects it
   * - ``EvrV1Reg``
     - ``IrqFlagWr`` and ``IrqFlagRd`` sit on the same bits of ``0x08`` without
       ``overlapEn`` (:issue:`217`).
   * - ``TPGSeqJump``
     - ``Class`` is declared at byte 1 bit 0 and overlaps bits 8 to 11 of
       ``StartAddr`` (:issue:`220`).
   * - ``TPGSeqState``
     - ``SeqCondACount`` to ``SeqCondDCount`` are declared at the same bit of
       byte 4 (:issue:`221`).
   * - ``TPGStatus``
     - ``CountSeq`` has a stride of 2 bytes for 32-bit counters, so neighbouring
       elements overlap (:issue:`228`).
   * - ``TPG``
     - It inherits the overlaps of ``TPGStatus``, ``TPGSeqJump``, and
       ``TPGSeqState``, and also adds ``TPGStatus`` and ``TPGSeqJump`` both at
       ``0x400`` (:issue:`228`).

Until those are fixed, build the rest of the tree without these classes.
Reproduce any of them with the known-issue command of :doc:`run_regression`.

See also
--------

- :doc:`/reference/pyrogue/index`
- :doc:`/reference/yaml_maps`
