LCLS-II EVR (EvrV2)
===================

The LCLS-II event receiver, ``EvrV2``, turns the timing message that the timing
core delivers into trigger pulses and per-channel event counts. A channel
decides which timing frames it cares about (event selection), a trigger turns
the frames its channel selects into a delayed pulse of a programmable width
(the trigger pipeline), and two register blocks let software configure both.
The older LCLS-I personality is described on the :doc:`evr_v1` page, and the
timing frame that feeds this block is described on the :doc:`architecture` page.

Structure
---------

The pieces are the leaves ``EvrV2EventSelect``, ``EvrV2Trigger``, and
``EvrV2TriggerCompl``, the register blocks ``EvrV2ChannelReg``, ``EvrV2TrigReg``,
and ``EvrV2Axi``, the message adapter ``EvrV2FromV1``, and two composites that
put them together.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Unit
     - Role
   * - ``EvrV2EventSelect`` (:repo:`LCLS-II/evr/rtl/EvrV2EventSelect.vhd`)
     - One channel's decision: does this timing frame match the channel's rate
       and destination selection.
   * - ``EvrV2Trigger`` (:repo:`LCLS-II/evr/rtl/EvrV2Trigger.vhd`)
     - One trigger output: a delayed pulse of programmable width, armed by a
       channel.
   * - ``EvrV2TriggerCompl`` (:repo:`LCLS-II/evr/rtl/EvrV2TriggerCompl.vhd`)
     - Optional AND or OR of a pair of trigger outputs.
   * - ``EvrV2CoreChannels`` (:repo:`LCLS-II/evr/rtl/EvrV2CoreChannels.vhd`)
     - Channel register block plus one event select per channel; the event
       select outputs are the trigger outputs.
   * - ``EvrV2CoreTriggers`` (:repo:`LCLS-II/evr/rtl/EvrV2CoreTriggers.vhd`)
     - Channels, triggers, and complementary pairs together, behind one AXI-Lite
       crossbar.
   * - ``EvrV2ChannelReg``, ``EvrV2TrigReg``, ``EvrV2Axi``
     - AXI-Lite register blocks for the channel and trigger configuration
       (:repo:`LCLS-II/evr/rtl/EvrV2ChannelReg.vhd`,
       :repo:`LCLS-II/evr/rtl/EvrV2TrigReg.vhd`,
       :repo:`LCLS-II/evr/rtl/EvrV2Axi.vhd`).
   * - ``EvrV2FromV1`` (:repo:`LCLS-II/evr/rtl/EvrV2FromV1.vhd`)
     - Rebuilds an LCLS-II timing message from the LCLS-I event stream.
   * - ``EvrV2Cache`` (:repo:`LCLS-II/evr/rtl/EvrV2Cache.vhd`)
     - A dual-clock RAM that holds 192-bit event entries for DMA readout.
   * - ``EvrV2CorePulseGen`` (:repo:`LCLS-II/evr/rtl/EvrV2CorePulseGen.vhd`)
     - A register-mapped pulse generator built from the same leaves.
   * - ``EvrV2Module`` (:repo:`LCLS-II/evr/rtl/EvrV2Module.vhd`)
     - An earlier assembly of the same leaves behind a two-slot crossbar.

The shared types and the configuration records are in ``EvrV2Pkg``
(:repo:`LCLS-II/evr/rtl/EvrV2Pkg.vhd`). A channel configuration is 81 bits wide
and a trigger configuration is 87 bits wide (31 bits plus two 28-bit counters);
both cross from the AXI-Lite clock to the EVR clock as a packed vector.

Configuration records
~~~~~~~~~~~~~~~~~~~~~

The bit layouts below are generated from the layout tables of the regression's
model, :repo:`tests/common/evr_model.py`, which the register block tests
(:repo:`tests/lcls2_evr/test_EvrV2ChannelReg.py` and
:repo:`tests/lcls2_evr/test_EvrV2TrigReg.py`) use to decode the packed
configuration vectors that the RTL outputs. Fields are packed from bit 0 in the
order ``toSlv`` assigns them in ``EvrV2Pkg``.

