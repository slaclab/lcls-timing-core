-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingGthWrapper.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-16
-- Last update: 2015-09-16
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: 
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

use work.StdRtlPkg.all;

entity TimingGthWrapper is

   generic (
      TPD_G : time := 1 ns);

   port (
      gtRxP      : in  sl;
      gtRxN      : in  sl;
      gtTxP      : out sl;
      gtTxN      : out sl;
      gtRefClkIn : in  sl;

      gtReset   : in sl;
      stableClk : in sl;

      txUsrClk  : in  sl;
      txRstDone : out sl;
      txData    : in  slv(15 downto 0);
      txDataK   : in  slv(1 downto 0);

      rxUsrClk  : in  sl;
      rxRstDone : out sl;
      rxData    : out slv(15 downto 0);
      rxDataK   : out slv(1 downto 0);
      rxDispErr : out slv(1 downto 0);
      rxDecErr  : out slv(1 downto 0)
      );

end entity TimingGthWrapper;

architecture rtl of TimingGthWrapper is

   component TimingGth
      port (
         gtwiz_userclk_tx_reset_in          : in  slv(0 downto 0);
         gtwiz_userclk_tx_active_in         : in  slv(0 downto 0);
         gtwiz_userclk_rx_active_in         : in  slv(0 downto 0);
         gtwiz_buffbypass_tx_reset_in       : in  slv(0 downto 0);
         gtwiz_buffbypass_tx_start_user_in  : in  slv(0 downto 0);
         gtwiz_buffbypass_tx_done_out       : out slv(0 downto 0);
         gtwiz_buffbypass_tx_error_out      : out slv(0 downto 0);
         gtwiz_buffbypass_rx_reset_in       : in  slv(0 downto 0);
         gtwiz_buffbypass_rx_start_user_in  : in  slv(0 downto 0);
         gtwiz_buffbypass_rx_done_out       : out slv(0 downto 0);
         gtwiz_buffbypass_rx_error_out      : out slv(0 downto 0);
         gtwiz_reset_clk_freerun_in         : in  slv(0 downto 0);
         gtwiz_reset_all_in                 : in  slv(0 downto 0);
         gtwiz_reset_tx_pll_and_datapath_in : in  slv(0 downto 0);
         gtwiz_reset_tx_datapath_in         : in  slv(0 downto 0);
         gtwiz_reset_rx_pll_and_datapath_in : in  slv(0 downto 0);
         gtwiz_reset_rx_datapath_in         : in  slv(0 downto 0);
         gtwiz_reset_rx_cdr_stable_out      : out slv(0 downto 0);
         gtwiz_reset_tx_done_out            : out slv(0 downto 0);
         gtwiz_reset_rx_done_out            : out slv(0 downto 0);
         gtwiz_userdata_tx_in               : in  slv(15 downto 0);
         gtwiz_userdata_rx_out              : out slv(15 downto 0);
         drpclk_in                          : in  slv(0 downto 0);
         gthrxn_in                          : in  slv(0 downto 0);
         gthrxp_in                          : in  slv(0 downto 0);
         gtrefclk0_in                       : in  slv(0 downto 0);
         rx8b10ben_in                       : in  slv(0 downto 0);
         rxcommadeten_in                    : in  slv(0 downto 0);
         rxmcommaalignen_in                 : in  slv(0 downto 0);
         rxpcommaalignen_in                 : in  slv(0 downto 0);
         rxusrclk_in                        : in  slv(0 downto 0);
         rxusrclk2_in                       : in  slv(0 downto 0);
         tx8b10ben_in                       : in  slv(0 downto 0);
         txctrl0_in                         : in  slv(15 downto 0);
         txctrl1_in                         : in  slv(15 downto 0);
         txctrl2_in                         : in  slv(7 downto 0);
         txusrclk_in                        : in  slv(0 downto 0);
         txusrclk2_in                       : in  slv(0 downto 0);
         gthtxn_out                         : out slv(0 downto 0);
         gthtxp_out                         : out slv(0 downto 0);
         rxbyteisaligned_out                : out slv(0 downto 0);
         rxbyterealign_out                  : out slv(0 downto 0);
         rxcommadet_out                     : out slv(0 downto 0);
         rxctrl0_out                        : out slv(15 downto 0);
         rxctrl1_out                        : out slv(15 downto 0);
         rxctrl2_out                        : out slv(7 downto 0);
         rxctrl3_out                        : out slv(7 downto 0);
         rxoutclk_out                       : out slv(0 downto 0);
         rxpmaresetdone_out                 : out slv(0 downto 0);
         txoutclk_out                       : out slv(0 downto 0);
         txpmaresetdone_out                 : out slv(0 downto 0)
         );
   end component;

