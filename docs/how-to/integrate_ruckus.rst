Integrate the library with ruckus
=================================

A firmware project pulls lcls-timing-core into its Vivado build through ruckus.
The library has no top-level design: the project instantiates its entities and
asks ruckus to load their sources. This page covers adding the repositories,
loading them, and the checks the library runs when it is loaded.

Add the repositories
--------------------

Add lcls-timing-core, surf, and ruckus to the project as git submodules (or as
plain clones next to it). The library imports surf throughout its RTL, and ruckus
provides the build procedures. A common layout keeps them under
``firmware/submodules/``:

.. code-block:: bash

   git submodule add https://github.com/slaclab/ruckus firmware/submodules/ruckus
   git submodule add https://github.com/slaclab/surf firmware/submodules/surf
   git submodule add https://github.com/slaclab/lcls-timing-core firmware/submodules/lcls-timing-core
   git -C firmware/submodules/lcls-timing-core checkout v3.12.0

Pin each submodule to a tag. The root :repo:`ruckus.tcl` of this repository
requires specific versions of ruckus and surf (see below), so a branch tip of
either is usually the wrong choice.

Load the library from the project
---------------------------------

In the ``ruckus.tcl`` of the firmware target, load surf first and then the
repository root. ``loadRuckusTcl`` sources the ``ruckus.tcl`` of the directory
you name and, through it, every child:

.. code-block:: tcl

   # Load RUCKUS environment and library
   source $::env(RUCKUS_PROC_TCL)

   loadRuckusTcl $::env(TOP_DIR)/submodules/surf
   loadRuckusTcl $::env(TOP_DIR)/submodules/lcls-timing-core

The root :repo:`ruckus.tcl` then loads both generations of the library:

- ``LCLS-I`` loads the legacy event receiver from ``evr/``.
- ``LCLS-II`` loads the timing core from ``core/`` and the EVR from ``evr/``,
  then loads one transceiver wrapper directory chosen by the FPGA family. The
  family table is on the :doc:`../explanation/gt_families` page.

Every source is compiled into one VHDL library named ``lcls_timing_core``, so
RTL instantiates a block as ``entity lcls_timing_core.<Name>`` and uses a package
as ``lcls_timing_core.<Name>Pkg``. Surf blocks are in the library ``surf``.

What the root ruckus.tcl checks
-------------------------------

Under Vivado (``VIVADO_VERSION`` greater than 0) the root file runs three
checks before it loads anything:

- ``VersionCheck 2019.1``: the Vivado version must be 2019.1 or later, or the
  build exits.
- ``SubmoduleCheck`` of ``ruckus`` at 2.1.2 and of ``surf`` at 2.53.0: the
  checked-out submodules must match those versions, or the build exits.
- ``OVERRIDE_SUBMODULE_LOCKS``: when this environment variable is set to a
  non-zero value, the submodule locks are skipped and a banner says so. The
  Vivado version check still runs.

Outside Vivado none of the checks runs, which is how the GHDL regression loads
the same file. The regression itself clones surf and ruckus ``main`` instead of
the locked versions, so it also catches upstream breakage; a firmware build
should stay on the locked tags.

Choosing the transceiver wrapper
--------------------------------

Do not load a transceiver wrapper yourself. The ``LCLS-II`` ruckus file calls
``getFpgaFamily`` and loads the matching directory, so setting the target part
selects the wrapper. A family that has no wrapper loads none, and the design
must provide its own transceiver. See :doc:`../explanation/architecture` for how
the wrapper connects to the timing core and :doc:`instantiate_timing_core` for
the connections.

See also
--------

- :doc:`/reference/families`
- :doc:`/reference/entities/index`
