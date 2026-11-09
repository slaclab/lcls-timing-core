LCLS-II EVR
===========

:repo:`LCLS-II/evr/ruckus.tcl` loads these sources into the ``lcls_timing_core`` library; a file that is not loaded says so in the Status column.

.. list-table::
   :header-rows: 1
   :widths: 20 40 25 15

   * - Entity
     - File
     - Status
     - Issues
   * - :ref:`EvrV2Axi <entity-lcls-ii-evr-rtl-evrv2axi-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2Axi.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV2Cache <entity-lcls-ii-evr-rtl-evrv2cache-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2Cache.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV2ChannelReg <entity-lcls-ii-evr-rtl-evrv2channelreg-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2ChannelReg.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV2CoreChannels <entity-lcls-ii-evr-rtl-evrv2corechannels-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2CoreChannels.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV2CorePulseGen <entity-lcls-ii-evr-rtl-evrv2corepulsegen-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2CorePulseGen.vhd`
     - simulated
     - none
   * - :ref:`EvrV2CoreTriggers <entity-lcls-ii-evr-rtl-evrv2coretriggers-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2CoreTriggers.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV2EventSelect <entity-lcls-ii-evr-rtl-evrv2eventselect-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2EventSelect.vhd`
     - simulated
     - none
   * - :ref:`EvrV2FromV1 <entity-lcls-ii-evr-rtl-evrv2fromv1-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2FromV1.vhd`
     - simulated
     - none
   * - :ref:`EvrV2Module <entity-lcls-ii-evr-rtl-evrv2module-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2Module.vhd`
     - baseline-excluded
     - issue pending, issue pending
   * - :ref:`EvrV2TrigReg <entity-lcls-ii-evr-rtl-evrv2trigreg-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2TrigReg.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV2Trigger <entity-lcls-ii-evr-rtl-evrv2trigger-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2Trigger.vhd`
     - simulated
     - none
   * - :ref:`EvrV2TriggerCompl <entity-lcls-ii-evr-rtl-evrv2triggercompl-vhd>`
     - :repo:`LCLS-II/evr/rtl/EvrV2TriggerCompl.vhd`
     - simulated
     - none
   * - :ref:`EvrV2_tb <entity-lcls-ii-evr-tb-evrv2-tb-vhd>`
     - :repo:`LCLS-II/evr/tb/EvrV2_tb.vhd`
     - baseline-excluded
     - issue pending, issue pending

Package files in this tree: :repo:`LCLS-II/evr/rtl/EvrV2Pkg.vhd`.

.. _entity-lcls-ii-evr-rtl-evrv2axi-vhd:

EvrV2Axi
--------

File: :repo:`LCLS-II/evr/rtl/EvrV2Axi.vhd`

