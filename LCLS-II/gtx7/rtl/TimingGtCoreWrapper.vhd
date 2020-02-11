-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Wrapper for GTX7 Core
-------------------------------------------------------------------------------
-- This file is part of 'LCLS2 Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS2 Timing Core', including this file, 
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

entity TimingGtCoreWrapper is
   generic (
      TPD_G             : time       := 1 ns;
      CPLL_REFCLK_SEL_G : bit_vector := "001";
      REFCLK_G          : boolean    := false;  --  FALSE: use gtRefClkP/N,  TRUE: use gtRefClkIn
      GT_CONFIG_G       : boolean    := true);  -- V1 = false, V2 = true    
   port (
      -- AXI-Lite Port
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType;
      -- GT Ports
      gtRefClkP       : in  sl := '0';  -- GT_CONFIG_G=true(371 MHz), GT_CONFIG_G=false(238 MHz)
      gtRefClkN       : in  sl := '1';
      gtRxP           : in  sl;
      gtRxN           : in  sl;
      gtTxP           : out sl;
      gtTxN           : out sl;
      gtRefClkIn      : in  sl := '0';  -- used with REFCLK_G = true
      stableClk       : in  sl := '0';  -- used with REFCLK_G = true
      stableRst       : in  sl := '0';  -- used with REFCLK_G = true
      -- Rx ports
      rxControl       : in  TimingPhyControlType;
      rxStatus        : out TimingPhyStatusType;
      rxOutClk        : out sl;
      rxOutRst        : out sl;
      rxData          : out slv(15 downto 0);
      rxDataK         : out slv(1 downto 0);
      rxDispErr       : out slv(1 downto 0);
      rxDecErr        : out slv(1 downto 0);
      -- Tx Ports
      txControl       : in  TimingPhyControlType;
      txStatus        : out TimingPhyStatusType;
      txOutClk        : out sl;
      txOutRst        : out sl;
      txData          : in  slv(15 downto 0);
      txDataK         : in  slv(1 downto 0);
      -- Misc. 
      loopback        : in  slv(2 downto 0));
end entity TimingGtCoreWrapper;

architecture rtl of TimingGtCoreWrapper is

   constant CPLL_FBDIV_C        : integer    := ite(GT_CONFIG_G, 1, 2);
   constant CPLL_FBDIV_45_C     : integer    := 5;
   constant CPLL_REFCLK_DIV_C   : integer    := 1;
   constant RXOUT_DIV_C         : integer    := ite(GT_CONFIG_G, 1, 2);
   constant TXOUT_DIV_C         : integer    := ite(GT_CONFIG_G, 1, 2);
   constant RX_CLK25_DIV_C      : integer    := ite(GT_CONFIG_G, 15, 10);
   constant TX_CLK25_DIV_C      : integer    := ite(GT_CONFIG_G, 15, 10);
--   constant RXCDR_CFG_C       : bit_vector := ite(GT_CONFIG_G, x"03000023ff20400020", x"03000023ff40200020");
   --  compensate for sync clock jitter
   constant RXCDR_CFG_C         : bit_vector := ite(GT_CONFIG_G, x"03800023ff10200020", x"03000023ff40200020");
   constant STABLE_CLK_PERIOD_C : real       := 4.0E-9;

   signal gtRefClk      : sl               := '0';
   signal gtRefClkDiv2  : sl               := '0';
   signal iStableClk    : sl               := '0';
   signal iStableRst    : sl               := '0';
   signal rxRst         : sl               := '0';
   signal gtRxResetDone : sl               := '0';
   signal dataValid     : sl               := '0';
   signal gtRxRecClk    : sl               := '0';
   signal linkUp        : sl               := '0';
   signal decErr        : slv(1 downto 0)  := (others => '0');
   signal dispErr       : slv(1 downto 0)  := (others => '0');
   signal cnt           : slv(23 downto 0) := (others => '0');
   signal gtRxData      : slv(19 downto 0) := (others => '0');
   signal data          : slv(15 downto 0) := (others => '0');
   signal dataK         : slv(1 downto 0)  := (others => '0');

   signal txResetDone : sl := '0';
   signal txUsrClk    : sl := '0';
   signal txClk       : sl := '0';

   signal drpRdy  : sl               := '0';
   signal drpEn   : sl               := '0';
   signal drpWe   : sl               := '0';
   signal drpAddr : slv(8 downto 0)  := (others => '0');
   signal drpDi   : slv(15 downto 0) := (others => '0');
   signal drpDo   : slv(15 downto 0) := (others => '0');


