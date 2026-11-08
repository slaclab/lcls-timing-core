-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingStreamType input of
--              EthTimingModule into a plain slv and exposes its inbound and
--              outbound AxiStream interfaces as flat S_AXIS and M_AXIS ports
--              through the surf stream shims. This file is never loaded by
--              any ruckus.tcl.
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
use surf.AxiStreamPkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;

entity EthTimingModuleWrapper is
   generic (
      TPD_G       : time    := 1 ns;
      STREAM_L1_G : boolean := true);
   port (
      timingClk     : in  sl;
      timingRst     : in  sl;
      timingStrobe  : in  sl;
      timingStream  : in  slv(TIMING_STREAM_BITS_C-1 downto 0);
      ethClk        : in  sl;
      ethRst        : in  sl;
      S_AXIS_TVALID : in  sl;
      S_AXIS_TDATA  : in  slv(127 downto 0);
      S_AXIS_TSTRB  : in  slv(15 downto 0);
      S_AXIS_TKEEP  : in  slv(15 downto 0);
      S_AXIS_TLAST  : in  sl;
      S_AXIS_TDEST  : in  slv(3 downto 0);
      S_AXIS_TID    : in  slv(0 downto 0);
      S_AXIS_TUSER  : in  slv(3 downto 0);
      S_AXIS_TREADY : out sl;
      M_AXIS_TVALID : out sl;
      M_AXIS_TDATA  : out slv(127 downto 0);
      M_AXIS_TSTRB  : out slv(15 downto 0);
      M_AXIS_TKEEP  : out slv(15 downto 0);
      M_AXIS_TLAST  : out sl;
      M_AXIS_TDEST  : out slv(3 downto 0);
      M_AXIS_TID    : out slv(0 downto 0);
      M_AXIS_TUSER  : out slv(3 downto 0);
      M_AXIS_TREADY : in  sl);
end entity EthTimingModuleWrapper;

architecture mapping of EthTimingModuleWrapper is

   signal ibEthMsgMaster : AxiStreamMasterType;
   signal ibEthMsgSlave  : AxiStreamSlaveType;
   signal obEthMsgMaster : AxiStreamMasterType;
   signal obEthMsgSlave  : AxiStreamSlaveType;

begin

   U_SlaveShim : entity surf.SlaveAxiStreamIpIntegrator
      generic map (
         TUSER_WIDTH     => 4,
         TID_WIDTH       => 1,
         TDEST_WIDTH     => 4,
         TDATA_NUM_BYTES => 16)
      port map (
         S_AXIS_ACLK    => ethClk,
         S_AXIS_ARESETN => not ethRst,
         S_AXIS_TVALID  => S_AXIS_TVALID,
         S_AXIS_TDATA   => S_AXIS_TDATA,
         S_AXIS_TSTRB   => S_AXIS_TSTRB,
         S_AXIS_TKEEP   => S_AXIS_TKEEP,
         S_AXIS_TLAST   => S_AXIS_TLAST,
         S_AXIS_TDEST   => S_AXIS_TDEST,
         S_AXIS_TID     => S_AXIS_TID,
         S_AXIS_TUSER   => S_AXIS_TUSER,
         S_AXIS_TREADY  => S_AXIS_TREADY,
         axisClk        => open,
         axisRst        => open,
         axisMaster     => ibEthMsgMaster,
         axisSlave      => ibEthMsgSlave);

   U_MasterShim : entity surf.MasterAxiStreamIpIntegrator
      generic map (
         TUSER_WIDTH     => 4,
         TID_WIDTH       => 1,
         TDEST_WIDTH     => 4,
         TDATA_NUM_BYTES => 16)
      port map (
         M_AXIS_ACLK    => ethClk,
         M_AXIS_ARESETN => not ethRst,
         M_AXIS_TVALID  => M_AXIS_TVALID,
         M_AXIS_TDATA   => M_AXIS_TDATA,
         M_AXIS_TSTRB   => M_AXIS_TSTRB,
         M_AXIS_TKEEP   => M_AXIS_TKEEP,
         M_AXIS_TLAST   => M_AXIS_TLAST,
         M_AXIS_TDEST   => M_AXIS_TDEST,
         M_AXIS_TID     => M_AXIS_TID,
         M_AXIS_TUSER   => M_AXIS_TUSER,
         M_AXIS_TREADY  => M_AXIS_TREADY,
         axisClk        => open,
         axisRst        => open,
         axisMaster     => obEthMsgMaster,
         axisSlave      => obEthMsgSlave);

   U_EthTimingModule : entity lcls_timing_core.EthTimingModule
      generic map (
         TPD_G       => TPD_G,
         STREAM_L1_G => STREAM_L1_G)
      port map (
         timingClk      => timingClk,
         timingRst      => timingRst,
         timingStrobe   => timingStrobe,
         timingStream   => toTimingStreamType(timingStream),
         ethClk         => ethClk,
         ethRst         => ethRst,
         ibEthMsgMaster => ibEthMsgMaster,
         ibEthMsgSlave  => ibEthMsgSlave,
         obEthMsgMaster => obEthMsgMaster,
         obEthMsgSlave  => obEthMsgSlave);

end architecture mapping;
