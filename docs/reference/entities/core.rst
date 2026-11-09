LCLS-II core
============

:repo:`LCLS-II/core/ruckus.tcl` loads these sources into the ``lcls_timing_core`` library; a file that is not loaded says so in the Status column.

.. list-table::
   :header-rows: 1
   :widths: 20 40 25 15

   * - Entity
     - File
     - Status
     - Issues
   * - :ref:`BsaControl <entity-lcls-ii-core-rtl-bsacontrol-vhd>`
     - :repo:`LCLS-II/core/rtl/BsaControl.vhd`
     - not simulated: not loaded by any ruckus.tcl
     - issue pending
   * - :ref:`BsaControl <entity-lcls-ii-core-rtl-bsacontrolv2-vhd>`
     - :repo:`LCLS-II/core/rtl/BsaControlv2.vhd`
     - simulated
     - none
   * - :ref:`ClockTime <entity-lcls-ii-core-rtl-clocktime-vhd>`
     - :repo:`LCLS-II/core/rtl/ClockTime.vhd`
     - simulated
     - none
   * - :ref:`ClockTime_186MHz <entity-lcls-ii-core-rtl-clocktime-186mhz-vhd>`
     - :repo:`LCLS-II/core/rtl/ClockTime_186MHz.vhd`
     - not simulated: not loaded by any ruckus.tcl
     - issue pending
   * - :ref:`CtrControl <entity-lcls-ii-core-rtl-ctrcontrol-vhd>`
     - :repo:`LCLS-II/core/rtl/CtrControl.vhd`
     - simulated
     - issue pending
   * - :ref:`Divider <entity-lcls-ii-core-rtl-divider-vhd>`
     - :repo:`LCLS-II/core/rtl/Divider.vhd`
     - simulated
     - none
   * - :ref:`EthTimingModule <entity-lcls-ii-core-rtl-ethtimingmodule-vhd>`
     - :repo:`LCLS-II/core/rtl/EthTimingModule.vhd`
     - simulated
     - issue pending
   * - :ref:`EventSelect <entity-lcls-ii-core-rtl-eventselect-vhd>`
     - :repo:`LCLS-II/core/rtl/EventSelect.vhd`
     - simulated
     - none
   * - :ref:`GthRxAlignCheck <entity-lcls-ii-core-rtl-gthrxaligncheck-vhd>`
     - :repo:`LCLS-II/core/rtl/GthRxAlignCheck.vhd`
     - simulated
     - none
   * - :ref:`TPFifo <entity-lcls-ii-core-rtl-tpfifo-vhd>`
     - :repo:`LCLS-II/core/rtl/TPFifo.vhd`
     - not simulated: not loaded by any ruckus.tcl
     - issue pending
   * - :ref:`TPGMini <entity-lcls-ii-core-rtl-tpgmini-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGMini.vhd`
     - simulated
     - issue pending
   * - :ref:`TPGMiniCore <entity-lcls-ii-core-rtl-tpgminicore-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGMiniCore.vhd`
     - baseline-excluded
     - issue pending, issue pending
   * - :ref:`TPGMiniEdef <entity-lcls-ii-core-rtl-tpgminiedef-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGMiniEdef.vhd`
     - simulated
     - issue pending
   * - :ref:`TPGMiniEdefTb <entity-lcls-ii-core-rtl-tpgminiedeftb-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGMiniEdefTb.vhd`
     - simulated
     - issue pending, issue pending
   * - :ref:`TPGMiniReg <entity-lcls-ii-core-rtl-tpgminireg-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGMiniReg.vhd`
     - baseline-excluded
     - issue pending, issue pending
   * - :ref:`TPGMiniStream <entity-lcls-ii-core-rtl-tpgministream-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGMiniStream.vhd`
     - simulated
     - none
   * - :ref:`TPGNotify <entity-lcls-ii-core-rtl-tpgnotify-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGNotify.vhd`
     - not simulated: not loaded by any ruckus.tcl
     - issue pending, issue pending
   * - :ref:`TPSerializer <entity-lcls-ii-core-rtl-tpserializer-vhd>`
     - :repo:`LCLS-II/core/rtl/TPSerializer.vhd`
     - simulated
     - none
   * - :ref:`TimingCore <entity-lcls-ii-core-rtl-timingcore-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingCore.vhd`
     - baseline-excluded
     - issue pending, issue pending
   * - :ref:`TimingDeserializer <entity-lcls-ii-core-rtl-timingdeserializer-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingDeserializer.vhd`
     - simulated
     - issue pending
   * - :ref:`TimingFrameRx <entity-lcls-ii-core-rtl-timingframerx-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingFrameRx.vhd`
     - simulated
     - issue pending
   * - :ref:`TimingGthWrapper <entity-lcls-ii-core-rtl-timinggthwrapper-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingGthWrapper.vhd`
     - baseline-excluded
     - issue pending, issue pending, issue pending
   * - :ref:`TimingMsgAxiRingBuffer <entity-lcls-ii-core-rtl-timingmsgaxiringbuffer-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingMsgAxiRingBuffer.vhd`
     - simulated
     - issue pending
   * - :ref:`TimingMsgDelay <entity-lcls-ii-core-rtl-timingmsgdelay-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingMsgDelay.vhd`
     - simulated
     - issue pending
   * - :ref:`TimingMsgToAxiStream <entity-lcls-ii-core-rtl-timingmsgtoaxistream-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingMsgToAxiStream.vhd`
     - simulated
     - none
   * - :ref:`TimingRx <entity-lcls-ii-core-rtl-timingrx-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingRx.vhd`
     - simulated
     - none
   * - :ref:`TimingSerialDelay <entity-lcls-ii-core-rtl-timingserialdelay-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingSerialDelay.vhd`
     - simulated
     - none
   * - :ref:`TimingSerializer <entity-lcls-ii-core-rtl-timingserializer-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingSerializer.vhd`
     - simulated
     - none
   * - :ref:`TimingStreamRx <entity-lcls-ii-core-rtl-timingstreamrx-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingStreamRx.vhd`
     - simulated
     - none
   * - :ref:`TimingStreamTx <entity-lcls-ii-core-rtl-timingstreamtx-vhd>`
     - :repo:`LCLS-II/core/rtl/TimingStreamTx.vhd`
     - simulated
     - issue pending
   * - :ref:`WordSerializer <entity-lcls-ii-core-rtl-wordserializer-vhd>`
     - :repo:`LCLS-II/core/rtl/WordSerializer.vhd`
     - simulated
     - none
   * - :ref:`TimingSerialDelayTb <entity-lcls-ii-core-tb-timingserialdelay-tb-vhd>`
     - :repo:`LCLS-II/core/tb/TimingSerialDelay_tb.vhd`
     - simulated
     - issue pending

