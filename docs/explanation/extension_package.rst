The timing extension package
============================

Besides the 944-bit timing message, the LCLS-II frame carries fifteen extension
streams. The receiver delivers them as raw data, 512 bits and a valid flag per
stream, in ``TimingExtensionMessageType`` (:repo:`LCLS-II/core/rtl/TimingPkg.vhd`).
``TimingExtnPkg`` is the package that gives those streams a typed view.

What the package declares
-------------------------

The default package, :repo:`LCLS-II/core/rtl/default/TimingExtnPkg.vhd`, defines:

- ``EXPT_STREAM_ID``, the stream number the default message uses (``x"2"``).
- ``ExptMessageType``, a 320-bit record of ``baseRateSince1Hz`` and
  ``baseRateSinceTM`` (32 bits each) and ``irigTimeCode`` (256 bits), with
  ``EXPT_MESSAGE_INIT_C`` and the conversions ``toSlv`` and
  ``toExptMessageType``.
- The extended interface that a project overrides: the subtype ``TimingExtnType``,
  ``TIMING_EXTN_INIT_C``, ``TIMING_EXTN_BITS_C``, ``TIMING_EXTN_STREAMS_C`` (2),
  ``TIMING_EXTN_WORDS_C``, and ``toTimingExtnType``, which has both a
  vector-to-record form and a procedure form that decodes a given stream number
  into the record and sets a valid flag.

In the procedure form the default decodes only stream 2 and does nothing for any
other stream number.

Where the default lives and what uses it
----------------------------------------

The default sits in a directory named ``default`` so that it is visibly the slot
a project replaces. Observed in the repository:

- No ``ruckus.tcl`` loads the file. :repo:`LCLS-II/core/ruckus.tcl` names its
  sources one by one and lists nothing from ``rtl/default``.
- No RTL file in the repository uses the package.
- The regression reaches it through a wrapper that is given the file
  explicitly: :repo:`LCLS-II/core/wrappers/TimingExtnPkgWrapper.vhd`, exercised
  in :repo:`tests/lcls2_core/test_TimingPkgConversions.py`. That test checks the
  320-bit layout and the two conversion functions against a Python model, with a
  single set bit walked through every position.
- The set of unloaded files is pinned by
  :repo:`tests/common/test_unloaded_sources.py`.

Supplying your own package
--------------------------

A downstream project that wants a different extension layout provides its own
package named ``TimingExtnPkg`` with the same names and signatures as the
default, in place of it. :doc:`/how-to/override_timing_extn_pkg` describes the procedure.

See also
--------

- :doc:`/reference/packages`
- :doc:`/how-to/override_timing_extn_pkg`
