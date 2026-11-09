-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the EvrV2TriggerConfigArray
--              input of EvrV2TriggerCompl into one plain slv port, with
--              element i in bits 87*i+86 downto 87*i. This file is never
--              loaded by any ruckus.tcl.
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

entity EvrV2TriggerComplWrapper is
   generic (
      TPD_G     : time    := 1 ns;
      REG_OUT_G : boolean := false);
   port (
      clk     : in  sl;
      rst     : in  sl;
      config  : in  slv(2*EVRV2_TRIGGER_CONFIG_BITS_C-1 downto 0);
      trigIn  : in  slv(1 downto 0);
      trigOut : out slv(1 downto 0));
end entity EvrV2TriggerComplWrapper;

architecture mapping of EvrV2TriggerComplWrapper is

   signal configArr : EvrV2TriggerConfigArray(1 downto 0);

begin

   GEN_CONFIG : for i in 0 to 1 generate
      configArr(i) <= toTriggerConfig(config(EVRV2_TRIGGER_CONFIG_BITS_C*i+EVRV2_TRIGGER_CONFIG_BITS_C-1 downto EVRV2_TRIGGER_CONFIG_BITS_C*i));
   end generate GEN_CONFIG;

   U_EvrV2TriggerCompl : entity lcls_timing_core.EvrV2TriggerCompl
      generic map (
         TPD_G     => TPD_G,
         REG_OUT_G => REG_OUT_G)
      port map (
         clk     => clk,
         rst     => rst,
         config  => configArr,
         trigIn  => trigIn,
         trigOut => trigOut);

end architecture mapping;
