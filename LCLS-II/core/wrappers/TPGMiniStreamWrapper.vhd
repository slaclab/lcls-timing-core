-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TPGConfigType input (only
--              timeStamp and timeStampWrEn are read by TPGMiniStream, the rest
--              stays at TPG_CONFIG_INIT_C), the TPGMiniEdefConfigType input and
--              the TimingDataBuffType simulation output of TPGMiniStream into
--              plain sl and slv ports, and maps the AC_PERIOD and NUM_EDEFS
--              generics. This file is never loaded by any ruckus.tcl.
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
use lcls_timing_core.TPGMiniEdefPkg.all;
-- vsg_on use_clause_501

entity TPGMiniStreamWrapper is
   generic (
      TPD_G       : time     := 1 ns;
      AC_PERIOD_G : positive := 2;
      NUM_EDEFS_G : natural  := 4);
   port (
      txClk            : in  sl;
      txRst            : in  sl;
      txRdy            : in  sl;
      cfgTimeStamp     : in  slv(63 downto 0) := (others => '0');
      cfgTimeStampWrEn : in  sl               := '0';
      edefNavg         : in  slv(7 downto 0);
      edefNsmp         : in  slv(11 downto 0);
      edefEdef         : in  slv(3 downto 0);
      edefSlot         : in  slv(2 downto 0);
      edefRate         : in  slv(2 downto 0);
      edefSevr         : in  slv(1 downto 0);
      edefWrEn         : in  sl;
      txData           : out slv(15 downto 0);
      txDataK          : out slv(1 downto 0);
      simData          : out slv(TIMING_DATABUFF_BITS_C-1 downto 0);
      simEvents        : out slv(69 downto 0);
      simStrobe        : out sl);
end entity TPGMiniStreamWrapper;

architecture mapping of TPGMiniStreamWrapper is

   signal config     : TPGConfigType := TPG_CONFIG_INIT_C;
   signal edefConfig : TPGMiniEdefConfigType;
   signal simDataRec : TimingDataBuffType;

begin

   config.timeStamp     <= cfgTimeStamp;
   config.timeStampWrEn <= cfgTimeStampWrEn;

   edefConfig.navg <= edefNavg;
   edefConfig.nsmp <= edefNsmp;
   edefConfig.edef <= edefEdef;
   edefConfig.slot <= edefSlot;
   edefConfig.rate <= edefRate;
   edefConfig.sevr <= edefSevr;
   edefConfig.wrEn <= edefWrEn;

   U_TPGMiniStream : entity lcls_timing_core.TPGMiniStream
      generic map (
         TPD_G     => TPD_G,
         AC_PERIOD => AC_PERIOD_G,
         NUM_EDEFS => NUM_EDEFS_G)
      port map (
         config     => config,
         edefConfig => edefConfig,
         txClk      => txClk,
         txRst      => txRst,
         txRdy      => txRdy,
         txData     => txData,
         txDataK    => txDataK,
         simData    => simDataRec,
         simEvents  => simEvents,
         simStrobe  => simStrobe);

   simData <= toSlv(simDataRec);

end architecture mapping;
