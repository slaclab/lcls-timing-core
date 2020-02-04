-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: 
-------------------------------------------------------------------------------
-- This file is part of 'LCLS2 Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS2 Timing Core', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;

library surf;
use surf.StdRtlPkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;

entity TimingFrameRx is
   generic (
      TPD_G : time := 1 ns);
   port (
      rxClk  : in sl;
      rxRst  : in sl;
      rxData : in TimingRxType;

      messageDelay    : in slv(19 downto 0);
      messageDelayRst : in sl;

      timingMessage       : out TimingMessageType;
      timingMessageStrobe : out sl;
      timingMessageValid  : out sl;

      timingExtension : out TimingExtensionArray;

      rxVersion : out slv(31 downto 0);
      staData   : out slv(4 downto 0));
end entity TimingFrameRx;

architecture rtl of TimingFrameRx is

   -------------------------------------------------------------------------------------------------
   -- rxClk Domain
   -------------------------------------------------------------------------------------------------
   type StateType is (IDLE_S, FRAME_S);

   type RegType is record
      vsnErr  : sl;
      version : slv(31 downto 0);
      dvalid  : slv(15 downto 1);
   end record;

   constant REG_INIT_C : RegType := (
      vsnErr  => '0',
      version => (others => '1'),
      dvalid  => (others => '0'));

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal fiducial         : sl;
   signal streams          : TimingSerialArray(15 downto 0);
   signal streamIds        : Slv4Array (15 downto 0);
   signal advance          : slv (15 downto 0);
   signal sof, eof, crcErr : sl;

   signal dframe0    : slv(TIMING_MESSAGE_BITS_C-1 downto 0);
   signal dvalid0    : sl;
   signal doverflow0 : sl;
   signal dstrobe0   : sl;

   signal delayRst       : sl;
   signal iTimingMessage : TimingMessageType;

   type DataArray is array (15 downto 1) of slv(TIMING_EXTENSION_MESSAGE_BITS_C-1 downto 0);
   signal dframe  : DataArray;
   signal dstrobe : slv(15 downto 1);
   signal dvalid  : slv(15 downto 1);

begin

   delayRst <= rxRst or messageDelayRst;

   GEN_STREAM_IDS : for i in 0 to 15 generate
      streamIds(i) <= toSlv(i, 4);
   end generate;

   U_Deserializer : entity lcls_timing_core.TimingDeserializer
      generic map (
         TPD_G     => TPD_G,
         STREAMS_C => 16)
      port map (
         clk       => rxClk,
         rst       => rxRst,
         fiducial  => fiducial,
         streams   => streams,
         streamIds => streamIds,
         advance   => advance,
         data      => rxData,
         sof       => sof,
         eof       => eof,
         crcErr    => crcErr);

   -- Delay for timing message on stream 0
   U_Delay0 : entity lcls_timing_core.TimingSerialDelay
      generic map (
         TPD_G    => TPD_G,
         NWORDS_G => TIMING_MESSAGE_WORDS_C,
         FDEPTH_G => 100)
      port map (
         clk        => rxClk,
         rst        => delayRst,
         delay      => messageDelay,
         fiducial_i => fiducial,
         advance_i  => advance(0),
         stream_i   => streams(0),
         frame_o    => dframe0,
         strobe_o   => dstrobe0,
         valid_o    => dvalid0,
         overflow_o => doverflow0);

   -- Place timing message onto output bus
   iTimingMessage      <= toTimingMessageType(dframe0);
   timingMessage       <= iTimingMessage;
   timingMessageStrobe <= dstrobe0;
   timingMessageValid  <= dvalid0 and not r.vsnErr;

   GEN_FOR : for i in 1 to 15 generate
      U_Extn : entity lcls_timing_core.TimingSerialDelay
         generic map (
            TPD_G    => TPD_G,
            NWORDS_G => TIMING_EXTENSION_MESSAGE_BITS_C/16,
            FDEPTH_G => 100)
         port map (
            clk        => rxClk,
            rst        => delayRst,
            delay      => messageDelay,
            fiducial_i => fiducial,
            advance_i  => advance(i),
            stream_i   => streams(i),
            frame_o    => dframe(i),    -- might need to latch data and valid on strobe
            strobe_o   => dstrobe(i),
            valid_o    => dvalid(i));
   end generate;


   rxVersion <= r.version;
   staData   <= r.vsnErr & (crcErr or doverflow0) & fiducial & eof & sof;

   comb : process (delayRst, dframe, dstrobe, dstrobe0, dvalid, iTimingMessage, r) is
      variable v          : RegType;
      variable extensionV : TimingExtensionArray;
   begin
      v := r;

      if dstrobe0 = '1' then
         v.version := x"0000" & iTimingMessage.version;
         if iTimingMessage.version = TIMING_MESSAGE_VERSION_C then
            v.vsnErr := '0';
         else
            v.vsnErr := '1';
         end if;
      end if;

      for i in 1 to 15 loop
         if (dstrobe(i) = '1') then
            v.dvalid(i) := dvalid(i);
         elsif (dstrobe0 = '1') then
            v.dvalid(i) := '0';
         end if;

         extensionV(i).valid := r.dvalid(i);
         extensionV(i).data  := dframe(i);

         if delayRst = '1' then
            extensionV(i).valid := '0';
            extensionV(i).data  := (others => '0');
         end if;
      end loop;

      rin             <= v;
      timingExtension <= extensionV;

   end process;

   seq : process (rxClk) is
   begin
      if rising_edge(rxClk) then
         r <= rin;
      end if;
   end process;

end architecture rtl;

