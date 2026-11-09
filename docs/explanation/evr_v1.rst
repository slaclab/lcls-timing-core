LCLS-I EVR (EvrV1)
==================

The LCLS-I event receiver, ``EvrV1``, is the older of the two EVR personalities.
It decodes an event-code stream (one 8-bit event code per clock on a 16-bit
link word, with K-character flags), runs those codes through programmable maps
to twelve pulse channels, and exposes a register file over AXI-Lite. It does
not use the LCLS-II timing frame, so it does not depend on ``TimingRx``. The LCLS-II
personality is described on the :doc:`evr_v2` page.

Structure
---------

``EvrV1Core`` (:repo:`LCLS-I/evr/EvrV1Core.vhd`) is the top. It instantiates two
children and connects them with a configuration record and a status record
(``EvrV1ConfigType`` and ``EvrV1StatusType`` in
:repo:`LCLS-I/evr/EvrV1Pkg.vhd`):

- ``EvrV1Reg`` (:repo:`LCLS-I/evr/EvrV1Reg.vhd`), the AXI-Lite register file on
  ``axiClk``. With the generic ``ENDIAN_G`` true the top swaps the byte lanes of
  the read data, write data, and write strobes around it.
- ``EvrV1EventReceiver`` (:repo:`LCLS-I/evr/EvrV1EventReceiver.vhd`), the event
  datapath on ``evrClk``. It synchronizes the configuration from ``axiClk`` to
  ``evrClk`` with surf synchronizers and returns status.

The register file also drives the interrupt handshake (``irqActive``,
``irqEnable``, ``irqReq``). The ISR message path that sits beside the core is
``EvrV1CoreIsrCtrl`` (:repo:`LCLS-I/evr/EvrV1CoreIsrCtrl.vhd`), which no other
file in this repository instantiates; downstream projects do.

Inside the event receiver
~~~~~~~~~~~~~~~~~~~~~~~~~

``EvrV1EventReceiver`` is a VHDL entity, and it is the one place where the
language changes: it declares four Verilog modules as VHDL components and
instantiates them.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Block
     - Role
   * - ``EvrV1EventReceiverChannel`` (:repo:`LCLS-I/evr/EvrV1EventReceiverChannel.v`)
     - One pulse channel, instantiated twelve times. It takes the event strobe,
       the delay, width, and prescale words, and the polarity bit, and produces
       the trigger, with set and reset overrides.
   * - ``EvrV1TimeofDayReceiver`` (:repo:`LCLS-I/evr/EvrV1TimeofDayReceiver.v`)
     - Shifts the seconds word in from the event codes 0x70 and 0x71 and latches
       it on 0x7D, then counts the lower word of the time stamp.
   * - ``EvrV1TimeStampGenerator`` (:repo:`LCLS-I/evr/EvrV1TimeStampGenerator.v`)
     - A free-running time stamp used when the internal event is enabled
       instead of the decoded one.
   * - ``EvrV1DbusDecode`` (:repo:`LCLS-I/evr/EvrV1DbusDecode.v`)
     - Decodes the data buffer that rides on the link, checks its checksum, and
       writes it into ``EvrV1Databuff``.

The VHDL children it instantiates are ``EvrV1EventRAM256x32``
(:repo:`LCLS-I/evr/EvrV1EventRAM256x32.vhd`, four instances for the reset, set,
pulse, and interrupt maps, repeated for each of two pages), ``EvrV1TimeStampFIFO``
(:repo:`LCLS-I/evr/EvrV1TimeStampFIFO.vhd`), and ``EvrV1HeartBeat``
(:repo:`LCLS-I/evr/EvrV1HeartBeat.vhd`). ``EvrV1Databuff``
(:repo:`LCLS-I/evr/EvrV1Databuff.vhd`) is the byte-write, word-read RAM that the
data buffer decoder fills.

The data path follows the event code. An event code from the link (or from the
internal or external event insertion, when enabled) addresses the four event
RAMs. The pulse word selects which of the twelve channels start, the set and
reset words force a channel output high or low, and bit 31 of the interrupt
word writes the time stamp and event code into the time stamp FIFO. A page bit chooses which of the two RAM pages is live, so
software can rewrite one page while the other runs. Each channel output is then
routed through an output crossbar: map value ``n`` below 12 selects channel
``n``, 61 selects a divided clock, 62 drives high, 63 drives low, and every
other value drives low.

Simulation and its limit
------------------------

