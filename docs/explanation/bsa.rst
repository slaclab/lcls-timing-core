Beam synchronous acquisition
============================

Beam synchronous acquisition (BSA) lets a consumer collect a measurement on
every pulse that matches a condition, average it, and write out the result.
The timing message tells the consumer which pulses to include. A definition says
which pulses qualify, how many to average, and how many averages to write. The
timing core turns each definition into four bits per BSA array, carried in the
message as ``bsaInit``, ``bsaActive``, ``bsaAvgDone``, and ``bsaDone``. The
message has 64 bits for each; the pattern generator drives the first
``NARRAYSBSA`` and holds the rest at zero.

The definition
--------------

A definition is a ``BsaDefType`` (:repo:`LCLS-II/core/rtl/TPGPkg.vhd`):

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Field
     - Width
     - Meaning
   * - ``nToAvg``
     - 13
     - Number of qualifying pulses averaged into one sample.
   * - ``avgToWr``
     - 16
     - Number of averages to write before the acquisition is done. The value
       ``0xFFFF`` makes the acquisition persist.
   * - ``rateSel``
     - 13
     - Which rate qualifies a pulse, a type in bits 12:11 and an index below
       (see the next section).
   * - ``destSel``
     - 19
     - Which beam destinations qualify, a mode in bits 17:16 and a destination
       mask in bits 15:0.
   * - ``maxSevr``
     - 2
     - Maximum alarm severity, copied onto the first cycle of the acquisition.
   * - ``noTmo``
     - 1
     - Do not use the timeout for done.
   * - ``init``
     - 1
     - Start a new acquisition on its rising edge.

The pattern generator holds one definition per BSA array in ``TPGMiniReg``; the
PyRogue variables are the ``Bsa*`` variables of ``TPGMiniCore``
(:repo:`python/LclsTimingCore/TPGMiniCore.py`). The ``CtrDefType`` that
``CtrControl`` uses has the same ``rateSel`` and ``destSel`` fields.

Selecting the pulses
--------------------

``EventSelect`` (:repo:`LCLS-II/core/rtl/EventSelect.vhd`) turns the ``rateSel``
fields into one bit per cycle. The type in bits 12:11 chooses the rate source:

- ``00``, fixed rate: bit ``fxRateSel`` of the fixed-rate vector.
- ``01``, AC rate: bit ``acRateSel`` of the AC-rate vector, qualified by a time
  slot mask. The time slot counts from 1 and selects bit ``acTS - 1`` of the
  mask.
- ``10``, sequence: bit ``seqbit`` of word ``seqword`` of the 18 sequence words.
  The word is registered, so the result follows a change of ``seqword`` one clock
  later, and a word number of 18 or more reads as zero.
- ``11``: never selects.

The first two modes are combinational. All four are pinned in
:repo:`tests/lcls2_core/test_EventSelect.py`.

``BsaControl`` and ``CtrControl`` then combine the rate bit with the destination.
The mode in ``destSel`` bits 17:16 acts as follows, with the beam-present flag
and the four-bit destination index taken from the beam request:

- ``00``, beam: the pulse counts when beam is present and the mask bit of its
  destination is set.
- ``01``, no beam: the pulse counts unless beam is present and the mask bit of its
  destination is set.
- ``10``, do not care: the pulse always counts.
- ``11``: never counts.

``TPGMini`` supplies zero for the beam request and ties the sequence words to
zero. Inside this repository that means beam mode ``00`` never counts, mode
``01`` always counts, and the sequence rate type never selects. A downstream
design connects real values.

The rateSel encoding and the sequence defect
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The fixed and AC fields agree everywhere. The sequence fields do not. The
comment on ``BsaDefType`` and ``CtrDefType`` in ``TPGPkg`` and the register
writer ``TPGMiniReg`` place the sequence number at ``rateSel`` bits 10:6 and the
bit in the low bits, while the decode in ``BsaControl`` and ``CtrControl`` reads
the sequence word from bits 10:5 and the bit from bits 4:0. The result is that a
sequence ``s`` written in the commented layout selects word ``2 * s``, and a
stale bit in ``rateSel`` bits 5:4 left from an earlier configuration changes the
word or the bit. This is a filed defect, :issue:`209`.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Field
     - Comment and ``TPGMiniReg``
     - ``BsaControl`` and ``CtrControl`` decode
   * - Sequence word
     - ``rateSel`` bits 10:6
     - ``rateSel`` bits 10:5
   * - Sequence bit
     - the low bits (3:0 written by ``TPGMiniReg``)
     - ``rateSel`` bits 4:0

