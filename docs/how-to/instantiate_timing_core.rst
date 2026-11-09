Instantiate TimingCore or TimingRx
==================================

``TimingCore`` is the usual entry point: it receives the timing link from a
transceiver, decodes it, and delivers a decoded timing bus to the application.
It can also transmit a timing frame from its embedded pattern generator.
``TimingRx`` is the receiver alone, for a design that provides its own
transmit side and AXI-Lite crossbar. Both are in the ``lcls_timing_core``
library; see :doc:`../explanation/architecture` for the data path and
:doc:`../explanation/clocking_cdc` for the clock domains.

What each one provides
----------------------

``TimingCore`` (:repo:`LCLS-II/core/rtl/TimingCore.vhd`):

- ``TimingRx`` decoding the LCLS-I stream and the LCLS-II frame, selected by
  ``CLKSEL_MODE_G`` and a run-time register.
- The decoded ``TimingBusType`` on ``appTimingBus``, crossed into
  ``appTimingClk`` when ``ASYNC_G`` is true. With ``ASYNC_G`` false the bus is
  used as decoded, so use that only when ``appTimingClk`` is the receive clock
  ``gtRxRecClk``.
- Two optional ring buffers (``AXIL_RINGB_G``) that capture raw words and
  decoded messages.
- The embedded pattern generator ``TPGMiniCore`` (``USE_TPGMINI_G``, forced off
  when ``TPGEN_G`` is true), which drives the transmit data, polarity,
  inhibit, loopback, and a transmit reset request.
- ``EthTimingModule``, whose message ports are ``ibEthMsgMaster``,
  ``ibEthMsgSlave``, ``obEthMsgMaster``, and ``obEthMsgSlave``. The inbound
  master and the outbound slave have defaults, so a design that does not use
  the Ethernet message path can leave all four unconnected.

``TimingRx`` (:repo:`LCLS-II/core/rtl/TimingRx.vhd`) is the receive side
without the crossbar, the ring buffers, the pattern generator, or the clock
crossing: it exposes the decoded stream, message, and extension outputs with
their strobes and valid flags, plus one AXI-Lite slave for its registers.

Instantiate TimingCore
----------------------

The signal names below belong to the board design; the generic and port names
are exactly those the entity declares. A design that does not need a generic
can leave it at its default.

.. code-block:: vhdl

   U_TimingCore : entity lcls_timing_core.TimingCore
      generic map (
         TPD_G             => TPD_G,
         DEFAULT_CLK_SEL_G => '1',
         CLKSEL_MODE_G     => "SELECT",
         TPGEN_G           => false,
         STREAM_L1_G       => false,
         AXIL_RINGB_G      => true,
         ASYNC_G           => true,
         AXIL_BASE_ADDR_G  => TIMING_BASE_ADDR_C,
         USE_TPGMINI_G     => true)
      port map (
         -- Interface to the transceiver
         gtTxUsrClk       => txUsrClk,
         gtTxUsrRst       => txUsrRst,
         gtRxRecClk       => rxUsrClk,
         gtRxData         => rxData,
         gtRxDataK        => rxDataK,
         gtRxDispErr      => rxDispErr,
         gtRxDecErr       => rxDecErr,
         gtRxControl      => rxControl,
         gtRxStatus       => rxStatus,
         gtTxReset        => txReset,
         gtLoopback       => loopback,
         tpgMiniTimingPhy => txPhy,
         timingClkSel     => timingClkSel,
         -- Decoded timing bus
         appTimingClk     => appTimingClk,
         appTimingRst     => appTimingRst,
         appTimingBus     => appTimingBus,
         appTimingMode    => appTimingMode,
         -- AXI-Lite
         axilClk          => axilClk,
         axilRst          => axilRst,
         axilReadMaster   => axilReadMaster,
         axilReadSlave    => axilReadSlave,
         axilWriteMaster  => axilWriteMaster,
         axilWriteSlave   => axilWriteSlave);

``CLKSEL_MODE_G`` is ``"SELECT"`` (choose the protocol at run time, starting from
``DEFAULT_CLK_SEL_G``), or one of ``"LCLSI"``, ``"LCLSII"``, ``"LCLSIPIIC"``, and
``"LCLSIIPIC"``, which fix the protocol and drop the receiver of the other one.
``timingClkSel`` is the reference clock selection: ``'0'`` for LCLS-I, ``'1'`` for
LCLS-II. The board uses it to switch the transceiver reference clock.

