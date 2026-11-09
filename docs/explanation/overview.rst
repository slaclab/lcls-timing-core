Overview and scope
==================

What the library is
-------------------

lcls-timing-core is the firmware and host-software library that receives, decodes,
generates, and distributes the LCLS-I and LCLS-II timing signals. A firmware
project pulls the RTL into its build through ruckus; a software project imports
the ``LclsTimingCore`` PyRogue package to read and write the same blocks over
AXI-Lite. The register layout is written down three times, in the VHDL register
decode, in the PyRogue device classes, and in the YAML maps, and the regression
checks that the three agree.

The library has no top-level design of its own. Every block is an entity or a
PyRogue device that a downstream project instantiates.

Layers
------

.. list-table::
   :header-rows: 1
   :widths: 24 30 46

   * - Layer
     - Location
     - What it provides
   * - LCLS-II timing core
     - :repo:`LCLS-II/core/rtl/`
     - The timing receiver (``TimingCore``, ``TimingRx``), the frame and stream
       decoders, the message delay and stream converters, the pattern
       generator (``TPGMini`` and friends), the BSA and counter controls, and
       the shared packages ``TimingPkg`` and ``TPGPkg``.
   * - LCLS-II EVR
     - :repo:`LCLS-II/evr/rtl/`
     - The event receiver personality built on the core: ``EvrV2Module``,
       ``EvrV2CoreTriggers``, ``EvrV2CoreChannels``, the register bridges,
       and ``EvrV2Pkg``.
   * - LCLS-I EVR
     - :repo:`LCLS-I/evr/`
     - The legacy event receiver, ``EvrV1Core`` and its leaves, a mix of VHDL
       and Verilog. It shares the ``lcls_timing_core`` library name but not
       the LCLS-II core sources.
   * - GT wrappers
     - :repo:`LCLS-II/gtp7/`, :repo:`LCLS-II/gtx7/`,
       :repo:`LCLS-II/gthUltraScale/`, :repo:`LCLS-II/gthUltraScale+/`,
       :repo:`LCLS-II/gtyUltraScale+/`
     - One transceiver wrapper per device family, with the vendor IP under
       each ``coregen/`` directory.
   * - PyRogue package
     - :repo:`python/LclsTimingCore/`
     - One ``pr.Device`` class per register block, for example
       ``TPGMiniCore``, ``EvrV2CoreTriggers``, ``EvrV1Reg``, and
       ``TimingFrameRx``.
   * - YAML maps
     - :repo:`yaml/`
     - The same register maps in the Rogue YAML schema.

How a firmware project consumes it
----------------------------------

A project's ``ruckus.tcl`` loads this repository with ``loadRuckusTcl``. The
root :repo:`ruckus.tcl` loads the LCLS-I and LCLS-II trees, and
:repo:`LCLS-II/ruckus.tcl` loads the core, the EVR, and the one GT directory that
matches the target family (see :doc:`gt_families`). Every source is compiled into the VHDL library
``lcls_timing_core``, and the code uses the ``surf`` library for AXI-Lite
plumbing, FIFOs, and clock-domain synchronizers, so the project must also load
``surf``. The root script pins ``ruckus`` and ``surf`` versions and requires
Vivado 2019.1 or later.

What the regression verifies
----------------------------

Every unit that GHDL can analyze has a cocotb test that simulates it:

- The VHDL units run under GHDL, and the LCLS-I Verilog leaves run under
  Icarus Verilog.
- The PyRogue classes are built in a Rogue environment and exercised against
  models of the hardware.
- The register maps are compared across the VHDL decode, the PyRogue
  classes, and the YAML files, and any difference must be listed and linked
  to an issue.

The regression does not cover everything. These limits are stated by the
regression itself in :repo:`tests/common/ghdl_analysis.py`:

- The GT primitives and the Vivado IP under each ``coregen/`` directory are not
  simulated. The GT wrappers are Vivado-only.
- GHDL cannot analyze seven units, each recorded with the reason: ``TPGMiniReg``,
  ``TPGMiniCore``, ``TimingCore``, ``EvrV2Module``, ``EvrV1CoreIsrCtrl``, the
  ``EvrV2_tb`` testbench, and ``TimingGthWrapper``. The register blocks among
  them are covered through the PyRogue models and the drift check instead.
- ``EvrV1EventReceiver`` and ``EvrV1Core`` are not simulated. The first
  instantiates Verilog modules declared as VHDL components, and GHDL cannot bind
  Verilog while Icarus cannot elaborate VHDL. The Verilog leaves and the VHDL
  children are tested on their own.
- Nothing is synthesized, because CI has no Vivado license.

:repo:`tests/README.md` describes how to run each leg.

How to read these docs
----------------------

The documentation has three sections.

- The how-to guides are short recipes for a task, such as adding a target.
- The reference lists facts: entities with their generics and ports, and the
  verification status of each. It is generated from the sources.
- The explanation pages, which this section holds, describe how the blocks fit
  together.

Where a page states a measured behavior it links the test that pins it. Where
the RTL does something without written intent, the page words it as observed,
intent unconfirmed, and links the open questions issue instead of calling it a
defect: :issue:`211` for the core, :issue:`217` for the EVR, and :issue:`228` for the
PyRogue package.

See also
--------

- :doc:`/reference/index`
- :doc:`/reference/entities/index`
- :doc:`/reference/registers/index`
- :doc:`/reference/pyrogue/index`
- :doc:`/reference/known_issues`