.. include:: ../_generated/evr_channel_config.inc

.. include:: ../_generated/evr_trigger_config.inc

How the regression tests this block
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every unit above except ``EvrV2Module`` is simulated under GHDL. The tests
compare the RTL with a cycle-accurate model on every clock; the model is
:repo:`tests/common/evr_model.py`, and it is derived from the RTL, so it is
evidence of what the RTL does and not of what was intended. Behavior whose
intent the maintainers have not confirmed is stated on this page as observed,
intent unconfirmed, and the questions are collected in :issue:`217`.
``EvrV2Module`` is not simulated because GHDL cannot analyze it (an index and a
range expression are not locally static); see :repo:`tests/common/ghdl_analysis.py`.

Event selection
---------------

``EvrV2EventSelect`` combines three things into one registered output:
``selectOut`` is the rate test, the destination test, the incoming strobe, and the
channel enable, and ``dmaOut`` is the same with the channel's DMA enable. Both
outputs are registered, so they appear one clock after the strobe. The register
that picks the control word is registered one clock before that, so the rate
test sees a control word that is already settled.

The rate test is chosen by the two top bits of the ``rateSel`` field of the
channel configuration:

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Mode
     - Name
     - Test
   * - ``00``
     - Fixed rate
     - Bit ``rateSel(3:0)`` of the message's ``fixedRates`` mask. An index of 10
       to 15 never selects.
   * - ``01``
     - AC rate
     - Bit ``rateSel(2:0)`` of the message's ``acRates`` mask, and only when the
       mask bit for the current ``acTimeSlot`` (bit ``acTimeSlot + 2`` of
       ``rateSel``) is set. An index of 6 or 7 never selects.
   * - ``10``
     - Event code
     - Bit ``rateSel(3:0)`` of control word ``rateSel(8:4)`` of the message.
   * - ``11``
     - Reserved
     - Never selects.

The destination test uses bits 17:16 of ``destSel`` and the destination
nibble of the message's beam request (``beamRequest(7:4)``): mode ``00`` selects when the beam is
present and the destination's mask bit is set, ``01`` selects when it is not,
``10`` always selects, and ``11`` never selects. All of this is checked against
the model on every sampled clock, over every mode, index, and boundary
index, plus a seeded random run, in
:repo:`tests/lcls2_evr/test_EvrV2EventSelect.py`.

Three points are stated as observed, intent unconfirmed (:issue:`217`): the AC
mask bits for time slots 0 and 7 overlap the index field or fall outside the
mask field, so those slots cannot be selected cleanly; destination mode ``11``
never selects and ``destSel(18)`` has no effect; and the header comment says the
time slot counts from 1.

One defect is filed. ``EvrV2EventSelect`` indexes the 18-word control array with
``rateSel(8:4)`` in every rate mode, behind a bound of 72 (``MAXEXPSEQDEPTH``),
so an index of 18 or more reads past the end of the array and GHDL stops the
simulation (:issue:`213`). The default run keeps the field at 17 or below. A test
gated behind ``RUN_KNOWN_ISSUE_TESTS`` reproduces the stop.

The trigger pipeline
--------------------

``EvrV2Trigger`` is the unit that produces a pulse. A channel arms it, a fire
strobe starts it, and its output (``trigstate``) rises after the configured delay
and falls after the configured width. The configuration fields are
``delay``, ``width``, ``polarity``, ``enabled``, and the channel number.

The mechanism, as the RTL shows it: a small FIFO holds the future edges of the
output as pairs of (level, clock count until the edge). When the trigger is armed
and a fire arrives, it pushes the delay to the next rising edge and then the
width to the falling edge. A fire whose pulse would precede an edge already in
the queue, or a width of 0, is skipped. The queue is a surf ``FifoSync``.

Measured in :repo:`tests/lcls2_evr/test_EvrV2Trigger.py`:

