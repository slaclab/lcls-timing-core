-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Wrapper for GTH Core
-------------------------------------------------------------------------------
-- This file is part of 'LCLS Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the
-- top-level directory of this distribution and at:
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
-- No part of 'LCLS Timing Core', including this file,
-- may be copied, modified, propagated, or distributed except according to
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;


library surf;
use surf.StdRtlPkg.all;
use surf.AxiLitePkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;

library unisim;
use unisim.vcomponents.all;

entity TimingGthCoreWrapper is
   generic (
      TPD_G             : time             := 1 ns;
      DISABLE_TIME_GT_G : boolean          := false;
      EXTREF_G          : boolean          := false;
      AXIL_BASE_ADDR_G  : slv(31 downto 0);
      ADDR_BITS_G       : positive         := 22;
      GTH_DRP_OFFSET_G  : slv(31 downto 0) := x"00400000");
   port (
      -- AXI-Lite Port
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType;

      stableClk    : in  sl;  -- Unused in GTHE3, but used in GTHE4/GTYE4
      stableRst    : in  sl;  -- Unused in GTHE3, but used in GTHE4/GTYE4
      -- GTH FPGA IO
      gtRefClk     : in  sl;
      gtRefClkDiv2 : in  sl;  -- Unused in GTHE3, but used in GTHE4/GTYE4
      gtRxP        : in  sl;
      gtRxN        : in  sl;
      gtTxP        : out sl;
      gtTxN        : out sl;

      -- GTGREFCLK Interface Option
      gtgRefClk     : in sl              := '0';
      cpllRefClkSel : in slv(2 downto 0) := "001";  -- Set for "111" for gtgRefClk

      -- Rx ports
      rxControl      : in  TimingPhyControlType;
      rxStatus       : out TimingPhyStatusType;
      rxUsrClkActive : in  sl;
      rxCdrStable    : out sl;
      rxUsrClk       : in  sl;
      rxData         : out slv(15 downto 0);
      rxDataK        : out slv(1 downto 0);
      rxDispErr      : out slv(1 downto 0);
      rxDecErr       : out slv(1 downto 0);
      rxOutClk       : out sl;

      -- Tx Ports
      txControl      : in  TimingPhyControlType;
      txStatus       : out TimingPhyStatusType;
      txUsrClk       : in  sl := '0';
      txUsrClkActive : in  sl := '0';
      txData         : in  slv(15 downto 0) := (others => '0');
      txDataK        : in  slv(1 downto 0)  := (others => '0');
      txOutClk       : out sl;

      loopback : in slv(2 downto 0));
end entity TimingGthCoreWrapper;

