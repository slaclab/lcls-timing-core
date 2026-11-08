-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that exposes the AxiStream output of
--              TimingMsgToAxiStream as flat M_AXIS ports through the surf
--              MasterAxiStreamIpIntegrator. This file is never loaded by any
--              ruckus.tcl.
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
use surf.SsiPkg.all;

library lcls_timing_core;

entity TimingMsgToAxiStreamWrapper is
   generic (
      TPD_G          : time     := 1 ns;
      COMMON_CLOCK_G : boolean  := true;
      SHIFT_SIZE_G   : positive := 32;
      VECTOR_SIZE_G  : positive := 944);
   port (
      timingClk           : in  sl;
      timingRst           : in  sl;
      timingMessageStrobe : in  sl;
      timingMessage       : in  slv(VECTOR_SIZE_G-1 downto 0);
      axisClk             : in  sl;
      axisRst             : in  sl;
      M_AXIS_TVALID       : out sl;
      M_AXIS_TDATA        : out slv(63 downto 0);
      M_AXIS_TSTRB        : out slv(7 downto 0);
      M_AXIS_TKEEP        : out slv(7 downto 0);
      M_AXIS_TLAST        : out sl;
      M_AXIS_TDEST        : out slv(SSI_TDEST_BITS_C-1 downto 0);
      M_AXIS_TID          : out slv(0 downto 0);
      M_AXIS_TUSER        : out slv(SSI_TUSER_BITS_C-1 downto 0);
      M_AXIS_TREADY       : in  sl);
end entity TimingMsgToAxiStreamWrapper;

architecture mapping of TimingMsgToAxiStreamWrapper is

   signal shimClk    : sl;
   signal shimRst    : sl;
   signal axisMaster : AxiStreamMasterType;
   signal axisSlave  : AxiStreamSlaveType;

begin

   U_MasterShim : entity surf.MasterAxiStreamIpIntegrator
      generic map (
         TUSER_WIDTH     => SSI_TUSER_BITS_C,
         TID_WIDTH       => 1,
         TDEST_WIDTH     => SSI_TDEST_BITS_C,
         TDATA_NUM_BYTES => 8)
      port map (
         M_AXIS_ACLK    => axisClk,
         M_AXIS_ARESETN => not axisRst,
         M_AXIS_TVALID  => M_AXIS_TVALID,
         M_AXIS_TDATA   => M_AXIS_TDATA,
         M_AXIS_TSTRB   => M_AXIS_TSTRB,
         M_AXIS_TKEEP   => M_AXIS_TKEEP,
         M_AXIS_TLAST   => M_AXIS_TLAST,
         M_AXIS_TDEST   => M_AXIS_TDEST,
         M_AXIS_TID     => M_AXIS_TID,
         M_AXIS_TUSER   => M_AXIS_TUSER,
         M_AXIS_TREADY  => M_AXIS_TREADY,
         axisClk        => shimClk,
         axisRst        => shimRst,
         axisMaster     => axisMaster,
         axisSlave      => axisSlave);

   U_TimingMsgToAxiStream : entity lcls_timing_core.TimingMsgToAxiStream
      generic map (
         TPD_G          => TPD_G,
         COMMON_CLOCK_G => COMMON_CLOCK_G,
         SHIFT_SIZE_G   => SHIFT_SIZE_G,
         VECTOR_SIZE_G  => VECTOR_SIZE_G)
      port map (
         timingClk           => timingClk,
         timingRst           => timingRst,
         timingMessage       => timingMessage,
         timingMessageStrobe => timingMessageStrobe,
         axisClk             => shimClk,
         axisRst             => shimRst,
         axisMaster          => axisMaster,
         axisSlave           => axisSlave);

end architecture mapping;
