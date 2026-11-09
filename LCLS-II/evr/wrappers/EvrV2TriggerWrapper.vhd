-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the EvrV2TriggerConfigType
--              input of EvrV2Trigger into one plain slv port. This file is
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
-- vsg_off use_clause_501
use lcls_timing_core.EvrV2Pkg.all;
-- vsg_on use_clause_501

entity EvrV2TriggerWrapper is
   generic (
      TPD_G        : time     := 1 ns;
      CHANNELS_G   : positive := 1;
      TRIG_DEPTH_G : natural  := 16;
      TRIG_WIDTH_G : positive := 28;
      USE_MASK_G   : boolean  := false);
   port (
      clk       : in  sl;
      rst       : in  sl;
      config    : in  slv(EVRV2_TRIGGER_CONFIG_BITS_C-1 downto 0);
      arm       : in  slv(CHANNELS_G-1 downto 0);
      fire      : in  sl;
      trigstate : out sl);
end entity EvrV2TriggerWrapper;

architecture mapping of EvrV2TriggerWrapper is

begin

   U_EvrV2Trigger : entity lcls_timing_core.EvrV2Trigger
      generic map (
         TPD_G        => TPD_G,
         CHANNELS_C   => CHANNELS_G,
         TRIG_DEPTH_C => TRIG_DEPTH_G,
         TRIG_WIDTH_C => TRIG_WIDTH_G,
         USE_MASK_G   => USE_MASK_G)
      port map (
         clk       => clk,
         rst       => rst,
         config    => toTriggerConfig(config),
         arm       => arm,
         fire      => fire,
         trigstate => trigstate);

end architecture mapping;
