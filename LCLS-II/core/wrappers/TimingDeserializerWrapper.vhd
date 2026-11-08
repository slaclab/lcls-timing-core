-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingRxType input and
--              the TimingSerialArray output of TimingDeserializer into plain
--              sl and slv ports. This file is never loaded by any ruckus.tcl.
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

entity TimingDeserializerWrapper is
   generic (
      TPD_G     : time     := 1 ns;
      STREAMS_G : positive := 1);
   port (
      clk          : in  sl;
      rst          : in  sl;
      rxData       : in  slv(15 downto 0);
      rxDataK      : in  slv(1 downto 0);
      rxDecErr     : in  slv(1 downto 0) := "00";
      rxDspErr     : in  slv(1 downto 0) := "00";
      streamIds    : in  slv(4*STREAMS_G-1 downto 0);
      fiducial     : out sl;
      sof          : out sl;
      eof          : out sl;
      crcErr       : out sl;
      streamReady  : out slv(STREAMS_G-1 downto 0);
      streamLast   : out slv(STREAMS_G-1 downto 0);
      streamData   : out slv(16*STREAMS_G-1 downto 0);
      streamOffset : out slv(7*STREAMS_G-1 downto 0);
      advance      : out slv(STREAMS_G-1 downto 0));
end entity TimingDeserializerWrapper;

architecture mapping of TimingDeserializerWrapper is

   signal rxDataRec : TimingRxType;
   signal streams   : TimingSerialArray(STREAMS_G-1 downto 0);
   signal streamIdA : Slv4Array(STREAMS_G-1 downto 0);

begin

   rxDataRec.data   <= rxData;
   rxDataRec.dataK  <= rxDataK;
   rxDataRec.decErr <= rxDecErr;
   rxDataRec.dspErr <= rxDspErr;

   GEN_STREAM : for i in 0 to STREAMS_G-1 generate
      streamIdA(i)                          <= streamIds(4*i+3 downto 4*i);
      streamReady(i)                        <= streams(i).ready;
      streamLast(i)                         <= streams(i).last;
      streamData(16*i+15 downto 16*i)       <= streams(i).data;
      streamOffset(7*i+6 downto 7*i)        <= streams(i).offset;
   end generate GEN_STREAM;

   U_TimingDeserializer : entity lcls_timing_core.TimingDeserializer
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
         data      => rxDataRec,
         sof       => sof,
         eof       => eof,
         crcErr    => crcErr);

end architecture mapping;
