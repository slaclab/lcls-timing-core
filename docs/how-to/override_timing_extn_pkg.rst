Override the timing extension package
=====================================

The timing frame carries extension streams beyond the 944-bit message, and
``TimingExtnPkg`` gives them a typed view for a design. The library ships a
default package, and a project that carries different extension data supplies
its own in place of it. The background is on the
:doc:`../explanation/extension_package` page; this page is the procedure.

What the default declares
-------------------------

The default, :repo:`LCLS-II/core/rtl/default/TimingExtnPkg.vhd`, declares:

- ``EXPT_STREAM_ID``, ``EXPT_MESSAGE_BITS_C`` (320), ``ExptMessageType``,
  ``EXPT_MESSAGE_INIT_C``, and the conversions ``toSlv`` and ``toExptMessageType``.
- The extended interface: the subtype ``TimingExtnType``, the constants
  ``TIMING_EXTN_INIT_C``, ``TIMING_EXTN_BITS_C``, ``TIMING_EXTN_STREAMS_C``, and
  ``TIMING_EXTN_WORDS_C``, and ``toTimingExtnType`` in a vector form and in a
  procedure form that decodes a given stream number.

Everything in the second group is the interface a design relies on. A
replacement must declare all of those names with the same types and parameter
lists, and may change what they hold.

Write the replacement
---------------------

Create a package named ``TimingExtnPkg`` in your own project, outside this
repository, with the same names. Change the message record, the bit counts, and
the decode procedure to your streams, and implement the conversions to match.
The outline below shows the declarations to keep; fill in the record and the
bodies:

.. code-block:: vhdl

   library ieee;
   use ieee.std_logic_1164.all;

   library surf;
   use surf.StdRtlPkg.all;

   package TimingExtnPkg is

      -- Replace with the record your project carries.
      type ProjectExtnType is record
         example : slv(31 downto 0);
      end record;

      subtype TimingExtnType is ProjectExtnType;
      constant TIMING_EXTN_INIT_C    : TimingExtnType := (example => (others => '0'));
      constant TIMING_EXTN_BITS_C    : integer := 32;
      constant TIMING_EXTN_STREAMS_C : integer := 1;
      constant TIMING_EXTN_WORDS_C   : IntegerArray(TIMING_EXTN_STREAMS_C-1 downto 0) := (
         0 => TIMING_EXTN_BITS_C/16);

      function toTimingExtnType (vector : slv) return TimingExtnType;
      procedure toTimingExtnType(stream : in    integer;
                                 vector : in    slv;
                                 validi : in    sl;
                                 extn   : inout TimingExtnType;
                                 valido : inout sl);

   end package TimingExtnPkg;

The entries of ``TIMING_EXTN_WORDS_C`` and the stream numbers the procedure
decodes follow your message definition. In the default, the procedure decodes
stream 2 only and leaves its outputs alone for any other stream number; decide
the same for each stream your package handles. Test the conversions the way the
regression tests the default: through a wrapper that exposes the vectors as
ports (see :doc:`add_wrapper_test`), with one set bit walked through every
position so a gap or an overlap in the layout shows.

Load it from your ruckus.tcl
----------------------------

Compile the package into the library ``lcls_timing_core``, the library the
default belongs to, from your project's ``ruckus.tcl``:

.. code-block:: tcl

   loadSource -lib lcls_timing_core -path "$::DIR_PATH/rtl/TimingExtnPkg.vhd"

Load only one ``TimingExtnPkg``. In this repository no ``ruckus.tcl`` loads the
default: ``LCLS-II/core/ruckus.tcl`` names its sources one by one and lists
nothing from ``rtl/default``, and no RTL file here uses the package. Supplying
your own therefore needs no change to the library and does not replace a loaded
copy; do not add the default file beside yours.

See also
--------

- :doc:`/reference/packages`
- :doc:`/explanation/extension_package`
