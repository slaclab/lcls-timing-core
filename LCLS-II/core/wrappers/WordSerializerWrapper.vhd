-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingSerialType stream
--              output of WordSerializer into plain sl and slv ports. This
--              file is never loaded by any ruckus.tcl.
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

entity WordSerializerWrapper is
   generic (
      NWORDS_G : integer := 2);
   port (
      txClk        : in  sl;
      txRst        : in  sl;
      fiducial     : in  sl;
      words        : in  slv(16*NWORDS_G-1 downto 0);
      ready        : in  sl;
      advance      : in  sl;
      streamReady  : out sl;
      streamData   : out slv(15 downto 0);
      streamOffset : out slv(6 downto 0);
      streamLast   : out sl);
end entity WordSerializerWrapper;

architecture mapping of WordSerializerWrapper is

   signal stream : TimingSerialType;

begin

   U_WordSerializer : entity lcls_timing_core.WordSerializer
      generic map (
         NWORDS_G => NWORDS_G)
      port map (
         txClk    => txClk,
         txRst    => txRst,
         fiducial => fiducial,
         words    => words,
         ready    => ready,
         advance  => advance,
         stream   => stream);

   streamReady  <= stream.ready;
   streamData   <= stream.data;
   streamOffset <= stream.offset;
   streamLast   <= stream.last;

end architecture mapping;
