-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingFrameRx.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2018-12-01
-- Platform   : 
-- Standard   : VHDL'93/02
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

use work.StdRtlPkg.all;
use work.TimingPkg.all;
use work.TimingExtnPkg.all;

entity TimingFrameRx is
   generic (
      TPD_G    : time    := 1 ns);
   port (
      rxClk               : in  sl;
      rxRst               : in  sl;
      rxData              : in  TimingRxType;

      messageDelay        : in  slv(19 downto 0);
      messageDelayRst     : in  sl;
      
      timingMessage       : out TimingMessageType;
      timingMessageStrobe : out sl;
      timingMessageValid  : out sl;
      timingExtn          : out TimingExtnType;
      timingExtnValid     : out sl;

      rxVersion           : out slv(31 downto 0);
      staData             : out slv(4 downto 0)
      );
end entity TimingFrameRx;

architecture rtl of TimingFrameRx is

   -------------------------------------------------------------------------------------------------
   -- rxClk Domain
   -------------------------------------------------------------------------------------------------
   type StateType is (IDLE_S, FRAME_S);

   type RegType is record
      vsnErr  : sl;
      version : slv(31 downto 0);
      dvalid  : slv(TIMING_EXTN_STREAMS_C downto 1);
   end record;

   constant REG_INIT_C : RegType := (
     vsnErr  => '0',
     version => (others=>'1'),
     dvalid  => (others=>'0') );

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal fiducial           : sl;
   signal streams            : TimingSerialArray(TIMING_EXTN_STREAMS_C downto 0);
   signal streamIds          : Slv4Array        (TIMING_EXTN_STREAMS_C downto 0);
   signal advance            : slv              (TIMING_EXTN_STREAMS_C downto 0);
   signal sof, eof, crcErr   : sl;
   signal dframe0            : slv(TIMING_MESSAGE_BITS_C-1 downto 0);
   signal dvalid0            : sl;
   signal doverflow0         : sl;
   signal dstrobe0           : sl;
   signal delayRst           : sl;
   signal dmsg               : TimingMessageType;

   type Slv512Array is array (natural range <>) of slv(511 downto 0);
   signal dframe             : Slv512Array(TIMING_EXTN_STREAMS_C downto 1);
   signal dstrobe            : slv        (TIMING_EXTN_STREAMS_C downto 1);
   signal dvalid             : slv        (TIMING_EXTN_STREAMS_C downto 1);
   signal itimingExtn        : TimingExtnType;
   signal itimingExtnValid   : sl;
begin

   timingExtn      <= itimingExtn;
   timingExtnValid <= itimingExtnValid;
   
   delayRst <= rxRst or messageDelayRst;

   GEN_STREAM_IDS : for i in 0 to TIMING_EXTN_STREAMS_C generate
     streamIds(i) <= toSlv(i,4);
   end generate;
     
   U_Deserializer : entity work.TimingDeserializer
      generic map ( TPD_G=>TPD_G, STREAMS_C => streams'length )
      port map ( clk       => rxClk,
                 rst       => rxRst,
                 fiducial  => fiducial,
                 streams   => streams,
                 streamIds => streamIds,
                 advance   => advance,
                 data      => rxData,
                 sof       => sof,
                 eof       => eof,
                 crcErr    => crcErr );

   U_Delay0 : entity work.TimingSerialDelay
     generic map ( TPD_G=>TPD_G, NWORDS_G => TIMING_MESSAGE_WORDS_C,
                   FDEPTH_G => 100 )
     port map ( clk        => rxClk,
                rst        => delayRst,
                delay      => messageDelay,
                fiducial_i => fiducial,
                advance_i  => advance(0),
                stream_i   => streams(0),
                frame_o    => dframe0,
                strobe_o   => dstrobe0,
                valid_o    => dvalid0,
                overflow_o => doverflow0);

   dmsg                <= toTimingMessageType(dframe0);
   timingMessage       <= dmsg;
   timingMessageStrobe <= dstrobe0;
   timingMessageValid  <= dvalid0 and not r.vsnErr;

   GEN_EXTN : if TIMING_EXTN_STREAMS_C > 0 generate
     GEN_FOR : for i in 1 to TIMING_EXTN_STREAMS_C generate
       U_Extn : entity work.TimingSerialDelay
         generic map ( TPD_G    => TPD_G,
                       NWORDS_G => TIMING_EXTN_WORDS_C(i-1),
                       FDEPTH_G => 100 )
         port map ( clk        => rxClk,
                    rst        => delayRst,
                    delay      => messageDelay,
                    fiducial_i => fiducial,
                    advance_i  => advance(i),
                    stream_i   => streams(i),
                    frame_o    => dframe (i)(16*TIMING_EXTN_WORDS_C(i-1)-1 downto 0),
                    strobe_o   => dstrobe(i),
                    valid_o    => dvalid (i));
     end generate;
   end generate;

   rxVersion           <= r.version;
   staData             <= r.vsnErr & (crcErr or doverflow0) & fiducial & eof & sof;

   comb: process ( delayRst, r, dmsg, dstrobe0, dstrobe,
                   dframe, dvalid, itimingExtn, itimingExtnValid, fiducial) is
     variable v : RegType;
     variable extn  : TimingExtnType;
     variable extnv : sl;
   begin
     v     := r;
     extn  := itimingExtn;
     extnv := itimingExtnValid;

     if dstrobe0 = '1' then
       v.version := x"0000" & dmsg.version;
       if dmsg.version=TIMING_MESSAGE_VERSION_C then
         v.vsnErr := '0';
       else
         v.vsnErr := '1';
       end if;
     end if;

     for i in 1 to TIMING_EXTN_STREAMS_C loop

       if dstrobe(i) = '1' then
         v.dvalid(i) := dvalid(i);
       elsif dstrobe0 = '1' then
         v.dvalid(i) := '0';
       end if;

       toTimingExtnType( stream => i,
                         vector => dframe(i),
                         validi => r.dvalid(i),
                         extn   => extn,
                         valido => extnv );
     end loop;

     if delayRst = '1' then
       extn  := TIMING_EXTN_INIT_C;
       extnv := '0';
     end if;
     
     rin <= v;

     itimingExtn      <= extn;
     itimingExtnValid <= extnv;
   end process;

   seq: process ( rxClk ) is
   begin
     if rising_edge(rxClk) then
       r <= rin;
     end if;
   end process;
     
end architecture rtl;