Package files in this tree: :repo:`LCLS-II/core/rtl/TPGMiniEdefPkg.vhd`, :repo:`LCLS-II/core/rtl/TPGPkg.vhd`, :repo:`LCLS-II/core/rtl/TimingPkg.vhd`, :repo:`LCLS-II/core/rtl/default/TimingExtnPkg.vhd`.

.. _entity-lcls-ii-core-rtl-bsacontrol-vhd:

BsaControl (LCLS-II/core/rtl/BsaControl.vhd)
--------------------------------------------

File: :repo:`LCLS-II/core/rtl/BsaControl.vhd`

Older definition of the entity BsaControl, the acquisition state of one BSA definition: it counts active cycles down from nToAvg and averages down from avgToWr, and treats an avgToWr of 0 as persist, as observed, intent unconfirmed. It has no tmo and tmocnt timeout inputs and no ruckus.tcl loads it, so the definition in use for this entity is BsaControlv2.vhd.

Status: not simulated: not loaded by any ruckus.tcl; declares entity BsaControl, which the loaded BsaControlv2.vhd also declares; TPGMini.vhd instantiates the loaded one

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
   * - ``ASYNC_REGCLK_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``sysclk``
     - in
     - ``sl``
   * - ``sysrst``
     - in
     - ``sl``
   * - ``bsadef``
     - in
     - ``BsaDefType``
   * - ``nToAvgOut``
     - out
     - ``slv(15 downto 0)``
   * - ``avgToWrOut``
     - out
     - ``slv(15 downto 0)``
   * - ``txclk``
     - in
     - ``sl``
   * - ``txrst``
     - in
     - ``sl``
   * - ``enable``
     - in
     - ``sl``
   * - ``fixedRate``
     - in
     - ``slv(FIXEDRATEDEPTH - 1 downto 0)``
   * - ``acRate``
     - in
     - ``slv(ACRATEDEPTH - 1 downto 0)``
   * - ``acTS``
     - in
     - ``slv(2 downto 0)``
   * - ``beamSeq``
     - in
     - ``slv(31 downto 0)``
   * - ``expSeq``
     - in
     - ``Slv16Array(0 to 17)``
   * - ``bsaInit``
     - out
     - ``sl``
   * - ``bsaActive``
     - out
     - ``sl``
   * - ``bsaAvgDone``
     - out
     - ``sl``
   * - ``bsaDone``
     - out
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-bsacontrolv2-vhd:

BsaControl (LCLS-II/core/rtl/BsaControlv2.vhd)
----------------------------------------------

File: :repo:`LCLS-II/core/rtl/BsaControlv2.vhd`

Acquisition state of one BSA definition in the txclk domain: after the bsadef init input rises while enabled it pulses bsaInit, then drives bsaActive while the selected rate and destination match, bsaAvgDone at each average boundary set by nToAvg, and bsaDone after avgToWr averages, or never when avgToWr is 0xFFFF. The nToAvgOut and avgToWrOut status outputs count up, and the optional tmo and tmocnt inputs can assert bsaDone after an average. This is the definition of entity BsaControl that ruckus loads.

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
   * - ``ASYNC_REGCLK_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``sysclk``
     - in
     - ``sl``
   * - ``sysrst``
     - in
     - ``sl``
   * - ``bsadef``
     - in
     - ``BsaDefType``
   * - ``tmo``
     - in
     - ``sl``
   * - ``tmocnt``
     - in
     - ``slv(3 downto 0)``
   * - ``nToAvgOut``
     - out
     - ``slv(15 downto 0)``
   * - ``avgToWrOut``
     - out
     - ``slv(15 downto 0)``
   * - ``txclk``
     - in
     - ``sl``
   * - ``txrst``
     - in
     - ``sl``
   * - ``enable``
     - in
     - ``sl``
   * - ``fixedRate``
     - in
     - ``slv(FIXEDRATEDEPTH - 1 downto 0)``
   * - ``acRate``
     - in
     - ``slv(ACRATEDEPTH - 1 downto 0)``
   * - ``acTS``
     - in
     - ``slv(2 downto 0)``
   * - ``beamSeq``
     - in
     - ``slv(31 downto 0)``
   * - ``expSeq``
     - in
     - ``Slv16Array(0 to 17)``
   * - ``bsaInit``
     - out
     - ``sl``
   * - ``bsaActive``
     - out
     - ``sl``
   * - ``bsaAvgDone``
     - out
     - ``sl``
   * - ``bsaDone``
     - out
     - ``sl``

Issues: none

.. _entity-lcls-ii-core-rtl-clocktime-vhd:

ClockTime
---------

File: :repo:`LCLS-II/core/rtl/ClockTime.vhd`

Free-running 64-bit time counter in the clkB domain, with nanoseconds in the low word and seconds in the high word. Each clkB cycle adds step nanoseconds, plus one more on the cycles where the fractional remainder (remainder over divisor) overflows, so the defaults advance 5 and 5/13 ns (1300/7 MHz). A time written on clkA with wrEnA crosses through a FIFO and loads when wrEnB is high, and wrEnB also copies the current time back to clkA as rdData.

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
   * - ``FRACTION_DEPTH_G``
     - ``integer``
     - ``5``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``step``
     - in
     - ``slv(4 downto 0)``
   * - ``remainder``
     - in
     - ``slv(FRACTION_DEPTH_G - 1 downto 0)``
   * - ``divisor``
     - in
     - ``slv(FRACTION_DEPTH_G - 1 downto 0)``
   * - ``rst``
     - in
     - ``sl``
   * - ``clkA``
     - in
     - ``sl``
   * - ``wrEnA``
     - in
     - ``sl``
   * - ``wrData``
     - in
     - ``slv(63 downto 0)``
   * - ``rdData``
     - out
     - ``slv(63 downto 0)``
   * - ``clkB``
     - in
     - ``sl``
   * - ``wrEnB``
     - in
     - ``sl``
   * - ``dataO``
     - out
     - ``slv(63 downto 0)``

