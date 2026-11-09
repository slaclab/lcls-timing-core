LCLS-I EVR
==========

:repo:`LCLS-I/ruckus.tcl` loads these sources into the ``lcls_timing_core`` library; a file that is not loaded says so in the Status column.

.. list-table::
   :header-rows: 1
   :widths: 20 40 25 15

   * - Entity
     - File
     - Status
     - Issues
   * - :ref:`EvrV1Core <entity-lcls-i-evr-evrv1core-vhd>`
     - :repo:`LCLS-I/evr/EvrV1Core.vhd`
     - not simulated
     - issue pending
   * - :ref:`EvrV1CoreIsrCtrl <entity-lcls-i-evr-evrv1coreisrctrl-vhd>`
     - :repo:`LCLS-I/evr/EvrV1CoreIsrCtrl.vhd`
     - baseline-excluded
     - issue pending, issue pending
   * - :ref:`EvrV1Databuff <entity-lcls-i-evr-evrv1databuff-vhd>`
     - :repo:`LCLS-I/evr/EvrV1Databuff.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV1DbusDecode <entity-lcls-i-evr-evrv1dbusdecode-v>`
     - :repo:`LCLS-I/evr/EvrV1DbusDecode.v`
     - simulated
     - :issue:`216`, issue pending
   * - :ref:`EvrV1EventRAM256x32 <entity-lcls-i-evr-evrv1eventram256x32-vhd>`
     - :repo:`LCLS-I/evr/EvrV1EventRAM256x32.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV1EventReceiver <entity-lcls-i-evr-evrv1eventreceiver-vhd>`
     - :repo:`LCLS-I/evr/EvrV1EventReceiver.vhd`
     - not simulated
     - issue pending
   * - :ref:`EvrV1EventReceiverChannel <entity-lcls-i-evr-evrv1eventreceiverchannel-v>`
     - :repo:`LCLS-I/evr/EvrV1EventReceiverChannel.v`
     - simulated
     - issue pending
   * - :ref:`EvrV1HeartBeat <entity-lcls-i-evr-evrv1heartbeat-vhd>`
     - :repo:`LCLS-I/evr/EvrV1HeartBeat.vhd`
     - simulated
     - none
   * - :ref:`EvrV1Reg <entity-lcls-i-evr-evrv1reg-vhd>`
     - :repo:`LCLS-I/evr/EvrV1Reg.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV1TimeStampFIFO <entity-lcls-i-evr-evrv1timestampfifo-vhd>`
     - :repo:`LCLS-I/evr/EvrV1TimeStampFIFO.vhd`
     - simulated
     - issue pending
   * - :ref:`EvrV1TimeStampGenerator <entity-lcls-i-evr-evrv1timestampgenerator-v>`
     - :repo:`LCLS-I/evr/EvrV1TimeStampGenerator.v`
     - simulated
     - issue pending
   * - :ref:`EvrV1TimeofDayReceiver <entity-lcls-i-evr-evrv1timeofdayreceiver-v>`
     - :repo:`LCLS-I/evr/EvrV1TimeofDayReceiver.v`
     - simulated
     - issue pending

Package files in this tree: :repo:`LCLS-I/evr/EvrV1Pkg.vhd`.

.. _entity-lcls-i-evr-evrv1core-vhd:

EvrV1Core
---------

File: :repo:`LCLS-I/evr/EvrV1Core.vhd`

Top level of the LCLS-I EVR core. It joins the EvrV1Reg AXI-Lite register file on axiClk with the EvrV1EventReceiver on evrClk, which turns the received event codes into 12 trigger outputs, an event stream, and interrupt status. ENDIAN_G true byte-swaps the AXI-Lite data and strobes for a big endian host.

