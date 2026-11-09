The pattern generator (TPG and TPGMini)
=======================================

The pattern generator is the transmit side of the library. It produces a timing
stream on its own, without an upstream source, so a board can drive its
receivers, run a test bench, or act as a small timing master. The embedded
version is ``TPGMini``, which is the version the core instantiates; its LCLS-I
counterpart is ``TPGMiniStream``.

Structure
---------

``TPGMiniCore`` (:repo:`LCLS-II/core/rtl/TPGMiniCore.vhd`) is the unit a
project sees. It holds the register block ``TPGMiniReg``
(:repo:`LCLS-II/core/rtl/TPGMiniReg.vhd`), the LCLS-II frame source ``TPGMini``,
and the LCLS-I frame source ``TPGMiniStream``, and exposes two transmit
interfaces. ``TimingCore`` selects one of them with the mode select. The
PyRogue class ``TPGMiniCore``
(:repo:`python/LclsTimingCore/TPGMiniCore.py`) mirrors the register block.

GHDL cannot analyze ``TPGMiniReg`` (it contains a case choice that GHDL cannot
prove locally static), and ``TPGMiniCore`` and ``TimingCore`` inherit the
failure when they re-analyze it. The registers are therefore verified through
the PyRogue model and the drift check, and ``TPGMini`` and ``TPGMiniStream`` are
simulated through wrappers that replace the register block with flat ports.

TPGMini: the LCLS-II frame source
---------------------------------

``TPGMini`` (:repo:`LCLS-II/core/rtl/TPGMini.vhd`) builds one timing message per
base period and sends it through ``TPSerializer`` and ``TimingSerializer``
(see the architecture page). What it generates:

- **Base rate.** A divider (``Divider``) on the transmit clock divides down to
  the base enable that starts each frame. The divisor is the register
  ``BaseControl`` of ``TPGMiniCore``.
- **Fixed rates.** Ten more dividers, one per bit of the ``fixedRates`` field,
  each counting base enables with its own divisor (register ``FixedRateDiv``).
- **Pulse id.** A 64-bit counter that increments once per frame and can be
  loaded through ``PulseIdWr`` and ``PulseIdSet``.
- **Time stamp.** A free-running clock-time counter (``ClockTime``) that can be
  loaded through ``TStampWr`` and ``TStampSet``.
- **BSA control.** One ``BsaControl`` per BSA array (``NARRAYSBSA``, 2 when
  ``TimingCore`` instantiates it), whose outputs fill the BSA fields of the
  message. See :doc:`bsa`.

The remaining message fields are constants. In the RTL, ``TPGMini`` ties the AC
rates, the beam request, the MPS fields, and the control words to zero. The
decoded frames carry version 1 and time slot 1, and every other field outside
the pulse id, time stamp, fixed rates, and BSA fields is zero.

The regression runs the generator into a ``TimingFrameRx`` and checks both sides
in :repo:`tests/lcls2_core/test_TPGMini.py`. Measured there:

- A frame leaves every 100 clocks at a base divisor of 100, each symbol equal to
  the model encoding of the decoded message, with a good CRC.
- The first frame carries the loaded pulse id and each later frame the previous
  one plus one. A write of the pulse id lands in the next frame and the
  sequence continues from it.
- Fixed rate bit i is set in frame k when k is at least 1 and k is a multiple of
  the divisor programmed for bit i, counting frames from the reset.
- At the cycle of a frame's fiducial, the status pulse id already equals the
  pulse id that frame carries.
- The time stamp advances by 70/13 ns per transmit clock, so frame to frame by
  538 or 539 ns.
- The receiver strobes for each frame, one frame late, with the message equal
  to the model vector.

TPGMiniStream: the LCLS-I frame source
--------------------------------------

``TPGMiniStream`` (:repo:`LCLS-II/core/rtl/TPGMiniStream.vhd`) sends the LCLS-I
stream through ``TimingStreamTx``. Its base strobe period, in transmit
clocks, is the generic ``AC_PERIOD``. The transmitter takes a fiducial only while it is idle, so
at a period of 2 clocks the generator sends frames back to back with a measured
period of 682 clocks, and only the strobe that starts a frame is followed by
one. Each frame decodes to a data buffer equal
to the generator's ``simData`` output and event codes equal to ``simEvents``,
as checked in :repo:`tests/lcls2_core/test_TPGMiniStream.py`.

TPGMiniEdef: event definitions
------------------------------

``TPGMiniEdef`` (:repo:`LCLS-II/core/rtl/TPGMiniEdef.vhd`) is one event
definition that ``TPGMiniStream`` instantiates for each of its ``NUM_EDEFS``
definitions. A configuration write names an event definition by index and sets
the number of inputs to average (``navg``), the number of samples to acquire
(``nsmp``), a time slot, a rate, and a severity level; the configuration type
is in :repo:`LCLS-II/core/rtl/TPGMiniEdefPkg.vhd`. The registers are the
``Lcls1Bsa*`` variables of ``TPGMiniCore``.

Measured in :repo:`tests/lcls2_core/test_TPGMiniEdef.py` and again through
``TPGMiniStream``:

- A write for a different definition changes nothing. A matching write pulses
  ``init`` in the following cycle and raises the active flag one cycle later.
- An average completes on every ``navg + 1`` th strobe, and the definition is
  all done once, on strobe ``(navg + 1) * (nsmp + 1)``.
- A write while the definition is running, or one cycle after the first write,
  is ignored.
- Clearing the enable input freezes the state, and the strobe-gated outputs
  still follow the strobe. Reset returns the block to idle and clears the
  configuration, even with the enable low.
- A write for an index that has no instance leaves every event-definition bit
  unchanged (observed, intent unconfirmed; see :issue:`211`).

:repo:`LCLS-II/core/rtl/TPGMiniEdefTb.vhd` is a testbench that sits in an ``rtl``
directory; no ``ruckus.tcl`` lists it, and
:repo:`tests/lcls2_core/test_TPGMiniEdefTb.py` runs it as a no-crash smoke test
with no assertions of its own.

See also
--------

- :doc:`/reference/registers/TPGMiniCore`
- :doc:`/reference/pyrogue/TPGMiniCore`
- :doc:`/reference/entities/core`
