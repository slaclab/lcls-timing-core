-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the CtrDefType and Slv16Array
--              inputs of CtrControl into plain slv ports. This file is never
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

entity CtrControlWrapper is
   generic (
      TPD_G          : time    := 1 ns;
      ASYNC_REGCLK_G : boolean := false);
   port (
      sysclk        : in  sl;
      sysrst        : in  sl;
      ctrdefRateSel : in  slv(12 downto 0);
      ctrdefDestSel : in  slv(18 downto 0);
      ctrrst        : in  sl;
      txclk         : in  sl;
      txrst         : in  sl;
      enable        : in  sl;
      fixedRate     : in  slv(FIXEDRATEDEPTH-1 downto 0);
      acRate        : in  slv(ACRATEDEPTH-1 downto 0);
      acTS          : in  slv(2 downto 0);
      beamSeq       : in  slv(31 downto 0);
      expSeq        : in  slv(18*16-1 downto 0);
      count         : out slv(31 downto 0));
end entity CtrControlWrapper;

architecture mapping of CtrControlWrapper is

   signal ctrdef    : CtrDefType;
   signal expSeqArr : Slv16Array(0 to 17);

begin

   ctrdef.rateSel <= ctrdefRateSel;
   ctrdef.destSel <= ctrdefDestSel;

   GEN_EXPSEQ : for i in 0 to 17 generate
      expSeqArr(i) <= expSeq(16*i+15 downto 16*i);
   end generate GEN_EXPSEQ;

   U_CtrControl : entity lcls_timing_core.CtrControl
      generic map (
         TPD_G          => TPD_G,
         ASYNC_REGCLK_G => ASYNC_REGCLK_G)
      port map (
         sysclk    => sysclk,
         sysrst    => sysrst,
         ctrdef    => ctrdef,
         ctrrst    => ctrrst,
         txclk     => txclk,
         txrst     => txrst,
         enable    => enable,
         fixedRate => fixedRate,
         acRate    => acRate,
         acTS      => acTS,
         beamSeq   => beamSeq,
         expSeq    => expSeqArr,
         count     => count);

end architecture mapping;
