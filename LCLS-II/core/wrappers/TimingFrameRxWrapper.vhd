-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingRxType input, the
--              TimingMessageType output and the TimingExtensionArray output
--              of TimingFrameRx into plain sl and slv ports. This file is
--              never loaded by any ruckus.tcl.
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

entity TimingFrameRxWrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      rxClk               : in  sl;
      rxRst               : in  sl;
      rxData              : in  slv(15 downto 0);
      rxDataK             : in  slv(1 downto 0);
      rxDecErr            : in  slv(1 downto 0)  := "00";
      rxDspErr            : in  slv(1 downto 0)  := "00";
      messageDelay        : in  slv(19 downto 0) := (others => '0');
      messageDelayRst     : in  sl               := '0';
      timingMessage       : out slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      timingMessageStrobe : out sl;
      timingMessageValid  : out sl;
      extensionValid      : out slv(15 downto 1);
      extensionData       : out slv(15*512-1 downto 0);
      rxVersion           : out slv(31 downto 0);
      staData             : out slv(4 downto 0));
end entity TimingFrameRxWrapper;

architecture mapping of TimingFrameRxWrapper is

   signal rxDataRec : TimingRxType;
   signal message   : TimingMessageType;
   signal extension : TimingExtensionArray;

begin

   rxDataRec.data   <= rxData;
   rxDataRec.dataK  <= rxDataK;
   rxDataRec.decErr <= rxDecErr;
   rxDataRec.dspErr <= rxDspErr;

   U_TimingFrameRx : entity lcls_timing_core.TimingFrameRx
      generic map (
         TPD_G => TPD_G)
      port map (
         rxClk               => rxClk,
         rxRst               => rxRst,
         rxData              => rxDataRec,
         messageDelay        => messageDelay,
         messageDelayRst     => messageDelayRst,
         timingMessage       => message,
         timingMessageStrobe => timingMessageStrobe,
         timingMessageValid  => timingMessageValid,
         timingExtension     => extension,
         rxVersion           => rxVersion,
         staData             => staData);

   timingMessage <= toSlv(message);

   GEN_EXT : for i in 1 to 15 generate
      extensionValid(i)                         <= extension(i).valid;
      extensionData(i*512-1 downto (i-1)*512) <= extension(i).data;
   end generate GEN_EXT;

end architecture mapping;
