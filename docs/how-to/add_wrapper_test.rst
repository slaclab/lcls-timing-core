Add a test with a wrapper
=========================

cocotb drives plain ``std_logic`` and ``std_logic_vector`` ports. A block whose
ports are VHDL records or record arrays (``TimingPhyControlType``,
``AxiLiteReadMasterType``, ``TimingSerialArray``, and so on) cannot be driven
directly, so the test compiles a thin wrapper that flattens them. This page
walks through adding a wrapper, the test that uses it, and the bookkeeping the
regression enforces around both.

When a wrapper is needed
------------------------

Write a wrapper when the block under test has a record or array-of-record
port, or an AXI-Lite or AXI-Stream interface. Pass the block itself as the
``toplevel`` when every port is already a vector, as the leaf tests of
``Divider`` and the LCLS-I Verilog modules do.

Where it goes
-------------

Put the wrapper in a ``wrappers/`` directory beside the RTL it wraps. The
regression knows three of them:

- :repo:`LCLS-II/core/wrappers/` for the LCLS-II core,
- :repo:`LCLS-II/evr/wrappers/` for the LCLS-II EVR,
- :repo:`LCLS-I/wrappers/` for the LCLS-I EVR.

Never name a wrapper in any ``ruckus.tcl``. The ruckus files of the production
trees load named files and the ``rtl/`` and ``evr/`` directories, never a
``wrappers/`` directory, so a wrapper is invisible to a Vivado build, and the
production guard allows ``.vhd`` files in a ``wrappers/`` directory. The wrapper is passed to the simulator by the test
(see below), which is the only place it is compiled.

Flatten the records
-------------------

Declare one plain port per record field, or one vector per array, and convert
inside the architecture. For a record that a package already converts to and
from a vector, call the package function (``toSlv``, ``toTimingMessageType``,
``toTimingExtnType``) so the test also exercises the conversion. For a record
array, slice a flat vector per element, as the existing serializer wrapper
does:

.. code-block:: vhdl

   library ieee;
   use ieee.std_logic_1164.all;

   library surf;
   use surf.StdRtlPkg.all;

   library lcls_timing_core;
   use lcls_timing_core.TimingPkg.all;

   entity TimingSerializerWrapper is
      generic (
         TPD_G     : time     := 1 ns;
         STREAMS_G : positive := 1);
      port (
         clk          : in  sl;
         rst          : in  sl;
         fiducial     : in  sl;
         streamReady  : in  slv(STREAMS_G-1 downto 0);
         streamData   : in  slv(16*STREAMS_G-1 downto 0);
         streamOffset : in  slv(7*STREAMS_G-1 downto 0) := (others => '0');
         streamLast   : in  slv(STREAMS_G-1 downto 0)   := (others => '1');
         streamIds    : in  slv(4*STREAMS_G-1 downto 0);
         advance      : out slv(STREAMS_G-1 downto 0);
         data         : out slv(15 downto 0);
         dataK        : out slv(1 downto 0));
   end entity TimingSerializerWrapper;

   architecture mapping of TimingSerializerWrapper is

      signal streams   : TimingSerialArray(STREAMS_G-1 downto 0);
      signal streamIdA : Slv4Array(STREAMS_G-1 downto 0);

   begin

      GEN_STREAM : for i in 0 to STREAMS_G-1 generate
         streams(i).ready  <= streamReady(i);
         streams(i).data   <= streamData(16*i+15 downto 16*i);
         streams(i).offset <= streamOffset(7*i+6 downto 7*i);
         streams(i).last   <= streamLast(i);
         streamIdA(i)      <= streamIds(4*i+3 downto 4*i);
      end generate GEN_STREAM;

      U_TimingSerializer : entity lcls_timing_core.TimingSerializer
         generic map (
            TPD_G     => TPD_G,
            STREAMS_C => STREAMS_G)
         port map (
            clk       => clk,
            rst       => rst,
            fiducial  => fiducial,
            streams   => streams,
            streamIds => streamIdA,
            advance   => advance,
            data      => data,
            dataK     => dataK);

   end architecture mapping;

Start the file with the banner and a ``Description:`` block that says what the
wrapper flattens and that it is never loaded by any ``ruckus.tcl``; copy the
header of an existing wrapper. A wrapper that exposes an AXI-Lite slave does so
through the surf ``SlaveAxiLiteIpIntegrator``, as :repo:`LCLS-II/core/wrappers/TimingRxWrapper.vhd`
does.

Lint the new file with the pinned vsg before staging. The lint job runs the
same style check on every file under a ``wrappers/`` directory:

.. code-block:: bash

   .venv/bin/vsg -f LCLS-II/core/wrappers/TimingSerializerWrapper.vhd -c vsg-linter.yml

The test file
-------------