Status: not simulated; it instantiates EvrV1EventReceiver, so it inherits the same mixed-language limit; its EvrV1Reg child is tested on its own

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
   * - ``BUILD_INFO_G``
     - ``BuildInfoType``
     - none
   * - ``SYNC_POLARITY_G``
     - ``sl``
     - ``'1'``
   * - ``USE_WSTRB_G``
     - ``boolean``
     - ``false``
   * - ``ENDIAN_G``
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
   * - ``axiReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axiReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``axiWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axiWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``irqActive``
     - in
     - ``sl``
   * - ``irqEnable``
     - out
     - ``sl``
   * - ``irqReq``
     - out
     - ``sl``
   * - ``sync``
     - in
     - ``sl``
   * - ``trigOut``
     - out
     - ``slv(11 downto 0)``
   * - ``eventStream``
     - out
     - ``slv(7 downto 0)``
   * - ``evrClk``
     - in
     - ``sl``
   * - ``evrRst``
     - in
     - ``sl``
   * - ``rxLinkUp``
     - in
     - ``sl``
   * - ``rxError``
     - in
     - ``sl``
   * - ``rxData``
     - in
     - ``slv(15 downto 0)``
   * - ``rxDataK``
     - in
     - ``slv(1 downto 0)``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1coreisrctrl-vhd:

EvrV1CoreIsrCtrl
----------------

File: :repo:`LCLS-I/evr/EvrV1CoreIsrCtrl.vhd`

Receive and interrupt front end of the LCLS-I EVR. On evrClk it raises rxLinkUp only after gtLinkUp has stayed high without decode or disparity errors for 0xFFFFFF clocks, then registers the GT data and flags later errors on rxError. On an interrupt request it sends an IRQ message on an AXI stream and waits for software, or, when the isrSelect bit at 0x0 is clear, reads the interrupt flags and registers itself over an AXI-Lite master and streams data buffer, event, FIFO full, pulse, heartbeat, and violation messages tagged by TDEST.

Status: baseline-excluded; GHDL analysis reports "string length does not match", which the regression records as a known failure

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
   * - ``DEFAULT_ISR_SEL_G``
     - ``sl``
     - ``'1'``
   * - ``TDEST_IRQ_MSG_G``
     - ``slv(7 downto 0)``
     - ``x"FF"``
   * - ``TDEST_DATABUF_MSG_G``
     - ``slv(7 downto 0)``
     - ``x"F5"``
   * - ``TDEST_PULSE_MSG_G``
     - ``slv(7 downto 0)``
     - ``x"F4"``
   * - ``TDEST_EVENT_MSG_G``
     - ``slv(7 downto 0)``
     - ``x"F3"``
   * - ``TDEST_HEARTBEAT_MSG_G``
     - ``slv(7 downto 0)``
     - ``x"F2"``
   * - ``TDEST_FIFOFULL_MSG_G``
     - ``slv(7 downto 0)``
     - ``x"F1"``
   * - ``TDEST_VIOLATION_MSG_G``
     - ``slv(7 downto 0)``
     - ``x"F0"``
   * - ``MEMORY_TYPE_G``
     - ``string``
     - ``"block"``
   * - ``FIFO_ADDR_WIDTH_G``
     - ``positive``
     - ``9``
   * - ``REM_BASE_ADDR_G``
     - ``slv(31 downto 0)``
     - ``(others => '0')``
   * - ``AXIS_CONFIG_G``
     - ``AxiStreamConfigType``
     - ``ssiAxiStreamConfig(4)``

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
   * - ``axilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``axilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``mAxilReadMaster``
     - out
     - ``AxiLiteReadMasterType``
   * - ``mAxilReadSlave``
     - in
     - ``AxiLiteReadSlaveType``
   * - ``mAxilWriteMaster``
     - out
     - ``AxiLiteWriteMasterType``
   * - ``mAxilWriteSlave``
     - in
     - ``AxiLiteWriteSlaveType``
   * - ``mAxisMaster``
     - out
     - ``AxiStreamMasterType``
   * - ``mAxisSlave``
     - in
     - ``AxiStreamSlaveType``
   * - ``irqActive``
     - out
     - ``sl``
   * - ``irqEnable``
     - in
     - ``sl``
   * - ``irqReq``
     - in
     - ``sl``
   * - ``evrClk``
     - in
     - ``sl``
   * - ``evrRst``
     - in
     - ``sl``
   * - ``gtLinkUp``
     - in
     - ``sl``
   * - ``gtRxData``
     - in
     - ``slv(15 downto 0)``
   * - ``gtRxDataK``
     - in
     - ``slv(1 downto 0)``
   * - ``gtRxDispErr``
     - in
     - ``slv(1 downto 0)``
   * - ``gtRxDecErr``
     - in
     - ``slv(1 downto 0)``
   * - ``rxLinkUp``
     - out
     - ``sl``
   * - ``rxError``
     - out
     - ``sl``
   * - ``rxData``
     - out
     - ``slv(15 downto 0)``
   * - ``rxDataK``
     - out
     - ``slv(1 downto 0)``

