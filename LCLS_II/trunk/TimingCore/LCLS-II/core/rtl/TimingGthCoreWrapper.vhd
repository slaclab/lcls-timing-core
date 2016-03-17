-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingGthCoreWrapper.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-06-09
-- Last update: 2016-03-03
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: 
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
use work.StdRtlPkg.all;

library unisim;
use unisim.vcomponents.all;

entity TimingGthCoreWrapper is

  generic (
    TPD_G    : time := 1 ns;
    EXTREF_G : boolean := false);

  port (
    stableClk : in  sl;
    -- GTH FPGA IO
    gtRefClk  : in  sl;
    gtRxP     : in  sl;
    gtRxN     : in  sl;
    gtTxP     : out sl;
    gtTxN     : out sl;

    -- Rx ports
    rxReset        : in  sl;
    rxUsrClkActive : in  sl;
    rxCdrStable    : out sl;
    rxResetDone    : out sl;
    rxUsrClk       : in  sl;
    rxPolarity     : in  sl := '0';
    rxData         : out slv(15 downto 0);
    rxDataK        : out slv(1 downto 0);
    rxDispErr      : out slv(1 downto 0);
    rxDecErr       : out slv(1 downto 0);
    rxOutClk       : out sl;

    -- Tx Ports
    txInhibit      : in  sl;
    txPolarity     : in  sl;
    txReset        : in  sl;
    txUsrClk       : in  sl;
    txUsrClkActive : in  sl;
    txResetDone    : out sl;
    txData         : in  slv(15 downto 0);
    txDataK        : in  slv(1 downto 0);
    txOutClk       : out sl;

    loopback : in slv(2 downto 0)
    );
end entity TimingGthCoreWrapper;

architecture rtl of TimingGthCoreWrapper is
  component TimingGth_clksel
    port (
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
      drpclk_in                          : in  std_logic_vector(0 downto 0);
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
      gthtxn_out                         : out std_logic_vector(0 downto 0);
      gthtxp_out                         : out std_logic_vector(0 downto 0);
      rxbyteisaligned_out                : out std_logic_vector(0 downto 0);
      rxbyterealign_out                  : out std_logic_vector(0 downto 0);
      rxcommadet_out                     : out std_logic_vector(0 downto 0);
      rxctrl0_out                        : out std_logic_vector(15 downto 0);
      rxctrl1_out                        : out std_logic_vector(15 downto 0);
      rxctrl2_out                        : out std_logic_vector(7 downto 0);
      rxctrl3_out                        : out std_logic_vector(7 downto 0);
      rxoutclk_out                       : out std_logic_vector(0 downto 0);
      rxpmaresetdone_out                 : out std_logic_vector(0 downto 0);
      txoutclk_out                       : out std_logic_vector(0 downto 0);
      txpmaresetdone_out                 : out std_logic_vector(0 downto 0)
      );
  end component;
  component TimingGth_polarity
    port (
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
      drpclk_in                          : in  std_logic_vector(0 downto 0);
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
      gthtxn_out                         : out std_logic_vector(0 downto 0);
      gthtxp_out                         : out std_logic_vector(0 downto 0);
      rxbyteisaligned_out                : out std_logic_vector(0 downto 0);
      rxbyterealign_out                  : out std_logic_vector(0 downto 0);
      rxcommadet_out                     : out std_logic_vector(0 downto 0);
      rxctrl0_out                        : out std_logic_vector(15 downto 0);
      rxctrl1_out                        : out std_logic_vector(15 downto 0);
      rxctrl2_out                        : out std_logic_vector(7 downto 0);
      rxctrl3_out                        : out std_logic_vector(7 downto 0);
      rxoutclk_out                       : out std_logic_vector(0 downto 0);
      rxpmaresetdone_out                 : out std_logic_vector(0 downto 0);
      txoutclk_out                       : out std_logic_vector(0 downto 0);
      txpmaresetdone_out                 : out std_logic_vector(0 downto 0)
      );
  end component;

  signal rxCtrl0Out : slv(15 downto 0);
  signal rxCtrl1Out : slv(15 downto 0);
  signal rxCtrl3Out : slv( 7 downto 0);
  signal txoutclk_out : sl;
  signal rxoutclk_out : sl;
  
