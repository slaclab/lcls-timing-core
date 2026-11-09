Clocking and clock-domain crossing
==================================

Every block in the library runs on one of a few clocks, and the blocks are
connected only through ``surf`` synchronizers and FIFOs. This page lists the
domains, what crosses between them, and the places where the regression
measured something that a reader building on the library should know.

Clock domains
-------------

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Clock
     - Port names
     - What runs on it
   * - Recovered timing clock
     - ``gtRxRecClk``, ``rxClk``, ``timingClk``
     - The receivers (``TimingDeserializer``, ``TimingFrameRx``,
       ``TimingStreamRx``), the message delay lines, and the write side of the
       ring buffers and the message FIFO.
   * - Transmit user clock
     - ``gtTxUsrClk``, ``txClk``
     - The pattern generator (``TPGMiniCore`` and everything inside it) and the
       serializers.
   * - AXI-Lite clock
     - ``axilClk``, ``axiClk``
     - Every register block, the status counters' read side, and the Ethernet
       message output.
   * - Application timing clock
     - ``appTimingClk``
     - The consumer side of the timing bus. It can equal the recovered clock, in
       which case ``ASYNC_G`` is false and no FIFO is built.
   * - EVR event clock
     - ``evrClk``
     - The LCLS-II EVR event select and trigger logic, and the LCLS-I EVR
       event decode.

The RTL treats the receiver clock, the transmit clock, and the AXI-Lite clock
as asynchronous to each other and crosses signals between them through
synchronizers and FIFOs.

What crosses and how
--------------------

Timing core
~~~~~~~~~~~

``TimingRx`` (:repo:`LCLS-II/core/rtl/TimingRx.vhd`) is the densest example:

- From ``axilClk`` to ``rxClk``: the message delay value goes through a
  ``SynchronizerVector``, the delay reset pulse through a ``Synchronizer``, and
  the clock and mode selects, the stream no-delay bit, and the buffer-bypass
  reset each through a ``Synchronizer``.
- From ``rxClk`` to ``axilClk``: the status counters use ``SyncStatusVector``,
  the receiver version a ``SynchronizerVector``, and the version error flag a
  ``Synchronizer``. The LCLS-I event counter is Gray encoded, crossed with a
  ``SynchronizerVector``, and decoded back to binary on the ``axilClk`` side.
- From ``txClk`` to ``axilClk``: the transmit clock activity counter uses
  ``SynchronizerOneShotCnt``.

``TimingCore`` (:repo:`LCLS-II/core/rtl/TimingCore.vhd`) crosses the decoded
message to ``appTimingClk`` with one ``SynchronizerFifo`` for the message and
one for each of the 15 extension streams, and crosses the mode select to the
receive, transmit, and application clocks with a ``Synchronizer`` each. The
link-up flags use a ``Synchronizer`` into ``appTimingClk``. The pattern
generator registers cross from ``axiClk`` to ``txClk`` through an
``AxiLiteAsync`` inside ``TPGMiniCore``
(:repo:`LCLS-II/core/rtl/TPGMiniCore.vhd`).

``TimingMsgToAxiStream`` takes a ``COMMON_CLOCK_G`` generic that is set when the
timing clock and the stream clock are the same, and otherwise crosses through
an ``AxiStreamFifoV2``. Both settings are simulated in
:repo:`tests/lcls2_core/test_TimingMsgToAxiStream.py`.

EVR
~~~

``EvrV2CoreTriggers`` and ``EvrV2CoreChannels`` carry a ``COMMON_CLK_G``
generic. When it is false they synchronize the channel and trigger
configuration from ``axilClk`` to ``evrClk`` with ``SynchronizerVector`` and
cross the event counters back with ``SyncStatusVector``. When it is true they
use the configuration directly and count events on ``evrClk``. The regression
runs the separate-clock case with ``axilClk`` at 10 ns and ``evrClk`` at 7 ns
and a reduced set with ``COMMON_CLK_G`` true; see
:repo:`tests/lcls2_evr/test_EvrV2CoreTriggers.py` and
:repo:`tests/lcls2_evr/test_EvrV2CoreChannels.py`.

``EvrV2Module`` (:repo:`LCLS-II/evr/rtl/EvrV2Module.vhd`) synchronizes its
channel and trigger configuration to ``evrClk`` and its event counts back to
``axiClk`` in the same way.

The LCLS-I ``EvrV1EventReceiver`` (:repo:`LCLS-I/evr/EvrV1EventReceiver.vhd`)
crosses its configuration from ``axiClk`` to ``evrClk`` with
``SynchronizerFifo``, ``SynchronizerVector``, and one-shot synchronizers. The
unit is not simulated (see the overview), so this is read from the RTL and not
measured.

Measured behavior to know about
-------------------------------

These facts come from the regression and are stated as observed. Where the RTL
carries no written intent they are marked intent unconfirmed and tied to the
open questions issue for the core, :issue:`211`.

- The clock and mode select outputs of ``TimingRx`` (``timingClkSel`` and
  ``timingModeSel``) are driven directly from the ``axilClk`` registers with no
  synchronizer. A consumer in another domain must synchronize them itself;
  ``TimingCore`` does so for its own uses. Pinned in
  :repo:`tests/lcls2_core/test_TimingRx.py` (``timingrx_select_switching``).
- The message delay reset is a one-cycle ``axilClk`` pulse into a plain
  ``Synchronizer``. A pulse that short is only guaranteed to span a receiver
  clock edge when ``axilClk`` is slower than ``rxClk``, so the regression runs
  ``axilClk`` at 12 ns against ``rxClk`` at 10 ns on purpose. Whether a faster
  ``axilClk`` is supported is not stated in the RTL (observed, intent
  unconfirmed). Pinned in :repo:`tests/lcls2_core/test_TimingRx.py`.
- A write to the delay register that changes the delay, or that sets bit 31,
  pulses the reset and discards a message already waiting in the delay line. A
  write of the same delay without bit 31 leaves it alone. Observed, intent
  unconfirmed; pinned in :repo:`tests/lcls2_core/test_TimingRx.py`
  (``timingrx_message_delay``).
- ``TimingMsgDelay`` declares ``FIFO_ADDR_WIDTH_G`` but builds both of its
  FIFOs with a fixed address width, so the generic has no effect. Observed,
  intent unconfirmed; pinned in
  :repo:`tests/lcls2_core/test_TimingMsgDelay.py`.

See also
--------

- :doc:`/reference/entities/core`
- :doc:`/reference/registers/TimingFrameRx`