- With the output sampled just after each clock edge, the output is first high in
  cycle fire + delay + 4, for delays of 0, 1, 2, 3, 10, and 50 and widths of 1, 2,
  and 5. The header comment of the RTL says the delay plus 5 clock ticks; whether it
  counts from a different reference cycle is asked in :issue:`217` (observed,
  intent unconfirmed).
- The queue holds ``2**bitSize(depth) + 1`` pulses. Measured at depths of 0, 1,
  4, 16, 28, and 127 with a delay of 1000 and a fire every 4 cycles, it accepts 3,
  3, 9, 33, 33, and 129 pulses. The header comment says "up to 127 triggers"
  (observed, intent unconfirmed, :issue:`217`).
- When the queue is full, later fires are dropped with no flag, and if the falling
  level of the last accepted pulse is the entry that is lost, the output stays
  high until the trigger is disabled or reset (observed, intent unconfirmed,
  :issue:`217`).
- With polarity 0 the output idles low after reset until the first pulse ends,
  because the idle level pushed into the queue at reset release does not land
  (observed, intent unconfirmed, :issue:`217`). A gated test holds the other
  reading.

One defect is filed. ``EvrV2Trigger`` indexes the ``arm`` vector with the 4-bit
``config.channel`` and the vector has only ``CHANNELS_C`` bits, so a trigger
enabled on a channel number at or above ``CHANNELS_C`` indexes past the end of
the vector and GHDL stops the simulation (:issue:`212`).

In the composites the two depth-like generics are easy to confuse. In
``EvrV2CoreTriggers``, the queue depth of each ``EvrV2Trigger`` is the generic
``TRIG_PIPE_G``, and ``TRIG_DEPTH_G`` (default 28) is passed to the trigger as the
width of its delay and width counters. The default ``TRIG_PIPE_G`` of 0 therefore
gives a queue of 3 pulses. Measured in
:repo:`tests/lcls2_evr/test_EvrV2CoreTriggers.py` with ``TRIG_DEPTH_G`` fixed at
28: ``TRIG_PIPE_G`` of 0, 16, 4, and 1 accept 3, 33, 9, and 3 pending pulses, and
the counter width does not change the capacity. Whether the 3-pulse default is
intended is asked in :issue:`217`. (``EvrV2Module`` passes its ``TRIG_DEPTH_G``
straight through as the queue depth, so the same name means a depth there.)

Complementary triggers
----------------------

``EvrV2TriggerCompl`` sits after a pair of triggers (triggers ``2i`` and ``2i + 1``
in ``EvrV2CoreTriggers``). For each of the two outputs, with ``complEn`` clear the
output is the trigger itself; with ``complEn`` set and ``complAnd`` set it is the
AND of the pair; with ``complEn`` set and ``complAnd`` clear it is the OR of the
pair. The output is combinational with ``REG_OUT_G`` false (which is how
``EvrV2CoreTriggers`` instantiates it) and one clock later with it true. A reset
forces the output to 0. The regression checks all sixteen configurations against
every input pair, then a seeded random run, in
:repo:`tests/lcls2_evr/test_EvrV2TriggerCompl.py`. A trigger count that is odd
leaves the last trigger unpaired and uncomplemented.

The AND and OR bits are decoded by ``EvrV2TrigReg`` at bits 28 and 29 of the
first word of a trigger group, but the PyRogue variables ``ComplEn`` and
``ComplAnd`` are declared at bits 29 and 30, one bit too high. Writing
``ComplEn`` from PyRogue therefore sets the firmware AND/OR select and leaves the
complement stage disabled (:issue:`214`).

Channels and triggers as composites
-----------------------------------

``EvrV2CoreChannels`` and ``EvrV2CoreTriggers`` wire the leaves together. Both
instantiate ``EvrV2FromV1`` to build the timing message (see below), delay the
bus strobe through a four-stage shift register, and give every channel an
``EvrV2EventSelect`` that is strobed from the second stage. The configuration
crosses from the AXI-Lite clock to the EVR clock through a surf synchronizer
vector unless ``COMMON_CLK_G`` is true, and the per-channel event counts cross
back through a status vector.

