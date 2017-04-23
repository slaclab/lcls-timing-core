-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2BsaChannel.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2017-04-23
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
    dmaData       : out EvrV2DmaDataType );
end EvrV2BsaChannel;


architecture mapping of EvrV2BsaChannel is

  type BsaIntState is (IDLE_S, DELAY_S, INTEG_S);
  type BsaReadState is ( IDLR_S, TAG_S,
                         PIDL_S, PIDU_S,
                         ACTL_S, ACTU_S,
                         AVDL_S, AVDU_S,
                         DONL_S, DONU_S );
  
  type RegType is record
    state : BsaIntState;
    rstate : BsaReadState;
    addra : slv( 8 downto 0);
    addrb : slv( 8 downto 0);
    count : slv(19 downto 0);
    phase       : slv(1 downto 0);
    strobe      : sl;
    evtSelect   : sl;
    ramen       : sl;
    pulseId     : slv(63 downto 0);
    pendActive  : slv(63 downto 0); -- mask of EDEFs gone active
    pendAvgDone : slv(63 downto 0); -- mask of EDEFs awaiting AvgDone
    newActive   : slv(63 downto 0); -- mask of EDEFs just gone active
    newAvgDone  : slv(63 downto 0);
    newDone     : slv(63 downto 0);
    newActiveOr : sl;
    newAvgDoneOr: sl;
    newDoneOr   : sl;
    dmaData     : EvrV2DmaDataType;
  end record;

  constant REG_TYPE_INIT_C : RegType := (
    state  => IDLE_S,
    rstate => IDLR_S,
    addra  => (others=>'0'),
    addrb  => (others=>'0'),
    count  => (others=>'0'),
    phase  => (others=>'0'),
    strobe => '0',
    evtSelect  => '0',
    ramen  => '0',
    pulseId     => (others=>'0'),
    pendActive  => (others=>'0'),
    pendAvgDone => (others=>'0'),
    newActive   => (others=>'0'),
    newAvgDone  => (others=>'0'),
    newDone     => (others=>'0'),
    newActiveOr => '0',
    newAvgDoneOr=> '0',
    newDoneOr   => '0',
    dmaData     => EVRV2_DMA_DATA_INIT_C );
  
  signal r    : RegType := REG_TYPE_INIT_C;
  signal rin  : RegType;

  signal frame, frameIn, frameOut : slv(63 downto 0);
  