``EvrV1EventReceiver`` and ``EvrV1Core`` are not simulated. GHDL cannot bind
a Verilog module, and Icarus Verilog cannot elaborate the VHDL entities around
it, so a top that mixes the two has no simulator in the regression. The two
tops analyze cleanly under GHDL, so they are listed as "analyzable, not
simulated" in ``NOT_SIMULATED`` in :repo:`tests/common/ghdl_analysis.py`, and
the inventory gate in :repo:`tests/common/test_core_inventory.py` rejects the
entry as soon as a test simulates the unit.

What the regression does instead is test every child on its own, with the
simulator that can read it:

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Unit
     - Simulator
     - Test
   * - ``EvrV1Reg``
     - GHDL
     - :repo:`tests/lcls1_evr/test_EvrV1Reg.py`, through a flat-port wrapper
   * - ``EvrV1EventRAM256x32``
     - GHDL
     - :repo:`tests/lcls1_evr/test_EvrV1EventRAM256x32.py`
   * - ``EvrV1TimeStampFIFO``
     - GHDL
     - :repo:`tests/lcls1_evr/test_EvrV1TimeStampFIFO.py`
   * - ``EvrV1HeartBeat``
     - GHDL
     - :repo:`tests/lcls1_evr/test_EvrV1HeartBeat.py`
   * - ``EvrV1Databuff``
     - GHDL
     - :repo:`tests/lcls1_evr/test_EvrV1Databuff.py`
   * - ``EvrV1EventReceiverChannel``
     - Icarus
     - :repo:`tests/lcls1_evr/test_EvrV1EventReceiverChannel.py`
   * - ``EvrV1TimeofDayReceiver``
     - Icarus
     - :repo:`tests/lcls1_evr/test_EvrV1TimeofDayReceiver.py`
   * - ``EvrV1TimeStampGenerator``
     - Icarus
     - :repo:`tests/lcls1_evr/test_EvrV1TimeStampGenerator.py`
   * - ``EvrV1DbusDecode``
     - Icarus
     - :repo:`tests/lcls1_evr/test_EvrV1DbusDecode.py`

Two details of that table matter to a reader.

``EvrV1DbusDecode`` writes into ``EvrV1Databuff``, which is VHDL, so Icarus
cannot elaborate the real RAM. The regression uses a test-only Verilog model of
the RAM (:repo:`tests/lcls1_evr/models/EvrV1Databuff_model.v`). The model is tied
to the production RAM by running the same vectors
(:repo:`tests/lcls1_evr/databuff_vectors.py`) against the production file under
GHDL in :repo:`tests/lcls1_evr/test_EvrV1Databuff.py` and against the model under
Icarus in :repo:`tests/lcls1_evr/test_EvrV1DatabuffModel.py`. The model is not
loaded by any ``ruckus.tcl`` and is never part of a firmware build.

``EvrV1DbusDecode`` itself does not elaborate under Icarus as written, so the
default run simulates a test-time copy with one change (see below).

An unsized constant that Icarus rejects
---------------------------------------