begin

   rxStatus.locked       <= linkUp;
   rxStatus.resetDone    <= gtRxResetDone;
   rxStatus.bufferByDone <= gtRxResetDone;
   rxStatus.bufferByErr  <= not(dataValid) and linkUp;

   txStatus.locked       <= txResetDone;
   txStatus.resetDone    <= txResetDone;
   txStatus.bufferByDone <= txResetDone;
   txStatus.bufferByErr  <= '0';

   rxOutClk <= gtRxRecClk;
   U_rxOutRst : entity surf.RstSync
      generic map (
         TPD_G         => TPD_G,
         IN_POLARITY_G => '0')
      port map (
         clk      => gtRxRecClk,
         asyncRst => gtRxResetDone,
         syncRst  => rxOutRst);

   txOutClk <= txUsrClk;
   U_txOutRst : entity surf.RstSync
      generic map (
         TPD_G         => TPD_G,
         IN_POLARITY_G => '0')
      port map (
         clk      => txUsrClk,
         asyncRst => txResetDone,
         syncRst  => txOutRst);
   
   INT_REFCLK : if (REFCLK_G = false) generate
   
      U_IBUFDS_GTE2 : IBUFDS_GTE2
         port map (
            I     => gtRefClkP,
            IB    => gtRefClkN,
            CEB   => '0',
            ODIV2 => gtRefClkDiv2,
            O     => gtRefClk);

      U_BUFG : BUFG
         port map (
            I => gtRefClkDiv2,
            O => iStableClk);
      
      U_PwrUpRst : entity surf.PwrUpRst
         generic map(
            TPD_G => TPD_G)
         port map (
            clk    => iStableClk,
            rstOut => iStableRst);
      
   end generate;
   
   EXT_REFCLK : if (REFCLK_G = true) generate
   
      iStableClk <= stableClk;
      iStableRst <= stableRst;
      gtRefClk <= gtRefClkIn;
   
   end generate;

   

   U_Decoder8b10b : entity surf.Decoder8b10b
      generic map (
         TPD_G          => TPD_G,
         RST_POLARITY_G => '0',         -- Active low polarity
         NUM_BYTES_G    => 2)
      port map (
         clk      => gtRxRecClk,
         rst      => gtRxResetDone,
         dataIn   => gtRxData,
         dataOut  => data,
         dataKOut => dataK,
         codeErr  => decErr,
         dispErr  => dispErr);

   rxData    <= data    when(linkUp = '1') else (others => '0');
   rxDataK   <= dataK   when(linkUp = '1') else (others => '0');
   rxDispErr <= decErr  when(linkUp = '1') else (others => '0');
   rxDecErr  <= dispErr when(linkUp = '1') else (others => '0');
   dataValid <= not (uOr(decErr) or uOr(dispErr));

   rxRst <= iStableRst or rxControl.reset;

   process(gtRxRecClk, gtRxResetDone)
   begin
      if gtRxResetDone = '0' then
         cnt    <= (others => '0') after TPD_G;
         linkUp <= '0'             after TPD_G;
      elsif rising_edge(gtRxRecClk) then
         if cnt = x"0000FF" then
            linkUp <= '1' after TPD_G;
         end if;
         cnt <= cnt + 1 after TPD_G;
      end if;
   end process;

   TxBUFG_Inst : BUFG
      port map (
         I => txClk,
         O => txUsrClk);

   U_Gtx : entity surf.Gtx7Core
      generic map (
         TPD_G                 => TPD_G,
         SIM_GTRESET_SPEEDUP_G => "FALSE",
         SIM_VERSION_G         => "4.0",
         SIMULATION_G          => false,
         STABLE_CLOCK_PERIOD_G => STABLE_CLK_PERIOD_C,
         CPLL_REFCLK_SEL_G     => CPLL_REFCLK_SEL_G,
         CPLL_FBDIV_G          => CPLL_FBDIV_C,
         CPLL_FBDIV_45_G       => CPLL_FBDIV_45_C,
         CPLL_REFCLK_DIV_G     => CPLL_REFCLK_DIV_C,
         RXOUT_DIV_G           => RXOUT_DIV_C,
         TXOUT_DIV_G           => TXOUT_DIV_C,
         RX_CLK25_DIV_G        => RX_CLK25_DIV_C,
         TX_CLK25_DIV_G        => TX_CLK25_DIV_C,
         TX_PLL_G              => "CPLL",
         RX_PLL_G              => "CPLL",
         TX_EXT_DATA_WIDTH_G   => 16,
         TX_INT_DATA_WIDTH_G   => 20,
         TX_8B10B_EN_G         => true,
         RX_EXT_DATA_WIDTH_G   => 20,
         RX_INT_DATA_WIDTH_G   => 20,
         RX_8B10B_EN_G         => false,
         TX_BUF_EN_G           => false,
         TX_OUTCLK_SRC_G       => "OUTCLKPMA",
         TX_DLY_BYPASS_G       => '1',
         TX_PHASE_ALIGN_G      => "NONE",
         RX_BUF_EN_G           => false,
         RX_OUTCLK_SRC_G       => "OUTCLKPMA",
         RX_USRCLK_SRC_G       => "RXOUTCLK",
         RX_DLY_BYPASS_G       => '1',
         RX_DDIEN_G            => '1',
         RX_ALIGN_MODE_G       => "FIXED_LAT",
         RX_DFE_KL_CFG2_G      => X"301148AC",
         RX_OS_CFG_G           => "0000010000000",
         RXCDR_CFG_G           => RXCDR_CFG_C,
         RXDFEXYDEN_G          => '1',
         RX_EQUALIZER_G        => "DFE",
         RXSLIDE_MODE_G        => "PMA",
         FIXED_COMMA_EN_G      => "0011",
         FIXED_ALIGN_COMMA_0_G => "----------0101111100",  -- Normal Comma
         FIXED_ALIGN_COMMA_1_G => "----------1010000011",  -- Inverted Comma
         FIXED_ALIGN_COMMA_2_G => "XXXXXXXXXXXXXXXXXXXX",  -- Unused
         FIXED_ALIGN_COMMA_3_G => "XXXXXXXXXXXXXXXXXXXX")  -- Unused         
      port map (
         stableClkIn      => iStableClk,
         cPllRefClkIn     => gtRefClk,
         cPllLockOut      => open,
         qPllRefClkIn     => '0',
         qPllClkIn        => '0',
         qPllLockIn       => '1',
         qPllRefClkLostIn => '0',
         qPllResetOut     => open,
         gtRxRefClkBufg   => iStableClk,
         -- Serial IO
         gtTxP            => gtTxP,
         gtTxN            => gtTxN,
         gtRxP            => gtRxP,
         gtRxN            => gtRxN,
         -- Rx Clock related signals
         rxOutClkOut      => gtRxRecClk,
         rxUsrClkIn       => gtRxRecClk,
         rxUsrClk2In      => gtRxRecClk,
         rxUserRdyOut     => open,
         rxMmcmResetOut   => open,
         rxMmcmLockedIn   => '1',
         -- Rx User Reset Signals
         rxUserResetIn    => rxRst,
         rxResetDoneOut   => gtRxResetDone,
         -- Manual Comma Align signals
         rxDataValidIn    => dataValid,
         rxSlideIn        => '0',
         -- Rx Data and decode signals
         rxDataOut        => gtRxData,
         rxCharIsKOut     => open,
         rxDecErrOut      => open,
         rxDispErrOut     => open,
         rxPolarityIn     => rxControl.polarity,
         rxBufStatusOut   => open,
         -- Rx Channel Bonding
         rxChBondLevelIn  => (others => '0'),
         rxChBondIn       => (others => '0'),
         rxChBondOut      => open,
         -- Tx Clock Related Signals
         txOutClkOut      => txClk,
         txUsrClkIn       => txUsrClk,
         txUsrClk2In      => txUsrClk,
         txUserRdyOut     => open,
         txMmcmResetOut   => open,
         txMmcmLockedIn   => '1',
         -- Tx User Reset signals
         txUserResetIn    => iStableRst,
         --txResetDoneOut   => open,
         txResetDoneOut   => txResetDone,
         -- Tx Data
         txDataIn         => txData,
         txCharIsKIn      => txDataK,
         txBufStatusOut   => open,
         txPolarityIn     => txControl.polarity,
         -- Misc.
         loopbackIn       => loopback,
         txPowerDown      => (others => txControl.inhibit),
         rxPowerDown      => (others => '0'),
         -- DRP Interface (drpClk Domain)      
         drpClk           => axilClk,
         drpRdy           => drpRdy,
         drpEn            => drpEn,
         drpWe            => drpWe,
         drpAddr          => drpAddr,
         drpDi            => drpDi,
         drpDo            => drpDo);

   U_AxiLiteToDrp : entity surf.AxiLiteToDrp
      generic map (
         TPD_G            => TPD_G,
         COMMON_CLK_G     => true,
         EN_ARBITRATION_G => false,
         TIMEOUT_G        => 4096,
         ADDR_WIDTH_G     => 9,
         DATA_WIDTH_G     => 16)
      port map (
         -- AXI-Lite Port
         axilClk         => axilClk,
         axilRst         => axilRst,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave,
         -- DRP Interface
         drpClk          => axilClk,
         drpRst          => axilRst,
         drpRdy          => drpRdy,
         drpEn           => drpEn,
         drpWe           => drpWe,
         drpAddr         => drpAddr,
         drpDi           => drpDi,
         drpDo           => drpDo);

end architecture rtl;
