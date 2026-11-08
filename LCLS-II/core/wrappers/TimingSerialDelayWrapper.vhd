-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingSerialType input
--              of TimingSerialDelay into plain sl and slv ports. This file is
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

entity TimingSerialDelayWrapper is
   generic (
      TPD_G    : time     := 1 ns;
      NWORDS_G : positive := 4;
      FDEPTH_G : positive := 16);
   port (
      clk          : in  sl;
      rst          : in  sl;
      delay        : in  slv(19 downto 0);
      fiducial_i   : in  sl;
      advance_i    : in  sl;
      streamReady  : in  sl;
      streamData   : in  slv(15 downto 0);
      streamOffset : in  slv(6 downto 0) := (others => '0');
      streamLast   : in  sl              := '1';
      frame_o      : out slv(16*NWORDS_G-1 downto 0);
      strobe_o     : out sl;
      valid_o      : out sl;
      overflow_o   : out sl);
end entity TimingSerialDelayWrapper;

architecture mapping of TimingSerialDelayWrapper is

   signal stream : TimingSerialType;

begin

   stream.ready  <= streamReady;
   stream.data   <= streamData;
   stream.offset <= streamOffset;
   stream.last   <= streamLast;

   U_TimingSerialDelay : entity lcls_timing_core.TimingSerialDelay
      generic map (
         TPD_G    => TPD_G,
         NWORDS_G => NWORDS_G,
         FDEPTH_G => FDEPTH_G,
         DEBUG_G  => false)
      port map (
         clk        => clk,
         rst        => rst,
         delay      => delay,
         fiducial_i => fiducial_i,
         advance_i  => advance_i,
         stream_i   => stream,
         frame_o    => frame_o,
         strobe_o   => strobe_o,
         valid_o    => valid_o,
         overflow_o => overflow_o);

end architecture mapping;