architecture rtl of TimingGthCoreWrapper is

   component TimingGth_fixedlat
      port (
         gtwiz_userclk_tx_reset_in          : in  std_logic_vector(0 downto 0);
         gtwiz_userclk_tx_active_in         : in  std_logic_vector(0 downto 0);
         gtwiz_userclk_rx_active_in         : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_reset_in       : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_start_user_in  : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_done_out       : out std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_error_out      : out std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_reset_in       : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_start_user_in  : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_done_out       : out std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_error_out      : out std_logic_vector(0 downto 0);
         gtwiz_reset_clk_freerun_in         : in  std_logic_vector(0 downto 0);
         gtwiz_reset_all_in                 : in  std_logic_vector(0 downto 0);
         gtwiz_reset_tx_pll_and_datapath_in : in  std_logic_vector(0 downto 0);
         gtwiz_reset_tx_datapath_in         : in  std_logic_vector(0 downto 0);
         gtwiz_reset_rx_pll_and_datapath_in : in  std_logic_vector(0 downto 0);
         gtwiz_reset_rx_datapath_in         : in  std_logic_vector(0 downto 0);
         gtwiz_reset_rx_cdr_stable_out      : out std_logic_vector(0 downto 0);
         gtwiz_reset_tx_done_out            : out std_logic_vector(0 downto 0);
         gtwiz_reset_rx_done_out            : out std_logic_vector(0 downto 0);
         gtwiz_userdata_tx_in               : in  std_logic_vector(15 downto 0);
         gtwiz_userdata_rx_out              : out std_logic_vector(15 downto 0);
         cpllrefclksel_in                   : in  std_logic_vector(2 downto 0);
         drpaddr_in                         : in  std_logic_vector(9 downto 0);
         drpclk_in                          : in  std_logic_vector(0 downto 0);
         drpdi_in                           : in  std_logic_vector(15 downto 0);
         drpen_in                           : in  std_logic_vector(0 downto 0);
         drpwe_in                           : in  std_logic_vector(0 downto 0);
         gtgrefclk_in                       : in  std_logic_vector(0 downto 0);
         gthrxn_in                          : in  std_logic_vector(0 downto 0);
         gthrxp_in                          : in  std_logic_vector(0 downto 0);
         gtrefclk0_in                       : in  std_logic_vector(0 downto 0);
         loopback_in                        : in  std_logic_vector(2 downto 0);
         rx8b10ben_in                       : in  std_logic_vector(0 downto 0);
         rxcommadeten_in                    : in  std_logic_vector(0 downto 0);
         rxmcommaalignen_in                 : in  std_logic_vector(0 downto 0);
         rxpcommaalignen_in                 : in  std_logic_vector(0 downto 0);
         rxpolarity_in                      : in  std_logic_vector(0 downto 0);
         rxusrclk_in                        : in  std_logic_vector(0 downto 0);
         rxusrclk2_in                       : in  std_logic_vector(0 downto 0);
         tx8b10ben_in                       : in  std_logic_vector(0 downto 0);
         txctrl0_in                         : in  std_logic_vector(15 downto 0);
         txctrl1_in                         : in  std_logic_vector(15 downto 0);
         txctrl2_in                         : in  std_logic_vector(7 downto 0);
         txinhibit_in                       : in  std_logic_vector(0 downto 0);
         txpolarity_in                      : in  std_logic_vector(0 downto 0);
         txusrclk_in                        : in  std_logic_vector(0 downto 0);
         txusrclk2_in                       : in  std_logic_vector(0 downto 0);
         drpdo_out                          : out std_logic_vector(15 downto 0);
         drprdy_out                         : out std_logic_vector(0 downto 0);
         gthtxn_out                         : out std_logic_vector(0 downto 0);
         gthtxp_out                         : out std_logic_vector(0 downto 0);
         gtpowergood_out                    : out std_logic_vector(0 downto 0);
         rxbyteisaligned_out                : out std_logic_vector(0 downto 0);
         rxbyterealign_out                  : out std_logic_vector(0 downto 0);
         rxcommadet_out                     : out std_logic_vector(0 downto 0);
         rxctrl0_out                        : out std_logic_vector(15 downto 0);
         rxctrl1_out                        : out std_logic_vector(15 downto 0);
         rxctrl2_out                        : out std_logic_vector(7 downto 0);
         rxctrl3_out                        : out std_logic_vector(7 downto 0);
         rxdlysresetdone_out                : out std_logic_vector(0 downto 0);
         rxoutclk_out                       : out std_logic_vector(0 downto 0);
         rxphaligndone_out                  : out std_logic_vector(0 downto 0);
         rxphalignerr_out                   : out std_logic_vector(0 downto 0);
         rxpmaresetdone_out                 : out std_logic_vector(0 downto 0);
         rxresetdone_out                    : out std_logic_vector(0 downto 0);
         rxsyncdone_out                     : out std_logic_vector(0 downto 0);
         rxsyncout_out                      : out std_logic_vector(0 downto 0);
         txoutclk_out                       : out std_logic_vector(0 downto 0);
         txpmaresetdone_out                 : out std_logic_vector(0 downto 0);
         txresetdone_out                    : out std_logic_vector(0 downto 0)
         );
   end component;
   component TimingGth_extref
      port (
         gtwiz_userclk_tx_reset_in          : in  std_logic_vector(0 downto 0);
         gtwiz_userclk_tx_active_in         : in  std_logic_vector(0 downto 0);
         gtwiz_userclk_rx_active_in         : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_reset_in       : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_start_user_in  : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_done_out       : out std_logic_vector(0 downto 0);
         gtwiz_buffbypass_tx_error_out      : out std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_reset_in       : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_start_user_in  : in  std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_done_out       : out std_logic_vector(0 downto 0);
         gtwiz_buffbypass_rx_error_out      : out std_logic_vector(0 downto 0);
         gtwiz_reset_clk_freerun_in         : in  std_logic_vector(0 downto 0);
         gtwiz_reset_all_in                 : in  std_logic_vector(0 downto 0);
         gtwiz_reset_tx_pll_and_datapath_in : in  std_logic_vector(0 downto 0);
         gtwiz_reset_tx_datapath_in         : in  std_logic_vector(0 downto 0);
         gtwiz_reset_rx_pll_and_datapath_in : in  std_logic_vector(0 downto 0);
         gtwiz_reset_rx_datapath_in         : in  std_logic_vector(0 downto 0);
         gtwiz_reset_rx_cdr_stable_out      : out std_logic_vector(0 downto 0);
         gtwiz_reset_tx_done_out            : out std_logic_vector(0 downto 0);
         gtwiz_reset_rx_done_out            : out std_logic_vector(0 downto 0);
         gtwiz_userdata_tx_in               : in  std_logic_vector(15 downto 0);
         gtwiz_userdata_rx_out              : out std_logic_vector(15 downto 0);
         drpaddr_in                         : in  std_logic_vector(9 downto 0);
         drpclk_in                          : in  std_logic_vector(0 downto 0);
         drpdi_in                           : in  std_logic_vector(15 downto 0);
         drpen_in                           : in  std_logic_vector(0 downto 0);
         drpwe_in                           : in  std_logic_vector(0 downto 0);
         gthrxn_in                          : in  std_logic_vector(0 downto 0);
         gthrxp_in                          : in  std_logic_vector(0 downto 0);
         gtrefclk0_in                       : in  std_logic_vector(0 downto 0);
         loopback_in                        : in  std_logic_vector(2 downto 0);
         rx8b10ben_in                       : in  std_logic_vector(0 downto 0);
         rxcommadeten_in                    : in  std_logic_vector(0 downto 0);
         rxmcommaalignen_in                 : in  std_logic_vector(0 downto 0);
         rxpcommaalignen_in                 : in  std_logic_vector(0 downto 0);
         rxpolarity_in                      : in  std_logic_vector(0 downto 0);
         rxusrclk_in                        : in  std_logic_vector(0 downto 0);
         rxusrclk2_in                       : in  std_logic_vector(0 downto 0);
         tx8b10ben_in                       : in  std_logic_vector(0 downto 0);
         txctrl0_in                         : in  std_logic_vector(15 downto 0);
         txctrl1_in                         : in  std_logic_vector(15 downto 0);
         txctrl2_in                         : in  std_logic_vector(7 downto 0);
         txinhibit_in                       : in  std_logic_vector(0 downto 0);
         txpolarity_in                      : in  std_logic_vector(0 downto 0);
         txusrclk_in                        : in  std_logic_vector(0 downto 0);
         txusrclk2_in                       : in  std_logic_vector(0 downto 0);
         drpdo_out                          : out std_logic_vector(15 downto 0);
         drprdy_out                         : out std_logic_vector(0 downto 0);
         gthtxn_out                         : out std_logic_vector(0 downto 0);
         gthtxp_out                         : out std_logic_vector(0 downto 0);
         gtpowergood_out                    : out std_logic_vector(0 downto 0);
         rxbyteisaligned_out                : out std_logic_vector(0 downto 0);
         rxbyterealign_out                  : out std_logic_vector(0 downto 0);
         rxcommadet_out                     : out std_logic_vector(0 downto 0);
         rxctrl0_out                        : out std_logic_vector(15 downto 0);
         rxctrl1_out                        : out std_logic_vector(15 downto 0);
         rxctrl2_out                        : out std_logic_vector(7 downto 0);
         rxctrl3_out                        : out std_logic_vector(7 downto 0);
         rxdlysresetdone_out                : out std_logic_vector(0 downto 0);
         rxoutclk_out                       : out std_logic_vector(0 downto 0);
         rxphaligndone_out                  : out std_logic_vector(0 downto 0);
         rxphalignerr_out                   : out std_logic_vector(0 downto 0);
         rxpmaresetdone_out                 : out std_logic_vector(0 downto 0);
         rxresetdone_out                    : out std_logic_vector(0 downto 0);
         rxsyncdone_out                     : out std_logic_vector(0 downto 0);
         rxsyncout_out                      : out std_logic_vector(0 downto 0);
         txoutclk_out                       : out std_logic_vector(0 downto 0);
         txpmaresetdone_out                 : out std_logic_vector(0 downto 0);
         txresetdone_out                    : out std_logic_vector(0 downto 0)
         );
   end component;

   constant AXI_CROSSBAR_MASTERS_CONFIG_C : AxiLiteCrossbarMasterConfigArray(1 downto 0) := (
      0               => (
         baseAddr     => (AXIL_BASE_ADDR_G+x"00000000"),
         addrBits     => ADDR_BITS_G,
         connectivity => x"FFFF"),
      1               => (
         baseAddr     => (AXIL_BASE_ADDR_G+GTH_DRP_OFFSET_G),
         addrBits     => ADDR_BITS_G,
         connectivity => x"FFFF"));

   signal rxCtrl0Out   : slv(15 downto 0) := (others => '0');
   signal rxCtrl1Out   : slv(15 downto 0) := (others => '0');
   signal rxCtrl3Out   : slv(7 downto 0)  := (others => '0');
   signal txoutclk_out : sl               := '0';
   signal txoutclkb    : sl               := '0';
   signal rxoutclk_out : sl               := '0';
   signal rxoutclkb    : sl               := '0';
   signal freeRunClk   : sl               := '0';

   signal drpAddr     : slv(9 downto 0)  := (others => '0');
   signal drpDi       : slv(15 downto 0) := (others => '0');
   signal drpEn       : sl               := '0';
   signal drpWe       : sl               := '0';
   signal drpDO       : slv(15 downto 0) := (others => '0');
   signal drpRdy      : sl               := '1';
   signal txbypassrst : sl               := '0';
   signal rxbypassrst : sl               := '0';
   signal rxRst       : sl               := '0';
   signal bypassdone  : sl               := '0';
   signal bypasserr   : sl               := '0';

   signal axilWriteMasters : AxiLiteWriteMasterArray(1 downto 0);
   signal axilWriteSlaves  : AxiLiteWriteSlaveArray(1 downto 0);
   signal axilReadMasters  : AxiLiteReadMasterArray(1 downto 0);
   signal axilReadSlaves   : AxiLiteReadSlaveArray(1 downto 0);

   signal mAxilWriteMaster : AxiLiteWriteMasterType;
   signal mAxilWriteSlave  : AxiLiteWriteSlaveType;
   signal mAxilReadMaster  : AxiLiteReadMasterType;
   signal mAxilReadSlave   : AxiLiteReadSlaveType;