``EvrV2CoreChannels`` stops there: each channel's select output is the trigger
output, so a channel with an enable and a rate selection is itself a one-step
pulse at a fixed offset after the strobe. It also passes the message time stamp, the BSA fields,
and the modifier words through on its trigger output record.
``EvrV2CoreTriggers`` goes on: each ``EvrV2Trigger`` is armed by the channel
selects and fired from the fourth shift stage, and the complementary stage
produces the output pulses. The unit tests drive both composites through
AXI-Lite and compare every step with a composite model, in
:repo:`tests/lcls2_evr/test_EvrV2CoreChannels.py` and
:repo:`tests/lcls2_evr/test_EvrV2CoreTriggers.py`. In the channels test the event
count of a channel read back equals the number of frames it selected.

The AXI-Lite map depends on ``EVR_CARD_G``. With it false the channel groups are
packed at a stride of 256 bytes and the trigger groups follow at a base of 0x1000;
with it true each group sits on a 4 kB boundary and the trigger block starts at
0x20000. The tests walk the register map at both strides and compare the read-back
masks and reset values with the layout tables.

The register blocks
~~~~~~~~~~~~~~~~~~~

``EvrV2ChannelReg`` decodes the channel groups (enable, rate select, destination
select, DMA and BSA fields, and a read-only event count), and ``EvrV2TrigReg``
decodes the trigger groups (source channel, polarity, delay, width, the
complementary bits, enable, and an optional delay-tap word). ``EvrV2Axi`` is the
channel and global block with a 32-byte group stride from 0x20. In every case the
regression walks a one through every bit of every word, records which
configuration bit each write drives, and compares the result with the layout
table and with the PyRogue declarations read as text:
:repo:`tests/lcls2_evr/test_EvrV2ChannelReg.py`,
:repo:`tests/lcls2_evr/test_EvrV2TrigReg.py`, and
:repo:`tests/lcls2_evr/test_EvrV2Axi.py`. The PyRogue classes are
:repo:`python/LclsTimingCore/EvrV2ChannelReg.py`,
:repo:`python/LclsTimingCore/EvrV2TriggerReg.py`, and
:repo:`python/LclsTimingCore/EvrV2Core.py`.

The comparison finds drift that is filed as :issue:`215`: the PyRogue widths and
channel count do not match the firmware. The firmware decodes a 19-bit
destination select and a 6-bit BSA setup field, and twelve channels, while the
PyRogue variables cover 18 bits, 12 bits, and the enable and rate select of
channel 0 only.

Observed behaviors, each pinned in the tests named above and worded as observed,
intent unconfirmed (:issue:`217`):

- An address above a group window aliases the first group, because the decode
  compares only enough address bits for the groups it has. With one trigger in
  256-byte groups, reads at 0x104, 0x204, 0x404, 0x1004, and 0x8004 return the
  delay of trigger 0, and a write at 0x1004 changes it.
- ``EvrV2Axi`` lists ``axiRst`` in its sensitivity list but never uses it, so a
  reset pulse clears none of its registers.
- A write to the delay-tap word of ``EvrV2TrigReg`` pulses the tap load output
  once for every value, including a value that does not change the tap.
- The PyRogue ``ChannelEventCnt`` and ``GlobalEventCnt`` are declared read-write
  and the firmware makes them read-only; a write is acknowledged and ignored.
- The trigger block of ``EvrV2Core.py`` starts at 0x200 with a 16-byte stride, which
  does not match the group layout of ``EvrV2TrigReg``. Which block the PyRogue
  trigger layout describes is a question.
- ``EvrV2CoreTriggers.py`` assumes ``EVR_CARD_G`` is false, because it always puts
  channel groups at ``i * 0x100`` and trigger groups at ``0x1000 + i * 0x100``.

DMA and the event cache
-----------------------

A channel's DMA enable gates the ``dmaOut`` of its event select. In this
repository nothing consumes ``dmaOut``: the composites leave it unconnected, and
the DMA blocks that would receive it are commented out of ``EvrV2CorePulseGen``.
``EvrV2Cache`` is the storage half of that path. It is a 1024-entry RAM written
on one clock (``clka``) with 192-bit entries and read on another (``clkb``) as six
32-bit words, lowest word first. No RTL file in this repository instantiates it.

