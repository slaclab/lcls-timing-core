Transceiver wrappers
====================

:repo:`LCLS-II/gtp7/ruckus.tcl`, :repo:`LCLS-II/gtx7/ruckus.tcl`, :repo:`LCLS-II/gthUltraScale/ruckus.tcl`, :repo:`LCLS-II/gthUltraScale+/ruckus.tcl`, and :repo:`LCLS-II/gtyUltraScale+/ruckus.tcl` load these sources into the ``lcls_timing_core`` library; a file that is not loaded says so in the Status column.

These wrappers instantiate Xilinx GT primitives and IP cores, so only Vivado builds them and the regression does not simulate them. LCLS-II/ruckus.tcl loads the wrapper directory of the FPGA family being built; the :doc:`family matrix </reference/families>` lists which.

.. list-table::
   :header-rows: 1
   :widths: 20 40 25 15

   * - Entity
     - File
     - Status
     - Issues
   * - :ref:`TimingGthCoreWrapper <entity-lcls-ii-gthultrascale-rtl-timinggthcorewrapper-vhd>`
     - :repo:`LCLS-II/gthUltraScale+/rtl/TimingGthCoreWrapper.vhd`
     - Vivado-only
     - none
   * - :ref:`TimingGtCoreWrapper <entity-lcls-ii-gthultrascale-rtl-timinggtcorewrapper-vhd>`
     - :repo:`LCLS-II/gthUltraScale/rtl/TimingGtCoreWrapper.vhd`
     - Vivado-only
     - none
   * - :ref:`TimingGtCoreWrapper <entity-lcls-ii-gtp7-rtl-timinggtcorewrapper-vhd>`
     - :repo:`LCLS-II/gtp7/rtl/TimingGtCoreWrapper.vhd`
     - Vivado-only
     - issue pending
   * - :ref:`TimingGtCoreWrapper <entity-lcls-ii-gtx7-rtl-timinggtcorewrapper-vhd>`
     - :repo:`LCLS-II/gtx7/rtl/TimingGtCoreWrapper.vhd`
     - Vivado-only
     - none
   * - :ref:`TimingGtCoreWrapper <entity-lcls-ii-gtyultrascale-rtl-timinggtcorewrapper-vhd>`
     - :repo:`LCLS-II/gtyUltraScale+/rtl/TimingGtCoreWrapper.vhd`
     - Vivado-only
     - none

.. _entity-lcls-ii-gthultrascale-rtl-timinggthcorewrapper-vhd:

TimingGthCoreWrapper
--------------------

File: :repo:`LCLS-II/gthUltraScale+/rtl/TimingGthCoreWrapper.vhd`

Timing transceiver wrapper for the UltraScale+ GTHE4, built like the Kintex UltraScale wrapper with the TimingGth_fixedlat or, with EXTREF_G, the TimingGth_extref IP core, a dummy channel when DISABLE_TIME_GT_G is true, and an AXI-Lite crossbar for GtRxAlignCheck and the DRP bridge. Its entity is TimingGthCoreWrapper, not TimingGtCoreWrapper, and its TX user clock and data ports have defaults.

Status: Vivado-only

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
   * - ``SIMULATION_G``
     - ``boolean``
     - ``false``
   * - ``DISABLE_TIME_GT_G``
     - ``boolean``
     - ``false``
   * - ``EXTREF_G``
     - ``boolean``
     - ``false``
   * - ``AXI_CLK_FREQ_G``
     - ``real``
     - ``156.25e6``
   * - ``AXIL_BASE_ADDR_G``
     - ``slv(31 downto 0)``
     - none
   * - ``ADDR_BITS_G``
     - ``positive``
     - ``22``
   * - ``GTH_DRP_OFFSET_G``
     - ``slv(31 downto 0)``
     - ``x"00400000"``

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
   * - ``stableClk``
     - in
     - ``sl``
   * - ``stableRst``
     - in
     - ``sl``
   * - ``gtRefClk``
     - in
     - ``sl``
   * - ``gtRefClkDiv2``
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
   * - ``gtgRefClk``
     - in
     - ``sl``
   * - ``cpllRefClkSel``
     - in
     - ``slv(2 downto 0)``
   * - ``rxControl``
     - in
     - ``TimingPhyControlType``
   * - ``rxStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``rxUsrClkActive``
     - in
     - ``sl``
   * - ``rxCdrStable``
     - out
     - ``sl``
   * - ``rxUsrClk``
     - in
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
   * - ``rxOutClk``
     - out
     - ``sl``
   * - ``txControl``
     - in
     - ``TimingPhyControlType``
   * - ``txStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``txUsrClk``
     - in
     - ``sl``
   * - ``txUsrClkActive``
     - in
     - ``sl``
   * - ``txData``
     - in
     - ``slv(15 downto 0)``
   * - ``txDataK``
     - in
     - ``slv(1 downto 0)``
   * - ``txOutClk``
     - out
     - ``sl``
   * - ``loopback``
     - in
     - ``slv(2 downto 0)``

Issues: none