AXI-Lite register block of the LCLS-II EVR channels, on axiClk. Per channel it holds the enable bit and the rateSel and destSel words at a 32 byte stride from 0x020 plus a read-only event count, and it has the count reset (0x010) and trigger select (0x014) bits; with DMA_ENABLE_G true it also maps the interrupt, debug, threshold, and BSA words. The channelConfig, irqEnable, rstCount, trigSel, and dmaFullThr outputs follow the registers, and word 0x008 is commented out of the RTL, so it reads 0.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``DMA_ENABLE_G``
     - ``boolean``
     - ``false``
   * - ``CHANNELS_C``
     - ``integer``
     - ``1``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``irqEnable``
     - out
     - ``sl``
   * - ``channelConfig``
     - out
     - ``EvrV2ChannelConfigArray(CHANNELS_C - 1 downto 0)``
   * - ``trigSel``
     - out
     - ``sl``
   * - ``dmaFullThr``
     - out
     - ``slv(23 downto 0)``
   * - ``irqReq``
     - in
     - ``sl``
   * - ``rstCount``
     - out
     - ``sl``
   * - ``eventCount``
     - in
     - ``SlVectorArray(CHANNELS_C downto 0, 31 downto 0)``
   * - ``gtxDebug``
     - in
     - ``slv(7 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-evr-rtl-evrv2cache-vhd:

EvrV2Cache
----------

File: :repo:`LCLS-II/evr/rtl/EvrV2Cache.vhd`

Dual-clock capture memory that stores 192-bit entries written on clka and reads each entry back as six 32-bit words on clkb, lowest word first. Both pointers stop at entry 1023, so empty rises only when the read pointer reaches that entry and only word 0 of entry 1023 can be read, as observed with intent unconfirmed.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``rsta``
     - in
     - ``sl``
   * - ``clka``
     - in
     - ``sl``
   * - ``wea``
     - in
     - ``sl``
   * - ``din``
     - in
     - ``slv(191 downto 0)``
   * - ``rstb``
     - in
     - ``sl``
   * - ``clkb``
     - in
     - ``sl``
   * - ``enb``
     - in
     - ``sl``
   * - ``empty``
     - out
     - ``sl``
   * - ``dout``
     - out
     - ``slv(31 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-evr-rtl-evrv2channelreg-vhd:

EvrV2ChannelReg
---------------

File: :repo:`LCLS-II/evr/rtl/EvrV2ChannelReg.vhd`

AXI-Lite register file for NCHANNELS_G EVR event-select channels. Each channel group has a 256 byte window (4096 bytes when EVR_CARD_G is true) holding the enable, rateSel, and destSel configuration, the BSA and DMA words when DMA_ENABLE_G is true, and a read-only event count. Group i drives channelConfig(i), and an address one decode window above group 0 aliases it.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``NCHANNELS_G``
     - ``integer``
     - ``1``
   * - ``EVR_CARD_G``
     - ``boolean``
     - ``false``
   * - ``DMA_ENABLE_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``channelConfig``
     - out
     - ``EvrV2ChannelConfigArray(NCHANNELS_G - 1 downto 0)``
   * - ``eventCount``
     - in
     - ``Slv32Array(NCHANNELS_G - 1 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-evr-rtl-evrv2corechannels-vhd:

EvrV2CoreChannels
-----------------

File: :repo:`LCLS-II/evr/rtl/EvrV2CoreChannels.vhd`

Event-select half of the LCLS-II EVR. An EvrV2ChannelReg on axilClk configures NCHANNELS_G EvrV2EventSelect channels on evrClk, which pick frames from the timing bus after EvrV2FromV1 has converted an LCLS-I stream when evrModeSel is low. trigPulse(i) is high for one step per frame channel i selects, and the output also carries the time stamp, BSA, and dmod fields of the bus; COMMON_CLK_G true drops the clock-domain synchronizers.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``NCHANNELS_G``
     - ``natural``
     - ``1``
   * - ``COMMON_CLK_G``
     - ``boolean``
     - ``false``
   * - ``EVR_CARD_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``axilClk``
     - in
     - ``sl``
   * - ``axilRst``
     - in
     - ``sl``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``evrClk``
     - in
     - ``sl``
   * - ``evrRst``
     - in
     - ``sl``
   * - ``evrBus``
     - in
     - ``TimingBusType``
   * - ``trigOut``
     - out
     - ``TimingTrigType``
   * - ``evrModeSel``
     - in
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-evr-rtl-evrv2corepulsegen-vhd:

EvrV2CorePulseGen
-----------------

File: :repo:`LCLS-II/evr/rtl/EvrV2CorePulseGen.vhd`

Self-contained LCLS-II EVR with 12 channels and 12 trigger outputs behind one AXI-Lite crossbar: EvrV2Axi at AXIL_BASE_ADDR_G and EvrV2TrigReg at +0x200 configure an EvrV2EventSelect per channel and an EvrV2Trigger per output, driven by the timing bus on evrClk. It maps an LCLS-I stream to an LCLS-II message inline when evrModeSel is low and exposes the trigger delay tap load, write, and read ports. Only the trigger groups at 0x200 and 0x300 answer, as triggers 2 and 3, as observed with intent unconfirmed.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``AXIL_BASE_ADDR_G``
     - ``slv(31 downto 0)``
     - ``(others => '0')``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``irqActive``
     - in
     - ``sl``
   * - ``irqEnable``
     - out
     - ``sl``
   * - ``irqReq``
     - out
     - ``sl``
   * - ``evrClk``
     - in
     - ``sl``
   * - ``evrRst``
     - in
     - ``sl``
   * - ``evrBus``
     - in
     - ``TimingBusType``
   * - ``gtxDebug``
     - in
     - ``slv(7 downto 0)``
   * - ``syncL``
     - in
     - ``sl``
   * - ``trigOut``
     - out
     - ``slv(11 downto 0)``
   * - ``evrModeSel``
     - in
     - ``sl``
   * - ``delay_ld``
     - out
     - ``slv(11 downto 0)``
   * - ``delay_wr``
     - out
     - ``Slv6Array(11 downto 0)``
   * - ``delay_rd``
     - in
     - ``Slv6Array(11 downto 0)``

Issues: none

.. _entity-lcls-ii-evr-rtl-evrv2coretriggers-vhd:

EvrV2CoreTriggers
-----------------

File: :repo:`LCLS-II/evr/rtl/EvrV2CoreTriggers.vhd`

Trigger half of the LCLS-II EVR. An AXI-Lite crossbar on axilClk places an EvrV2ChannelReg for NCHANNELS_G channels and an EvrV2TrigReg for NTRIGGERS_G triggers at AXIL_BASEADDR_G and at +0x1000 (+0x20000 when EVR_CARD_G is true). On evrClk each trigger is an EvrV2Trigger armed by its channel and fired on the strobe, and each adjacent pair passes through EvrV2TriggerCompl for an optional AND or OR.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``NCHANNELS_G``
     - ``natural``
     - ``1``
   * - ``NTRIGGERS_G``
     - ``natural``
     - ``1``
   * - ``TRIG_DEPTH_G``
     - ``natural``
     - ``28``
   * - ``TRIG_PIPE_G``
     - ``natural``
     - ``0``
   * - ``COMMON_CLK_G``
     - ``boolean``
     - ``false``
   * - ``EVR_CARD_G``
     - ``boolean``
     - ``false``
   * - ``AXIL_BASEADDR_G``
     - ``slv(31 downto 0)``
     - ``x"00080000"``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``axilClk``
     - in
     - ``sl``
   * - ``axilRst``
     - in
     - ``sl``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``evrClk``
     - in
     - ``sl``
   * - ``evrRst``
     - in
     - ``sl``
   * - ``evrBus``
     - in
     - ``TimingBusType``
   * - ``trigOut``
     - out
     - ``TimingTrigType``
   * - ``evrModeSel``
     - in
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-evr-rtl-evrv2eventselect-vhd:

EvrV2EventSelect
----------------

File: :repo:`LCLS-II/evr/rtl/EvrV2EventSelect.vhd`

Decides on each strobe whether one event-select channel fires. selectOut is registered one clock after strobeIn when the channel is enabled, its rate selection matches the frame (a fixed rate bit, an AC rate bit gated by the time slot mask, or a bit of one of the 18 control words), and its destination selection matches the beam request; dmaOut adds dmaEnabled. In GHDL a control word index above 17 stops the simulation with an index out of bounds.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``clk``
     - in
     - ``sl``
   * - ``rst``
     - in
     - ``sl``
   * - ``config``
     - in
     - ``EvrV2ChannelConfig``
   * - ``strobeIn``
     - in
     - ``sl``
   * - ``dataIn``
     - in
     - ``TimingMessageType``
   * - ``selectOut``
     - out
     - ``sl``
   * - ``dmaOut``
     - out
     - ``sl``

Issues: none

.. _entity-lcls-ii-evr-rtl-evrv2fromv1-vhd:

EvrV2FromV1
-----------

File: :repo:`LCLS-II/evr/rtl/EvrV2FromV1.vhd`

Converts an LCLS-I timing stream into an LCLS-II timing message, registered on clk when timingIn.strobe is high. With disable low it rebuilds the pulse ID, time stamp, BSA, AC rate, modifier, and control words from the stream and makes up a beam request destination from dmod bits 61, 60, and 83; with disable high it passes timingIn.message through. Message fields it never assigns keep their previous value, as observed with intent unconfirmed.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``clk``
     - in
     - ``sl``
   * - ``disable``
     - in
     - ``sl``
   * - ``timingIn``
     - in
     - ``TimingBusType``
   * - ``timingOut``
     - out
     - ``TimingMessageType``

Issues: none

.. _entity-lcls-ii-evr-rtl-evrv2module-vhd:

EvrV2Module
-----------

File: :repo:`LCLS-II/evr/rtl/EvrV2Module.vhd`

Top level of the small LCLS-II EVR. An AXI-Lite crossbar splits axiClk traffic between EvrV2Axi at AXIL_BASEADDR and EvrV2TrigReg at +0x200, and the channel and trigger configurations cross to evrClk through synchronizers into NCHANNELS_G EvrV2EventSelect units and NTRIGGERS_G EvrV2Trigger units behind an EvrV2FromV1 stage. Event counts cross back to axiClk, and trigOut carries the NTRIGGERS_G outputs.

Status: baseline-excluded; GHDL analysis reports "must be locally static", which the regression records as a known failure

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``NCHANNELS_G``
     - ``integer``
     - ``1``
   * - ``NTRIGGERS_G``
     - ``integer``
     - ``1``
   * - ``TRIG_DEPTH_G``
     - ``integer``
     - ``16``
   * - ``COMMON_CLK_G``
     - ``boolean``
     - ``false``
   * - ``AXIL_BASEADDR``
     - ``slv(31 downto 0)``
     - ``x"00080000"``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``evrClk``
     - in
     - ``sl``
   * - ``evrRst``
     - in
     - ``sl``
   * - ``evrBus``
     - in
     - ``TimingBusType``
   * - ``trigOut``
     - out
     - ``slv(NTRIGGERS_G - 1 downto 0)``
   * - ``evrModeSel``
     - in
     - ``sl``

Issues: issue pending, issue pending

.. _entity-lcls-ii-evr-rtl-evrv2trigreg-vhd:

EvrV2TrigReg
------------

File: :repo:`LCLS-II/evr/rtl/EvrV2TrigReg.vhd`

AXI-Lite register file for TRIGGERS_C EVR triggers. Each group, 256 bytes (4096 when EVR_CARD_G is true), holds the channel, polarity, complement enable, complement AND, and enable bits in its first word, then the delay and width words; with USE_TAP_C it adds a delay tap word whose write pulses loadTap once and whose upper bits read delay_rd. Group i drives triggerConfig(i).

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``EVR_CARD_G``
     - ``boolean``
     - ``false``
   * - ``TRIGGERS_C``
     - ``integer``
     - ``1``
   * - ``USE_TAP_C``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``triggerConfig``
     - out
     - ``EvrV2TriggerConfigArray(TRIGGERS_C - 1 downto 0)``
   * - ``delay_rd``
     - in
     - ``Slv6Array(TRIGGERS_C - 1 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-evr-rtl-evrv2trigger-vhd:

EvrV2Trigger
------------

File: :repo:`LCLS-II/evr/rtl/EvrV2Trigger.vhd`

One EVR trigger output. After its arm input is seen (the channel chosen by config.channel, or any channel in the config.channels mask when USE_MASK_G is true) and the next fire strobe arrives, it queues a pulse in a FIFO that a state machine plays out as an edge config.delay clocks after the strobe lasting config.width clocks. A pulse is skipped when it would start before the previous queued pulse has ended or when the width is 0, and polarity sets the pulse level.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``CHANNELS_C``
     - ``integer``
     - ``1``
   * - ``TRIG_DEPTH_C``
     - ``integer``
     - ``16``
   * - ``TRIG_WIDTH_C``
     - ``integer``
     - ``EVRV2_TRIG_WIDTH_C``
   * - ``USE_MASK_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``clk``
     - in
     - ``sl``
   * - ``rst``
     - in
     - ``sl``
   * - ``config``
     - in
     - ``EvrV2TriggerConfigType``
   * - ``arm``
     - in
     - ``slv(CHANNELS_C - 1 downto 0)``
   * - ``fire``
     - in
     - ``sl``
   * - ``trigstate``
     - out
     - ``sl``

Issues: none

.. _entity-lcls-ii-evr-rtl-evrv2triggercompl-vhd:

EvrV2TriggerCompl
-----------------

File: :repo:`LCLS-II/evr/rtl/EvrV2TriggerCompl.vhd`

Complementary stage for a pair of trigger outputs. For each output, complEn low passes its own trigIn through, and otherwise the output is the AND (complAnd high) or OR (complAnd low) of both trigIn bits. The result is combinational, or one clock later when REG_OUT_G is true, and trigOut is 0 while rst is high.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``REG_OUT_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``clk``
     - in
     - ``sl``
   * - ``rst``
     - in
     - ``sl``
   * - ``config``
     - in
     - ``EvrV2TriggerConfigArray(1 downto 0)``
   * - ``trigIn``
     - in
     - ``slv(1 downto 0)``
   * - ``trigOut``
     - out
     - ``slv(1 downto 0)``

Issues: none

.. _entity-lcls-ii-evr-tb-evrv2-tb-vhd:

EvrV2_tb
--------

File: :repo:`LCLS-II/evr/tb/EvrV2_tb.vhd`

Free-running bench for the EVR blocks with 12 channels and 12 trigger outputs on a 5.4 ns evrClk, with a TPGMini and a TimingDeserializer producing the timing bus for EvrV2EventSelect and EvrV2Trigger instances. It also instantiates EvrV2Dma, EvrV2BsaControl, EvrV2BsaChannel, and EvrV2EventDma and uses an ExptBusType that nothing in the repository declares, so it is stale and GHDL cannot analyze it.

Status: baseline-excluded; GHDL analysis reports "no declaration for "exptbustype"", which the regression records as a known failure

.. rubric:: Generics

none

.. rubric:: Ports

none

Issues: issue pending, issue pending