Connect the transceiver wrapper
-------------------------------

The transceiver wrapper of each family (the ``TimingGtCoreWrapper`` and
``TimingGthCoreWrapper`` entities under ``LCLS-II/gtp7/``, ``gtx7/``,
``gthUltraScale/``, ``gthUltraScale+/``, and ``gtyUltraScale+/``) has ports for
the same signals, so a connection is by meaning:

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - TimingCore port
     - Wrapper side
   * - ``gtRxRecClk``
     - The receive user clock (``rxUsrClk``, typically driven from
       ``rxOutClk`` through the board's clock buffer).
   * - ``gtRxData``, ``gtRxDataK``, ``gtRxDispErr``, ``gtRxDecErr``
     - ``rxData``, ``rxDataK``, ``rxDispErr``, ``rxDecErr``.
   * - ``gtRxControl``, ``gtRxStatus``
     - ``rxControl`` (to the wrapper) and ``rxStatus`` (from the wrapper).
   * - ``tpgMiniTimingPhy``
     - The transmit side: its data, K flags, and control feed ``txData``,
       ``txDataK``, and ``txControl``.
   * - ``gtTxUsrClk``, ``gtTxUsrRst``
     - The transmit user clock and its reset, the clock of ``txUsrClk``.
   * - ``gtLoopback``
     - ``loopback``.
   * - ``gtTxReset``, ``timingClkSel``
     - Board level: the transmit reset request and the reference clock select
       go to the board's own reset and clock logic.

The AXI-Lite address map
------------------------

``AXIL_BASE_ADDR_G`` is the base of a 256 KiB window, decoded by a crossbar
inside ``TimingCore``:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Offset
     - Block
     - PyRogue class
   * - ``0x00000``
     - ``TimingRx`` status and control
     - ``TimingFrameRx``
   * - ``0x10000``
     - Raw word ring buffer (when ``AXIL_RINGB_G``)
     - A surf ring buffer device
   * - ``0x20000``
     - Decoded message ring buffer (when ``AXIL_RINGB_G``)
     - A surf ring buffer device
   * - ``0x30000``
     - ``TPGMiniCore`` (when the pattern generator is used)
     - ``TPGMiniCore``

An unused window answers with a decode error. ``GthRxAlignCheck`` is not
instantiated by ``TimingCore`` or by any transceiver wrapper in this
repository; a board design that wants the phase-lock check instantiates it
separately, chooses its address, and maps it with the ``GthRxAlignCheck`` class.
See :doc:`use_pyrogue` for building the tree.

Instantiate TimingRx
--------------------

Use ``TimingRx`` directly when the design supplies the crossbar and transmit
path itself:

.. code-block:: vhdl

   U_TimingRx : entity lcls_timing_core.TimingRx
      generic map (
         TPD_G             => TPD_G,
         DEFAULT_CLK_SEL_G => '1',
         CLKSEL_MODE_G     => "SELECT")
      port map (
         rxClk               => rxUsrClk,
         rxData              => timingRxData,
         rxControl           => rxControl,
         rxStatus            => rxStatus,
         timingClkSel        => timingClkSel,
         timingModeSel       => timingModeSel,
         timingStreamUser    => timingStreamUser,
         timingStreamPrompt  => timingStreamPrompt,
         timingStreamStrobe  => timingStreamStrobe,
         timingStreamValid   => timingStreamValid,
         timingMessage       => timingMessage,
         timingMessageStrobe => timingMessageStrobe,
         timingMessageValid  => timingMessageValid,
         timingExtension     => timingExtension,
         txClk               => txUsrClk,
         axilClk             => axilClk,
         axilRst             => axilRst,
         axilReadMaster      => axilReadMaster,
         axilReadSlave       => axilReadSlave,
         axilWriteMaster     => axilWriteMaster,
         axilWriteSlave      => axilWriteSlave);

``rxData`` is a ``TimingRxType`` record: assign its ``data``, ``dataK``,
``decErr``, and ``dspErr`` fields from the transceiver outputs, as ``TimingCore``
does. The AXI-Lite slave is the register block that ``TimingFrameRx`` maps.

See also
--------

- :doc:`/reference/entities/core`
- :doc:`/reference/registers/TimingFrameRx`
- :doc:`/reference/pyrogue/TimingFrameRx`
