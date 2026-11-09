-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the EvrV2ChannelConfig and
--              TimingMessageType inputs of EvrV2EventSelect into plain slv
--              ports. This file is never loaded by any ruckus.tcl.
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
use lcls_timing_core.EvrV2Pkg.all;
use lcls_timing_core.TimingPkg.all;
-- vsg_on use_clause_501

entity EvrV2EventSelectWrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      clk       : in  sl;
      rst       : in  sl;
      config    : in  slv(EVRV2_CHANNEL_CONFIG_BITS_C-1 downto 0);
      strobeIn  : in  sl;
      dataIn    : in  slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      selectOut : out sl;
      dmaOut    : out sl);
end entity EvrV2EventSelectWrapper;

architecture mapping of EvrV2EventSelectWrapper is

begin

   U_EvrV2EventSelect : entity lcls_timing_core.EvrV2EventSelect
      generic map (
         TPD_G => TPD_G)
      port map (
         clk       => clk,
         rst       => rst,
         config    => toChannelConfig(config),
         strobeIn  => strobeIn,
         dataIn    => toTimingMessageType(dataIn),
         selectOut => selectOut,
         dmaOut    => dmaOut);

end architecture mapping;
