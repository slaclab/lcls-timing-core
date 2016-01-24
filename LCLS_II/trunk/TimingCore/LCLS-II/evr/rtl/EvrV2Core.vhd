-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2Core.vhd
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
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;
use ieee.NUMERIC_STD.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;
use work.AxiStreamPkg.all;
use work.SsiPciePkg.all;
use work.TimingPkg.all;
use work.EvrV2Pkg.all;
--use work.PciPkg.all;
use work.SsiPkg.all;

entity EvrV2Core is
  generic (
    TPD_G : time := 1 ns);
  port (
    -- AXI-Lite and IRQ Interface
    axiClk              : in  sl;
    axiRst              : in  sl;
    axilWriteMaster     : in  AxiLiteWriteMasterType;
    axilWriteSlave      : out AxiLiteWriteSlaveType;
    axilReadMaster      : in  AxiLiteReadMasterType;
    axilReadSlave       : out AxiLiteReadSlaveType;
    irqActive           : in  sl;
    irqEnable           : out sl;
    irqReq              : out sl;
    -- DMA
    dmaRxIbMaster       : out AxiStreamMasterType;
    dmaRxIbSlave        : in  AxiStreamSlaveType;
    dmaRxTranFromPci    : in  TranFromPcieType;
    -- EVR Ports
    evrClk              : in  sl;
    evrRst              : in  sl;
    evrBus              : in  TimingBusType;
    txPhyClk            : in  sl;
    txPhyRst            : in  sl;
    gtxDebug            : in  slv(7 downto 0);
    -- Trigger and Sync Port
    syncL               : in  sl;
    trigOut             : out slv(11 downto 0);
    evrModeSel          : out sl;
    -- Misc.
    cardRst             : in  sl;
    ledRedL             : out sl;
    ledGreenL           : out sl;
    ledBlueL            : out sl);  
end EvrV2Core;

architecture mapping of EvrV2Core is

  constant NUM_AXI_MASTERS_C : natural := 2;
  constant CSR_INDEX_C       : natural := 0;
  constant DMA_INDEX_C       : natural := 1;

  constant AXI_CROSSBAR_MASTERS_CONFIG_C : AxiLiteCrossbarMasterConfigArray(NUM_AXI_MASTERS_C-1 downto 0) := (
    CSR_INDEX_C      => (
      baseAddr      => x"00000000",
      addrBits      => 10,
      connectivity  => X"0001"),
    DMA_INDEX_C => (
      baseAddr      => x"00000400",
      addrBits      => 10,
      connectivity  => X"0001") );
  
  signal mAxiWriteMasters : AxiLiteWriteMasterArray(NUM_AXI_MASTERS_C-1 downto 0);
  signal mAxiWriteSlaves  : AxiLiteWriteSlaveArray (NUM_AXI_MASTERS_C-1 downto 0);
  signal mAxiReadMasters  : AxiLiteReadMasterArray (NUM_AXI_MASTERS_C-1 downto 0);
  signal mAxiReadSlaves   : AxiLiteReadSlaveArray  (NUM_AXI_MASTERS_C-1 downto 0);
  
  constant STROBE_INTERVAL_C : integer := 10;
  
  signal bsaControl       : EvrV2BsaControlType;
  signal bsaChannel       : EvrV2BsaChannelArray   (ReadoutChannels-1 downto 0);
  signal channelConfig    : EvrV2ChannelConfigArray(ReadoutChannels-1 downto 0);
  signal channelConfigS   : EvrV2ChannelConfigArray(ReadoutChannels-1 downto 0) := (others=>EVRV2_CHANNEL_CONFIG_INIT_C);
  signal triggerConfig    : EvrV2TriggerConfigArray(TriggerOutputs-1 downto 0);
  signal triggerConfigS   : EvrV2TriggerConfigArray(TriggerOutputs-1 downto 0) := (others=>EVRV2_TRIGGER_CONFIG_INIT_C);
  
  signal gtxDebugS   : slv(7 downto 0);

  signal rStrobe        : slv(ReadoutChannels*STROBE_INTERVAL_C downto 0) := (others=>'0');
  signal timingMsg      : TimingMessageType := TIMING_MESSAGE_INIT_C;
  signal eventSel       : slv(ReadoutChannels-1 downto 0) := (others=>'0');
  signal eventCount     : SlVectorArray(ReadoutChannels downto 0,31 downto 0);
  signal rstCount : sl;
  
  signal dmaControl : EvrV2DmaControlArray(ReadoutChannels+1 downto 0) :=
    (others=>EVRV2_DMA_CONTROL_INIT_C);
  signal dmaData    : EvrV2DmaDataArray(ReadoutChannels+1 downto 0);

  constant SAXIS_MASTER_CONFIG_C : AxiStreamConfigType := ssiAxiStreamConfig(4);
  
  signal dmaMaster : AxiStreamMasterType;
  signal dmaSlave  : AxiStreamSlaveType;

  signal pciClk : sl;
  signal pciRst : sl;

  signal rxDescToPci   : DescToPcieType;
  signal rxDescFromPci : DescFromPcieType;

  signal bsaEnabled : slv(ReadoutChannels-1 downto 0);
  signal anyBsaEnabled : sl;
  
  signal irqRequest : sl;

