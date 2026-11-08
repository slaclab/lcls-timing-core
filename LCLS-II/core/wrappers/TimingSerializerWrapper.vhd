-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingSerialArray and
--              Slv4Array inputs of TimingSerializer into plain sl and slv
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
use lcls_timing_core.TimingPkg.all;

entity TimingSerializerWrapper is
   generic (
      TPD_G     : time     := 1 ns;
      STREAMS_G : positive := 1);
   port (
      clk          : in  sl;
      rst          : in  sl;
      fiducial     : in  sl;
      streamReady  : in  slv(STREAMS_G-1 downto 0);
      streamData   : in  slv(16*STREAMS_G-1 downto 0);
      streamOffset : in  slv(7*STREAMS_G-1 downto 0) := (others => '0');
      streamLast   : in  slv(STREAMS_G-1 downto 0)   := (others => '1');
      streamIds    : in  slv(4*STREAMS_G-1 downto 0);
      advance      : out slv(STREAMS_G-1 downto 0);
      data         : out slv(15 downto 0);
      dataK        : out slv(1 downto 0));
end entity TimingSerializerWrapper;

architecture mapping of TimingSerializerWrapper is

   signal streams   : TimingSerialArray(STREAMS_G-1 downto 0);
   signal streamIdA : Slv4Array(STREAMS_G-1 downto 0);

begin

   GEN_STREAM : for i in 0 to STREAMS_G-1 generate
      streams(i).ready  <= streamReady(i);
      streams(i).data   <= streamData(16*i+15 downto 16*i);
      streams(i).offset <= streamOffset(7*i+6 downto 7*i);
      streams(i).last   <= streamLast(i);
      streamIdA(i)      <= streamIds(4*i+3 downto 4*i);
   end generate GEN_STREAM;

   U_TimingSerializer : entity lcls_timing_core.TimingSerializer
      generic map (
         TPD_G     => TPD_G,
         STREAMS_C => STREAMS_G)
      port map (
         clk       => clk,
         rst       => rst,
         fiducial  => fiducial,
         streams   => streams,
         streamIds => streamIdA,
         advance   => advance,
         data      => data,
         dataK     => dataK);

end architecture mapping;
