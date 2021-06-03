-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Wrapper for GTX7 Core
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

entity TimingGtCoreWrapper is
   generic (
      TPD_G       : time    := 1 ns;
      PLL_G       : string  := "PLL0";
      GT_CONFIG_G : boolean := true);   -- V1 = false, V2 = true
   port (
      -- AXI-Lite Port
      axilClk          : in  sl;
      axilRst          : in  sl;
      axilReadMaster   : in  AxiLiteReadMasterType;
      axilReadSlave    : out AxiLiteReadSlaveType;
      axilWriteMaster  : in  AxiLiteWriteMasterType;
      axilWriteSlave   : out AxiLiteWriteSlaveType;
      -- QPLL Ports
      gtQPllOutRefClk  : in  slv(1 downto 0);
      gtQPllOutClk     : in  slv(1 downto 0);
      gtQPllLock       : in  slv(1 downto 0);
      gtQPllRefClkLost : in  slv(1 downto 0);
      gtQPllReset      : out slv(1 downto 0);
      -- GT Ports
      gtRxP            : in  sl;
      gtRxN            : in  sl;
      gtTxP            : out sl;
      gtTxN            : out sl;
      stableClk        : in  sl;
      stableRst        : in  sl;
      -- Rx ports
      rxControl        : in  TimingPhyControlType;
      rxStatus         : out TimingPhyStatusType;
      rxOutClk         : out sl;
      rxOutRst         : out sl;
      rxData           : out slv(15 downto 0);
      rxDataK          : out slv(1 downto 0);
      rxDispErr        : out slv(1 downto 0);
      rxDecErr         : out slv(1 downto 0);
      -- Tx Ports
      txControl        : in  TimingPhyControlType;
      txStatus         : out TimingPhyStatusType;
      txOutClk         : out sl;
      txOutRst         : out sl;
      txData           : in  slv(15 downto 0);
      txDataK          : in  slv(1 downto 0);
      -- Misc.
      loopback         : in  slv(2 downto 0));
end entity TimingGtCoreWrapper;

architecture rtl of TimingGtCoreWrapper is

   constant RXOUT_DIV_C         : integer    := ite(GT_CONFIG_G, 1, 2);
   constant TXOUT_DIV_C         : integer    := ite(GT_CONFIG_G, 1, 2);
   constant RX_CLK25_DIV_C      : integer    := ite(GT_CONFIG_G, 8, 5);
   constant TX_CLK25_DIV_C      : integer    := ite(GT_CONFIG_G, 8, 5);
   constant RXCDR_CFG_C         : bit_vector := ite(GT_CONFIG_G, x"0000107FE406001041010", x"0000107FE206001041010");
   constant STABLE_CLK_PERIOD_C : real       := 4.0E-9;

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
   signal drpGnt  : sl               := '0';
   signal drpReq  : sl               := '0';
   signal drpAddr : slv(8 downto 0)  := (others => '0');
   signal drpDi   : slv(15 downto 0) := (others => '0');
   signal drpDo   : slv(15 downto 0) := (others => '0');

   signal iTxPowerDown : slv(1 downto 0);

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

   rxRst <= stableRst or rxControl.reset;

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

   U_Gtp : entity surf.Gtp7Core
      generic map (
         -- Simulation Generics
         TPD_G                 => 1 ns,
         SIM_GTRESET_SPEEDUP_G => "FALSE",
         SIM_VERSION_G         => "1.0",
         SIMULATION_G          => false,
         STABLE_CLOCK_PERIOD_G => STABLE_CLK_PERIOD_C,
         -- TX/RX Settings
         RXOUT_DIV_G           => RXOUT_DIV_C,
         TXOUT_DIV_G           => TXOUT_DIV_C,
         RX_CLK25_DIV_G        => RX_CLK25_DIV_C,
         TX_CLK25_DIV_G        => TX_CLK25_DIV_C,
         RX_OS_CFG_G           => "0000010000000",
         RXCDR_CFG_G           => RXCDR_CFG_C,
         RXLPM_INCM_CFG_G      => '1',
         RXLPM_IPCM_CFG_G      => '0',
         -- Configure PLL sources
         TX_PLL_G              => PLL_G,
         RX_PLL_G              => PLL_G,
         -- Configure Data widths
         RX_EXT_DATA_WIDTH_G   => 20,
         RX_INT_DATA_WIDTH_G   => 20,
         RX_8B10B_EN_G         => false,
         -- Configure RX comma alignment and buffer usage
         RX_ALIGN_MODE_G       => "FIXED_LAT",
         RX_BUF_EN_G           => false,
         RX_OUTCLK_SRC_G       => "OUTCLKPMA",
         RX_USRCLK_SRC_G       => "RXOUTCLK",
         RX_DLY_BYPASS_G       => '1',
         RX_DDIEN_G            => '0',
         RXSLIDE_MODE_G        => "PMA",
         -- Fixed Latency comma alignment (If RX_ALIGN_MODE_G = "FIXED_LAT")
         FIXED_COMMA_EN_G      => "0011",
         FIXED_ALIGN_COMMA_0_G => "----------0101111100",  -- Normal Comma
         FIXED_ALIGN_COMMA_1_G => "----------1010000011",  -- Inverted Comma
         FIXED_ALIGN_COMMA_2_G => "XXXXXXXXXXXXXXXXXXXX",  -- Unused
         FIXED_ALIGN_COMMA_3_G => "XXXXXXXXXXXXXXXXXXXX")  -- Unused 
      port map (
         stableClkIn      => stableClk,
         qPllRefClkIn     => gtQPllOutRefClk,
         qPllClkIn        => gtQPllOutClk,
         qPllLockIn       => gtQPllLock,
         qPllRefClkLostIn => gtQPllRefClkLost,
         qPllResetOut     => gtQPllReset,
         gtRxRefClkBufg   => stableClk,
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
         txUserResetIn    => stableRst,
         --txResetDoneOut   => open,
         txResetDoneOut   => txResetDone,
         -- Tx Data
         txDataIn         => txData,
         txCharIsKIn      => txDataK,
         txBufStatusOut   => open,
         txPolarityIn     => txControl.polarity,
         -- Misc.
         loopbackIn       => loopback,
         txPowerDown      => iTxPowerDown,
         rxPowerDown      => (others => '0'),
         -- DRP Interface (stableClkIn Domain)
         drpGnt           => drpGnt,
         drpRdy           => drpRdy,
         drpOverride      => drpReq,
         drpEn            => drpEn,
         drpWe            => drpWe,
         drpAddr          => drpAddr,
         drpDi            => drpDi,
         drpDo            => drpDo);

   iTxPowerDown <= (others => txControl.inhibit);

   U_AxiLiteToDrp : entity surf.AxiLiteToDrp
      generic map (
         TPD_G            => TPD_G,
         COMMON_CLK_G     => true,
         EN_ARBITRATION_G => true,
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
         drpGnt          => drpGnt,
         drpReq          => drpReq,
         drpRdy          => drpRdy,
         drpEn           => drpEn,
         drpWe           => drpWe,
         drpAddr         => drpAddr,
         drpDi           => drpDi,
         drpDo           => drpDo);

end architecture rtl;