Issues: issue pending, issue pending

.. _entity-lcls-i-evr-evrv1databuff-vhd:

EvrV1Databuff
-------------

File: :repo:`LCLS-I/evr/EvrV1Databuff.vhd`

Dual-clock 2048 byte receive buffer for the LCLS-I data buffer. Bytes are written one at a time on clka at an 11-bit byte address and read back as little endian 32-bit words on clkb at a 9-bit word address, with one clkb clock of read latency. It is four 8-bit surf SimpleDualPortRam lanes with no reset, and words never written read 0 in simulation.

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
   * - ``clka``
     - in
     - ``sl``
   * - ``wea``
     - in
     - ``slv(0 downto 0)``
   * - ``addra``
     - in
     - ``slv(10 downto 0)``
   * - ``dina``
     - in
     - ``slv(7 downto 0)``
   * - ``clkb``
     - in
     - ``sl``
   * - ``addrb``
     - in
     - ``slv(8 downto 0)``
   * - ``doutb``
     - out
     - ``slv(31 downto 0)``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1dbusdecode-v:

EvrV1DbusDecode
---------------

File: :repo:`LCLS-I/evr/EvrV1DbusDecode.v`

Decoder for the LCLS-I data buffer carried on the event stream. After a K28.0 start code it stores alternating filler and data bytes into EvrV1Databuff on EventClock until a K28.1 or K28.5 end code, checks the complemented 16-bit sum in the next two bytes, and reports the byte count on rxSize, dbrx while receiving, dbrdy when a buffer is ready, and dbcs on a checksum error. Icarus rejects the unsized constant in its rxSize assignment, so the regression simulates a patched copy of this file.

Status: simulated; a cocotb test runs the module in Icarus Verilog

.. rubric:: Generics

none

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``Clock``
     - in
     - ``wire``
   * - ``EventClock``
     - in
     - ``wire``
   * - ``Reset``
     - in
     - ``wire``
   * - ``dbus``
     - in
     - ``[7:0]``
   * - ``isK``
     - in
     - ``wire``
   * - ``dbRdAddr``
     - in
     - ``[8:0]``
   * - ``dbena``
     - in
     - ``wire``
   * - ``dbdis``
     - in
     - ``wire``
   * - ``dben``
     - in
     - ``wire``
   * - ``rxSize``
     - out
     - ``[11:0]``
   * - ``dbrx``
     - out
     - ``wire``
   * - ``dbrdy``
     - out
     - ``wire``
   * - ``dbcs``
     - out
     - ``wire``
   * - ``disBus``
     - out
     - ``[7:0]``
   * - ``dataBuffOut``
     - out
     - ``[31:0]``
   * - ``dbDebug``
     - out
     - ``[73:0]``

Issues: :issue:`216`, issue pending

.. _entity-lcls-i-evr-evrv1eventram256x32-vhd:

EvrV1EventRAM256x32
-------------------

File: :repo:`LCLS-I/evr/EvrV1EventRAM256x32.vhd`

True dual-port 256 by 32 bit RAM, a surf TrueDualPortRam in read-first mode, that the LCLS-I EVR uses for its event code maps. Each port has its own clock, enable, write enable, address, and data, reads take one clock, and a write to the address being read returns the old word on that port in the same cycle.

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
   * - ``clka``
     - in
     - ``sl``
   * - ``ena``
     - in
     - ``sl``
   * - ``wea``
     - in
     - ``sl``
   * - ``addra``
     - in
     - ``slv(7 downto 0)``
   * - ``dina``
     - in
     - ``slv(31 downto 0)``
   * - ``douta``
     - out
     - ``slv(31 downto 0)``
   * - ``clkb``
     - in
     - ``sl``
   * - ``enb``
     - in
     - ``sl``
   * - ``web``
     - in
     - ``sl``
   * - ``addrb``
     - in
     - ``slv(7 downto 0)``
   * - ``dinb``
     - in
     - ``slv(31 downto 0)``
   * - ``doutb``
     - out
     - ``slv(31 downto 0)``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1eventreceiver-vhd:

EvrV1EventReceiver
------------------

File: :repo:`LCLS-I/evr/EvrV1EventReceiver.vhd`

