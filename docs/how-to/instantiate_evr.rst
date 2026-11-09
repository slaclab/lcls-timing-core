Instantiate the EVR trigger and channel composites
==================================================

The LCLS-II EVR is built from small leaf entities. Two composites bundle them
for a board design:

- ``EvrV2CoreTriggers`` (:repo:`LCLS-II/evr/rtl/EvrV2CoreTriggers.vhd`) holds the
  channel registers, one event select per channel, the trigger registers, one
  trigger per output, and the optional complement pairs, all behind one
  AXI-Lite crossbar.
- ``EvrV2CoreChannels`` (:repo:`LCLS-II/evr/rtl/EvrV2CoreChannels.vhd`) holds the
  channel registers and the event selects only. Its outputs are the event
  select results, so a design that wants its own trigger logic uses this one.

Both take the decoded timing bus (``TimingBusType``) that ``TimingCore`` delivers
on ``appTimingBus`` (see :doc:`instantiate_timing_core`) and drive a
``TimingTrigType`` record on ``trigOut``.

EvrV2CoreTriggers
-----------------

The generics:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Generic
     - Meaning
   * - ``NCHANNELS_G``
     - Number of event selection channels.
   * - ``NTRIGGERS_G``
     - Number of trigger outputs. Triggers are paired for the optional AND or OR
       complement; an odd last trigger passes through unpaired.
   * - ``TRIG_DEPTH_G``
     - Width in bits of each trigger's delay and width counters (28 by default).
   * - ``TRIG_PIPE_G``
     - Trigger pipeline depth (0 by default, no pipeline).
   * - ``COMMON_CLK_G``
     - True when ``axilClk`` and ``evrClk`` are the same clock, which removes the
       synchronizers on the configuration. False (the default) crosses them.
   * - ``EVR_CARD_G``
     - Register stride. False packs the channel groups at a 256-byte stride and
       puts the trigger groups at a base of ``0x1000`` from the entity's base. True groups
       the registers on 4 KiB boundaries, with the trigger block at ``0x20000``,
       so separate processes can map the registers of their own channels.
   * - ``AXIL_BASEADDR_G``
     - The entity's AXI-Lite base address (``0x00080000`` by default). The
       crossbar inside the entity decodes full addresses, so the bus address
       presented to the entity must fall in the windows that follow this base.

.. code-block:: vhdl

   U_EvrTriggers : entity lcls_timing_core.EvrV2CoreTriggers
      generic map (
         TPD_G           => TPD_G,
         NCHANNELS_G     => 8,
         NTRIGGERS_G     => 8,
         TRIG_DEPTH_G    => 28,
         TRIG_PIPE_G     => 0,
         COMMON_CLK_G    => false,
         EVR_CARD_G      => false,
         AXIL_BASEADDR_G => EVR_BASE_ADDR_C)
      port map (
         axilClk         => axilClk,
         axilRst         => axilRst,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         evrClk          => appTimingClk,
         evrRst          => appTimingRst,
         evrBus          => appTimingBus,
         trigOut         => trigOut,
         evrModeSel      => appTimingMode);

``evrModeSel`` is the timing mode of the decoded bus. At ``'1'`` (its default) the
LCLS-II message is used as is; at ``'0'`` the entity rebuilds an LCLS-II style
message from the LCLS-I stream. Connect ``appTimingMode`` of ``TimingCore`` to
follow the receiver.

EvrV2CoreChannels
-----------------

The channel composite has the same ports and the generics ``TPD_G``,
``NCHANNELS_G``, ``COMMON_CLK_G``, and ``EVR_CARD_G`` with the meanings above.
It declares no base address generic: its AXI-Lite slave is the channel register
block itself, so the caller's crossbar decodes the address.

.. code-block:: vhdl

   U_EvrChannels : entity lcls_timing_core.EvrV2CoreChannels
      generic map (
         TPD_G        => TPD_G,
         NCHANNELS_G  => 8,
         COMMON_CLK_G => false,
         EVR_CARD_G   => false)
      port map (
         axilClk         => axilClk,
         axilRst         => axilRst,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         evrClk          => appTimingClk,
         evrRst          => appTimingRst,
         evrBus          => appTimingBus,
         trigOut         => trigOut,
         evrModeSel      => appTimingMode);

The matching PyRogue classes
----------------------------

``EvrV2CoreTriggers`` and ``EvrV2CoreChannels`` in ``python/LclsTimingCore/`` map
these two entities. Both take ``numTrig`` (1 to 16; any other value raises
``ValueError``), ``dmaEnable``, ``useTap``, and ``tickUnit``. ``EvrV2CoreTriggers``
builds ``numTrig`` channel register groups at ``i * 0x100`` and ``numTrig``
trigger register groups at ``0x1000 + i * 0x100``, so set ``NCHANNELS_G`` and
``NTRIGGERS_G`` to the same value and keep ``EVR_CARD_G`` false: the class
assumes the packed stride. ``EvrV2CoreChannels`` builds the channel groups only.
The device's ``offset`` in the tree is the base address of the entity
(``AXIL_BASEADDR_G`` for the triggers composite). See :doc:`use_pyrogue` for the
construction.
