-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the AxiStreamMasterType
--              obDebugMaster output of TPGNotify into plain sl and slv
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
use surf.AxiStreamPkg.all;

library lcls_timing_core;

entity TPGNotifyWrapper is
   port (
      txClk     : in  sl;
      txRst     : in  sl;
      irqReq    : in  sl;
      irqEnable : in  sl;
      tValid    : out sl;
      tLast     : out sl;
      tDest     : out slv(7 downto 0);
      tData     : out slv(31 downto 0));
end entity TPGNotifyWrapper;

architecture mapping of TPGNotifyWrapper is

   signal master : AxiStreamMasterType;

begin

   U_TPGNotify : entity lcls_timing_core.TPGNotify
      port map (
         txClk         => txClk,
         txRst         => txRst,
         irqReq        => irqReq,
         irqEnable     => irqEnable,
         obDebugMaster => master);

   tValid <= master.tValid;
   tLast  <= master.tLast;
   tDest  <= master.tDest;
   tData  <= master.tData(31 downto 0);

end architecture mapping;
