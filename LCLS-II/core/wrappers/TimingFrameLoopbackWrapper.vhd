-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only structural loopback of the LCLS-II timing link:
--              WordSerializer feeds TimingSerializer, and the serializer
--              output drives both TimingDeserializer and TimingFrameRx. The
--              wrapper flattens the TimingRxType record built from the
--              serializer output and the two error ports, the
--              TimingSerialArray output of the deserializer and the
--              TimingMessageType output of the receiver into plain sl and
--              slv ports. It adds no logic of its own. This file is never
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
use lcls_timing_core.TimingPkg.all;

entity TimingFrameLoopbackWrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      txClk               : in  sl;
      txRst               : in  sl;
      fiducial            : in  sl;
      ready               : in  sl;
      words               : in  slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      rxDecErr            : in  slv(1 downto 0) := "00";
      rxDspErr            : in  slv(1 downto 0) := "00";
      txData              : out slv(15 downto 0);
      txDataK             : out slv(1 downto 0);
      desFiducial         : out sl;
      desSof              : out sl;
      desEof              : out sl;
      desCrcErr           : out sl;
      desStreamReady      : out sl;
      desStreamLast       : out sl;
      desAdvance          : out sl;
      desStreamData       : out slv(15 downto 0);
      desStreamOffset     : out slv(6 downto 0);
      timingMessage       : out slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      timingMessageStrobe : out sl;
      timingMessageValid  : out sl;
      staData             : out slv(4 downto 0));
end entity TimingFrameLoopbackWrapper;

architecture mapping of TimingFrameLoopbackWrapper is

   signal wordStream   : TimingSerialType;
   signal serStreams   : TimingSerialArray(0 downto 0);
   signal serStreamIds : Slv4Array(0 downto 0);
   signal serAdvance   : slv(0 downto 0);
   signal serData      : slv(15 downto 0);
   signal serDataK     : slv(1 downto 0);

   signal rxDataRec    : TimingRxType;
   signal desStreams   : TimingSerialArray(0 downto 0);
   signal desStreamIds : Slv4Array(0 downto 0);
   signal desAdvanceV  : slv(0 downto 0);
   signal message      : TimingMessageType;
   signal rxVersion    : slv(31 downto 0);

begin

   serStreams(0)   <= wordStream;
   serStreamIds(0) <= x"0";
   desStreamIds(0) <= x"0";

   rxDataRec.data   <= serData;
   rxDataRec.dataK  <= serDataK;
   rxDataRec.decErr <= rxDecErr;
   rxDataRec.dspErr <= rxDspErr;

   U_WordSerializer : entity lcls_timing_core.WordSerializer
      generic map (
         NWORDS_G => TIMING_MESSAGE_WORDS_C)
      port map (
         txClk    => txClk,
         txRst    => txRst,
         fiducial => fiducial,
         words    => words,
         ready    => ready,
         advance  => serAdvance(0),
         stream   => wordStream);

   U_TimingSerializer : entity lcls_timing_core.TimingSerializer
      generic map (
         TPD_G     => TPD_G,
         STREAMS_C => 1)
      port map (
         clk       => txClk,
         rst       => txRst,
         fiducial  => fiducial,
         streams   => serStreams,
         streamIds => serStreamIds,
         advance   => serAdvance,
         data      => serData,
         dataK     => serDataK);

   U_TimingDeserializer : entity lcls_timing_core.TimingDeserializer
      generic map (
         TPD_G     => TPD_G,
         STREAMS_C => 1)
      port map (
         clk       => txClk,
         rst       => txRst,
         fiducial  => desFiducial,
         streams   => desStreams,
         streamIds => desStreamIds,
         advance   => desAdvanceV,
         data      => rxDataRec,
         sof       => desSof,
         eof       => desEof,
         crcErr    => desCrcErr);

   U_TimingFrameRx : entity lcls_timing_core.TimingFrameRx
      generic map (
         TPD_G => TPD_G)
      port map (
         rxClk               => txClk,
         rxRst               => txRst,
         rxData              => rxDataRec,
         messageDelay        => (others => '0'),
         messageDelayRst     => '0',
         timingMessage       => message,
         timingMessageStrobe => timingMessageStrobe,
         timingMessageValid  => timingMessageValid,
         rxVersion           => rxVersion,
         staData             => staData);

   txData  <= serData;
   txDataK <= serDataK;

   desAdvance      <= desAdvanceV(0);
   desStreamReady  <= desStreams(0).ready;
   desStreamLast   <= desStreams(0).last;
   desStreamData   <= desStreams(0).data;
   desStreamOffset <= desStreams(0).offset;

   timingMessage <= toSlv(message);

end architecture mapping;