Event decoder of the LCLS-I EVR on evrClk. The GT receive words feed the data buffer decoder, a time of day receiver, and four 256 by 32 event RAMs (reset, set, pulse, and interrupt maps) that drive twelve EvrV1EventReceiverChannel pulse generators for trigOut. It also queues event time stamps in EvrV1TimeStampFIFO, watches the 0x7A heartbeat code with EvrV1HeartBeat, sets the interrupt flags, and crosses the configuration and status to axiClk through surf synchronizers.

Status: not simulated; it instantiates EvrV1EventReceiverChannel, EvrV1TimeofDayReceiver, EvrV1TimeStampGenerator, and EvrV1DbusDecode, which are Verilog modules declared as VHDL components; GHDL cannot bind Verilog and Icarus cannot elaborate VHDL, so the mixed-language top is not simulated; the four Verilog leaves and its VHDL children are tested on their own

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
   * - ``SYNC_POLARITY_G``
     - ``sl``
     - ``'1'``

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
   * - ``status``
     - out
     - :ref:`EvrV1StatusType <type-evrv1statustype>`
   * - ``config``
     - in
     - :ref:`EvrV1ConfigType <type-evrv1configtype>`
   * - ``sync``
     - in
     - ``sl``
   * - ``trigOut``
     - out
     - ``slv(11 downto 0)``
   * - ``eventStreamOut``
     - out
     - ``slv(7 downto 0)``
   * - ``evrClk``
     - in
     - ``sl``
   * - ``evrRst``
     - in
     - ``sl``
   * - ``rxLinkUp``
     - in
     - ``sl``
   * - ``rxError``
     - in
     - ``sl``
   * - ``rxData``
     - in
     - ``slv(15 downto 0)``
   * - ``rxDataK``
     - in
     - ``slv(1 downto 0)``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1eventreceiverchannel-v:

EvrV1EventReceiverChannel
-------------------------

File: :repo:`LCLS-I/evr/EvrV1EventReceiverChannel.v`

One LCLS-I EVR pulse channel. When myEvent rises it waits myDelay ticks and then holds the output for myWidth ticks, where a tick is one Clock or, for a myPreScale above 1, myPreScale clocks; a width of 0 gives no pulse and myPolarity sets the active level. setPulse forces the output on and resetPulse forces it off, with setPulse winning, and Reset returns the channel to idle.

Status: simulated; a cocotb test runs the module in Icarus Verilog

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``delayIdle``
     - ``parameter [1:0]``
     - ``2'b00``
   * - ``delayWait``
     - ``parameter [1:0]``
     - ``2'b01``
   * - ``delayOut``
     - ``parameter [1:0]``
     - ``2'b10``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``Clock``
     - in
     - ``wire``
   * - ``Reset``
     - in
     - ``wire``
   * - ``myEvent``
     - in
     - ``wire``
   * - ``myDelay``
     - in
     - ``[31:0]``
   * - ``myWidth``
     - in
     - ``[31:0]``
   * - ``myPolarity``
     - in
     - ``wire``
   * - ``trigger``
     - out
     - ``wire``
   * - ``myPreScale``
     - in
     - ``[31:0]``
   * - ``setPulse``
     - in
     - ``wire``
   * - ``resetPulse``
     - in
     - ``wire``
   * - ``channelDebug``
     - out
     - ``[102:0]``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1heartbeat-vhd:

EvrV1HeartBeat
--------------

File: :repo:`LCLS-I/evr/EvrV1HeartBeat.vhd`

Heartbeat timeout monitor on eventClk. Event code 0x7A reloads a 32-bit counter from uSecDividerReg, any other code lets it count down, and heartBeatTimeOut pulses for one clock when the count reaches 0. With no 0x7A the counter wraps and times out again after 4294967296 clocks, and reset clears the count.

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
   * - ``reset``
     - in
     - ``sl``
   * - ``uSecDividerReg``
     - in
     - ``slv(31 downto 0)``
   * - ``eventCode``
     - in
     - ``slv(7 downto 0)``
   * - ``eventClk``
     - in
     - ``sl``
   * - ``heartBeatTimeOut``
     - out
     - ``sl``

Issues: none

.. _entity-lcls-i-evr-evrv1reg-vhd:

EvrV1Reg
--------