begin

   rxStatus.bufferByDone <= bypassdone;
   rxStatus.bufferByErr  <= bypasserr;

   U_XBAR : entity surf.AxiLiteCrossbar
      generic map (
         TPD_G              => TPD_G,
         NUM_SLAVE_SLOTS_G  => 2,
         NUM_MASTER_SLOTS_G => 2,
         MASTERS_CONFIG_G   => AXI_CROSSBAR_MASTERS_CONFIG_C)
      port map (
         axiClk              => axilClk,
         axiClkRst           => axilRst,
         sAxiWriteMasters(0) => axilWriteMaster,
         sAxiWriteMasters(1) => mAxilWriteMaster,
         sAxiWriteSlaves(0)  => axilWriteSlave,
         sAxiWriteSlaves(1)  => mAxilWriteSlave,
         sAxiReadMasters(0)  => axilReadMaster,
         sAxiReadMasters(1)  => mAxilReadMaster,
         sAxiReadSlaves(0)   => axilReadSlave,
         sAxiReadSlaves(1)   => mAxilReadSlave,
         mAxiWriteMasters    => axilWriteMasters,
         mAxiWriteSlaves     => axilWriteSlaves,
         mAxiReadMasters     => axilReadMasters,
         mAxiReadSlaves      => axilReadSlaves);

   U_AlignCheck : entity lcls_timing_core.GthRxAlignCheck
      generic map (
         TPD_G      => TPD_G,
         GT_TYPE_G  => "GTHE3",
         DRP_ADDR_G => AXI_CROSSBAR_MASTERS_CONFIG_C(1).baseAddr)
      port map (
         -- Clock Monitoring
         txClk            => txoutclkb,
         rxClk            => rxoutclkb,
         -- GTH Status/Control Interface
         resetIn          => rxControl.reset,
         resetDone        => bypassdone,
         resetErr         => bypasserr,
         resetOut         => rxRst,
         locked           => rxStatus.locked,
         -- Clock and Reset
         axilClk          => axilClk,
         axilRst          => axilRst,
         -- Slave AXI-Lite Interface
         mAxilReadMaster  => mAxilReadMaster,
         mAxilReadSlave   => mAxilReadSlave,
         mAxilWriteMaster => mAxilWriteMaster,
         mAxilWriteSlave  => mAxilWriteSlave,
         -- Slave AXI-Lite Interface
         sAxilReadMaster  => axilReadMasters(0),
         sAxilReadSlave   => axilReadSlaves(0),
         sAxilWriteMaster => axilWriteMasters(0),
         sAxilWriteSlave  => axilWriteSlaves(0));

   U_AxiLiteToDrp : entity surf.AxiLiteToDrp
      generic map (
         TPD_G            => TPD_G,
         COMMON_CLK_G     => true,
         EN_ARBITRATION_G => false,
         TIMEOUT_G        => 4096,
         ADDR_WIDTH_G     => 10,
         DATA_WIDTH_G     => 16)
      port map (
         -- AXI-Lite Port
         axilClk         => axilClk,
         axilRst         => axilRst,
         axilReadMaster  => axilReadMasters(1),
         axilReadSlave   => axilReadSlaves(1),
         axilWriteMaster => axilWriteMasters(1),
         axilWriteSlave  => axilWriteSlaves(1),
         -- DRP Interface
         drpClk          => axilClk,
         drpRst          => axilRst,
         drpRdy          => drpRdy,
         drpEn           => drpEn,
         drpWe           => drpWe,
         drpAddr         => drpAddr,
         drpDi           => drpDi,
         drpDo           => drpDo);

   GEN_DISABLE_GT : if (DISABLE_TIME_GT_G = true) generate

      U_TERM : entity surf.Gthe4ChannelDummy
         generic map (
            TPD_G   => TPD_G,
            WIDTH_G => 1)
         port map (
            refClk   => axilClk,
            gtRxP(0) => gtRxP,
            gtRxN(0) => gtRxN,
            gtTxP(0) => gtTxP,
            gtTxN(0) => gtTxN);

      bypassdone         <= '1';
      bypasserr          <= '0';
      rxCdrStable        <= '1';
      txStatus.resetDone <= '1';
      rxStatus.resetDone <= '1';
      drpDo              <= (others => '0');
      drpRdy             <= '1';
      rxCtrl0Out         <= (others => '0');
      rxCtrl1Out         <= (others => '0');
      rxCtrl3Out         <= (others => '0');
      rxData             <= txData;
      rxDataK            <= txDataK;
      rxDispErr          <= (others => '0');
      rxDecErr           <= (others => '0');
      txoutclkb          <= gtRefClkDiv2;
      rxoutclkb          <= gtRefClkDiv2;
      rxoutclk_out       <= gtRefClkDiv2;
      txoutclk_out       <= gtRefClkDiv2;

   end generate;

   GEN_EXTREF : if (DISABLE_TIME_GT_G = false) and (EXTREF_G = true)generate
      U_TimingGthCore : TimingGth_extref
         port map (
            gtwiz_userclk_tx_reset_in(0)          => txbypassrst,
            gtwiz_userclk_tx_active_in(0)         => txUsrClkActive,
            gtwiz_userclk_rx_active_in(0)         => rxUsrClkActive,
            gtwiz_buffbypass_tx_reset_in(0)       => txbypassrst,
            gtwiz_buffbypass_tx_start_user_in(0)  => '0',
            gtwiz_buffbypass_tx_done_out          => open,
            gtwiz_buffbypass_tx_error_out         => open,
            gtwiz_buffbypass_rx_reset_in(0)       => rxbypassrst,
            gtwiz_buffbypass_rx_start_user_in(0)  => '0',
            gtwiz_buffbypass_rx_done_out(0)       => bypassdone,
            gtwiz_buffbypass_rx_error_out(0)      => bypasserr,
            gtwiz_reset_clk_freerun_in(0)         => freeRunClk,
            gtwiz_reset_all_in(0)                 => stableRst,
            gtwiz_reset_tx_pll_and_datapath_in(0) => txControl.pllReset,
            gtwiz_reset_tx_datapath_in(0)         => txControl.reset,
            gtwiz_reset_rx_pll_and_datapath_in(0) => rxControl.pllReset,
            gtwiz_reset_rx_datapath_in(0)         => rxRst,
            gtwiz_reset_rx_cdr_stable_out(0)      => rxCdrStable,
            gtwiz_reset_tx_done_out(0)            => txStatus.resetDone,
            gtwiz_reset_rx_done_out(0)            => rxStatus.resetDone,
            gtwiz_userdata_tx_in                  => txData,
            gtwiz_userdata_rx_out                 => rxData,
            drpaddr_in                            => drpAddr,
            drpclk_in(0)                          => axilClk,
            drpdi_in                              => drpDi,
            drpen_in(0)                           => drpEn,
            drpwe_in(0)                           => drpWe,
            gthrxn_in(0)                          => gtRxN,
            gthrxp_in(0)                          => gtRxP,
            gtrefclk0_in(0)                       => gtRefClk,
            loopback_in                           => loopback,
            rx8b10ben_in(0)                       => '1',
            rxcommadeten_in(0)                    => '1',
            rxmcommaalignen_in(0)                 => '1',
            rxpcommaalignen_in(0)                 => '1',
            rxpolarity_in(0)                      => rxControl.polarity,
            rxusrclk_in(0)                        => rxUsrClk,
            rxusrclk2_in(0)                       => rxUsrClk,
            tx8b10ben_in(0)                       => '1',
            txctrl0_in                            => X"0000",
            txctrl1_in                            => X"0000",
            txctrl2_in(1 downto 0)                => txDataK,
            txctrl2_in(7 downto 2)                => (others => '0'),
            txinhibit_in(0)                       => txControl.inhibit,
            txpolarity_in(0)                      => txControl.polarity,
            txusrclk_in(0)                        => txUsrClk,
            txusrclk2_in(0)                       => txUsrClk,
            drpdo_out                             => drpDo,
            drprdy_out(0)                         => drpRdy,
            gthtxn_out(0)                         => gtTxN,
            gthtxp_out(0)                         => gtTxP,
            rxbyteisaligned_out                   => open,
            rxbyterealign_out                     => open,
            rxcommadet_out                        => open,
            rxctrl0_out                           => rxCtrl0Out,
            rxctrl1_out                           => rxCtrl1Out,
            rxctrl2_out                           => open,
            rxctrl3_out                           => rxCtrl3Out,
            rxoutclk_out(0)                       => rxoutclk_out,
            rxpmaresetdone_out                    => open,
            txoutclk_out(0)                       => txoutclk_out,
            txpmaresetdone_out                    => open);

      rxDataK   <= rxCtrl0Out(1 downto 0);
      rxDispErr <= rxCtrl1Out(1 downto 0);
      rxDecErr  <= rxCtrl3Out(1 downto 0);

      TIMING_FRCLK_BUFG_GT : BUFG_GT
         port map (
            I       => stableClk,
            CE      => '1',
            CEMASK  => '1',
            CLR     => '0',
            CLRMASK => '1',
            DIV     => "000",           -- Divide-by-1
            O       => freeRunClk);
      
      txoutclkb <= gtRefClkDiv2;

      TIMING_RECCLK_BUFG_GT : BUFG_GT
         port map (
            I       => rxoutclk_out,
            CE      => '1',
            CEMASK  => '1',
            CLR     => '0',
            CLRMASK => '1',
            DIV     => "000",           -- Divide-by-1
            O       => rxoutclkb);
   end generate;

   LOCREF_G : if (DISABLE_TIME_GT_G = false) and (EXTREF_G = false)generate
      U_TimingGthCore : TimingGth_fixedlat
         port map (
            gtwiz_userclk_tx_reset_in(0)          => txbypassrst,
            gtwiz_userclk_tx_active_in(0)         => txUsrClkActive,
            gtwiz_userclk_rx_active_in(0)         => rxUsrClkActive,
            gtwiz_buffbypass_tx_reset_in(0)       => txbypassrst,
            gtwiz_buffbypass_tx_start_user_in(0)  => '0',
            gtwiz_buffbypass_tx_done_out          => open,
            gtwiz_buffbypass_tx_error_out         => open,
            gtwiz_buffbypass_rx_reset_in(0)       => rxbypassrst,
            gtwiz_buffbypass_rx_start_user_in(0)  => '0',
            gtwiz_buffbypass_rx_done_out(0)       => bypassdone,
            gtwiz_buffbypass_rx_error_out(0)      => bypasserr,
            gtwiz_reset_clk_freerun_in(0)         => freeRunClk,
            gtwiz_reset_all_in(0)                 => stableRst,
            gtwiz_reset_tx_pll_and_datapath_in(0) => txControl.pllReset,
            gtwiz_reset_tx_datapath_in(0)         => txControl.reset,
            gtwiz_reset_rx_pll_and_datapath_in(0) => rxControl.pllReset,
            gtwiz_reset_rx_datapath_in(0)         => rxRst,
            gtwiz_reset_rx_cdr_stable_out(0)      => rxCdrStable,
            gtwiz_reset_tx_done_out(0)            => txStatus.resetDone,
            gtwiz_reset_rx_done_out(0)            => rxStatus.resetDone,
            gtwiz_userdata_tx_in                  => txData,
            gtwiz_userdata_rx_out                 => rxData,
            cpllrefclksel_in                      => cpllRefClkSel,
            drpaddr_in                            => drpAddr,
            drpclk_in(0)                          => axilClk,
            drpdi_in                              => drpDi,
            drpen_in(0)                           => drpEn,
            drpwe_in(0)                           => drpWe,
            gtgrefclk_in(0)                       => gtgRefClk,
            gthrxn_in(0)                          => gtRxN,
            gthrxp_in(0)                          => gtRxP,
            gtrefclk0_in(0)                       => gtRefClk,
            loopback_in                           => loopback,
            rx8b10ben_in(0)                       => '1',
            rxcommadeten_in(0)                    => '1',
            rxmcommaalignen_in(0)                 => '1',
            rxpcommaalignen_in(0)                 => '1',
            rxpolarity_in(0)                      => rxControl.polarity,
            rxusrclk_in(0)                        => rxUsrClk,
            rxusrclk2_in(0)                       => rxUsrClk,
            tx8b10ben_in(0)                       => '1',
            txctrl0_in                            => X"0000",
            txctrl1_in                            => X"0000",
            txctrl2_in(1 downto 0)                => txDataK,
            txctrl2_in(7 downto 2)                => (others => '0'),
            txinhibit_in(0)                       => txControl.inhibit,
            txpolarity_in(0)                      => txControl.polarity,
            txusrclk_in(0)                        => txUsrClk,
            txusrclk2_in(0)                       => txUsrClk,
            drpdo_out                             => drpDo,
            drprdy_out(0)                         => drpRdy,
            gthtxn_out(0)                         => gtTxN,
            gthtxp_out(0)                         => gtTxP,
            rxbyteisaligned_out                   => open,
            rxbyterealign_out                     => open,
            rxcommadet_out                        => open,
            rxctrl0_out                           => rxCtrl0Out,
            rxctrl1_out                           => rxCtrl1Out,
            rxctrl2_out                           => open,
            rxctrl3_out                           => rxCtrl3Out,
            rxoutclk_out(0)                       => rxoutclk_out,
            rxpmaresetdone_out                    => open,
            txoutclk_out(0)                       => txoutclk_out,
            txpmaresetdone_out                    => open);

      rxDataK   <= rxCtrl0Out(1 downto 0);
      rxDispErr <= rxCtrl1Out(1 downto 0);
      rxDecErr  <= rxCtrl3Out(1 downto 0);