begin

  GEN_EXTREF: if EXTREF_G generate
    U_TimingGthCore : TimingGth_clksel
      port map (
        gtwiz_userclk_tx_active_in(0)         => txUsrClkActive,
        gtwiz_userclk_rx_active_in(0)         => rxUsrClkActive,
        gtwiz_buffbypass_tx_reset_in(0)       => '0',
        gtwiz_buffbypass_tx_start_user_in(0)  => '0',
        gtwiz_buffbypass_tx_done_out          => open,
        gtwiz_buffbypass_tx_error_out         => open,
        gtwiz_buffbypass_rx_reset_in(0)       => '0',
        gtwiz_buffbypass_rx_start_user_in(0)  => '0',
        gtwiz_buffbypass_rx_done_out          => open,  -- Might need this
        gtwiz_buffbypass_rx_error_out         => open,  -- Might need this
        gtwiz_reset_clk_freerun_in(0)         => stableClk,
        gtwiz_reset_all_in(0)                 => '0',
        gtwiz_reset_tx_pll_and_datapath_in(0) => '0',
        gtwiz_reset_tx_datapath_in(0)         => txReset,
        gtwiz_reset_rx_pll_and_datapath_in(0) => rxReset,
        gtwiz_reset_rx_datapath_in(0)         => '0',
        gtwiz_reset_rx_cdr_stable_out(0)      => rxCdrStable,
        gtwiz_reset_tx_done_out(0)            => txResetDone,
        gtwiz_reset_rx_done_out(0)            => rxResetDone,
        gtwiz_userdata_tx_in                  => txData,
        gtwiz_userdata_rx_out                 => rxData,
        drpclk_in(0)                          => stableClk,
        gthrxn_in(0)                          => gtRxN,
        gthrxp_in(0)                          => gtRxP,
        gtrefclk0_in(0)                       => gtRefClk,
        loopback_in                           => loopback,
        rx8b10ben_in(0)                       => '1',
        rxcommadeten_in(0)                    => '1',
        rxmcommaalignen_in(0)                 => '1',
        rxpcommaalignen_in(0)                 => '1',
        rxpolarity_in(0)                      => rxPolarity,
        rxusrclk_in(0)                        => rxUsrClk,
        rxusrclk2_in(0)                       => rxUsrClk,
        tx8b10ben_in(0)                       => '1',
        txctrl0_in                            => X"0000",
        txctrl1_in                            => X"0000",
        txctrl2_in(1 downto 0)                => txDataK,
        txctrl2_in(7 downto 2)                => (others => '0'),
        txinhibit_in(0)                       => txInhibit,
        txpolarity_in(0)                      => txPolarity,
        txusrclk_in(0)                        => txUsrClk,
        txusrclk2_in(0)                       => txUsrClk,
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

    TIMING_TXCLK_BUFG_GT : BUFG_GT
      port map (
        I       => txoutclk_out,
        CE      => '1',
        CEMASK  => '1',
        CLR     => '0',
        CLRMASK => '1',
        DIV     => "000",              -- Divide-by-1
        O       => txOutClk);

    TIMING_RECCLK_BUFG_GT : BUFG_GT
      port map (
        I       => rxoutclk_out,
        CE      => '1',
        CEMASK  => '1',
        CLR     => '0',
        CLRMASK => '1',
        DIV     => "000",              -- Divide-by-1
        O       => rxOutClk);
  end generate;

  LOCREF_G: if not EXTREF_G generate
    U_TimingGthCore : TimingGth_polarity
      port map (
--         gtwiz_userclk_tx_reset_in(0)          => txReset,
        gtwiz_userclk_tx_active_in(0)         => txUsrClkActive,
        gtwiz_userclk_rx_active_in(0)         => rxUsrClkActive,
        gtwiz_buffbypass_tx_reset_in(0)       => '0',
        gtwiz_buffbypass_tx_start_user_in(0)  => '0',
        gtwiz_buffbypass_tx_done_out          => open,
        gtwiz_buffbypass_tx_error_out         => open,
        gtwiz_buffbypass_rx_reset_in(0)       => '0',
        gtwiz_buffbypass_rx_start_user_in(0)  => '0',
        gtwiz_buffbypass_rx_done_out          => open,  -- Might need this
        gtwiz_buffbypass_rx_error_out         => open,  -- Might need this
        gtwiz_reset_clk_freerun_in(0)         => stableClk,
        gtwiz_reset_all_in(0)                 => '0',
        gtwiz_reset_tx_pll_and_datapath_in(0) => '0',
        gtwiz_reset_tx_datapath_in(0)         => txReset,
        gtwiz_reset_rx_pll_and_datapath_in(0) => rxReset,
        gtwiz_reset_rx_datapath_in(0)         => '0',
        gtwiz_reset_rx_cdr_stable_out(0)      => rxCdrStable,
        gtwiz_reset_tx_done_out(0)            => txResetDone,
        gtwiz_reset_rx_done_out(0)            => rxResetDone,
        gtwiz_userdata_tx_in                  => txData,
        gtwiz_userdata_rx_out                 => rxData,
        drpclk_in(0)                          => stableClk,
        gthrxn_in(0)                          => gtRxN,
        gthrxp_in(0)                          => gtRxP,
        gtrefclk0_in(0)                       => gtRefClk,
        loopback_in                           => loopback,
        rx8b10ben_in(0)                       => '1',
        rxcommadeten_in(0)                    => '1',
        rxmcommaalignen_in(0)                 => '1',
        rxpcommaalignen_in(0)                 => '1',
        rxpolarity_in(0)                      => rxPolarity,
        rxusrclk_in(0)                        => rxUsrClk,
        rxusrclk2_in(0)                       => rxUsrClk,
        tx8b10ben_in(0)                       => '1',
        txctrl0_in                            => X"0000",
        txctrl1_in                            => X"0000",
        txctrl2_in(1 downto 0)                => txDataK,
        txctrl2_in(7 downto 2)                => (others => '0'),
        txinhibit_in(0)                       => txInhibit,
        txpolarity_in(0)                      => txPolarity,
        txusrclk_in(0)                        => txUsrClk,
        txusrclk2_in(0)                       => txUsrClk,
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

    TIMING_TXCLK_BUFG_GT : BUFG_GT
      port map (
        I       => txoutclk_out,
        CE      => '1',
        CEMASK  => '1',
        CLR     => '0',
        CLRMASK => '1',
        DIV     => "001",              -- Divide-by-2
        O       => txOutClk);

    TIMING_RECCLK_BUFG_GT : BUFG_GT
      port map (
        I       => rxoutclk_out,
        CE      => '1',
        CEMASK  => '1',
        CLR     => '0',
        CLRMASK => '1',
        DIV     => "000",              -- Divide-by-1
        O       => rxOutClk);
  end generate;
end architecture rtl;
