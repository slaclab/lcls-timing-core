GT family selection
===================

The timing core is family agnostic. It talks to a transceiver only through the
ports of ``TimingCore`` (``gtRxRecClk``, ``gtRxData``, ``gtRxDataK``,
``gtRxStatus``, ``gtRxControl``, and the transmit side). The wrapper that sits
between those ports and the vendor transceiver is chosen at build time, from the
device family of the target.

How the build chooses
---------------------

:repo:`LCLS-II/ruckus.tcl` loads the core and the EVR unconditionally, then asks
ruckus for the family with ``getFpgaFamily`` and loads one wrapper directory.
The families it recognizes are:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - ``getFpgaFamily`` value
     - Directory loaded
     - Wrapper entity
   * - ``artix7``
     - :repo:`LCLS-II/gtp7/`
     - ``TimingGtCoreWrapper``
   * - ``kintex7``
     - :repo:`LCLS-II/gtx7/`
     - ``TimingGtCoreWrapper``
   * - ``kintexu``
     - :repo:`LCLS-II/gthUltraScale/`
     - ``TimingGtCoreWrapper``
   * - ``kintexuplus``, ``virtexuplus``, ``virtexuplusHBM``, ``zynquplus``,
       ``zynquplusRFSOC``, ``qzynquplusRFSOC``
     - :repo:`LCLS-II/gtyUltraScale+/` and :repo:`LCLS-II/gthUltraScale+/`
     - ``TimingGtCoreWrapper`` (GTY) and ``TimingGthCoreWrapper`` (GTH)

The four wrappers that share the name ``TimingGtCoreWrapper`` are never loaded
together. The two UltraScale+ directories are loaded together, and their entity
names differ, so a design can use either transceiver type. A family that is not
in the table loads no wrapper at all.

Wrapper contents
----------------

The 7-series wrappers build on surf transceiver cores. ``gtp7`` instantiates
``surf.Gtp7Core`` and ``gtx7`` instantiates ``surf.Gtx7Core``, each with an
8b10b decoder, reset synchronizers, and an ``AxiLiteToDrp`` bridge. No
vendor IP file is loaded for either family.

The UltraScale and UltraScale+ wrappers instantiate transceiver IP that this
repository ships as generated cores under ``coregen/``:

- ``TimingGth_extref`` and ``TimingGth_fixedlat`` for the GTH families.
- ``TimingGty_extref`` and ``TimingGty_fixedlat`` for the GTY family, plus
  ``TimingGty_fixedlat_Lcls1Only`` for the LCLS-I-only configuration.

The wrapper builds the ``extref`` core when its ``EXTREF_G`` generic is true
and the ``fixedlat`` core when it is false (the RTL labels that branch the local
reference case). On GTY, ``LCLS1_ONLY_G`` selects the LCLS-I-only core instead
of ``fixedlat``. ``DISABLE_TIME_GT_G`` replaces the timing transceiver with a
channel dummy. Each UltraScale wrapper also carries a surf ``GtRxAlignCheck``
and an AXI-Lite crossbar that exposes the DRP port.

Version gates and IP choice
---------------------------

Each GT ``ruckus.tcl`` checks the tool version before it loads anything, and
loads either the generated checkpoint or the IP source:

- ``gtp7`` has no gate and loads only its ``rtl/`` directory.
- ``gtx7`` requires ``surf`` 2.74.0 or later and exits the build otherwise, in
  addition to the 2.53.0 pin in the root :repo:`ruckus.tcl`.
- ``gthUltraScale`` needs Vivado 2016.4 or later. From Vivado 2025.1 it loads
  the cores in ``coregen/2025.1``, which also ship a constraints file that the
  script scopes to ``TimingGth_fixedlat`` and processes early; earlier versions
  load ``coregen/2016.4``.
- ``gthUltraScale+`` needs Vivado 2022.2 or later and prints a warning and
  loads nothing below that.
- ``gtyUltraScale+`` needs Vivado 2021.1 or later for the standard 317 MHz
  reference oscillator cores. When the ``TIMING_246MHz`` environment variable
  is set to a nonzero value it loads the 245.76 MHz cores from
  ``coregen/smurf`` instead and needs Vivado 2018.2 or later.

By default each script loads the ``.dcp`` checkpoint of the core. Setting
``LCLS_TIMING_GTH_XCI`` to 1 loads the ``.xci`` IP source for the GTH
directories, and ``LCLS_TIMING_GTY_XCI`` to 1 does the same for GTY.

Not simulated in CI
-------------------

The GT wrappers are Vivado-only. They instantiate vendor primitives and
generated IP that GHDL and Icarus cannot elaborate, and CI has no Xilinx
license, so no test simulates them and no wrapper is built. The rest of the
timing core is verified against models of the transceiver interface instead:
the tests drive ``rxData`` and the status ports directly. A further file,
:repo:`LCLS-II/core/rtl/TimingGthWrapper.vhd`, declares the entity
``TimingGthWrapper``, which no ``ruckus.tcl`` loads and no file instantiates; it is one
of the seven units GHDL cannot analyze (see the overview).
