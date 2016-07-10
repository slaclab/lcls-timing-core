-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingFrameRx.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2016-07-09
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
use work.AxiLitePkg.all;
use work.TimingPkg.all;

entity TimingFrameRx is

   generic (
      TPD_G             : time            := 1 ns;
      AXIL_ERROR_RESP_G : slv(1 downto 0) := AXI_RESP_OK_C);
   port (
      rxClk               : in  sl;
      rxRst               : in  sl;
      rxData              : in  TimingRxType;

      messageDelay        : in  slv(19 downto 0);
      messageDelayRst     : in  sl;
      
      timingMessage       : out TimingMessageType;
      timingMessageStrobe : out sl;
      timingMessageValid  : out sl;

      exptMessage         : out ExptMessageType;
      exptMessageValid    : out sl;
      
      staData             : out slv(3 downto 0)
      );
end entity TimingFrameRx;

architecture rtl of TimingFrameRx is

   -------------------------------------------------------------------------------------------------
   -- rxClk Domain
   -------------------------------------------------------------------------------------------------
   type StateType is (IDLE_S, FRAME_S);

   type RegType is record
      timingMessage       : TimingMessageType;
      timingMessageShift  : slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      timingMessageStrobe : sl;
      timingMessageValid  : sl;
      exptMessage         : ExptMessageType;
      exptMessageShift    : slv(EXPT_MESSAGE_BITS_C-1 downto 0);
      exptMessageValid    : sl;
   end record;

   constant REG_INIT_C : RegType := (
      timingMessage       => TIMING_MESSAGE_INIT_C,
      timingMessageShift  => (others => '0'),
      timingMessageStrobe => '0',
      timingMessageValid  => '0',
      exptMessage         => EXPT_MESSAGE_INIT_C,
      exptMessageShift    => (others => '0'),
      exptMessageValid    => '0'
      );

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal fiducial           : sl;
   signal streams            : TimingSerialArray(1 downto 0);
   signal streamIds          : Slv4Array        (1 downto 0) := ( x"1", x"0" );
   signal advance            : slv              (1 downto 0);
   signal sof, eof, crcErr   : sl;
   signal dframe0            : slv(TIMING_MESSAGE_BITS_C-1 downto 0);
   signal dvalid0            : sl;
   signal doverflow0         : sl;
   signal dframe1            : slv(EXPT_MESSAGE_BITS_C-1 downto 0);
   signal dvalid1            : sl;
   signal dstrobe            : sl;
   signal delayRst           : sl;
begin

   delayRst <= rxRst or messageDelayRst;
   
   U_Deserializer : entity work.TimingDeserializer
      generic map ( STREAMS_C => 2 )
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
     generic map ( NWORDS_G => TIMING_MESSAGE_WORDS_C,
                   FDEPTH_G => 100 )
     port map ( clk        => rxClk,
                rst        => delayRst,
                delay      => messageDelay,
                fiducial_i => fiducial,
                advance_i  => advance(0),
                stream_i   => streams(0),
                frame_o    => dframe0,
                strobe_o   => dstrobe,
                valid_o    => dvalid0,
                overflow_o => doverflow0);

   U_Delay1 : entity work.TimingSerialDelay
     generic map ( NWORDS_G => EXPT_MESSAGE_BITS_C/16,
                   FDEPTH_G => 100 )
     port map ( clk        => rxClk,
                rst        => delayRst,
                delay      => messageDelay,
                fiducial_i => fiducial,
                advance_i  => advance(1),
                stream_i   => streams(1),
                frame_o    => dframe1,
                strobe_o   => open,
                valid_o    => dvalid1 );

   timingMessage       <= toTimingMessageType(dframe0);
   timingMessageStrobe <= dstrobe;
   timingMessageValid  <= dvalid0;
   exptMessage         <= toExptMessageType(dframe1);
   exptMessageValid    <= dvalid1;

   staData             <= (crcErr or doverflow0) & fiducial & eof & sof;
   
end architecture rtl;

