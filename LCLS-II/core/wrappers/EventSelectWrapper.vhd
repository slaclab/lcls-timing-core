-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the Slv16Array expSeq input
--              of EventSelect into a single slv port. This file is never
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
use lcls_timing_core.TPGPkg.all;
-- vsg_on use_clause_501

entity EventSelectWrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      clk       : in  sl;
      rateType  : in  slv(1 downto 0);
      fxRateSel : in  slv(3 downto 0);
      acRateSel : in  slv(2 downto 0);
      acTSmask  : in  slv(5 downto 0);
      seqword   : in  slv(5 downto 0);
      seqbit    : in  slv(4 downto 0);
      fixedRate : in  slv(FIXEDRATEDEPTH-1 downto 0);
      acRate    : in  slv(ACRATEDEPTH-1 downto 0);
      acTS      : in  slv(2 downto 0);
      expSeq    : in  slv(18*16-1 downto 0);
      rateSel   : out sl);
end entity EventSelectWrapper;

architecture mapping of EventSelectWrapper is

   signal expSeqArr : Slv16Array(0 to 17);

begin

   GEN_EXPSEQ : for i in 0 to 17 generate
      expSeqArr(i) <= expSeq(16*i+15 downto 16*i);
   end generate GEN_EXPSEQ;

   U_EventSelect : entity lcls_timing_core.EventSelect
      generic map (
         TPD_G => TPD_G)
      port map (
         clk       => clk,
         rateType  => rateType,
         fxRateSel => fxRateSel,
         acRateSel => acRateSel,
         acTSmask  => acTSmask,
         seqword   => seqword,
         seqbit    => seqbit,
         fixedRate => fixedRate,
         acRate    => acRate,
         acTS      => acTS,
         expSeq    => expSeqArr,
         rateSel   => rateSel);

end architecture mapping;