Measured in :repo:`tests/lcls2_evr/test_EvrV2Cache.py`: every entry that is
written reads back in full, six words in order. The pointer behavior follows the
RTL and is stated as observed, intent unconfirmed (:issue:`217`):

- The write pointer stops at entry 1023, and later writes keep overwriting that
  entry. A signal that would gate the writes (``wea`` and not done) is computed
  and never read.
- ``empty`` rises when the read pointer reaches entry 1023, whatever the writer
  has written, and from then on the word select no longer advances, so only
  word 0 of entry 1023 can be read. The limit is observable as ``empty`` rising
  after 6138 words (1023 entries of six words) have been enabled.
- ``rsta`` and ``rstb`` clear their pointers and done flags.

``EvrV2CorePulseGen`` builds ``EvrV2Axi`` without ``DMA_ENABLE_G`` and
``EvrV2TrigReg`` without ``USE_TAP_C``, so the words for the interrupt enable,
interrupt request, debug, DMA threshold, the BSA and DMA channel fields, and the
delay tap are not mapped: they read 0 and ignore writes, and ``irqReq`` is
driven by nothing (observed, intent unconfirmed, :issue:`217`).

Adapting the LCLS-I stream
--------------------------

``EvrV2FromV1`` builds a LCLS-II-shaped message from the LCLS-I stream and data
buffer. On each strobe with ``disable`` low (``evrModeSel`` is wired to
``disable``), it copies the pulse id, epics time, and BSA masks (with the minor
and major masks encoded on the init mask), the AC rates and time slot from the
data buffer modifier words, the MPS fields, and the event codes. Event code ``n``
lands in control word ``n div 16`` as bit ``n mod 16``, so an LCLS-I event code
is selected by a channel in event-code mode with ``rateSel(8:4)`` equal to
``n div 16`` and ``rateSel(3:0)`` equal to ``n mod 16``. The beam request is
synthesized: the destination is taken from two modifier bits and the beam bit from
a third. With ``disable`` high the input message passes through unchanged. All of
this equals the model on every sampled clock in
:repo:`tests/lcls2_evr/test_EvrV2FromV1.py`.

The fields ``version``, ``resync``, ``syncStatus``, ``mpsValid``, and ``bcsFault``
are never assigned, so they keep whatever the output held: the power-up value, or
the last message copied with ``disable`` high (observed, intent unconfirmed,
:issue:`217`).

Register-mapped pulse generator and the earlier module
------------------------------------------------------

``EvrV2CorePulseGen`` combines ``EvrV2Axi``, ``EvrV2TrigReg``, one event select per
channel, and twelve triggers. In
:repo:`tests/lcls2_evr/test_EvrV2CorePulseGen.py` it is configured over AXI-Lite
and fired by timing frames, and a trigger raises one pulse of the written width
at a fixed offset after the bus strobe of every frame that follows a frame its
channel selected. Its trigger register block sits in the crossbar at 0x200 with a
9-bit window, while ``EvrV2TrigReg`` decodes twelve 256-byte groups counted from
address 0, so only the groups at 0x200 and 0x300 answer, as triggers 2 and 3;
reads and writes at 0x400, 0x500, 0xB00, and 0xF00 answer a decode error. That
layout is observed, intent unconfirmed (:issue:`217`). No firmware file in this
repository instantiates ``EvrV2CorePulseGen`` (the test wrapper aside); whether downstream firmware uses it
is a question in the same issue.

``EvrV2Module`` assembles the same leaves behind a two-slot crossbar. Its
architecture never reads the generic ``COMMON_CLK_G``, so the channel
configuration is always synchronized to ``evrClk``, and the synchronized trigger
configuration that it builds is not the signal the ``EvrV2Trigger`` instances read
(they take ``triggerConfig`` directly). Both are readings of the RTL; no test pins
them, because GHDL cannot analyze the unit.