File: :repo:`LCLS-I/evr/EvrV1Reg.vhd`

AXI-Lite register file of the LCLS-I EVR on axiClk. It decodes writes into the EvrV1ConfigType outputs (pulse control, prescale, delay, and width for twelve channels, output map, event RAM windows, interrupt control and clear, data buffer control) and builds reads from the EvrV1StatusType input and the firmware version of BUILD_INFO_G. A read after a reset or a time stamp latch write waits LATCH_TS_LATENCY_G clocks, and unmapped, read-only, or unaligned accesses answer DECERR.

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
   * - ``BUILD_INFO_G``
     - ``BuildInfoType``
     - none
   * - ``USE_WSTRB_G``
     - ``boolean``
     - ``false``
   * - ``LATCH_TS_LATENCY_G``
     - ``natural``
     - ``15``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``irqActive``
     - in
     - ``sl``
   * - ``irqEnable``
     - out
     - ``sl``
   * - ``irqReq``
     - out
     - ``sl``
   * - ``axiReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axiReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``axiWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axiWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``status``
     - in
     - :ref:`EvrV1StatusType <type-evrv1statustype>`
   * - ``config``
     - out
     - :ref:`EvrV1ConfigType <type-evrv1configtype>`
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1timestampfifo-vhd:

EvrV1TimeStampFIFO
------------------

File: :repo:`LCLS-I/evr/EvrV1TimeStampFIFO.vhd`

512 word, 72 bit first-word-fall-through FIFO between two clocks for the LCLS-I EVR time stamped event records, built from a surf FifoAsync. It keeps the first 512 words written and drops a word written into a full FIFO; the port named full is the overflow pulse, high for one cycle after such a write, and both data counts are exposed.

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
   * - ``rst``
     - in
     - ``sl``
   * - ``wr_clk``
     - in
     - ``sl``
   * - ``wr_en``
     - in
     - ``sl``
   * - ``din``
     - in
     - ``slv(71 downto 0)``
   * - ``wr_data_count``
     - out
     - ``slv(8 downto 0)``
   * - ``full``
     - out
     - ``sl``
   * - ``rd_clk``
     - in
     - ``sl``
   * - ``rd_en``
     - in
     - ``sl``
   * - ``dout``
     - out
     - ``slv(71 downto 0)``
   * - ``rd_data_count``
     - out
     - ``slv(8 downto 0)``
   * - ``empty``
     - out
     - ``sl``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1timestampgenerator-v:

EvrV1TimeStampGenerator
-----------------------

File: :repo:`LCLS-I/evr/EvrV1TimeStampGenerator.v`

Free-running 64-bit time stamp for the LCLS-I EVR in a single Clock domain. TimeStamp counts up by 1 on every Clock, and every 330556 clocks a reload puts the seconds counter in bits 63:32 and clears the low word while the seconds counter increments. Reset clears the seconds counter, the reload counter, and TimeStamp.

Status: simulated; a cocotb test runs the module in Icarus Verilog

.. rubric:: Generics

none

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``Clock``
     - in
     - ``wire``
   * - ``Reset``
     - in
     - ``wire``
   * - ``TimeStamp``
     - out
     - ``[63:0]``

Issues: issue pending

.. _entity-lcls-i-evr-evrv1timeofdayreceiver-v:

EvrV1TimeofDayReceiver
----------------------

File: :repo:`LCLS-I/evr/EvrV1TimeofDayReceiver.v`

Receives the LCLS-I time of day from the event stream. Each 0x70 or 0x71 event code shifts a 0 or 1 into a 32-bit seconds word, most significant bit first, and the 0x7D code latches the word into bits 63:32 of TimeStamp with the low word cleared, after which TimeStamp counts up by 1 each clock. secondsShift shows the word as it arrives, and Reset clears the seconds, the bit pointer, and TimeStamp.

Status: simulated; a cocotb test runs the module in Icarus Verilog

.. rubric:: Generics

none

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``Clock``
     - in
     - ``wire``
   * - ``Reset``
     - in
     - ``wire``
   * - ``EventStream``
     - in
     - ``[7:0]``
   * - ``TimeStamp``
     - out
     - ``[63:0]``
   * - ``timeDebug``
     - out
     - ``[36:0]``
   * - ``secondsShift``
     - out
     - ``[31:0]``

Issues: issue pending
