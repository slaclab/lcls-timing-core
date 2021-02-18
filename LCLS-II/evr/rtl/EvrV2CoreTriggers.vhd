-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description:
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
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;
use ieee.NUMERIC_STD.all;


library surf;
use surf.StdRtlPkg.all;
use surf.AxiLitePkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;
use lcls_timing_core.EvrV2Pkg.all;

entity EvrV2CoreTriggers is
  generic (
    TPD_G            : time             := 1 ns;
    NCHANNELS_G      : natural          := 1;   -- event selection channels
    NTRIGGERS_G      : natural          := 1;   -- trigger outputs
    TRIG_DEPTH_G     : natural          := 28;
    TRIG_PIPE_G      : natural          := 0;  -- no trigger pipeline by default
    COMMON_CLK_G     : boolean          := false;
    EVR_CARD_G       : boolean          := false; -- false = packs registers in tight 256B for small BAR0 applications, true = groups registers in 4kB boundary to "virtualize" the channels allowing separate processes to memory map the register space for their dedicated channels.
    AXIL_BASEADDR_G  : slv(31 downto 0) := x"00080000" );
  port (
    -- AXI-Lite and IRQ Interface
    axilClk             : in  sl;
    axilRst             : in  sl;
    axilWriteMaster     : in  AxiLiteWriteMasterType;
    axilWriteSlave      : out AxiLiteWriteSlaveType;
    axilReadMaster      : in  AxiLiteReadMasterType;
    axilReadSlave       : out AxiLiteReadSlaveType;
    -- EVR Ports
    evrClk              : in  sl;
    evrRst              : in  sl;
    evrBus              : in  TimingBusType;
    -- Trigger and Sync Port
    trigOut             : out TimingTrigType := TIMING_TRIG_INIT_C;
    evrModeSel          : in  sl := '1' );
end EvrV2CoreTriggers;

architecture mapping of EvrV2CoreTriggers is

  constant NUM_AXI_MASTERS_C : natural := 2;
  constant CHAN_INDEX_C  : natural := 0;
  constant TRIG_INDEX_C  : natural := 1;

  constant AXI_CROSSBAR_MASTERS_CONFIG_C : AxiLiteCrossbarMasterConfigArray(NUM_AXI_MASTERS_C-1 downto 0) := (
    CHAN_INDEX_C      => (
      baseAddr      => x"0000_0000" + AXIL_BASEADDR_G,
      addrBits      => ite(EVR_CARD_G,17,12),
      connectivity  => X"FFFF"),
    TRIG_INDEX_C => (
      baseAddr      => ite(EVR_CARD_G,(x"00020000" + AXIL_BASEADDR_G),(x"0000_1000" + AXIL_BASEADDR_G)),
      addrBits      => ite(EVR_CARD_G,17,12),
      connectivity  => X"FFFF") );

  signal axiWriteMasters : AxiLiteWriteMasterArray(NUM_AXI_MASTERS_C-1 downto 0);
  signal axiWriteSlaves  : AxiLiteWriteSlaveArray (NUM_AXI_MASTERS_C-1 downto 0);
  signal axiReadMasters  : AxiLiteReadMasterArray (NUM_AXI_MASTERS_C-1 downto 0);
  signal axiReadSlaves   : AxiLiteReadSlaveArray  (NUM_AXI_MASTERS_C-1 downto 0);

  signal channelConfig    : EvrV2ChannelConfigArray(NCHANNELS_G-1 downto 0);
  signal channelConfigS   : EvrV2ChannelConfigArray(NCHANNELS_G-1 downto 0);
  signal channelConfigAV  : slv(NCHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto 0) := (others => '0');
  signal channelConfigSV  : slv(NCHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto 0) := (others => '0');

  signal triggerConfig    : EvrV2TriggerConfigArray(NTRIGGERS_G-1 downto 0);
  signal triggerConfigS   : EvrV2TriggerConfigArray(NTRIGGERS_G-1 downto 0);
  signal triggerConfigAV  : slv(NTRIGGERS_G*EVRV2_TRIGGER_CONFIG_BITS_C-1 downto 0) := (others => '0');
  signal triggerConfigSV  : slv(NTRIGGERS_G*EVRV2_TRIGGER_CONFIG_BITS_C-1 downto 0) := (others => '0');

  signal timingMsg      : TimingMessageType := TIMING_MESSAGE_INIT_C;
  signal eventSel       : slv          (NCHANNELS_G-1 downto 0) := (others=>'0');
  signal eventCount     : SlVectorArray(NCHANNELS_G-1 downto 0,31 downto 0) := (others => (others => '0'));
  signal eventCountV    : Slv32Array(NCHANNELS_G-1 downto 0) := (others => (others => '0'));
  signal strobe         : slv(3 downto 0);
  signal trigPulse      : slv(NTRIGGERS_G-1 downto 0) := (others => '0');