.. _entity-lcls-ii-gthultrascale-rtl-timinggtcorewrapper-vhd:

TimingGtCoreWrapper (LCLS-II/gthUltraScale/rtl/TimingGtCoreWrapper.vhd)
-----------------------------------------------------------------------

File: :repo:`LCLS-II/gthUltraScale/rtl/TimingGtCoreWrapper.vhd`

Timing transceiver wrapper for the Kintex UltraScale GTHE3. It instantiates the TimingGth_fixedlat or, with EXTREF_G, the TimingGth_extref IP core, or ties the channel off with a dummy when DISABLE_TIME_GT_G is true, and an AXI-Lite crossbar gives a surf GtRxAlignCheck and a DRP bridge access to the channel. The IP comes from the coregen directory that ruckus selects by Vivado version.

Status: Vivado-only

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
   * - ``SIMULATION_G``
     - ``boolean``
     - ``false``
   * - ``DISABLE_TIME_GT_G``
     - ``boolean``
     - ``false``
   * - ``EXTREF_G``
     - ``boolean``
     - ``false``
   * - ``AXI_CLK_FREQ_G``
     - ``real``
     - ``156.25e6``
   * - ``AXIL_BASE_ADDR_G``
     - ``slv(31 downto 0)``
     - none
   * - ``ADDR_BITS_G``
     - ``positive``
     - ``22``
   * - ``GTH_DRP_OFFSET_G``
     - ``slv(31 downto 0)``
     - ``x"00400000"``

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
   * - ``stableClk``
     - in
     - ``sl``
   * - ``stableRst``
     - in
     - ``sl``
   * - ``gtRefClk``
     - in
     - ``sl``
   * - ``gtRefClkDiv2``
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
   * - ``gtgRefClk``
     - in
     - ``sl``
   * - ``cpllRefClkSel``
     - in
     - ``slv(2 downto 0)``
   * - ``rxControl``
     - in
     - ``TimingPhyControlType``
   * - ``rxStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``rxUsrClkActive``
     - in
     - ``sl``
   * - ``rxCdrStable``
     - out
     - ``sl``
   * - ``rxUsrClk``
     - in
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
   * - ``rxOutClk``
     - out
     - ``sl``
   * - ``txControl``
     - in
     - ``TimingPhyControlType``
   * - ``txStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``txUsrClk``
     - in
     - ``sl``
   * - ``txUsrClkActive``
     - in
     - ``sl``
   * - ``txData``
     - in
     - ``slv(15 downto 0)``
   * - ``txDataK``
     - in
     - ``slv(1 downto 0)``
   * - ``txOutClk``
     - out
     - ``sl``
   * - ``loopback``
     - in
     - ``slv(2 downto 0)``

Issues: none

.. _entity-lcls-ii-gtp7-rtl-timinggtcorewrapper-vhd:

TimingGtCoreWrapper (LCLS-II/gtp7/rtl/TimingGtCoreWrapper.vhd)
--------------------------------------------------------------

File: :repo:`LCLS-II/gtp7/rtl/TimingGtCoreWrapper.vhd`

Timing transceiver wrapper for the Artix-7 GTP: a surf Gtp7Core with the 8b10b decoder, the RX and TX output reset synchronizers, and an AXI-Lite to DRP bridge, presenting 16-bit rxData and txData paths with K flags and the timing PHY control and status records. PLL_G selects the PLL and GT_CONFIG_G selects the LCLS-I or LCLS-II line configuration.

Status: Vivado-only

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
   * - ``PLL_G``
     - ``string``
     - ``"PLL0"``
   * - ``GT_CONFIG_G``
     - ``boolean``
     - ``true``

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
   * - ``gtQPllOutRefClk``
     - in
     - ``slv(1 downto 0)``
   * - ``gtQPllOutClk``
     - in
     - ``slv(1 downto 0)``
   * - ``gtQPllLock``
     - in
     - ``slv(1 downto 0)``
   * - ``gtQPllRefClkLost``
     - in
     - ``slv(1 downto 0)``
   * - ``gtQPllReset``
     - out
     - ``slv(1 downto 0)``
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
   * - ``stableClk``
     - in
     - ``sl``
   * - ``stableRst``
     - in
     - ``sl``
   * - ``rxControl``
     - in
     - ``TimingPhyControlType``
   * - ``rxStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``rxOutClk``
     - out
     - ``sl``
   * - ``rxOutRst``
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
   * - ``txControl``
     - in
     - ``TimingPhyControlType``
   * - ``txStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``txOutClk``
     - out
     - ``sl``
   * - ``txOutRst``
     - out
     - ``sl``
   * - ``txData``
     - in
     - ``slv(15 downto 0)``
   * - ``txDataK``
     - in
     - ``slv(1 downto 0)``
   * - ``loopback``
     - in
     - ``slv(2 downto 0)``

Issues: issue pending

.. _entity-lcls-ii-gtx7-rtl-timinggtcorewrapper-vhd:

TimingGtCoreWrapper (LCLS-II/gtx7/rtl/TimingGtCoreWrapper.vhd)
--------------------------------------------------------------

