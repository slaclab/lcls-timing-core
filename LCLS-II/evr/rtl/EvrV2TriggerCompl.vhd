-------------------------------------------------------------------------------
-- Title         : EvrV2TriggerCompl
-- Project       : LCLS-II Timing Pattern Generator
-------------------------------------------------------------------------------
-- File          : EvrV2TriggerCompl.vhd
-- Author        : Matt Weaver, weaver@slac.stanford.edu
-- Created       : 01/23/2016
-------------------------------------------------------------------------------
-- Description:
-- Enable complementary trigger pairs where the output can be a logical OR or AND
-- of the two trigger inputs, or it can just pass through.
-- The result needs to be registered by the clock so that the trigger output
-- does not shift (sub-ns) when the logic configuration is changed.
-------------------------------------------------------------------------------
-- This file is part of 'LCLS2 Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the
-- top-level directory of this distribution and at:
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
-- No part of 'LCLS2 Timing Core', including this file,
-- may be copied, modified, propagated, or distributed except according to
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------
-- Modification history:
-- 01/23/2016: created.
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

library surf;
use surf.StdRtlPkg.all;

library lcls_timing_core;
use lcls_timing_core.EvrV2Pkg.all;

entity EvrV2TriggerCompl is
   generic (
      TPD_G     : time    := 1 ns;
      REG_OUT_G : boolean := false);
   port (
      clk     : in  sl;
      rst     : in  sl;
      config  : in  EvrV2TriggerConfigArray(1 downto 0);
      trigIn  : in  slv(1 downto 0);
      trigOut : out slv(1 downto 0));
end EvrV2TriggerCompl;

architecture rtl of EvrV2TriggerCompl is

   type RegType is record
      trig : slv(1 downto 0);
   end record;

   constant REG_INIT_C : RegType := (
      trig => (others => '0'));

   signal r    : RegType := REG_INIT_C;
   signal r_in : RegType;

begin
   comb : process (rst, r, trigIn, config) is
      variable v : RegType;
   begin
      for i in 0 to 1 loop
         if config(i).complEn = '0' then
           v.trig(i) := trigIn(i);
         else
           case config(i).complOp is
             when "00" => v.trig(i) <=     trigIn(0) or  trigIn(1);
             when "01" => v.trig(i) <=     trigIn(0) and trigIn(1);
             when "10" => v.trig(i) <=     trigIn(0) xor trigIn(1);
             when "11" => v.trig(i) <= '1';  -- reserved
           end case;
         end if;
      end loop;

      if rst = '1' then
         v := REG_INIT_C;
      end if;

      r_in <= v;

      if REG_OUT_G then
         trigOut <= r.trig;
      else
         trigOut <= v.trig;
      end if;
   end process comb;

   seq : process (clk) is
   begin
      if rising_edge(clk) then
         r <= r_in after TPD_G;
      end if;
   end process seq;

end rtl;
