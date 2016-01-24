-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2BsaChannel.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2016-01-24
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description:
-- Integrates the BSA Active and AvgDone bits over a configured interval of
-- timing frames with respect to <evtSelect>.  If another <evtSelect> occurs
-- before the completion of the interval, the partially integrated result is
-- taken.  The <strobeOut> signal indicates validity of the integrated result.
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
use work.EvrV2Pkg.all;

entity EvrV2BsaChannel is
  generic (
    TPD_G : time := 1ns;
    CHAN_C  : integer := 0 );
  port (
    evrClk        : in  sl;
    evrRst        : in  sl;
    channelConfig : in  EvrV2ChannelConfig;
    evtSelect     : in  sl;
    strobeIn      : in  sl;
    dataIn        : in  TimingMessageType;
    dmaCntl       : in  EvrV2DmaControlType;
    dmaData       : out EvrV2DmaDataType );
end EvrV2BsaChannel;


architecture mapping of EvrV2BsaChannel is

  type BsaIntState is (IDLE_S, DELAY_S, INTEG_S);

  type RegType is record
    state : BsaIntState;
    addra : slv( 6 downto 0);
    addrb : slv( 6 downto 0);
    count : slv(19 downto 0);
    strobe : slv(7 downto 0);
    dataBuff : EvrV2BsaChannelType;
    dataOut  : slv(255 downto 0);
  end record;

  constant REG_TYPE_INIT_C : RegType := (
    state  => IDLE_S,
    addra  => (others=>'0'),
    addrb  => (others=>'0'),
    count  => (others=>'0'),
    strobe => (others=>'0'),
    dataBuff=> EVRV2_BSA_CHANNEL_INIT_C,
    dataOut => (others=>'0') );
  
  signal r    : RegType := REG_TYPE_INIT_C;
  signal r_in : RegType;

  signal bsaActiveSetup : slv( 6 downto 0);
  signal bsaActiveDelay : slv(19 downto 0);
  signal bsaActiveWidth : slv(19 downto 0);
  signal bsaEnabled     : sl;
  signal countResetS : sl;

  signal frame, frameIn, frameOut : slv(128 downto 0);
  
begin  -- mapping

  dmaData.tValid <= r.strobe(0);
  dmaData.tLast  <= r.strobe(0) and not r.strobe(1);
  dmaData.tData  <= r.dataOut(31 downto 0);
  
  frameIn    <= evtSelect & dataIn.bsaAvgDone & dataIn.bsaActive;
  frame      <= frameIn when allBits(channelConfig.bsaActiveSetup,'0') else
                frameOut;

  -- Could save half of the BRAM by instrumenting as double wide SinglePort
  U_Pipeline : entity work.SimpleDualPortRam
    generic map ( TPD_G        => TPD_G,
                  DATA_WIDTH_G => 129,
                  ADDR_WIDTH_G => 7 )
    port map    ( clka         => evrClk,
                  ena          => strobeIn,
                  wea          => '1',
                  addra        => r.addra,
                  dina         => frameIn,
                  clkb         => evrClk,
                  enb          => strobeIn,
                  addrb        => r.addrb,
                  doutb        => frameOut );

  process (r, frame, strobeIn, channelConfig, dataIn, evrRst, evtSelect, countResetS)
    variable v : RegType;
  begin  -- process
    v := r;

    v.strobe := '0' & r.strobe(r.strobe'left downto 1);
    v.dataOut:= x"00000000" & r.dataOut(r.dataOut'left downto 32);
    if strobeIn='1' then
      v.addrb := r.addrb+1;
      v.addra := r.addrb+channelConfig.bsaActiveSetup+1;
      v.count := r.count+1;

      -- premature termination
      if evtSelect='1' then
        v.dataOut            := r.dataBuff.bsaAvgDone &
                                r.dataBuff.bsaActive &
                                r.dataBuff.pulseId    &
                                slv(conv_unsigned(CHAN_C,16)) &
                                EVRV2_BSA_CHANNEL_TAG &
                                slv(conv_unsigned(r.dataOut'length,32));
        v.dataBuff.pulseId   := dataIn.pulseId;
        v.dataBuff.bsaActive := (others=>'0');
        v.dataBuff.bsaAvgDone:= (others=>'0');

        if r.state/=IDLE_S then
          v.dataOut(63) := '1';
          v.strobe      := (others=>'1');
        end if;

        if channelConfig.bsaActiveDelay=x"00000" then
          v.state := INTEG_S;
        else
          v.state := DELAY_S;
        end if;
        v.count := x"00001";
      elsif r.state=DELAY_S then
        if r.count=channelConfig.bsaActiveDelay then
          v.state := INTEG_S;
          v.count := x"00001";
        end if;
      elsif r.state=INTEG_S then
        v.dataBuff.bsaActive  := r.dataBuff.bsaActive  or frame( 63 downto 0);
        v.dataBuff.bsaAvgDone := r.dataBuff.bsaAvgDone or frame(127 downto 64);
        -- natural termination
        if r.count=channelConfig.bsaActiveWidth then
          v.dataOut            := r.dataBuff.bsaAvgDone &
                                r.dataBuff.bsaActive &
                                r.dataBuff.pulseId    &
                                slv(conv_unsigned(CHAN_C,16)) &
                                EVRV2_BSA_CHANNEL_TAG &
                                slv(conv_unsigned(r.dataOut'length,32));
          v.strobe             := (others=>'1');
          v.state              := IDLE_S;
        end if;
      end if;
      
    end if;

    if evrRst='1' or channelConfig.bsaEnabled='0' then
      v := REG_TYPE_INIT_C;
    end if;

    r_in <= v;
  end process;    

  process (evrClk)
  begin  -- process
    if rising_edge(evrClk) then
      r <= r_in;
    end if;
  end process;

end mapping;