Line 216 of ``EvrV1DbusDecode.v`` assigns ``rxSize <= {0, iRxSize};``. The
unsized constant in a concatenation has no defined width in IEEE 1364, and
Icarus Verilog 12.0 refuses to elaborate the file at every language level.
Vivado accepts it and truncates to the 12-bit ``rxSize``, so ``{1'b0, iRxSize}``
has the same value. This is filed as :issue:`216`.

In :repo:`tests/lcls1_evr/test_EvrV1DbusDecode.py` the default run therefore
simulates a copy of the file written under ``tests/sim_build`` at test time,
with that single text replaced; the production file is only read, and the test
fails loudly if the replaced text is not found exactly once. A test that is
gated behind ``RUN_KNOWN_ISSUE_TESTS`` compiles the production file itself and
passes once the constant has a width.

The decoder's behavior, as measured on the patched copy, includes the following
points whose intent is unconfirmed (observed, intent unconfirmed, with the
questions issue :issue:`217`): a ``dbena`` pulse is remembered while ``dben`` is
low, so the next buffer after ``dben`` rises is received with no new pulse; and
``dbrdy`` and ``rxSize`` report a buffer that was not stored when no ``dbena``
pulse preceded it or when ``dbdis`` cut it short.

Registers and the PyRogue map
-----------------------------

``EvrV1Reg`` decodes word addresses on the AXI-Lite bus into the control,
status, pulse, event RAM, output map, and interrupt words. The regression
reads the offsets of the write and read decode out of ``EvrV1Reg.vhd`` itself
and compares them with the tables the test uses, so a new decode arm turns the
test red; see :repo:`tests/lcls1_evr/test_EvrV1Reg.py`. Every writable word
resets to 0, the version words are built from the firmware version, and a read
waits for the latch latency before it returns.

The PyRogue class ``EvrV1Reg`` (:repo:`python/LclsTimingCore/EvrV1Reg.py`)
mirrors this block, and the regression compares the two. Two drifts are filed:

- ``IntEventEn`` and ``IntEventCount`` have their widths swapped relative to the
  firmware, which stores the enable from one bit and the count from 32 bits
  (:issue:`226`).
- The twelve ``OutputMap`` variables are declared at a stride of one word each,
  while the firmware packs two entries per word, so the variables do not land
  on the entries they name (:issue:`227`).

A third observation is held as a question rather than a defect. ``IrqFlagWr``
and ``IrqFlagRd`` are declared at the one offset 0x08, which is the write view
and the read view of the same word in the RTL, without ``overlapEn``, and Rogue
6.16.0 rejects the tree when it starts, naming ``IrqFlagWr``. The rejection is
pinned as observed in :repo:`tests/rogue/test_EvrV1Reg.py`, and whether the
shared offset is intended is asked in :issue:`217`.

Other register-block behavior, each pinned in
:repo:`tests/lcls1_evr/test_EvrV1Reg.py` and worded as observed, intent
unconfirmed (:issue:`217`):

- A write to the event RAM window is answered with a decode error, although it
  drives the select and write-enable masks and the data and address buses.
- A write of 0xFFFFFFFF to the interrupt clear word clears nothing, while other
  values clear the flags named by their set bits.
- With ``USE_WSTRB_G`` true, the output map words update an entry only for the
  matching half-word strobe; a full-word write changes neither entry.
- The status inputs ``tsFifoValid``, ``tsFifoNext``, ``tsFifoWrCnt``,
  ``dbInt``, and ``dbIntEna`` are read by no register word.

Leaf behavior worth knowing
---------------------------

Measured in the leaf tests, and the intent unconfirmed where noted (questions
issue :issue:`217`):

- ``EvrV1EventReceiverChannel``: with the event captured at index E, the
  trigger first becomes active at E + 1 + delay times the prescale ticks and
  stays active for width times the prescale ticks; a width of 0 gives no pulse
  (:repo:`tests/lcls1_evr/test_EvrV1EventReceiverChannel.py`). A second event
  edge during the delay is ignored by the state machine but restarts the
  prescaler, which shifts the pulse (observed, intent unconfirmed).
- ``EvrV1TimeofDayReceiver``: after 0x7D the upper word of the time stamp is
  the received seconds and the lower word starts at 0 and rises by one per clock
  (:repo:`tests/lcls1_evr/test_EvrV1TimeofDayReceiver.py`).
- ``EvrV1TimeStampGenerator``: the time stamp rises by one per clock, and the
  upper word reaches 1 after a reload period of 330556 clocks
  (:repo:`tests/lcls1_evr/test_EvrV1TimeStampGenerator.py`).
- ``EvrV1TimeStampFIFO``: holds 512 words, the first 512 written, and drops a
  write into the full FIFO; the port named ``full`` is driven by the FifoAsync
  overflow output, so it pulses on a write into a full FIFO and is low while the
  FIFO is merely full; ``empty`` goes high while one or two words are still
  readable (:repo:`tests/lcls1_evr/test_EvrV1TimeStampFIFO.py`; the last two
  are observed, intent unconfirmed).
- ``EvrV1HeartBeat``: an event code 0x7A reloads the counter, and the timeout
  pulses once, a divider count later; the first cycle after reset release also
  pulses (:repo:`tests/lcls1_evr/test_EvrV1HeartBeat.py`; the pulse after reset
  is observed, intent unconfirmed).
- ``EvrV1EventRAM256x32``: one-clock read latency, read-first on a same-address
  access, and no change to the memory with the enable low
  (:repo:`tests/lcls1_evr/test_EvrV1EventRAM256x32.py`).

EvrV1CoreIsrCtrl
----------------

``EvrV1CoreIsrCtrl`` is the one LCLS-I unit that GHDL cannot analyze: a string
literal in it has a length that does not match the surf ``tKeep`` width, so
GHDL reports "string length does not match". The failure is recorded as an
expected one in ``KNOWN_GHDL_UNANALYZABLE`` in
:repo:`tests/common/ghdl_analysis.py`, and the unit is not simulated. Its register
map is covered through the PyRogue class ``EvrV1Isr``
(:repo:`python/LclsTimingCore/EvrV1Isr.py`) in
:repo:`tests/rogue/test_EvrV1Isr.py`.
