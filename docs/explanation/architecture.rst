Architecture and data flow
==========================

The library is organized around one data path. A transceiver delivers 16-bit
words with K-character flags, a receiver block turns them into a decoded timing
message and a strobe, and consumers use the message to fire triggers, select
events, or log and forward the frame. A second path runs the other way: the
pattern generator builds a timing frame and serializes it into the transmitter.
Every block has its own register map on AXI-Lite, and the PyRogue tree mirrors
those blocks one to one.

The receive path
----------------

.. code-block:: text

   serial link
        |
        v
   GT wrapper (one per device family, see the GT family page)
        |  gtRxRecClk, gtRxData, gtRxDataK, gtRxDispErr, gtRxDecErr
        v
   +-- TimingCore ---------------------------------------------------------+
   |                                                                       |
   |   TimingRx                                                            |
   |     +-- TimingStreamRx   LCLS-I stream receiver                       |
   |     |                    (built unless CLKSEL_MODE_G is LCLSII or      |
   |     |                    LCLSIIPIC)                                   |
   |     |                                                                 |
   |     +-- TimingFrameRx    LCLS-II frame receiver                       |
   |           TimingDeserializer   words to 16 serial streams, CRC check  |
   |           TimingSerialDelay    stream 0: timing message, delayed      |
   |           TimingSerialDelay    streams 1 to 15: extension messages    |
   |           (built unless CLKSEL_MODE_G is LCLSI or LCLSIPIIC)          |
   |                                                                       |
   |   TimingMessageType or TimingStreamType, strobe, valid                |
   |   AxiLiteRingBuffer x2 (raw GT words, decoded messages)               |
   |   SynchronizerFifo to appTimingClk                                    |
   +-----------------------------+-----------------------------------------+
                                 |  appTimingBus (TimingBusType)
        +------------------------+------------------------+
        v                        v                        v
   EvrV2CoreTriggers      EvrV2CoreChannels       blocks a project wires
   EvrV2Module            (event select,          up itself:
   (event select,         event counts)           TimingMsgToAxiStream,
   trigger outputs)                               TimingMsgAxiRingBuffer,
                                                  TimingMsgDelay

``TimingMsgToAxiStream``, ``TimingMsgAxiRingBuffer``, and ``TimingMsgDelay``
are library blocks that no RTL file in this repository instantiates; they have
wrappers for the regression and are meant for the downstream project to connect.

The LCLS-I EVR is a separate path. ``EvrV1EventReceiver`` takes ``rxData`` and
``rxDataK`` straight from the transceiver and decodes events itself, without
the LCLS-II core.

Receiver blocks
~~~~~~~~~~~~~~~

``TimingRx`` (:repo:`LCLS-II/core/rtl/TimingRx.vhd`) instantiates the
receiver for each protocol with a generate on ``CLKSEL_MODE_G``. A mode that
has no receiver for a protocol ties that protocol's outputs to their reset
values. Register ``0x20`` selects which receiver feeds the status counters and
which one is held in reset. In the ``SELECT`` mode the selection bits are
writable; in every other mode they are read only and hold the value the mode
implies. The regression sweeps all five modes in
:repo:`tests/lcls2_core/test_TimingRx.py`.

``TimingFrameRx`` (:repo:`LCLS-II/core/rtl/TimingFrameRx.vhd`) decodes the
LCLS-II frame. ``TimingDeserializer``
(:repo:`LCLS-II/core/rtl/TimingDeserializer.vhd`) splits the word stream into 16
serial streams and checks the frame CRC. Stream 0 carries the timing message
and passes through a ``TimingSerialDelay``
(:repo:`LCLS-II/core/rtl/TimingSerialDelay.vhd`), whose delay comes from register
``0x24`` of ``TimingRx``; streams 1 to 15 each get their own delay line and
become the extension messages. The strobe for a frame arrives when the start of
the following frame is seen, so the receiver delivers the previous frame, as
measured in :repo:`tests/lcls2_core/test_TimingFrameRx.py`.

``TimingStreamRx`` (:repo:`LCLS-II/core/rtl/TimingStreamRx.vhd`) decodes the
LCLS-I stream directly from the symbols, with no deserializer. It outputs the
user and prompt copies of the stream, a strobe, and a valid flag. The strobe
comes 14002 clocks after the event code marker symbol, as measured in
:repo:`tests/lcls2_core/test_TimingRx.py` and exercised against the transmitter
in :repo:`tests/lcls2_core/test_TimingStream.py`.

``TimingCore`` (:repo:`LCLS-II/core/rtl/TimingCore.vhd`) wraps ``TimingRx`` as
``U_TimingRx`` and adds an AXI-Lite crossbar with four slots: the receiver
registers at offset ``0x00000``, a ring buffer of raw GT words at ``0x10000``,
a ring buffer of decoded messages at ``0x20000``, and the pattern generator
registers at ``0x30000``, each relative to ``AXIL_BASE_ADDR_G``. The ring
buffers are built when ``AXIL_RINGB_G`` is true and the pattern generator when
``USE_TPGMINI_G`` is true and ``TPGEN_G`` is false. The decoded message
crosses from the recovered clock to ``appTimingClk`` through a
``SynchronizerFifo`` when ``ASYNC_G`` is true. ``TimingCore`` contains
``TPGMiniCore`` and the Ethernet message block ``EthTimingModule``
(:repo:`LCLS-II/core/rtl/EthTimingModule.vhd`); GHDL cannot analyze ``TimingCore``, so
the block is covered through its children and the register-map checks (see the
overview).

