TimingMessageType
=================

``TimingMessageType`` (:repo:`LCLS-II/core/rtl/TimingPkg.vhd`) is the decoded
LCLS-II timing message: one record that carries everything the accelerator
timing system broadcasts on a fiducial. ``TimingFrameRx`` produces it from the
wire frame, ``TPGMini`` fills one in to generate a frame, and the consumers
(``EvrV2EventSelect``, the trigger and channel blocks, the message ring buffer,
and the message to AXI stream converter) read its fields. The record travels
inside ``TimingBusType`` next to a strobe and a valid flag.

The message is 944 bits, which is 59 sixteen-bit words, and the frame carries
it as a single segment (see :doc:`lcls2_frame`). The constants
``TIMING_MESSAGE_BITS_C`` (944) and ``TIMING_MESSAGE_WORDS_C`` (59) give the
size. The current format version is ``x"0001"``, which added the photon
wavelength words; ``TIMING_MESSAGE_INIT_C`` carries that version and sets every
``mpsClass`` nibble to ones.

Layout
------

The table below is generated from the layout table of the regression's reference
model, :repo:`tests/common/timing_model.py`, and is not drawn by hand. Fields are
packed starting at bit 0 in the order ``toSlv`` assigns them; an array field is
shown as one row whose range spans all of its elements, element 0 in the lowest
bits.

.. include:: ../_generated/timing_message.inc

The ``unused`` row is 13 bits that ``toSlv`` writes as zero and
``toTimingMessageType`` skips; it is not a field of the record. Together with
``syncStatus``, ``mpsValid``, and ``bcsFault`` it fills the 16-bit word at bits
304 to 319.

Field groups
------------

Identity and time
   ``version`` is the format version. ``pulseId`` counts fiducials. ``timeStamp``
   is the 64-bit time of the pulse; ``EvrV2CoreTriggers`` and
   ``EvrV2CoreChannels`` copy it to the trigger bus unchanged.

Rates
   ``fixedRates`` has one bit per fixed rate (10 bits), ``acRates`` has one bit
   per AC-synchronous rate (6 bits), ``acTimeSlot`` is the AC time slot (3 bits),
   and ``acTimeSlotPhase`` is the phase inside that slot (12 bits). ``EvrV2EventSelect``
   picks a bit of ``fixedRates`` or ``acRates`` with the channel's ``rateSel``
   field, and uses ``acTimeSlot`` to select which of the time-slot enable bits
   applies. ``resync`` is a single bit.

Beam request and energy
   ``beamRequest`` is a 32-bit word. The comment in ``TimingPkg`` gives bit 0 as
   beam present, bits 7 to 4 as the destination, and bits 31 to 16 as the
   charge in pC. ``EvrV2EventSelect`` tests bit 0 and indexes the channel's
   ``destSel`` mask with the destination. ``beamEnergy`` holds four 16-bit
   energies and ``photonWavelen`` two 16-bit photon wavelengths.

Machine protection
   ``syncStatus``, ``mpsValid``, and ``bcsFault`` are single bits, ``mpsLimit`` is
   a 16-bit limit, and ``mpsClass`` is sixteen 4-bit classes.

Bunch synchronous acquisition
   ``bsaInit``, ``bsaActive``, ``bsaAvgDone``, and ``bsaDone`` are 64-bit masks,
   one bit per BSA buffer (see :doc:`bsa`).

Control words
   ``control`` is eighteen 16-bit words. ``EvrV2EventSelect`` picks one of them
   with the channel's ``rateSel`` field for the experiment-sequence selection.
   ``EvrV2FromV1`` fills words 0 to 15 from the 256-bit LCLS-I event-code mask
   and word 16 from the data buffer's modifier bits.

From the record to the wire
---------------------------

``toSlv`` walks the record in the order of the table and calls ``assignSlv`` for
each field, so field ``n`` starts where field ``n - 1`` ended and array element
``j`` follows element ``j - 1``. The 944-bit vector is cut into 59 words, word
``k`` being bits ``16k + 15`` down to ``16k``, and the serializer sends word 0
first. ``toTimingMessageType`` is the inverse. The record, the 944-bit vector,
and the words agree with the model bit for bit: the regression in
:repo:`tests/lcls2_core/test_TimingPkgConversions.py` walks a single one bit
through every position of the vector and checks that it lands in exactly one
field, and it compares ``toSlv`` and ``toTimingMessageType`` with the model for
all-zero, all-ones, and seeded random messages.

A shorter vector is also accepted by ``toTimingMessageType``: the variant without
BSA described on :doc:`lcls2_frame`, which has 672 bits. On that path the
conversion leaves ``version``, ``syncStatus``, ``mpsValid``, ``bcsFault``, and
the four BSA fields unassigned. That is observed and the intent is not
confirmed; it is open as :issue:`211`.