File: :repo:`LCLS-II/gtx7/rtl/TimingGtCoreWrapper.vhd`

Timing transceiver wrapper for the Kintex-7 GTX: a surf Gtx7Core with power-up resets, the 8b10b decoder, RX and TX output reset synchronizers, and an AXI-Lite to DRP bridge. Generics select the CPLL reference clock, whether the reference comes from gtRefClkP and gtRefClkN or from gtRefClkIn, the CDR lock wait, the stable clock period, and the LCLS-I or LCLS-II line configuration.

Status: Vivado-only

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
   * - ``SIM_GTRESET_SPEEDUP_G``
     - ``boolean``
     - ``false``
   * - ``WAIT_TIME_CDRLOCK_G``
     - ``integer``
     - ``-1``
   * - ``CPLL_REFCLK_SEL_G``
     - ``bit_vector``
     - ``"001"``
   * - ``REFCLK_G``
     - ``boolean``
     - ``false``
   * - ``GT_CONFIG_G``
     - ``boolean``
     - ``true``
   * - ``STABLE_CLK_PERIOD_G``
     - ``real``
     - ``4.0E-9``

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
   * - ``gtRefClkP``
     - in
     - ``sl``
   * - ``gtRefClkN``
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
   * - ``gtRefClkIn``
     - in
     - ``sl``
   * - ``stableClk``
     - in
     - ``sl``
   * - ``stableRst``
     - in
     - ``sl``
   * - ``rxControl``
     - in
     - ``TimingPhyControlType``
   * - ``rxStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``rxOutClk``
     - out
     - ``sl``
   * - ``rxOutRst``
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
   * - ``txControl``
     - in
     - ``TimingPhyControlType``
   * - ``txStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``txOutClk``
     - out
     - ``sl``
   * - ``txOutRst``
     - out
     - ``sl``
   * - ``txData``
     - in
     - ``slv(15 downto 0)``
   * - ``txDataK``
     - in
     - ``slv(1 downto 0)``
   * - ``loopback``
     - in
     - ``slv(2 downto 0)``

Issues: none

.. _entity-lcls-ii-gtyultrascale-rtl-timinggtcorewrapper-vhd:

TimingGtCoreWrapper (LCLS-II/gtyUltraScale+/rtl/TimingGtCoreWrapper.vhd)
------------------------------------------------------------------------

File: :repo:`LCLS-II/gtyUltraScale+/rtl/TimingGtCoreWrapper.vhd`

Timing transceiver wrapper for the UltraScale+ GTYE4, built like the GTH wrappers with the TimingGty_fixedlat or, with EXTREF_G, the TimingGty_extref IP core, a dummy channel when DISABLE_TIME_GT_G is true, and an AXI-Lite crossbar for GtRxAlignCheck and the DRP bridge. With LCLS1_ONLY_G true the local reference core is TimingGty_fixedlat_Lcls1Only instead.

Status: Vivado-only

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
   * - ``SIMULATION_G``
     - ``boolean``
     - ``false``
   * - ``DISABLE_TIME_GT_G``
     - ``boolean``
     - ``false``
   * - ``EXTREF_G``
     - ``boolean``
     - ``false``
   * - ``LCLS1_ONLY_G``
     - ``boolean``
     - ``false``
   * - ``AXI_CLK_FREQ_G``
     - ``real``
     - ``156.25e6``
   * - ``AXIL_BASE_ADDR_G``
     - ``slv(31 downto 0)``
     - none
   * - ``GTY_DRP_OFFSET_G``
     - ``slv(31 downto 0)``
     - ``x"00400000"``

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
   * - ``stableClk``
     - in
     - ``sl``
   * - ``stableRst``
     - in
     - ``sl``
   * - ``gtRefClk``
     - in
     - ``sl``
   * - ``gtRefClkDiv2``
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
   * - ``gtgRefClk``
     - in
     - ``sl``
   * - ``cpllRefClkSel``
     - in
     - ``slv(2 downto 0)``
   * - ``rxControl``
     - in
     - ``TimingPhyControlType``
   * - ``rxStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``rxUsrClkActive``
     - in
     - ``sl``
   * - ``rxCdrStable``
     - out
     - ``sl``
   * - ``rxPmaRstDoneOut``
     - out
     - ``sl``
   * - ``rxUsrClk``
     - in
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
   * - ``rxOutClk``
     - out
     - ``sl``
   * - ``txControl``
     - in
     - ``TimingPhyControlType``
   * - ``txStatus``
     - out
     - ``TimingPhyStatusType``
   * - ``txUsrClk``
     - in
     - ``sl``
   * - ``txUsrClkActive``
     - in
     - ``sl``
   * - ``txData``
     - in
     - ``slv(15 downto 0)``
   * - ``txDataK``
     - in
     - ``slv(1 downto 0)``
   * - ``txOutClk``
     - out
     - ``sl``
   * - ``loopback``
     - in
     - ``slv(2 downto 0)``

Issues: none