Add ``tests/<leg>/test_<Entity>.py`` in the leg that matches the source tree
(``lcls2_core``, ``lcls2_evr``, or ``lcls1_evr``). The compliance audit now
fails the lint job on any finding, so the file needs:

- the license banner, then a module docstring that carries a
  ``Test methodology:`` block with the labels Sweep, Stimulus, Checks, Timing,
  and Propagation sampling (write "not applicable" with the reason for a label
  that has no content);
- a ``timeout_time`` on every ``@cocotb.test`` so a stalled wait fails instead
  of hanging;
- bounded waits only: a loop over a fixed number of clock cycles, never
  ``while True``;
- a reason on every skip, and no bare ``return`` in a cocotb entrypoint after
  the test has started checking.

The pytest function builds the simulation through ``run_lcls_vhdl_test``. The
wrapper file is handed over in ``extra_vhdl_sources`` under the library name
``lcls_timing_core``, and the ``toplevel`` is the wrapper entity in lower case:

.. code-block:: python

   """TimingSerializer through its wrapper: one stream is serialized in order.

   Test methodology:
       Sweep: one stream, then three streams.
       Stimulus: ready and data are driven per stream and the output words are
           read on each rising edge.
       Checks: the 16-bit words appear in stream order and every compared
           output is resolvable.
       Timing: outputs follow the inputs by one clock.
       Propagation sampling: every sample waits 2 ns past the rising edge so
           the registered outputs, which settle TPD_G = 1 ns after the edge,
           are stable.
   """

   from pathlib import Path

   import cocotb
   from cocotb.triggers import Timer

   from tests.common.regression_utils import (
       REPO_ROOT,
       cocotb_filtered_env,
       cocotb_test_filter,
       run_lcls_vhdl_test,
   )

   WRAPPER = REPO_ROOT / "LCLS-II/core/wrappers/TimingSerializerWrapper.vhd"


   @cocotb.test(timeout_time=100, timeout_unit="us")
   async def serializer_orders_streams(dut):
       """Words leave in stream order.

       Propagation sampling: outputs are read 2 ns after the rising edge.
       """
       dut.rst.value = 1
       await Timer(10, unit="ns")
       dut.rst.value = 0
       # ... drive the inputs and compare the outputs with a bounded loop ...


   def test_TimingSerializer():
       run_lcls_vhdl_test(
           test_file=Path(__file__),
           toplevel="lcls_timing_core.timingserializerwrapper",
           extra_vhdl_sources={"lcls_timing_core": [str(WRAPPER)]},
           extra_env=cocotb_filtered_env({}, cocotb_test_filter("serializer_orders_streams")),
       )

Pass generics through ``parameters=`` (and the same dictionary to
``cocotb_filtered_env``) when the test sweeps them, as
:repo:`tests/lcls2_core/test_TimingRx.py` does with ``CLKSEL_MODE_G``. A
Verilog leaf uses ``run_icarus_verilog_test`` instead and needs no wrapper.

How the coverage gate counts a wrapper
--------------------------------------

:repo:`tests/common/test_core_inventory.py` fails when a unit that a
``ruckus.tcl`` loads has no test of its own. A VHDL entity counts as tested
when a test passes it, or its own wrapper, as the ``toplevel`` of
``run_lcls_vhdl_test``. The wrapper is matched by name: ``<Entity>Wrapper``,
declared in a ``wrappers/`` directory of one of the three trees above. That is
why the wrapper name must be the entity name plus ``Wrapper``. Being
instantiated inside some other unit's wrapper does not count, so a block that
is only reached through a parent needs its own test.

Gate a defect test
------------------

A test that states the intended end state of a defect and fails while the
defect exists is gated, so the default run stays green. The form is fixed:

- a module-level ``KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"``,
- a test name that contains ``known_issue``,
- ``@pytest.mark.skipif(KNOWN_ISSUE_SKIP, reason=...)`` with a single string
  literal reason of the form
  ``known issue: <what>; see https://github.com/slaclab/lcls-timing-core/issues/<n>; set RUN_KNOWN_ISSUE_TESTS=1 to reproduce``.

File the issue first: a reason without a filed issue link fails
:repo:`tests/common/test_known_issue_links.py`. Run the gated tests with the
command of :doc:`run_regression`, which reports each one as ``XFAIL`` while the
defect reproduces.

Regenerate the reference
------------------------

The verification status of each entity on the reference pages (simulated, not
simulated, baseline-excluded, and so on) is computed from the test inventory,
not written by hand. After adding a test, or any change that moves an entity's
status, regenerate the pages and commit them with the change; the ``common``
leg fails on a stale page.

.. code-block:: bash

   .venv/bin/python -m tests.common.gen_docs

See also
--------

- :doc:`/reference/known_issues`
- :doc:`/reference/entities/index`
