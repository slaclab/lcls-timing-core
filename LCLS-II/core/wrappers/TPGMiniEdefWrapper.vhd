-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TPGMiniEdefConfigType
--              input of TPGMiniEdef into plain slv ports and turns the EdefType
--              generic into a natural. This file is never loaded by any
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

library lcls_timing_core;
-- vsg_off use_clause_501
use lcls_timing_core.TPGMiniEdefPkg.all;
-- vsg_on use_clause_501

entity TPGMiniEdefWrapper is
   generic (
      TPD_G  : time                  := 1 ns;
      EDEF_G : natural range 0 to 15 := 0);
   port (
      clk      : in  sl;
      rst      : in  sl;
      cen      : in  sl;
      strb     : in  sl;
      cnfgNavg : in  slv(7 downto 0);
      cnfgNsmp : in  slv(11 downto 0);
      cnfgEdef : in  slv(3 downto 0);
      cnfgSlot : in  slv(2 downto 0);
      cnfgRate : in  slv(2 downto 0);
      cnfgSevr : in  slv(1 downto 0);
      cnfgWrEn : in  sl;
      actv     : out sl;
      avgD     : out sl;
      allD     : out sl;
      init     : out sl;
      smin     : out sl;
      smaj     : out sl;
      rate     : out slv(2 downto 0);
      slot     : out slv(2 downto 0));
end entity TPGMiniEdefWrapper;

architecture mapping of TPGMiniEdefWrapper is

   signal cnfg : TPGMiniEdefConfigType;

begin

   cnfg.navg <= cnfgNavg;
   cnfg.nsmp <= cnfgNsmp;
   cnfg.edef <= cnfgEdef;
   cnfg.slot <= cnfgSlot;
   cnfg.rate <= cnfgRate;
   cnfg.sevr <= cnfgSevr;
   cnfg.wrEn <= cnfgWrEn;

   U_TPGMiniEdef : entity lcls_timing_core.TPGMiniEdef
      generic map (
         TPD_G  => TPD_G,
         EDEF_G => toSlv(EDEF_G, 4))
      port map (
         clk  => clk,
         rst  => rst,
         cen  => cen,
         strb => strb,
         cnfg => cnfg,
         actv => actv,
         avgD => avgD,
         allD => allD,
         init => init,
         smin => smin,
         smaj => smaj,
         rate => rate,
         slot => slot);

end architecture mapping;