Issues: none

.. _entity-lcls-ii-core-rtl-clocktime-186mhz-vhd:

ClockTime_186MHz
----------------

File: :repo:`LCLS-II/core/rtl/ClockTime_186MHz.vhd`

Same time counter as ClockTime with the step fixed at 5 and 5/13 ns (1300/7 MHz) instead of taken from inputs. No ruckus.tcl loads it and nothing else in the repository instantiates it.

Status: not simulated: not loaded by any ruckus.tcl; no file in the repository instantiates ClockTime_186MHz

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
   * - ``clkA``
     - in
     - ``sl``
   * - ``wrEnA``
     - in
     - ``sl``
   * - ``wrData``
     - in
     - ``slv(63 downto 0)``
   * - ``rdData``
     - out
     - ``slv(63 downto 0)``
   * - ``clkB``
     - in
     - ``sl``
   * - ``wrEnB``
     - in
     - ``sl``
   * - ``dataO``
     - out
     - ``slv(63 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-ctrcontrol-vhd:

CtrControl
----------

File: :repo:`LCLS-II/core/rtl/CtrControl.vhd`

Counter of the txclk cycles, while enabled, in which the rate selected by ctrdef through EventSelect is set and the destination mask of ctrdef matches the beam destination, using the same destination test as BsaControl. A rising edge of ctrrst latches the count to the count output and restarts it at 0, and as observed a qualifying cycle on the latch edge is not counted, intent unconfirmed.

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
   * - ``ASYNC_REGCLK_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``sysclk``
     - in
     - ``sl``
   * - ``sysrst``
     - in
     - ``sl``
   * - ``ctrdef``
     - in
     - ``CtrDefType``
   * - ``ctrrst``
     - in
     - ``sl``
   * - ``txclk``
     - in
     - ``sl``
   * - ``txrst``
     - in
     - ``sl``
   * - ``enable``
     - in
     - ``sl``
   * - ``fixedRate``
     - in
     - ``slv(FIXEDRATEDEPTH - 1 downto 0)``
   * - ``acRate``
     - in
     - ``slv(ACRATEDEPTH - 1 downto 0)``
   * - ``acTS``
     - in
     - ``slv(2 downto 0)``
   * - ``beamSeq``
     - in
     - ``slv(31 downto 0)``
   * - ``expSeq``
     - in
     - ``Slv16Array(0 to 17)``
   * - ``count``
     - out
     - ``slv(31 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-divider-vhd:

Divider
-------

File: :repo:`LCLS-II/core/rtl/Divider.vhd`

Prescaler that raises trigO for one sysClk cycle every divisor cycles while enable is high, counting from 1 up to divisor and restarting at 1. Holding enable low freezes the count and the trigO level, clear with enable low forces trigO low, and sysReset restarts the count at 1 and drops trigO. A divisor of 0 never matches until the Width-bit counter wraps, so at the default Width of 4 the period is 16 cycles.

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
   * - ``Width``
     - ``integer``
     - ``4``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``sysClk``
     - in
     - ``std_logic``
   * - ``sysReset``
     - in
     - ``std_logic``
   * - ``enable``
     - in
     - ``std_logic``
   * - ``clear``
     - in
     - ``std_logic``
   * - ``divisor``
     - in
     - ``std_logic_vector(Width - 1 downto 0)``
   * - ``trigO``
     - out
     - ``std_logic``

Issues: none

.. _entity-lcls-ii-core-rtl-ethtimingmodule-vhd:

EthTimingModule
---------------

File: :repo:`LCLS-II/core/rtl/EthTimingModule.vhd`

With STREAM_L1_G true, copies the 704 bit LCLS-I timing stream into an AXI- Stream frame on each timingStrobe and passes it to ethClk through a FIFO, but only while a timeout flag is clear. The flag starts set and clears on the first inbound beat on ibEthMsgMaster, and the RTL sets it again after 2^29 ethClk cycles without one. With STREAM_L1_G false the module only holds the inbound slave ready.

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
   * - ``STREAM_L1_G``
     - ``boolean``
     - ``false``
   * - ``BUILD_ILA_G``
     - ``boolean``
     - ``false``
   * - ``ETHMSG_AXIS_CFG_G``
     - ``AxiStreamConfigType``
     - ``AXI_STREAM_CONFIG_INIT_C``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``timingClk``
     - in
     - ``sl``
   * - ``timingRst``
     - in
     - ``sl``
   * - ``timingStrobe``
     - in
     - ``sl``
   * - ``timingStream``
     - in
     - ``TimingStreamType``
   * - ``ethClk``
     - in
     - ``sl``
   * - ``ethRst``
     - in
     - ``sl``
   * - ``ibEthMsgMaster``
     - in
     - ``AxiStreamMasterType``
   * - ``ibEthMsgSlave``
     - out
     - ``AxiStreamSlaveType``
   * - ``obEthMsgMaster``
     - out
     - ``AxiStreamMasterType``
   * - ``obEthMsgSlave``
     - in
     - ``AxiStreamSlaveType``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-eventselect-vhd:

EventSelect
-----------

File: :repo:`LCLS-II/core/rtl/EventSelect.vhd`

Picks one bit of the timing pattern for a definition, by rateType. Type 00 takes fixedRate indexed by fxRateSel, type 01 takes acRate indexed by acRateSel when the acTSmask bit of the current time slot is set, type 10 takes bit seqbit of the registered expSeq word chosen by seqword (zero from word 18 up), and type 11 gives 0.

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
   * - ``rateType``
     - in
     - ``slv(1 downto 0)``
   * - ``fxRateSel``
     - in
     - ``slv(3 downto 0)``
   * - ``acRateSel``
     - in
     - ``slv(2 downto 0)``
   * - ``acTSmask``
     - in
     - ``slv(5 downto 0)``
   * - ``seqword``
     - in
     - ``slv(5 downto 0)``
   * - ``seqbit``
     - in
     - ``slv(4 downto 0)``
   * - ``fixedRate``
     - in
     - ``slv(FIXEDRATEDEPTH - 1 downto 0)``
   * - ``acRate``
     - in
     - ``slv(ACRATEDEPTH - 1 downto 0)``
   * - ``acTS``
     - in
     - ``slv(2 downto 0)``
   * - ``expSeq``
     - in
     - ``Slv16Array(0 to 17)``
   * - ``rateSel``
     - out
     - ``sl``

Issues: none

.. _entity-lcls-ii-core-rtl-gthrxaligncheck-vhd:

GthRxAlignCheck
---------------

File: :repo:`LCLS-II/core/rtl/GthRxAlignCheck.vhd`

Checks the comma alignment latency of a GT receiver. After resetDone it reads the DRP latency register through an AXI-Lite master, locks when the low seven bits match the target under the mask, and otherwise pulses resetOut and reads again, counting every value in a 40 entry histogram that an AXI-Lite slave block exposes with the target, mask, last value, and clock frequencies. As observed, a latency of 40 or more indexes past the histogram and stops the simulator, intent unconfirmed.

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
   * - ``GT_TYPE_G``
     - ``string``
     - ``"GTHE3"``
   * - ``DRP_ADDR_G``
     - ``slv(31 downto 0)``
     - none

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``txClk``
     - in
     - ``sl``
   * - ``rxClk``
     - in
     - ``sl``
   * - ``resetIn``
     - in
     - ``sl``
   * - ``resetOut``
     - out
     - ``sl``
   * - ``resetDone``
     - in
     - ``sl``
   * - ``resetErr``
     - in
     - ``sl``
   * - ``locked``
     - out
     - ``sl``
   * - ``axilClk``
     - in
     - ``sl``
   * - ``axilRst``
     - in
     - ``sl``
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
   * - ``sAxilReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``sAxilReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``sAxilWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``sAxilWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``

Issues: none

.. _entity-lcls-ii-core-rtl-tpfifo-vhd:

TPFifo
------

File: :repo:`LCLS-II/core/rtl/TPFifo.vhd`

Caches timing message words in a delay RAM and, when the trig input selects a ready word at a start of frame, copies that frame into an asynchronous FIFO read on rdClk, preceded by a word holding the mask wsel. Words are kept only where the wsel bit indexed by wrDataWord is set, and the full flag latches until rst. No ruckus.tcl loads it and nothing else in the repository instantiates it.

Status: not simulated: not loaded by any ruckus.tcl; no file in the repository instantiates TPFifo

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
   * - ``LOGDEPTH``
     - ``integer``
     - ``10``

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
   * - ``wrClk``
     - in
     - ``sl``
   * - ``sof``
     - in
     - ``sl``
   * - ``eof``
     - in
     - ``sl``
   * - ``wrData``
     - in
     - ``slv(15 downto 0)``
   * - ``wrDataWord``
     - in
     - ``slv(3 downto 0)``
   * - ``trig``
     - in
     - ``slv(11 downto 0)``
   * - ``wsel``
     - in
     - ``slv(15 downto 0)``
   * - ``rdClk``
     - in
     - ``sl``
   * - ``rdEn``
     - in
     - ``sl``
   * - ``rdData``
     - out
     - ``slv(31 downto 0)``
   * - ``full``
     - out
     - ``sl``
   * - ``empty``
     - out
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-tpgmini-vhd:

TPGMini
-------

File: :repo:`LCLS-II/core/rtl/TPGMini.vhd`

Generates LCLS-II timing frames. A base-rate divider paces the frames and increments the pulse ID, fixed-rate dividers and one BsaControl per definition fill the TimingMessageType frame, and TPSerializer and TimingSerializer send it on txData and txDataK with a CRC. It also keeps the status counters that TPGMiniReg reads, and the STREAM_INTF generic hands the frame out as a stream instead.

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
   * - ``NARRAYSBSA``
     - ``integer``
     - ``2``
   * - ``STREAM_INTF``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``statusO``
     - out
     - ``TPGStatusType``
   * - ``configI``
     - in
     - ``TPGConfigType``
   * - ``txClk``
     - in
     - ``sl``
   * - ``txRst``
     - in
     - ``sl``
   * - ``txRdy``
     - in
     - ``sl``
   * - ``txData``
     - out
     - ``slv(15 downto 0)``
   * - ``txDataK``
     - out
     - ``slv(1 downto 0)``
   * - ``streams``
     - out
     - ``TimingSerialArray(0 downto 0)``
   * - ``streamIds``
     - out
     - ``Slv4Array(0 downto 0)``
   * - ``advance``
     - in
     - ``slv(0 downto 0)``
   * - ``fiducial``
     - out
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-tpgminicore-vhd:

TPGMiniCore
-----------

File: :repo:`LCLS-II/core/rtl/TPGMiniCore.vhd`

Top level of the mini pattern generator. It crosses the AXI-Lite port to txClk, instantiates TPGMiniReg for the registers, TPGMini for the LCLS-II frame on txData(1), and TPGMiniStream for the LCLS-I stream on txData(0), and passes txResetO, txLoopback, txInhibit, and txPolarity through from the register block. GHDL cannot analyze it because TPGMiniReg fails first, so its registers are checked through the PyRogue model and the register drift check.

Status: baseline-excluded; GHDL analysis reports "not locally static", which the regression records as a known failure

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
   * - ``NARRAYSBSA``
     - ``natural``
     - ``1``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``txClk``
     - in
     - ``sl``
   * - ``txRst``
     - in
     - ``sl``
   * - ``txRdy``
     - in
     - ``sl``
   * - ``txData``
     - out
     - ``Slv16Array(1 downto 0)``
   * - ``txDataK``
     - out
     - ``Slv2Array(1 downto 0)``
   * - ``txPolarity``
     - out
     - ``sl``
   * - ``txResetO``
     - out
     - ``sl``
   * - ``txLoopback``
     - out
     - ``slv(2 downto 0)``
   * - ``txInhibit``
     - out
     - ``sl``
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

Issues: issue pending, issue pending

.. _entity-lcls-ii-core-rtl-tpgminiedef-vhd:

TPGMiniEdef
-----------

File: :repo:`LCLS-II/core/rtl/TPGMiniEdef.vhd`

One event definition of the mini generator. When cnfg.wrEn is set for its EDEF_G number while it is idle, it latches navg, nsmp, rate, slot, and sevr, pulses init, and becomes active. While active it counts strb pulses into averages of navg and nsmp samples, raising avgD on each average and allD on the last, with its state advancing only on cen, and smin and smaj carry the severity bits.

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
   * - ``EDEF_G``
     - ``EdefType``
     - ``(others => '0')``

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
   * - ``cen``
     - in
     - ``sl``
   * - ``strb``
     - in
     - ``sl``
   * - ``cnfg``
     - in
     - ``TPGMiniEdefConfigType``
   * - ``actv``
     - out
     - ``sl``
   * - ``avgD``
     - out
     - ``sl``
   * - ``allD``
     - out
     - ``sl``
   * - ``init``
     - out
     - ``sl``
   * - ``smin``
     - out
     - ``sl``
   * - ``smaj``
     - out
     - ``sl``
   * - ``rate``
     - out
     - ``EdefRateType``
   * - ``slot``
     - out
     - ``EdefTSType``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-tpgminiedeftb-vhd:

TPGMiniEdefTb
-------------

File: :repo:`LCLS-II/core/rtl/TPGMiniEdefTb.vhd`

Port-less testbench for TPGMiniStream. It runs a 100 ns clock, releases reset after 4 cycles, writes one event definition (navg 2, nsmp 1, rate 1, slot 2) at cycle 40, prints a trace of the timeslot and event definition flags, and stops itself after 1600 cycles. It has no assertions.

Status: simulated

.. rubric:: Generics

none

.. rubric:: Ports

none

Issues: issue pending, issue pending

.. _entity-lcls-ii-core-rtl-tpgminireg-vhd:

TPGMiniReg
----------

File: :repo:`LCLS-II/core/rtl/TPGMiniReg.vhd`

AXI-Lite register block of TPGMiniCore. It decodes the clock select, base divisor, fixed rate, pulse ID, timestamp, interval, and BSA definition registers into the TPGConfigType and TPGMiniEdefConfigType outputs, returns TPGStatusType counters on reads, and drives txReset, txLoopback, and txInhibit, while irqEnable and irqReq are tied low. GHDL cannot analyze this file, so its registers are checked through the PyRogue model and the register drift check.

Status: baseline-excluded; GHDL analysis reports "not locally static", which the regression records as a known failure

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
   * - ``NARRAYS_BSA``
     - ``integer``
     - ``1``
   * - ``USE_WSTRB_G``
     - ``boolean``
     - ``false``

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
     - ``TPGStatusType``
   * - ``config``
     - out
     - ``TPGConfigType``
   * - ``edefConfig``
     - out
     - ``TPGMiniEdefConfigType``
   * - ``txReset``
     - out
     - ``sl``
   * - ``txLoopback``
     - out
     - ``slv(2 downto 0)``
   * - ``txInhibit``
     - out
     - ``sl``
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``

Issues: issue pending, issue pending

.. _entity-lcls-ii-core-rtl-tpgministream-vhd:

TPGMiniStream
-------------

File: :repo:`LCLS-II/core/rtl/TPGMiniStream.vhd`

Generates the LCLS-I timing stream for the mini generator. A base-rate divider and fixed-rate dividers drive the event codes, the pulse ID (which wraps at 0x1FFDF), the time slot, a ClockTime timestamp, and NUM_EDEFS TPGMiniEdef blocks, and TimingStreamTx sends them as event code and data buffer bytes on txData and txDataK. The simData, simEvents, and simStrobe outputs expose the same data to simulation.

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
   * - ``AC_PERIOD``
     - ``integer``
     - ``200 * 1666``
   * - ``NUM_EDEFS``
     - ``natural``
     - ``4``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``config``
     - in
     - ``TPGConfigType``
   * - ``edefConfig``
     - in
     - ``TPGMiniEdefConfigType``
   * - ``txClk``
     - in
     - ``sl``
   * - ``txRst``
     - in
     - ``sl``
   * - ``txRdy``
     - in
     - ``sl``
   * - ``txData``
     - out
     - ``slv(15 downto 0)``
   * - ``txDataK``
     - out
     - ``slv(1 downto 0)``
   * - ``simData``
     - out
     - ``TimingDataBuffType``
   * - ``simEvents``
     - out
     - ``slv(69 downto 0)``
   * - ``simStrobe``
     - out
     - ``sl``

Issues: none

.. _entity-lcls-ii-core-rtl-tpgnotify-vhd:

TPGNotify
---------

File: :repo:`LCLS-II/core/rtl/TPGNotify.vhd`

Interrupt notifier for the pattern generator. When irqEnable and irqReq are both high, synchronized to txClk, it counts the event and presents a one word AXI-Stream message with the 32 bit count and tDest 0xFF. As observed, nothing in the file clears tValid once it is set, intent unconfirmed, and no ruckus.tcl loads it.

Status: not simulated: not loaded by any ruckus.tcl; no file in the repository instantiates TPGNotify

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
   * - ``txClk``
     - in
     - ``sl``
   * - ``txRst``
     - in
     - ``sl``
   * - ``irqReq``
     - in
     - ``sl``
   * - ``irqEnable``
     - in
     - ``sl``
   * - ``obDebugMaster``
     - out
     - ``AxiStreamMasterType``

Issues: issue pending, issue pending

.. _entity-lcls-ii-core-rtl-tpserializer-vhd:

TPSerializer
------------

File: :repo:`LCLS-II/core/rtl/TPSerializer.vhd`

Latches the 944 bit TimingMessageType on fiducial and shifts it out as 59 16-bit words, least significant word first, on a TimingSerialType stream that TimingSerializer pulls with advance. The Id generic is returned as the streamId of the segment.

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
   * - ``Id``
     - ``integer``
     - ``0``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``txClk``
     - in
     - ``sl``
   * - ``txRst``
     - in
     - ``sl``
   * - ``fiducial``
     - in
     - ``sl``
   * - ``msg``
     - in
     - ``TimingMessageType``
   * - ``advance``
     - in
     - ``sl``
   * - ``stream``
     - out
     - ``TimingSerialType``
   * - ``streamId``
     - out
     - ``slv(3 downto 0)``

Issues: none

.. _entity-lcls-ii-core-rtl-timingcore-vhd:

TimingCore
----------

File: :repo:`LCLS-II/core/rtl/TimingCore.vhd`

Family-agnostic timing receiver around the GT interface. An AXI-Lite crossbar serves TimingRx at offset 0x00000, ring buffers of the raw GT words at 0x10000 and of the decoded messages at 0x20000 (present when AXIL_RINGB_G is true), and TPGMiniCore at 0x30000. It passes either the LCLS-I stream or the LCLS-II message to appTimingBus on appTimingClk according to the selected mode, and adds EthTimingModule when STREAM_L1_G is true.

Status: baseline-excluded; GHDL analysis reports "not locally static", which the regression records as a known failure

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
   * - ``DEFAULT_CLK_SEL_G``
     - ``sl``
     - ``'1'``
   * - ``CLKSEL_MODE_G``
     - ``string``
     - ``"SELECT"``
   * - ``TPGEN_G``
     - ``boolean``
     - ``false``
   * - ``STREAM_L1_G``
     - ``boolean``
     - ``false``
   * - ``ETHMSG_AXIS_CFG_G``
     - ``AxiStreamConfigType``
     - ``EMAC_AXIS_CONFIG_C``
   * - ``AXIL_RINGB_G``
     - ``boolean``
     - ``true``
   * - ``ASYNC_G``
     - ``boolean``
     - ``true``
   * - ``AXIL_BASE_ADDR_G``
     - ``slv(31 downto 0)``
     - ``(others => '0')``
   * - ``USE_TPGMINI_G``
     - ``boolean``
     - ``true``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``gtTxUsrClk``
     - in
     - ``sl``
   * - ``gtTxUsrRst``
     - in
     - ``sl``
   * - ``gtRxRecClk``
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
   * - ``gtRxControl``
     - out
     - ``TimingPhyControlType``
   * - ``gtRxStatus``
     - in
     - ``TimingPhyStatusType``
   * - ``gtTxReset``
     - out
     - ``sl``
   * - ``gtLoopback``
     - out
     - ``slv(2 downto 0)``
   * - ``tpgMiniTimingPhy``
     - out
     - ``TimingPhyType``
   * - ``timingClkSel``
     - out
     - ``sl``
   * - ``appTimingClk``
     - in
     - ``sl``
   * - ``appTimingRst``
     - in
     - ``sl``
   * - ``appTimingBus``
     - out
     - ``TimingBusType``
   * - ``appTimingMode``
     - out
     - ``sl``
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
   * - ``ibEthMsgMaster``
     - in
     - ``AxiStreamMasterType``
   * - ``ibEthMsgSlave``
     - out
     - ``AxiStreamSlaveType``
   * - ``obEthMsgMaster``
     - out
     - ``AxiStreamMasterType``
   * - ``obEthMsgSlave``
     - in
     - ``AxiStreamSlaveType``

Issues: issue pending, issue pending

.. _entity-lcls-ii-core-rtl-timingdeserializer-vhd:

TimingDeserializer
------------------

File: :repo:`LCLS-II/core/rtl/TimingDeserializer.vhd`

Receives the 16-bit character stream of a timing link. A K23.7 start of frame opens a frame, each segment header routes its words to the stream with the matching streamId (words for an unknown id are sunk), K28.0 ends a segment, and K29.7 followed by two CRC words ends the frame. It outputs fiducial, sof, and eof strobes and raises crcErr when the received CRC32 differs from the one it computed.

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
   * - ``STREAMS_C``
     - ``integer``
     - ``1``

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
   * - ``fiducial``
     - out
     - ``sl``
   * - ``streams``
     - out
     - ``TimingSerialArray(STREAMS_C - 1 downto 0)``
   * - ``streamIds``
     - in
     - ``Slv4Array(STREAMS_C - 1 downto 0)``
   * - ``advance``
     - out
     - ``slv(STREAMS_C - 1 downto 0)``
   * - ``data``
     - in
     - ``TimingRxType``
   * - ``sof``
     - out
     - ``sl``
   * - ``eof``
     - out
     - ``sl``
   * - ``crcErr``
     - out
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-timingframerx-vhd:

TimingFrameRx
-------------

File: :repo:`LCLS-II/core/rtl/TimingFrameRx.vhd`

LCLS-II receiver front end. TimingDeserializer splits the character stream into 16 segment streams, a TimingSerialDelay delays the 944 bit message on stream 0 by messageDelay clocks onto timingMessage with a strobe, and one more per stream 1 to 15 delivers the extension messages. A message version other than 1 is flagged on staData and rxVersion and lowers timingMessageValid, which as observed settles one cycle after the strobe, intent unconfirmed.

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
   * - ``rxClk``
     - in
     - ``sl``
   * - ``rxRst``
     - in
     - ``sl``
   * - ``rxData``
     - in
     - ``TimingRxType``
   * - ``messageDelay``
     - in
     - ``slv(19 downto 0)``
   * - ``messageDelayRst``
     - in
     - ``sl``
   * - ``timingMessage``
     - out
     - ``TimingMessageType``
   * - ``timingMessageStrobe``
     - out
     - ``sl``
   * - ``timingMessageValid``
     - out
     - ``sl``
   * - ``timingExtension``
     - out
     - ``TimingExtensionArray``
   * - ``rxVersion``
     - out
     - ``slv(31 downto 0)``
   * - ``staData``
     - out
     - ``slv(4 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-timinggthwrapper-vhd:

TimingGthWrapper
----------------

File: :repo:`LCLS-II/core/rtl/TimingGthWrapper.vhd`

Wraps the TimingGth transceiver IP as a timing receive link: it passes the reference clock, the differential receive pair, and txInhibit to the IP, drives the transmit data to zero, and returns the recovered clock, receive data, K flags, disparity and decode errors, and the receive reset done. The IP is declared as a component and is not part of this repository, and no ruckus.tcl loads the file.

Status: baseline-excluded; GHDL analysis reports "no declaration for "ieee"", which the regression records as a known failure

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
   * - ``stableClk``
     - in
     - ``sl``
   * - ``gtRefClk``
     - in
     - ``sl``
   * - ``gtRxP``
     - in
     - ``sl``
   * - ``gtRxN``
     - in
     - ``sl``
   * - ``gtTxP``
     - out
     - ``sl``
   * - ``gtTxN``
     - out
     - ``sl``
   * - ``txInhibit``
     - in
     - ``sl``
   * - ``rxRecClk``
     - out
     - ``sl``
   * - ``rxUsrClk``
     - in
     - ``sl``
   * - ``rxReset``
     - in
     - ``sl``
   * - ``rxRstDone``
     - out
     - ``sl``
   * - ``rxData``
     - out
     - ``slv(15 downto 0)``
   * - ``rxDataK``
     - out
     - ``slv(1 downto 0)``
   * - ``rxDispErr``
     - out
     - ``slv(1 downto 0)``
   * - ``rxDecErr``
     - out
     - ``slv(1 downto 0)``

Issues: issue pending, issue pending, issue pending

.. _entity-lcls-ii-core-rtl-timingmsgaxiringbuffer-vhd:

TimingMsgAxiRingBuffer
----------------------

File: :repo:`LCLS-II/core/rtl/TimingMsgAxiRingBuffer.vhd`

Records timing messages for readout over AXI-Lite. TimingMsgToAxiStream splits each message into 32 bit words and every valid word is written to a surf AxiLiteRingBuffer in the timing clock domain. Because TimingMsgToAxiStream never ends its stream, zero words follow each message while recording stays enabled, as observed, intent unconfirmed.

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
   * - ``MEMORY_TYPE_G``
     - ``string``
     - ``"block"``
   * - ``REG_EN_G``
     - ``boolean``
     - ``true``
   * - ``RAM_ADDR_WIDTH_G``
     - ``positive range 1 to (2 ** 24)``
     - ``10``
   * - ``VECTOR_SIZE_G``
     - ``integer``
     - none

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``timingClk``
     - in
     - ``sl``
   * - ``timingRst``
     - in
     - ``sl``
   * - ``timingMessage``
     - in
     - ``slv(VECTOR_SIZE_G - 1 downto 0)``
   * - ``timingMessageStrobe``
     - in
     - ``sl``
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

Issues: issue pending

.. _entity-lcls-ii-core-rtl-timingmsgdelay-vhd:

TimingMsgDelay
--------------

File: :repo:`LCLS-II/core/rtl/TimingMsgDelay.vhd`

Delays decoded timing messages by a programmable number of timingClk cycles. Each strobed message is stored in a FIFO with the free-running counter value plus delay and read out, with timingMessageStrobeOut, when the counter reaches that value. As observed, the FIFO_ADDR_WIDTH_G generic is declared but not used.

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
   * - ``MEMORY_TYPE_G``
     - ``string``
     - ``"block"``
   * - ``FIFO_ADDR_WIDTH_G``
     - ``positive range 1 to (2 ** 24)``
     - ``7``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``timingClk``
     - in
     - ``sl``
   * - ``timingRst``
     - in
     - ``sl``
   * - ``timingMessageIn``
     - in
     - ``TimingMessageType``
   * - ``timingMessageStrobeIn``
     - in
     - ``sl``
   * - ``delay``
     - in
     - ``slv(15 downto 0)``
   * - ``timingMessageOut``
     - out
     - ``TimingMessageType``
   * - ``timingMessageStrobeOut``
     - out
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-timingmsgtoaxistream-vhd:

TimingMsgToAxiStream
--------------------

File: :repo:`LCLS-II/core/rtl/TimingMsgToAxiStream.vhd`

Copies a timing message vector on timingMessageStrobe and shifts it out SHIFT_SIZE_G bits at a time, least significant bits first, through an AxiStreamFifoV2 that converts to the configured output width. The frame counter is cleared every cycle, so as observed tLast never asserts and zero beats follow the message indefinitely, intent unconfirmed.

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
   * - ``COMMON_CLOCK_G``
     - ``boolean``
     - ``false``
   * - ``SHIFT_SIZE_G``
     - ``integer range 16 to 128``
     - none
   * - ``AXIS_CONFIG_G``
     - ``AxiStreamConfigType``
     - ``ssiAxiStreamConfig(8, TKEEP_NORMAL_C)``
   * - ``VECTOR_SIZE_G``
     - ``integer``
     - none

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``timingClk``
     - in
     - ``sl``
   * - ``timingRst``
     - in
     - ``sl``
   * - ``timingMessage``
     - in
     - ``slv(VECTOR_SIZE_G - 1 downto 0)``
   * - ``timingMessageStrobe``
     - in
     - ``sl``
   * - ``axisClk``
     - in
     - ``sl``
   * - ``axisRst``
     - in
     - ``sl``
   * - ``axisMaster``
     - out
     - ``AxiStreamMasterType``
   * - ``axisSlave``
     - in
     - ``AxiStreamSlaveType``

Issues: none

.. _entity-lcls-ii-core-rtl-timingrx-vhd:

TimingRx
--------

File: :repo:`LCLS-II/core/rtl/TimingRx.vhd`

Receiver that parses both timing protocols. CLKSEL_MODE_G keeps the LCLS-I receiver (TimingStreamRx), the LCLS-II receiver (TimingFrameRx), or both, and in a mode with no receiver for a protocol the outputs for that protocol stay at their reset values. An AXI-Lite block at 0x00 to 0x40 holds the status counters, the receiver select and reset bits at 0x20, the message delay at 0x24, and the clock counts and version.

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
   * - ``DEFAULT_CLK_SEL_G``
     - ``sl``
     - ``'1'``
   * - ``CLKSEL_MODE_G``
     - ``string``
     - ``"SELECT"``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``rxClk``
     - in
     - ``sl``
   * - ``rxData``
     - in
     - ``TimingRxType``
   * - ``rxControl``
     - out
     - ``TimingPhyControlType``
   * - ``rxStatus``
     - in
     - ``TimingPhyStatusType``
   * - ``timingClkSel``
     - out
     - ``sl``
   * - ``timingModeSel``
     - out
     - ``sl``
   * - ``timingStreamUser``
     - out
     - ``TimingStreamType``
   * - ``timingStreamPrompt``
     - out
     - ``TimingStreamType``
   * - ``timingStreamStrobe``
     - out
     - ``sl``
   * - ``timingStreamValid``
     - out
     - ``sl``
   * - ``timingMessage``
     - out
     - ``TimingMessageType``
   * - ``timingMessageStrobe``
     - out
     - ``sl``
   * - ``timingMessageValid``
     - out
     - ``sl``
   * - ``timingExtension``
     - out
     - ``TimingExtensionArray``
   * - ``txClk``
     - in
     - ``sl``
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

Issues: none

.. _entity-lcls-ii-core-rtl-timingserialdelay-vhd:

TimingSerialDelay
-----------------

File: :repo:`LCLS-II/core/rtl/TimingSerialDelay.vhd`

Delays a received frame by a programmable number of clocks. The words of each frame, accepted on advance_i after fiducial_i, go into a FIFO and the frame is released on strobe_o with valid_o when its delay expires, and overflow_o flags a frame pipeline overrun. As observed, frame N leaves 4 + delay clocks after the fiducial of frame N + 1, and stream_i ready is never read, intent unconfirmed.

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
   * - ``NWORDS_G``
     - ``integer``
     - ``16``
   * - ``FDEPTH_G``
     - ``integer``
     - ``100``
   * - ``DEBUG_G``
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
   * - ``delay``
     - in
     - ``slv(19 downto 0)``
   * - ``fiducial_i``
     - in
     - ``sl``
   * - ``advance_i``
     - in
     - ``sl``
   * - ``stream_i``
     - in
     - ``TimingSerialType``
   * - ``frame_o``
     - out
     - ``slv(16 * NWORDS_G - 1 downto 0)``
   * - ``strobe_o``
     - out
     - ``sl``
   * - ``valid_o``
     - out
     - ``sl``
   * - ``overflow_o``
     - out
     - ``sl``

Issues: none

.. _entity-lcls-ii-core-rtl-timingserializer-vhd:

TimingSerializer
----------------

File: :repo:`LCLS-II/core/rtl/TimingSerializer.vhd`

Builds the LCLS-II 16-bit character stream. It sends K28.5 commas when idle, an alignment comma and K23.7 start of frame on fiducial, then each ready stream as a segment with a header word carrying streamId, last, and offset, K28.0 between segments, K29.7 at the end of the frame, and the frame CRC32 in two words. It pulls the words of a stream with advance.

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
   * - ``STREAMS_C``
     - ``integer``
     - ``1``

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
   * - ``fiducial``
     - in
     - ``sl``
   * - ``streams``
     - in
     - ``TimingSerialArray(STREAMS_C - 1 downto 0)``
   * - ``streamIds``
     - in
     - ``Slv4Array(STREAMS_C - 1 downto 0)``
   * - ``advance``
     - out
     - ``slv(STREAMS_C - 1 downto 0)``
   * - ``data``
     - out
     - ``slv(15 downto 0)``
   * - ``dataK``
     - out
     - ``slv(1 downto 0)``

Issues: none

.. _entity-lcls-ii-core-rtl-timingstreamrx-vhd:

TimingStreamRx
--------------

File: :repo:`LCLS-II/core/rtl/TimingStreamRx.vhd`

Decodes the LCLS-I stream. A K28.0 on the high half opens a data buffer that closes at K28.5 or K28.1, event codes 0x70 and 0x71 shift in the pulse ID bit by bit, and 0x7D starts a counted frame of event code flags that ends after 0x36B0 cycles. It then strobes the stream with the newest data buffer or one from two frames earlier, selected by timingMessageNoDely, and any decode or disparity error resets the decoder.

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
   * - ``rxClk``
     - in
     - ``sl``
   * - ``rxRst``
     - in
     - ``sl``
   * - ``rxData``
     - in
     - ``TimingRxType``
   * - ``timingMessageNoDely``
     - in
     - ``sl``
   * - ``timingMessageUser``
     - out
     - ``TimingStreamType``
   * - ``timingMessagePrompt``
     - out
     - ``TimingStreamType``
   * - ``timingMessageStrobe``
     - out
     - ``sl``
   * - ``timingMessageValid``
     - out
     - ``sl``
   * - ``timingTSEventCounter``
     - out
     - ``slv(31 downto 0)``
   * - ``rxVersion``
     - out
     - ``slv(31 downto 0)``
   * - ``staData``
     - out
     - ``slv(4 downto 0)``

Issues: none

.. _entity-lcls-ii-core-rtl-timingstreamtx-vhd:

TimingStreamTx
--------------

File: :repo:`LCLS-II/core/rtl/TimingStreamTx.vhd`

Generates the LCLS-I stream. On fiducial it latches the data buffer, pulse ID, and event codes, sends the data buffer bytes on the high half between K28.0 and K28.1, then the pulse ID bit by bit as event codes 0x70 and 0x71, an 0x7D marker, and a scan of event codes 0 to 255 on the low half, with K28.5 commas on the idle half cycles.

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
   * - ``fiducial``
     - in
     - ``sl``
   * - ``dataBuff``
     - in
     - ``TimingDataBuffType``
   * - ``pulseId``
     - in
     - ``slv(31 downto 0)``
   * - ``eventCodes``
     - in
     - ``slv(255 downto 0)``
   * - ``data``
     - out
     - ``slv(15 downto 0)``
   * - ``dataK``
     - out
     - ``slv(1 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-wordserializer-vhd:

WordSerializer
--------------

File: :repo:`LCLS-II/core/rtl/WordSerializer.vhd`

Latches NWORDS_G 16-bit words on fiducial and shifts them out one per advance on a TimingSerialType stream, the same shift register as TPSerializer for an arbitrary word vector. Ready stays low when the stream is not ready at the latch and drops after the last word.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``NWORDS_G``
     - ``integer``
     - ``0``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``txClk``
     - in
     - ``sl``
   * - ``txRst``
     - in
     - ``sl``
   * - ``fiducial``
     - in
     - ``sl``
   * - ``words``
     - in
     - ``slv(16 * NWORDS_G - 1 downto 0)``
   * - ``ready``
     - in
     - ``sl``
   * - ``advance``
     - in
     - ``sl``
   * - ``stream``
     - out
     - ``TimingSerialType``

Issues: none

.. _entity-lcls-ii-core-tb-timingserialdelay-tb-vhd:

TimingSerialDelayTb
-------------------

File: :repo:`LCLS-II/core/tb/TimingSerialDelay_tb.vhd`

Self-checking testbench for TimingSerialDelay with no ports. It runs a 10 ns clock with a fiducial every 66 clocks, 16 word frames, and periodic resets of the delay line, and asserts the frame contents, the overflow flag, and the delay of each frame. As observed its 8 bit frame tag wraps after about 169 us and the delay check fails after the wrap.

Status: simulated

.. rubric:: Generics

none

.. rubric:: Ports

none

Issues: issue pending
