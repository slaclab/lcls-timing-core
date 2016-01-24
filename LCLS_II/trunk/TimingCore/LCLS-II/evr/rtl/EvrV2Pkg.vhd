-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2Pkg.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2016-01-24
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

use work.StdRtlPkg.all;
use work.TimingPkg.all;

package EvrV2Pkg is

  constant TriggerOutputs  : integer := 12;
  constant ReadoutChannels : integer := 12;
  
  -- pipeline depth of frames for integrating BSA active signals:
  -- BSA active signals are integrating from <BsaActiveSetup> frames
  -- prior to the <eventSelect> until <BsaActiveDelay> + <BsaActiveWidth> after
  -- the <eventSelect>
  constant BsaActiveSetup : integer := 108;
  
  type EvrV2ChannelConfig is record
    enabled          : sl;
    -- EventSelection
    rateSel          : slv(15 downto 0);
    -- Bits(15:14)=(fixed,AC,seq,reserved)
    -- fixed:  marker = 3:0
    -- AC   :  marker = 2:0;  TS = 8:3 (mask)
    -- seq  :  bit    = 5:0;  seq = 10:6
    destSel          : slv(15 downto 0);
    -- 15:15 = DONT_CARE
    --  3:0  = Destination
    -- BSA
    bsaEnabled       : sl;              -- participate in BSA
    bsaActiveSetup   : slv( 6 downto 0);
    bsaActiveDelay   : slv(19 downto 0);
    bsaActiveWidth   : slv(19 downto 0);
    dmaEnabled       : sl;
  end record;

  constant EVRV2_CHANNEL_CONFIG_INIT_C : EvrV2ChannelConfig := (
    enabled        => '0',
    rateSel        => (others=>'0'),
    destSel        => (others=>'0'),
    bsaEnabled     => '0',
    bsaActiveSetup => (others=>'0'),
    bsaActiveDelay => (others=>'0'),
    bsaActiveWidth => (others=>'0'),
    dmaEnabled     => '0' );

  type EvrV2ChannelConfigArray is array (natural range<>) of EvrV2ChannelConfig;

  type EvrV2TriggerConfigType is record
    enabled  : sl;
    polarity : sl;
    delay    : slv(19 downto 0);
    width    : slv(19 downto 0);
    channel  : slv( 3 downto 0);
  end record;

  constant EVRV2_TRIGGER_CONFIG_INIT_C : EvrV2TriggerConfigType := (
    enabled   => '0',
    polarity  => '1',
    delay     => (others=>'0'),
    width     => (others=>'0'),
    channel   => (others=>'0') );

  type EvrV2TriggerConfigArray is array (natural range<>) of EvrV2TriggerConfigType;

  type EvrV2BsaControlType is record
    timeStamp  : slv(63 downto 0);
    bsaInit    : slv(63 downto 0);
    bsaDone    : slv(63 downto 0);
  end record;
  
  constant EVRV2_BSA_CONTROL_INIT_C : EvrV2BsaControlType := (
    timeStamp  => (others=>'0'),
    bsaInit    => (others=>'0'),
    bsaDone    => (others=>'0') );

  type EvrV2BsaChannelType is record
    pulseId    : slv(63 downto 0);
    bsaActive  : slv(63 downto 0);
    bsaAvgDone : slv(63 downto 0);
  end record;

  constant EVRV2_BSA_CHANNEL_INIT_C : EvrV2BsaChannelType := (
    pulseId   => (others=>'0'),
    bsaActive => (others=>'0'),
    bsaAvgDone=> (others=>'0') );

  type EvrV2BsaChannelArray is array (natural range<>) of EvrV2BsaChannelType;
  
  type EvrV2DataType is record
    strobe      : sl;
    timingFrame : TimingMessageType;
  end record;

  type EvrV2CacheControlType is record
    reset       : sl;
    rdclk       : sl;
    advance     : sl;
  end record;

  constant EVRV2_CACHE_CONTROL_INIT_C : EvrV2CacheControlType := (
    reset   => '0',
    rdclk   => '0',
    advance => '0' );
  
  type EvrV2CacheControlArray is array (natural range<>) of EvrV2CacheControlType;
  
  type EvrV2CacheDataType is record
    empty       : sl;
    count       : slv(31 downto 0);
    data        : slv(31 downto 0);
  end record;

  constant EVRV2_CACHE_DATA_INIT_C : EvrV2CacheDataType := (
    empty   => '0',
    count   => (others=>'0'),
    data    => (others=>'0') );

  type EvrV2CacheDataArray is array (natural range<>) of EvrV2CacheDataType;

  type EvrV2DmaControlType is record
    ready : sl;
  end record;

  constant EVRV2_DMA_CONTROL_INIT_C : EvrV2DmaControlType := ( ready => '0' );

  type EvrV2DmaControlArray is array (natural range<>) of EvrV2DmaControlType;

  type EvrV2DmaDataType is record
    tValid : sl;
    tLast  : sl;
    tData  : slv(31 downto 0);
  end record;

  constant EVRV2_DMA_DATA_INIT_C : EvrV2DmaDataType := (
    tValid  => '0',
    tLast   => '0',
    tData   => (others=>'0') );

  type EvrV2DmaDataArray is array (natural range<>) of EvrV2DmaDataType;

  constant EVRV2_EVENT_TAG       : slv(15 downto 0) := x"0000";
  constant EVRV2_BSA_CONTROL_TAG : slv(15 downto 0) := x"0001";
  constant EVRV2_BSA_CHANNEL_TAG : slv(15 downto 0) := x"0002";
  
end EvrV2Pkg;
  
