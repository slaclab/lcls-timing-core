-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingFrameRx.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2016-06-28
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

begin

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

   comb: process (r, rxRst, advance, streams, fiducial) is
      variable v : RegType;
   begin
      v := r;
      v.timingMessageStrobe:= '0';

      if advance(0)='1' then
        v.timingMessageShift := streams(0).data & r.timingMessageShift(TIMING_MESSAGE_BITS_C-1 downto 16);
      end if;
      if advance(1)='1' then
        v.exptMessageShift   := streams(1).data & r.exptMessageShift(EXPT_MESSAGE_BITS_C-1 downto 16);
      end if;

      if (fiducial='1') then
        v.timingMessageStrobe := '1';
        v.timingMessage       := toTimingMessageType(r.timingMessageShift(TIMING_MESSAGE_BITS_C-1 downto 0));
        v.timingMessageValid  := streams(0).ready;
        v.exptMessageValid    := streams(1).ready;
        v.exptMessage         := toExptMessageType(r.exptMessageShift(EXPT_MESSAGE_BITS_C-1 downto 0));
      end if;

      if (rxRst='1') then
        v := REG_INIT_C;
      end if;
      
      rin <= v;
   end process comb;
   
   seq : process (rxClk) is
   begin
      if (rising_edge(rxClk)) then
         r <= rin after TPD_G;
      end if;
   end process seq;

   timingMessage       <= r.timingMessage;
   timingMessageStrobe <= r.timingMessageStrobe;
   timingMessageValid  <= r.timingMessageValid;
   exptMessage         <= r.exptMessage;
   exptMessageValid    <= r.exptMessageValid;

   staData             <= crcErr & fiducial & eof & sof;
   
end architecture rtl;

