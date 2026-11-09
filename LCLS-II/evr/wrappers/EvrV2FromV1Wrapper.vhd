-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingBusType input and
--              the TimingMessageType output of EvrV2FromV1 into plain slv
--              ports. Only strobe, message and stream of the bus are used by
--              the entity. This file is never loaded by any ruckus.tcl.
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
-- vsg_off use_clause_501
use lcls_timing_core.TimingPkg.all;
-- vsg_on use_clause_501

entity EvrV2FromV1Wrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      clk       : in  sl;
      disable   : in  sl;
      strobe    : in  sl;
      message   : in  slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      stream    : in  slv(TIMING_STREAM_BITS_C-1 downto 0);
      timingOut : out slv(TIMING_MESSAGE_BITS_C-1 downto 0));
end entity EvrV2FromV1Wrapper;

architecture mapping of EvrV2FromV1Wrapper is

   signal timingIn : TimingBusType;
   signal msgOut   : TimingMessageType;

begin

   process (message, strobe, stream) is
      variable busV : TimingBusType;
   begin
      busV         := TIMING_BUS_INIT_C;
      busV.strobe  := strobe;
      busV.message := toTimingMessageType(message);
      busV.stream  := toTimingStreamType(stream);
      timingIn      <= busV;
   end process;

   U_EvrV2FromV1 : entity lcls_timing_core.EvrV2FromV1
      generic map (
         TPD_G => TPD_G)
      port map (
         clk       => clk,
         disable   => disable,
         timingIn  => timingIn,
         timingOut => msgOut);

   timingOut <= toSlv(msgOut);

end architecture mapping;
