-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingMessageType input
--              and the TimingSerialType stream output of TPSerializer into
--              plain sl and slv ports. This file is never loaded by any
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
use lcls_timing_core.TimingPkg.all;

entity TPSerializerWrapper is
   generic (
      TPD_G : time                  := 1 ns;
      ID_G  : natural range 0 to 15 := 0);
   port (
      txClk        : in  sl;
      txRst        : in  sl;
      fiducial     : in  sl;
      msg          : in  slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      advance      : in  sl;
      streamReady  : out sl;
      streamLast   : out sl;
      streamData   : out slv(15 downto 0);
      streamOffset : out slv(6 downto 0);
      streamId     : out slv(3 downto 0));
end entity TPSerializerWrapper;

architecture mapping of TPSerializerWrapper is

   signal msgRec : TimingMessageType;
   signal stream : TimingSerialType;

begin

   msgRec <= toTimingMessageType(msg);

   U_TPSerializer : entity lcls_timing_core.TPSerializer
      generic map (
         TPD_G => TPD_G,
         ID    => ID_G)
      port map (
         txClk    => txClk,
         txRst    => txRst,
         fiducial => fiducial,
         msg      => msgRec,
         advance  => advance,
         stream   => stream,
         streamId => streamId);

   streamReady  <= stream.ready;
   streamLast   <= stream.last;
   streamData   <= stream.data;
   streamOffset <= stream.offset;

end architecture mapping;
