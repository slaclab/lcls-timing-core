-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingMessageType input
--              and output of TimingMsgDelay into plain slv ports. This file
--              is never loaded by any ruckus.tcl.
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

entity TimingMsgDelayWrapper is
   generic (
      TPD_G             : time     := 1 ns;
      FIFO_ADDR_WIDTH_G : positive := 7);
   port (
      timingClk              : in  sl;
      timingRst              : in  sl;
      timingMessageIn        : in  slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      timingMessageStrobeIn  : in  sl;
      delay                  : in  slv(15 downto 0);
      timingMessageOut       : out slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      timingMessageStrobeOut : out sl);
end entity TimingMsgDelayWrapper;

architecture mapping of TimingMsgDelayWrapper is

   signal messageOut : TimingMessageType;

begin

   U_TimingMsgDelay : entity lcls_timing_core.TimingMsgDelay
      generic map (
         TPD_G             => TPD_G,
         FIFO_ADDR_WIDTH_G => FIFO_ADDR_WIDTH_G)
      port map (
         timingClk              => timingClk,
         timingRst              => timingRst,
         timingMessageIn        => toTimingMessageType(timingMessageIn),
         timingMessageStrobeIn  => timingMessageStrobeIn,
         delay                  => delay,
         timingMessageOut       => messageOut,
         timingMessageStrobeOut => timingMessageStrobeOut);

   timingMessageOut <= toSlv(messageOut);

end architecture mapping;