begin  -- rtl

  -------------------------
  -- AXI-Lite Crossbar Core
  -------------------------
  AxiLiteCrossbar_Inst : entity surf.AxiLiteCrossbar
    generic map (
      TPD_G              => TPD_G,
      NUM_SLAVE_SLOTS_G  => 1,
      NUM_MASTER_SLOTS_G => NUM_AXI_MASTERS_C,
      MASTERS_CONFIG_G   => AXI_CROSSBAR_MASTERS_CONFIG_C)
    port map (
      axiClk              => axilClk,
      axiClkRst           => axilRst,
      sAxiWriteMasters(0) => axilWriteMaster,
      sAxiWriteSlaves (0) => axilWriteSlave,
      sAxiReadMasters (0) => axilReadMaster,
      sAxiReadSlaves  (0) => axilReadSlave,
      mAxiWriteMasters    => axiWriteMasters,
      mAxiWriteSlaves     => axiWriteSlaves,
      mAxiReadMasters     => axiReadMasters,
      mAxiReadSlaves      => axiReadSlaves);

  U_TrigReg : entity lcls_timing_core.EvrV2TrigReg
    generic map ( TPD_G      => TPD_G,
                  EVR_CARD_G => EVR_CARD_G,
                  TRIGGERS_C => NTRIGGERS_G )
    port map (    axiClk              => axilClk,
                  axiRst              => axilRst,
                  axilWriteMaster     => axiWriteMasters (TRIG_INDEX_C),
                  axilWriteSlave      => axiWriteSlaves  (TRIG_INDEX_C),
                  axilReadMaster      => axiReadMasters  (TRIG_INDEX_C),
                  axilReadSlave       => axiReadSlaves   (TRIG_INDEX_C),
                  -- configuration
                  triggerConfig       => triggerConfig );

  U_EvrChanReg : entity lcls_timing_core.EvrV2ChannelReg
    generic map ( TPD_G        => TPD_G,
                  EVR_CARD_G   => EVR_CARD_G,
                  NCHANNELS_G  => NCHANNELS_G )
    port map (    axiClk              => axilClk,
                  axiRst              => axilRst,
                  axilWriteMaster     => axiWriteMasters (CHAN_INDEX_C),
                  axilWriteSlave      => axiWriteSlaves  (CHAN_INDEX_C),
                  axilReadMaster      => axiReadMasters  (CHAN_INDEX_C),
                  axilReadSlave       => axiReadSlaves   (CHAN_INDEX_C),
                  -- configuration
                  channelConfig       => channelConfig,
                  -- status
                  eventCount          => eventCountV(NCHANNELS_G-1 downto 0));

   Loop_EventSel: for i in 0 to NCHANNELS_G-1 generate
     U_EventSel : entity lcls_timing_core.EvrV2EventSelect
       generic map ( TPD_G         => TPD_G )
       port map    ( clk           => evrClk,
                     rst           => evrRst,
                     config        => channelConfigS(i),
                     strobeIn      => strobe(1),
                     dataIn        => timingMsg,
                     selectOut     => eventSel(i) );
   end generate;

   Loop_Triggers: for i in 0 to NTRIGGERS_G-1 generate
     U_Trig : entity lcls_timing_core.EvrV2Trigger
       generic map ( TPD_G        => TPD_G,
                     CHANNELS_C   => NCHANNELS_G,
                     TRIG_DEPTH_C => TRIG_PIPE_G,
                     TRIG_WIDTH_C => TRIG_DEPTH_G,
                     USE_MASK_G   => false )
       port map (    clk      => evrClk,
                     rst      => evrRst,
                     config   => triggerConfigS(i),
                     arm      => eventSel,
                     fire     => strobe(3),
                     trigstate=> trigPulse(i) );
   end generate;  -- i

   Loop_Compl: for i in 0 to NTRIGGERS_G/2-1 generate
      U_Trig : entity lcls_timing_core.EvrV2TriggerCompl
         generic map ( REG_OUT_G => false )
         port map ( clk     => evrClk,
                    rst     => evrRst,
                    config  => triggerConfigS(2*i+1 downto 2*i),
                    trigIn  => trigPulse(2*i+1 downto 2*i),
                    trigOut => trigOut.trigPulse(2*i+1 downto 2*i) );
   end generate;

   Odd_Compl : if (NTRIGGERS_G mod 2) = 1 generate
      trigOut.trigPulse(NTRIGGERS_G-1) <= trigPulse(NTRIGGERS_G-1);
   end generate;

   trigOut.timeStamp <= timingMsg.timeStamp;
   trigOut.bsa       <= evrBus.stream.dbuff.edefAvgDn &
                        evrBus.stream.dbuff.edefMinor &
                        evrBus.stream.dbuff.edefMajor &
                        evrBus.stream.dbuff.edefInit;
   trigOut.dmod      <= evrBus.stream.dbuff.dmod;

   U_V2FromV1 : entity lcls_timing_core.EvrV2FromV1
     port map ( clk       => evrClk,
                disable   => evrModeSel,
                timingIn  => evrBus,
                timingOut => timingMsg );

   NOGEN_SYNC : if COMMON_CLK_G generate
     channelConfigS <= channelConfig;
     triggerConfigS <= triggerConfig;

     process(evrClk) is
     begin
       if rising_edge(evrClk) then
         Loop_EventCnt: for i in 0 to NCHANNELS_G-1 loop
           if eventSel(i) = '1' then
             eventCountV(i) <= eventCountV(i)+1;
           end if;
         end loop;
       end if;
     end process;
   end generate;

   GEN_SYNC : if not COMMON_CLK_G generate
     -- Synchronize configurations to evrClk
     U_SyncChannelConfig : entity surf.SynchronizerVector
       generic map ( WIDTH_G => NCHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C )
       port map ( clk     => evrClk,
                  dataIn  => channelConfigAV,
                  dataOut => channelConfigSV );
     U_SyncTriggerConfig : entity surf.SynchronizerVector
       generic map ( WIDTH_G => NTRIGGERS_G*EVRV2_TRIGGER_CONFIG_BITS_C )
       port map ( clk     => evrClk,
                  dataIn  => triggerConfigAV,
                  dataOut => triggerConfigSV );
     Loop_Chans: for i in 0 to NCHANNELS_G-1 generate
       channelConfigAV((i+1)*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto i*EVRV2_CHANNEL_CONFIG_BITS_C)
         <= toSlv(channelConfig(i));
       channelConfigS(i) <= toChannelConfig(channelConfigSV((i+1)*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto i*EVRV2_CHANNEL_CONFIG_BITS_C));
     end generate;
     Loop_Trigs: for i in 0 to NTRIGGERS_G-1 generate
       triggerConfigAV((i+1)*EVRV2_TRIGGER_CONFIG_BITS_C-1 downto i*EVRV2_TRIGGER_CONFIG_BITS_C)
         <= toSlv(triggerConfig(i));
       triggerConfigS(i) <= toTriggerConfig(triggerConfigSV((i+1)*EVRV2_TRIGGER_CONFIG_BITS_C-1 downto i*EVRV2_TRIGGER_CONFIG_BITS_C));
     end generate;

     Sync_EvtCount : entity surf.SyncStatusVector
       generic map ( TPD_G   => TPD_G,
                     WIDTH_G => NCHANNELS_G )
       port map    ( statusIn     => eventSel,
                     cntRstIn     => evrRst,
                     rollOverEnIn => (others=>'1'),
                     cntOut       => eventCount,
                     wrClk        => evrClk,
                     wrRst        => '0',
                     rdClk        => axilClk,
                     rdRst        => axilRst );
     Loop_EventCnt: for i in 0 to NCHANNELS_G-1 generate
       eventCountV(i) <= muxSlVectorArray(eventCount,i);
     end generate;
   end generate;


   process (evrClk)
   begin
     if rising_edge(evrClk) then
       strobe <= strobe(strobe'left-1 downto 0) & evrBus.strobe;
     end if;
   end process;

end mapping;