--      TIMING_TXCLK_BUFG_GT : BUFG_GT
--         port map (
--            I       => txoutclk_out,
--            CE      => '1',
--            CEMASK  => '1',
--            CLR     => '0',
--            CLRMASK => '1',
--            DIV     => "001",           -- Divide-by-2
--            O       => txoutclkb);
      txoutclkb <= gtRefClkDiv2;

      TIMING_RECCLK_BUFG_GT : BUFG_GT
         port map (
            I       => rxoutclk_out,
            CE      => '1',
            CEMASK  => '1',
            CLR     => '0',
            CLRMASK => '1',
            DIV     => "000",           -- Divide-by-1
            O       => rxoutclkb);
   end generate;

   U_RstSyncTx : entity surf.RstSync
      generic map (TPD_G => TPD_G)
      port map (clk      => txoutclkb,
                asyncRst => txControl.reset,
                syncRst  => txbypassrst);

   U_RstSyncRx : entity surf.RstSync
      generic map (TPD_G => TPD_G)
      port map (clk      => rxoutclkb,
                asyncRst => rxRst,
                syncRst  => rxbypassrst);

--   txRst    <= txControl.reset;
--   rxRst    <= rxControl.reset;

   txOutClk <= txoutclkb;
   rxOutClk <= rxoutclkb;

end architecture rtl;