begin  -- mapping

  dmaData    <= r.dmaData;
  
  frameIn    <= dataIn.bsaActive  when r.phase="00" else
                dataIn.bsaAvgDone when r.phase="01" else
                dataIn.bsaDone    when r.phase="10" else
                dataIn.pulseId;
  
  frame      <= frameIn when allBits(channelConfig.bsaActiveSetup,'0') else
                frameOut;

  -- Could save half of the BRAM by instrumenting as double wide SinglePort
  U_Pipeline : entity work.SimpleDualPortRam
    generic map ( TPD_G        => TPD_G,
                  DATA_WIDTH_G => 64,
                  ADDR_WIDTH_G => 9 )
    port map    ( clka         => evrClk,
                  ena          => '1',
                  wea          => rin.ramen,
                  addra        => r.addra,
                  dina         => frameIn,
                  clkb         => evrClk,
                  enb          => '1',
                  addrb        => r.addrb,
                  doutb        => frameOut );

  process (r, frame, strobeIn, channelConfig, dataIn, evrRst, evtSelect)
    variable v : RegType;
  begin  -- process
    v := r;
    v.strobe    := strobeIn;
    v.evtSelect := evtSelect;
    
    if r.phase/="00" then
      v.phase := r.phase+1;
    else
      v.ramen := '0';
    end if;

    if strobeIn='1' or r.addrb(1 downto 0)/="00" then
      v.addrb := r.addrb+1;
    end if;
    
    v.addra := r.addrb+(channelConfig.bsaActiveSetup & "00");

    if r.strobe='1' then
      v.count := r.count+1;
      v.phase := r.phase+1;
      v.ramen := '1';
      
      -- premature termination
      if r.evtSelect='1' then
        if channelConfig.bsaActiveDelay=x"00000" then
          v.state := INTEG_S;
          v.pendActive      := (others=>'0');
        else
          v.state := DELAY_S;
        end if;
        v.count := x"00001";
      elsif r.state=DELAY_S then
        if r.count=channelConfig.bsaActiveDelay then
          v.state := INTEG_S;
          v.count := x"00001";
          v.pendActive      := (others=>'0');
        end if;
      elsif r.state=INTEG_S then
        if r.count=channelConfig.bsaActiveWidth then
          v.state := IDLE_S;
        end if;
      end if;
    end if;

    if v.ramen='1' then
      case r.phase is
        when "00" =>
          if v.state=INTEG_S then
            v.newActive   := frame and not r.pendActive;
            v.pendAvgDone := r.pendAvgDone or v.newActive;
          end if;
        when "01" =>
          if r.state=INTEG_S then
            v.newActiveOr := uOr(r.newActive);
          end if;
          v.pendActive  := r.newActive or r.pendActive;
          v.newAvgDone  := frame and r.pendAvgDone;
        when "10" =>
          v.newDone     := frame;
          v.pendAvgDone := r.pendAvgDone and not r.newAvgDone;
          v.newAvgDoneOr:= uOr(r.newAvgDone);
        when "11" =>
          v.pulseId     := frame;
          v.newDoneOr   := uOr(r.newDone);
        when others => null;
      end case;
    end if;

    if r.ramen='1' and r.phase="00" and r.rstate=IDLR_S then
      if (r.newActiveOr='1' or r.newAvgDoneOr='1' or r.newDoneOr='1') then
        v.rstate       := TAG_S;
        v.newActiveOr  := '0';
        v.newAvgDoneOr := '0';
        v.newDoneOr    := '0';
      end if;
    end if;

    if r.rstate = IDLR_S then
      v.dmaData.tValid := '0';
    else
      v.dmaData.tValid := '1';
    end if;
    
    case r.rstate is
      when TAG_S =>
        v.dmaData.tData  := EVRV2_BSA_CHANNEL_TAG &
                            slv(conv_unsigned(CHAN_C,16));
        v.rstate := PIDL_S;
      when PIDL_S =>
        v.dmaData.tData  := r.pulseId(31 downto 0);
        v.rstate := PIDU_S;
      when PIDU_S =>
        v.dmaData.tData  := r.pulseId(63 downto 32);
        v.rstate := ACTL_S;
      when ACTL_S =>
        v.dmaData.tData  := r.newActive(31 downto 0);
        v.rstate := ACTU_S;
      when ACTU_S =>
        v.dmaData.tData  := r.newActive(63 downto 32);
        v.rstate := AVDL_S;
      when AVDL_S =>
        v.dmaData.tData  := r.newAvgDone(31 downto 0);
        v.rstate := AVDU_S;
      when AVDU_S =>
        v.dmaData.tData  := r.newAvgDone(63 downto 32);
        v.rstate := DONL_S;
      when DONL_S =>
        v.dmaData.tData  := r.newDone(31 downto 0);
        v.rstate := DONU_S;
      when DONU_S =>
        v.dmaData.tData  := r.newDone(63 downto 32);
        v.rstate := IDLR_S;
        v.newActive  := (others=>'0');
        v.newAvgDone := (others=>'0');
        v.newDone    := (others=>'0');
      when others => null;
    end case;
    
    if evrRst='1' or channelConfig.bsaEnabled='0' then
      v := REG_TYPE_INIT_C;
    end if;

    rin <= v;
  end process;    

  process (evrClk)
  begin  -- process
    if rising_edge(evrClk) then
      r <= rin;
    end if;
  end process;

end mapping;
