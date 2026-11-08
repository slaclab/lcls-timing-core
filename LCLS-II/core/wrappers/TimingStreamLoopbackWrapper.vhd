-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only structural loopback of the LCLS-I timing stream:
--              TimingStreamTx drives TimingStreamRx. The wrapper flattens
--              the TimingDataBuffType input of the transmitter, the
--              TimingRxType record built from the transmitter output and the
--              two error ports, and the TimingStreamType outputs of the
--              receiver (through the production toSlv) into plain sl and slv
--              ports. It adds no logic of its own. This file is never loaded
--              by any ruckus.tcl.
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

entity TimingStreamLoopbackWrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      clk                 : in  sl;
      rst                 : in  sl;
      fiducial            : in  sl;
      dataBuff            : in  slv(TIMING_DATABUFF_BITS_C-1 downto 0);
      pulseId             : in  slv(31 downto 0);
      eventCodes          : in  slv(255 downto 0);
      timingMessageNoDely : in  sl              := '0';
      rxDecErr            : in  slv(1 downto 0) := "00";
      rxDspErr            : in  slv(1 downto 0) := "00";
      txData              : out slv(15 downto 0);
      txDataK             : out slv(1 downto 0);
      timingMessageUser   : out slv(TIMING_STREAM_BITS_C-1 downto 0);
      timingMessagePrompt : out slv(TIMING_STREAM_BITS_C-1 downto 0);
      timingMessageStrobe : out sl;
      timingMessageValid  : out sl;
      staData             : out slv(4 downto 0));
end entity TimingStreamLoopbackWrapper;

architecture mapping of TimingStreamLoopbackWrapper is

   signal dataBuffRec : TimingDataBuffType;
   signal txDataInt   : slv(15 downto 0);
   signal txDataKInt  : slv(1 downto 0);
   signal rxDataRec   : TimingRxType;
   signal user        : TimingStreamType;
   signal prompt      : TimingStreamType;
   signal rxVersion   : slv(31 downto 0);
   signal tsCounter   : slv(31 downto 0);

begin

   dataBuffRec <= toTimingDataBuffType(dataBuff);

   rxDataRec.data   <= txDataInt;
   rxDataRec.dataK  <= txDataKInt;
   rxDataRec.decErr <= rxDecErr;
   rxDataRec.dspErr <= rxDspErr;

   U_TimingStreamTx : entity lcls_timing_core.TimingStreamTx
      generic map (
         TPD_G => TPD_G)
      port map (
         clk        => clk,
         rst        => rst,
         fiducial   => fiducial,
         dataBuff   => dataBuffRec,
         pulseId    => pulseId,
         eventCodes => eventCodes,
         data       => txDataInt,
         dataK      => txDataKInt);

   U_TimingStreamRx : entity lcls_timing_core.TimingStreamRx
      generic map (
         TPD_G => TPD_G)
      port map (
         rxClk                => clk,
         rxRst                => rst,
         rxData               => rxDataRec,
         timingMessageNoDely  => timingMessageNoDely,
         timingMessageUser    => user,
         timingMessagePrompt  => prompt,
         timingMessageStrobe  => timingMessageStrobe,
         timingMessageValid   => timingMessageValid,
         timingTSEventCounter => tsCounter,
         rxVersion            => rxVersion,
         staData              => staData);

   txData  <= txDataInt;
   txDataK <= txDataKInt;

   timingMessageUser   <= toSlv(user);
   timingMessagePrompt <= toSlv(prompt);

end architecture mapping;