The regression pins the observed mapping in the default run and holds the
commented mapping in a gated test, ``bsa_rate_field_comment_mapping`` in
:repo:`tests/lcls2_core/test_BsaControl.py`, which runs with
``RUN_KNOWN_ISSUE_TESTS=1`` and fails until the defect is fixed.

BsaControl: the acquisition state
---------------------------------

``BsaControl`` is entity ``BsaControl`` declared in ``BsaControlv2.vhd``
(:repo:`LCLS-II/core/rtl/BsaControlv2.vhd`); ``ruckus.tcl`` loads that file and
not :repo:`LCLS-II/core/rtl/BsaControl.vhd`, which declares the same entity.
One instance runs one definition on the transmit clock. Its outputs behave like
this, as measured in :repo:`tests/lcls2_core/test_BsaControl.py`:

- ``bsaInit`` is a one-cycle pulse, one cycle after ``init`` rises while the
  block is enabled. On that cycle ``bsaActive`` and ``bsaAvgDone`` carry
  ``maxSevr(0)`` and ``maxSevr(1)``.
- ``bsaActive`` follows the selected rate and destination in the same cycle,
  while the acquisition is not done.
- ``bsaAvgDone`` marks the end of an average and ``bsaDone`` marks the end of the
  acquisition. A value of ``0xFFFF`` in ``avgToWr`` never finishes.
- The counters ``nToAvgOut`` and ``avgToWrOut`` report progress. With
  ``ASYNC_REGCLK_G`` true they cross to ``sysclk`` through a surf synchronizer
  FIFO, which drops its first writes after the init pulse and then updates in
  bursts; the measured lag behind the counter is 5 to 10 transmit clocks.

The thresholds below have no written definition in the RTL, so they are stated
as observed, intent unconfirmed, and each open question is linked on its
bullet:

- With the rate selected on every cycle, a fresh acquisition makes its first
  ``bsaActive`` cycle two cycles after the init input.
- An average ends on the ``nToAvg + 1`` th active cycle for ``nToAvg`` of 2 or
  more, on every active cycle for ``nToAvg`` of 1, and never for ``nToAvg`` of 0,
  where the 13-bit counter has to wrap (:issue:`253`).
- The acquisition ends with ``bsaDone`` on the ``avgToWr`` th average. For
  ``nToAvg`` of 1 and ``avgToWr`` of 2 or more it ends one average later,
  because the last-average flag lags the counter by one cycle (:issue:`253`). It
  never ends for ``avgToWr`` of 0.
- A timeout pulses ``bsaDone`` but does not stop the acquisition; it keeps running
  when the rate returns (:issue:`254`). ``noTmo`` disables the timeout, and
  ``tmocnt`` sets its length in counts of the ``tmo`` input.

CtrControl: counting qualifying pulses
--------------------------------------

``CtrControl`` (:repo:`LCLS-II/core/rtl/CtrControl.vhd`) counts the pulses that
pass the same rate and destination test and reports the count on a rising edge
of ``ctrrst``. The count output holds the number of qualifying cycles between two
latch edges and is unchanged between them. The latch edge is 3 cycles after the
``ctrrst`` rising edge (the latency of the edge detector, measured), a ``ctrrst``
held high does not latch again, and a transmit reset clears the latched value.
The qualifying cycle on the latch edge itself is lost, because the count restarts
from zero there (observed, intent unconfirmed, :issue:`256`). These behaviors are
pinned in :repo:`tests/lcls2_core/test_CtrControl.py`. No RTL file in this
repository instantiates ``CtrControl``; downstream projects do.

See also
--------

- :doc:`/reference/registers/TPGMiniCore`
- :doc:`/reference/pyrogue/TPGMiniCore`
- :doc:`/reference/entities/core`