begin  -- rtl

  -- Undefined signals
  ledRedL    <= '1';
  ledGreenL  <= '1';
  ledBlueL   <= '1';
  
  pciClk <= axiClk;
  pciRst <= axiRst;
  irqReq <= irqRequest;

  -------------------------
  -- AXI-Lite Crossbar Core
  -------------------------  
  AxiLiteCrossbar_Inst : entity work.AxiLiteCrossbar
    generic map (
      TPD_G              => TPD_G,
      NUM_SLAVE_SLOTS_G  => 1,
      NUM_MASTER_SLOTS_G => NUM_AXI_MASTERS_C,
      MASTERS_CONFIG_G   => AXI_CROSSBAR_MASTERS_CONFIG_C)
    port map (
      axiClk              => axiClk,
      axiClkRst           => axiRst,
      sAxiWriteMasters(0) => axilWriteMaster,
      sAxiWriteSlaves(0)  => axilWriteSlave,
      sAxiReadMasters(0)  => axilReadMaster,
      sAxiReadSlaves(0)   => axilReadSlave,
      mAxiWriteMasters    => mAxiWriteMasters,
      mAxiWriteSlaves     => mAxiWriteSlaves,
      mAxiReadMasters     => mAxiReadMasters,
      mAxiReadSlaves      => mAxiReadSlaves);   
  
  U_PciRxDesc : entity work.EvrV2PcieRxDesc
    generic map ( DMA_SIZE_G       => 1 )
    port map (    dmaDescToPci(0)  => rxDescToPci,
                  dmaDescFromPci(0)=> rxDescFromPci,
                  axiReadMaster    => mAxiReadMasters (DMA_INDEX_C),
                  axiReadSlave     => mAxiReadSlaves  (DMA_INDEX_C),
                  axiWriteMaster   => mAxiWriteMasters(DMA_INDEX_C),
                  axiWriteSlave    => mAxiWriteSlaves (DMA_INDEX_C),
                  irqReq           => irqRequest,
                  cntRst           => '0',
                  pciClk           => pciClk,
                  pciRst           => pciRst );

  U_PciRxDma : entity work.EvrV2PcieRxDma
    generic map ( TPD_G                 => TPD_G,
                  SAXIS_MASTER_CONFIG_G => SAXIS_MASTER_CONFIG_C )
    port map (    sAxisClk    => evrClk,
                  sAxisRst    => evrRst,
                  sAxisMaster => dmaMaster,
                  sAxisSlave  => dmaSlave,
                  pciClk      => pciClk,
                  pciRst      => pciRst,
                  dmaIbMaster => dmaRxIbMaster,
                  dmaIbSlave  => dmaRxIbSlave,
                  dmaDescFromPci => rxDescFromPci,
                  dmaDescToPci   => rxDescToPci,
                  dmaTranFromPci => dmaRxTranFromPci,
                  dmaChannel     => x"0" );

  U_Dma : entity work.EvrV2Dma
    generic map ( CHANNELS_C    => ReadoutChannels+2,
                  AXIS_CONFIG_C => SAXIS_MASTER_CONFIG_C )
    port map (    clk        => evrClk,
                  dmaCntl    => dmaControl,
                  dmaData    => dmaData,
                  dmaMaster  => dmaMaster,
                  dmaSlave   => dmaSlave );
  
  U_BsaControl : entity work.EvrV2BsaControl
    generic map ( TPD_G      => TPD_G )
    port map (    evrClk     => evrClk,
                  evrRst     => evrRst,
                  enable     => anyBsaEnabled,
                  strobeIn   => evrBus.strobe,
                  dataIn     => evrBus.message,
                  dmaCntl    => dmaControl     (ReadoutChannels),
                  dmaData    => dmaData        (ReadoutChannels) );

  Loop_BsaCh: for i in 0 to ReadoutChannels-1 generate
    U_EventSel   : entity work.EvrV2EventSelect
      generic map ( TPD_G         => TPD_G )
      port map    ( clk           => evrClk,
                    rst           => evrRst,
                    config        => channelConfigS(i),
                    strobeIn      => rStrobe(i*STROBE_INTERVAL_C),
                    dataIn        => timingMsg,
                    selectOut     => eventSel(i) );
    U_BsaChannel : entity work.EvrV2BsaChannel
      generic map ( TPD_G         => TPD_G )
      port map    ( evrClk        => evrClk,
                    evrRst        => evrRst,
                    channelConfig => channelConfigS(i),
                    evtSelect     => eventSel(i),
                    strobeIn      => rStrobe(i*STROBE_INTERVAL_C+1),
                    dataIn        => timingMsg,
                    dmaCntl       => dmaControl(i),
                    dmaData       => dmaData(i) );
  end generate;  -- i

  U_EventDma : entity work.EvrV2EventDma
    generic map ( TPD_G      => TPD_G,
                  CHANNELS_C => ReadoutChannels )
    port map (    clk        => evrClk,
                  rst        => evrBus.strobe,
                  strobe     => rStrobe(ReadoutChannels*STROBE_INTERVAL_C),
                  eventSel   => eventSel,
                  eventData  => timingMsg,
                  dmaCntl    => dmaControl(ReadoutChannels+1),
                  dmaData    => dmaData   (ReadoutChannels+1) );
    
  process (evrClk)
  begin  -- process
    if rising_edge(evrClk) then
      rStrobe    <= rStrobe(rStrobe'left-1 downto 0) & evrBus.strobe;
      if evrBus.strobe='1' then
        timingMsg <= evrBus.message;
      end if;
    end if;
  end process;

  SyncVector_Gtx : entity work.SynchronizerVector
    generic map (
      TPD_G          => TPD_G,
      WIDTH_G        => 8)
    port map (
      clk                   => axiClk,
      dataIn                => gtxDebug,
      dataOut               => gtxDebugS );

  Sync_EvtCount : entity work.SyncStatusVector
    generic map ( TPD_G   => TPD_G,
                  WIDTH_G => ReadoutChannels+1 )
    port map    ( statusIn(ReadoutChannels) => evrBus.strobe,
                  statusIn(ReadoutChannels-1 downto 0) => eventSel,
                  cntRstIn     => rstCount,
                  rollOverEnIn => (others=>'1'),
                  cntOut       => eventCount,
                  wrClk        => evrClk,
                  wrRst        => evrRst,
                  rdClk        => axiClk,
                  rdRst        => axiRst );

  Out_Trigger: for i in 0 to TriggerOutputs-1 generate
     U_Trig : entity work.EvrV2Trigger
        generic map ( TPD_G    => TPD_G,
                      CHANNELS_C => ReadoutChannels,
                      --DEBUG_C    => (i<1) )
                      DEBUG_C    => false )
        port map (    clk      => evrClk,
                      rst      => evrRst,
                      config   => triggerConfigS(i),
                      arm      => eventSel,
                      fire     => evrBus.strobe,
                      trigstate=> trigOut(i) );
  end generate Out_Trigger;
  
  U_EvrAxi : entity work.EvrV2Axi
    generic map ( TPD_G      => TPD_G,
                  CHANNELS_C => ReadoutChannels,
                  TRIGGERS_C => TriggerOutputs )
    port map (    axiClk              => axiClk,
                  axiRst              => axiRst,
                  axilWriteMaster     => mAxiWriteMasters (CSR_INDEX_C),
                  axilWriteSlave      => mAxiWriteSlaves  (CSR_INDEX_C),
                  axilReadMaster      => mAxiReadMasters  (CSR_INDEX_C),
                  axilReadSlave       => mAxiReadSlaves   (CSR_INDEX_C),
                  -- configuration
                  irqEnable           => irqEnable,
                  channelConfig       => channelConfig,
                  triggerConfig       => triggerConfig,
                  trigSel             => evrModeSel,
                  -- status
                  irqReq              => irqRequest,
                  rstCount            => rstCount,
                  eventCount          => eventCount,
                  gtxDebug            => gtxDebugS );

  anyBsaEnabled <= uOr(bsaEnabled);

  -- Synchronize configurations to evrClk
  Sync_Channel: for i in 0 to ReadoutChannels-1 generate
    
    U_SyncRate : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => channelConfig (i).rateSel'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).rateSel,
                    dataOut => channelConfigS(i).rateSel );
    
    U_SyncDest : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => channelConfig (i).destSel'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).destSel,
                    dataOut => channelConfigS(i).destSel );
     
    Sync_Enable : entity work.Synchronizer
      generic map ( TPD_G   => TPD_G )
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).enabled,
                    dataOut => channelConfigS(i).enabled );

    Sync_dmaEnable : entity work.Synchronizer
      generic map ( TPD_G   => TPD_G )
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).dmaEnabled,
                    dataOut => channelConfigS(i).dmaEnabled );

    Sync_bsaEnable : entity work.Synchronizer
      generic map ( TPD_G   => TPD_G )
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).bsaEnabled,
                    dataOut => bsaEnabled(i) );

    channelConfigS(i).bsaEnabled <= bsaEnabled(i);
    
    Sync_Setup : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => channelConfig (i).bsaActiveSetup'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).bsaActiveSetup,
                    dataOut => channelConfigS(i).bsaActiveSetup );
    
    Sync_Delay : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => channelConfig (i).bsaActiveDelay'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).bsaActiveDelay,
                    dataOut => channelConfigS(i).bsaActiveDelay );
    
    Sync_Width : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => channelConfig (i).bsaActiveWidth'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => channelConfig (i).bsaActiveWidth,
                    dataOut => channelConfigS(i).bsaActiveWidth );
  
  end generate Sync_Channel;

  Sync_Trigger: for i in 0 to TriggerOutputs-1 generate
    
    Sync_Enable : entity work.Synchronizer
      generic map ( TPD_G   => TPD_G )
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => triggerConfig (i).enabled,
                    dataOut => triggerConfigS(i).enabled );

    Sync_Polarity : entity work.Synchronizer
      generic map ( TPD_G   => TPD_G )
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => triggerConfig (i).polarity,
                    dataOut => triggerConfigS(i).polarity );

    Sync_Channel : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => triggerConfig (i).channel'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => triggerConfig (i).channel,
                    dataOut => triggerConfigS(i).channel );
    
    U_SyncDelay : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => triggerConfig (i).delay'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => triggerConfig (i).delay,
                    dataOut => triggerConfigS(i).delay );
    
    U_SyncWidth : entity work.SynchronizerVector
      generic map ( TPD_G   => TPD_G,
                    WIDTH_G => triggerConfig (i).width'length)
      port map (    clk     => evrClk,
                    rst     => evrRst,
                    dataIn  => triggerConfig (i).width,
                    dataOut => triggerConfigS(i).width );
     
  end generate Sync_Trigger;

end mapping;
