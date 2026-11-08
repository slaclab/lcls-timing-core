-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper around TPGMini. It builds the
--              TPGConfigType input from TPG_CONFIG_INIT_C with the fields the
--              generator reads replaced by flat ports, flattens the used
--              TPGStatusType fields, and structurally feeds the generator
--              txData and txDataK into a TimingFrameRx so that one simulation
--              covers the generator and the production receiver. This file is
--              never loaded by any ruckus.tcl.
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

library surf;
use surf.StdRtlPkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;
-- vsg_off use_clause_501
use lcls_timing_core.TPGPkg.all;
-- vsg_on use_clause_501

entity TPGMiniWrapper is
   generic (
      TPD_G        : time     := 1 ns;
      NARRAYSBSA_G : positive := 2);
   port (
      txClk                : in  sl;
      txRst                : in  sl;
      txRdy                : in  sl;
      cfgBaseDivisor       : in  slv(15 downto 0)                   := x"00C8";
      cfgFixedRateDivisors : in  slv(10*20-1 downto 0);
      cfgPulseId           : in  slv(63 downto 0)                   := (others => '0');
      cfgPulseIdWrEn       : in  sl                                 := '1';
      cfgTimeStamp         : in  slv(63 downto 0)                   := (others => '0');
      cfgTimeStampWrEn     : in  sl                                 := '0';
      cfgInterval          : in  slv(31 downto 0)                   := x"0000488B";
      cfgIntervalRst       : in  sl                                 := '1';
      txData               : out slv(15 downto 0);
      txDataK              : out slv(1 downto 0);
      fiducial             : out sl;
      statusPulseId        : out slv(63 downto 0);
      statusTimeStamp      : out slv(63 downto 0);
      statusNarraysbsa     : out slv(7 downto 0);
      timingMessage        : out slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      timingMessageStrobe  : out sl;
      timingMessageValid   : out sl;
      staData              : out slv(4 downto 0));
end entity TPGMiniWrapper;

architecture mapping of TPGMiniWrapper is

   signal config  : TPGConfigType := TPG_CONFIG_INIT_C;
   signal status  : TPGStatusType;
   signal txDataI : slv(15 downto 0);
   signal txKI    : slv(1 downto 0);
   signal rxData  : TimingRxType;
   signal message : TimingMessageType;

begin

   config.baseDivisor   <= cfgBaseDivisor;
   config.pulseId       <= cfgPulseId;
   config.pulseIdWrEn   <= cfgPulseIdWrEn;
   config.timeStamp     <= cfgTimeStamp;
   config.timeStampWrEn <= cfgTimeStampWrEn;
   config.interval      <= cfgInterval;
   config.intervalRst   <= cfgIntervalRst;

   GEN_FIXED_RATE : for i in 0 to 9 generate
      config.FixedRateDivisors(i) <= cfgFixedRateDivisors(20*i+19 downto 20*i);
   end generate GEN_FIXED_RATE;

   U_TPGMini : entity lcls_timing_core.TPGMini
      generic map (
         TPD_G       => TPD_G,
         NARRAYSBSA  => NARRAYSBSA_G,
         STREAM_INTF => false)
      port map (
         statusO   => status,
         configI   => config,
         txClk     => txClk,
         txRst     => txRst,
         txRdy     => txRdy,
         txData    => txDataI,
         txDataK   => txKI,
         streams   => open,
         streamIds => open,
         fiducial  => fiducial);

   txData  <= txDataI;
   txDataK <= txKI;

   statusPulseId    <= status.pulseId;
   statusTimeStamp  <= status.timeStamp;
   statusNarraysbsa <= status.narraysbsa;

   rxData.data   <= txDataI;
   rxData.dataK  <= txKI;
   rxData.decErr <= "00";
   rxData.dspErr <= "00";

   U_TimingFrameRx : entity lcls_timing_core.TimingFrameRx
      generic map (
         TPD_G => TPD_G)
      port map (
         rxClk               => txClk,
         rxRst               => txRst,
         rxData              => rxData,
         messageDelay        => (others => '0'),
         messageDelayRst     => '0',
         timingMessage       => message,
         timingMessageStrobe => timingMessageStrobe,
         timingMessageValid  => timingMessageValid,
         timingExtension     => open,
         rxVersion           => open,
         staData             => staData);

   timingMessage <= toSlv(message);

end architecture mapping;
