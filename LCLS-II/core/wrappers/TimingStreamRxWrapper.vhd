-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingRxType input and
--              the TimingStreamType outputs of TimingStreamRx into plain sl
--              and slv ports. The stream outputs use the production toSlv.
--              This file is never loaded by any ruckus.tcl.
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

entity TimingStreamRxWrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      rxClk                : in  sl;
      rxRst                : in  sl;
      rxData               : in  slv(15 downto 0);
      rxDataK              : in  slv(1 downto 0);
      rxDecErr             : in  slv(1 downto 0) := "00";
      rxDspErr             : in  slv(1 downto 0) := "00";
      timingMessageNoDely  : in  sl              := '0';
      timingMessageUser    : out slv(TIMING_STREAM_BITS_C-1 downto 0);
      timingMessagePrompt  : out slv(TIMING_STREAM_BITS_C-1 downto 0);
      timingMessageStrobe  : out sl;
      timingMessageValid   : out sl;
      timingTSEventCounter : out slv(31 downto 0);
      rxVersion            : out slv(31 downto 0);
      staData              : out slv(4 downto 0));
end entity TimingStreamRxWrapper;

architecture mapping of TimingStreamRxWrapper is

   signal rxDataRec : TimingRxType;
   signal user      : TimingStreamType;
   signal prompt    : TimingStreamType;

begin

   rxDataRec.data   <= rxData;
   rxDataRec.dataK  <= rxDataK;
   rxDataRec.decErr <= rxDecErr;
   rxDataRec.dspErr <= rxDspErr;

   U_TimingStreamRx : entity lcls_timing_core.TimingStreamRx
      generic map (
         TPD_G => TPD_G)
      port map (
         rxClk                => rxClk,
         rxRst                => rxRst,
         rxData               => rxDataRec,
         timingMessageNoDely  => timingMessageNoDely,
         timingMessageUser    => user,
         timingMessagePrompt  => prompt,
         timingMessageStrobe  => timingMessageStrobe,
         timingMessageValid   => timingMessageValid,
         timingTSEventCounter => timingTSEventCounter,
         rxVersion            => rxVersion,
         staData              => staData);

   timingMessageUser   <= toSlv(user);
   timingMessagePrompt <= toSlv(prompt);

end architecture mapping;