Message types
~~~~~~~~~~~~~

The decoded frame is a ``TimingMessageType`` and the LCLS-I frame is a
``TimingStreamType``. ``TimingCore`` selects one of them with the mode select
and presents both on ``TimingBusType``, with the ``modesel`` flag saying which
one is current. When ``ASYNC_G`` is true the unselected field is held at its
reset value. The conversion functions between the records and bit vectors, and the
bit widths, are pinned in
:repo:`tests/lcls2_core/test_TimingPkgConversions.py`.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Record
     - Defined in
     - Role
   * - ``TimingRxType``
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - One cycle of received words: data, K flags, decode and disparity errors.
   * - ``TimingPhyControlType``, ``TimingPhyStatusType``
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - Control to the transceiver (reset, polarity, PLL reset) and status back
       from it (locked, reset done, buffer bypass).
   * - ``TimingSerialType``
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - One 16-bit segment of a serial stream with its offset and last flag.
   * - ``TimingMessageType``
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - The decoded LCLS-II message: pulse id, time stamp, rates, beam request
       and energy, MPS fields, BSA fields, and the control words.
   * - ``TimingStreamType``
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - The LCLS-I stream: pulse id, event codes, and the data buffer.
   * - ``TimingExtensionMessageType``
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - A valid flag and 512 data bits for each of extension streams 1 to 15.
   * - ``TimingBusType``
     - :repo:`LCLS-II/core/rtl/TimingPkg.vhd`
     - The bus the application sees: strobe, valid, both message forms, link
       status, mode select, and the extensions.
   * - ``TPGConfigType``, ``TPGStatusType``
     - :repo:`LCLS-II/core/rtl/TPGPkg.vhd`
     - Pattern generator configuration and status, decoded from the TPGMini
       registers.
   * - ``EvrV2ChannelConfig``, ``EvrV2TriggerConfigType``
     - :repo:`LCLS-II/evr/rtl/EvrV2Pkg.vhd`
     - EVR channel and trigger configuration, decoded from the EVR registers.

The pattern generator path
--------------------------

.. code-block:: text

   AXI-Lite (axiClk)
        |
        v
   TPGMiniCore
     AxiLiteAsync            axiClk to txClk
     TPGMiniReg              registers on txClk
        |  config, status
        +--> TPGMini         LCLS-II frame source
        |      Divider       base and fixed-rate dividers
        |      BsaControl    BSA acquisition state
        |      ClockTime     time stamp
        |      TPSerializer  message to serial stream
        |      TimingSerializer   stream to words with CRC
        |             |
        |             +--> txData(1), txDataK(1)
        |
        +--> TPGMiniStream   LCLS-I frame source
               Divider, ClockTime, TPGMiniEdef
               TimingStreamTx
                      |
                      +--> txData(0), txDataK(0)

   TimingCore picks txData(1) or txData(0) by the mode select
   and drives the result into the GT transmitter.

``TPGMiniCore`` (:repo:`LCLS-II/core/rtl/TPGMiniCore.vhd`) holds one
register block and two frame sources. ``TPGMini``
(:repo:`LCLS-II/core/rtl/TPGMini.vhd`) builds the LCLS-II frame, and
``TPGMiniStream`` (:repo:`LCLS-II/core/rtl/TPGMiniStream.vhd`) builds the LCLS-I
stream through ``TimingStreamTx`` (:repo:`LCLS-II/core/rtl/TimingStreamTx.vhd`).
Inside ``TPGMini``, ``TPSerializer``
(:repo:`LCLS-II/core/rtl/TPSerializer.vhd`) packs the message into 16-bit
segments and ``TimingSerializer``
(:repo:`LCLS-II/core/rtl/TimingSerializer.vhd`) frames the segments, appends the
CRC, and produces the words for the transmitter. The pattern generator
is described on its own page.

The whole transmit chain is checked end to end by looping the serializer output
back into the receivers in :repo:`tests/lcls2_core/test_TimingLoopback.py`.

Where state lives
-----------------

There is no central state manager. Each block keeps its state in its own
registers, in the clock domain it runs on, and exposes it through its own
AXI-Lite window. Signals that cross domains go through the ``surf``
synchronizers described on :doc:`clocking_cdc`.

On the host, the ``LclsTimingCore`` package mirrors the register blocks:
``TPG`` roots the pattern generator and ``EvrV2Core`` roots the LCLS-II EVR,
with one ``pr.Device`` class per block under
:repo:`python/LclsTimingCore/`. The register offsets in the VHDL decode, the
Python classes, and the YAML maps in :repo:`yaml/` are kept in agreement by hand,
and the regression's drift check reports any difference.