begin

   your_instance_name : TimingGth
      port map (
         gtwiz_userclk_tx_reset_in          => gtReset,
         gtwiz_userclk_tx_active_in         => '1',
         gtwiz_userclk_rx_active_in         => '1',
         gtwiz_buffbypass_tx_reset_in       => gtwiz_buffbypass_tx_reset_in,
         gtwiz_buffbypass_tx_start_user_in  => gtwiz_buffbypass_tx_start_user_in,
         gtwiz_buffbypass_tx_done_out       => gtwiz_buffbypass_tx_done_out,
         gtwiz_buffbypass_tx_error_out      => gtwiz_buffbypass_tx_error_out,
         gtwiz_buffbypass_rx_reset_in       => gtwiz_buffbypass_rx_reset_in,
         gtwiz_buffbypass_rx_start_user_in  => gtwiz_buffbypass_rx_start_user_in,
         gtwiz_buffbypass_rx_done_out       => gtwiz_buffbypass_rx_done_out,
         gtwiz_buffbypass_rx_error_out      => gtwiz_buffbypass_rx_error_out,
         gtwiz_reset_clk_freerun_in         => gtwiz_reset_clk_freerun_in,
         gtwiz_reset_all_in                 => gtwiz_reset_all_in,
         gtwiz_reset_tx_pll_and_datapath_in => gtwiz_reset_tx_pll_and_datapath_in,
         gtwiz_reset_tx_datapath_in         => gtwiz_reset_tx_datapath_in,
         gtwiz_reset_rx_pll_and_datapath_in => gtwiz_reset_rx_pll_and_datapath_in,
         gtwiz_reset_rx_datapath_in         => gtwiz_reset_rx_datapath_in,
         gtwiz_reset_rx_cdr_stable_out      => gtwiz_reset_rx_cdr_stable_out,
         gtwiz_reset_tx_done_out            => gtwiz_reset_tx_done_out,
         gtwiz_reset_rx_done_out            => gtwiz_reset_rx_done_out,
         gtwiz_userdata_tx_in               => gtwiz_userdata_tx_in,
         gtwiz_userdata_rx_out              => gtwiz_userdata_rx_out,
         drpclk_in                          => drpclk_in,
         gthrxn_in                          => gthrxn_in,
         gthrxp_in                          => gthrxp_in,
         gtrefclk0_in                       => gtrefclk0_in,
         rx8b10ben_in                       => rx8b10ben_in,
         rxcommadeten_in                    => rxcommadeten_in,
         rxmcommaalignen_in                 => rxmcommaalignen_in,
         rxpcommaalignen_in                 => rxpcommaalignen_in,
         rxusrclk_in                        => rxusrclk_in,
         rxusrclk2_in                       => rxusrclk2_in,
         tx8b10ben_in                       => tx8b10ben_in,
         txctrl0_in                         => txctrl0_in,
         txctrl1_in                         => txctrl1_in,
         txctrl2_in                         => txctrl2_in,
         txusrclk_in                        => txusrclk_in,
         txusrclk2_in                       => txusrclk2_in,
         gthtxn_out                         => gthtxn_out,
         gthtxp_out                         => gthtxp_out,
         rxbyteisaligned_out                => rxbyteisaligned_out,
         rxbyterealign_out                  => rxbyterealign_out,
         rxcommadet_out                     => rxcommadet_out,
         rxctrl0_out                        => rxctrl0_out,
         rxctrl1_out                        => rxctrl1_out,
         rxctrl2_out                        => rxctrl2_out,
         rxctrl3_out                        => rxctrl3_out,
         rxoutclk_out                       => rxoutclk_out,
         rxpmaresetdone_out                 => rxpmaresetdone_out,
         txoutclk_out                       => txoutclk_out,
         txpmaresetdone_out                 => txpmaresetdone_out
         );

end architecture rtl;


-- COMP_TAG_END ------ End COMPONENT Declaration ------------

-- The following code must appear in the VHDL architecture
-- body. Substitute your own instance name and net names.

------------- Begin Cut here for INSTANTIATION Template ----- INST_TAG

-- INST_TAG_END ------ E
