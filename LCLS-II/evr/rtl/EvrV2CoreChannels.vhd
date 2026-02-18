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

entity EvrV2CoreChannels is
   generic (
      TPD_G           : time             := 1 ns;
      NCHANNELS_G     : natural          := 1;      -- event selection channels
      COMMON_CLK_G    : boolean          := false;
      EVR_CARD_G      : boolean          := false); -- false = packs registers in tight 256B for small BAR0 applications, true = groups registers in 4kB boundary to "virtualize" the channels allowing separate processes to memory map the register space for their dedicated channels.
   port (
      -- AXI-Lite and IRQ Interface
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      -- EVR Ports
      evrClk          : in  sl;
      evrRst          : in  sl;
      evrBus          : in  TimingBusType;
      -- Trigger and Sync Port
      trigOut         : out TimingTrigType := TIMING_TRIG_INIT_C;
      evrModeSel      : in  sl             := '1');
end EvrV2CoreChannels;

architecture mapping of EvrV2CoreChannels is

   signal channelConfig   : EvrV2ChannelConfigArray(NCHANNELS_G-1 downto 0);
   signal channelConfigS  : EvrV2ChannelConfigArray(NCHANNELS_G-1 downto 0);
   signal channelConfigAV : slv(NCHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto 0) := (others => '0');
   signal channelConfigSV : slv(NCHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto 0) := (others => '0');

   signal timingMsg   : TimingMessageType                                  := TIMING_MESSAGE_INIT_C;
   signal eventSel    : slv (NCHANNELS_G-1 downto 0)                       := (others => '0');
   signal eventCount  : SlVectorArray(NCHANNELS_G-1 downto 0, 31 downto 0) := (others => (others => '0'));
   signal eventCountV : Slv32Array(NCHANNELS_G-1 downto 0)                 := (others => (others => '0'));
   signal strobe      : slv(3 downto 0);

begin  -- rtl

   U_EvrChanReg : entity lcls_timing_core.EvrV2ChannelReg
      generic map (
         TPD_G       => TPD_G,
         EVR_CARD_G  => EVR_CARD_G,
         NCHANNELS_G => NCHANNELS_G)
      port map (
         axiClk          => axilClk,
         axiRst          => axilRst,
         axilWriteMaster => axiWriteMasters(CHAN_INDEX_C),
         axilWriteSlave  => axiWriteSlaves(CHAN_INDEX_C),
         axilReadMaster  => axiReadMasters(CHAN_INDEX_C),
         axilReadSlave   => axiReadSlaves(CHAN_INDEX_C),
         -- configuration
         channelConfig   => channelConfig,
         -- status
         eventCount      => eventCountV(NCHANNELS_G-1 downto 0));

   Loop_EventSel : for i in 0 to NCHANNELS_G-1 generate
      U_EventSel : entity lcls_timing_core.EvrV2EventSelect
         generic map (
            TPD_G => TPD_G)
         port map (
            clk       => evrClk,
            rst       => evrRst,
            config    => channelConfigS(i),
            strobeIn  => strobe(1),
            dataIn    => timingMsg,
            selectOut => eventSel(i));
   end generate;

   trigOut.trigPulse(eventSel'range) <= eventSel;
   trigOut.timeStamp <= timingMsg.timeStamp;
   trigOut.bsa       <= evrBus.stream.dbuff.edefAvgDn &
                        evrBus.stream.dbuff.edefMinor &
                        evrBus.stream.dbuff.edefMajor &
                        evrBus.stream.dbuff.edefInit;
   trigOut.dmod <= evrBus.stream.dbuff.dmod;

   U_V2FromV1 : entity lcls_timing_core.EvrV2FromV1
      port map (
         clk       => evrClk,
         disable   => evrModeSel,
         timingIn  => evrBus,
         timingOut => timingMsg);

   NOGEN_SYNC : if COMMON_CLK_G generate
      channelConfigS <= channelConfig;

      process(evrClk) is
      begin
         if rising_edge(evrClk) then
            Loop_EventCnt : for i in 0 to NCHANNELS_G-1 loop
               if eventSel(i) = '1' then
                  eventCountV(i) <= eventCountV(i)+1 after TPD_G;
               end if;
            end loop;
         end if;
      end process;
   end generate;

   GEN_SYNC : if not COMMON_CLK_G generate
      -- Synchronize configurations to evrClk
      U_SyncChannelConfig : entity surf.SynchronizerVector
         generic map (
            WIDTH_G => NCHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C)
         port map (
            clk     => evrClk,
            dataIn  => channelConfigAV,
            dataOut => channelConfigSV);

      Loop_Chans : for i in 0 to NCHANNELS_G-1 generate
         channelConfigAV((i+1)*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto i*EVRV2_CHANNEL_CONFIG_BITS_C)
            <= toSlv(channelConfig(i));
         channelConfigS(i) <= toChannelConfig(channelConfigSV((i+1)*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto i*EVRV2_CHANNEL_CONFIG_BITS_C));
      end generate;

      Sync_EvtCount : entity surf.SyncStatusVector
         generic map (
            TPD_G   => TPD_G,
            WIDTH_G => NCHANNELS_G)
         port map (
            statusIn     => eventSel,
            cntRstIn     => evrRst,
            rollOverEnIn => (others => '1'),
            cntOut       => eventCount,
            wrClk        => evrClk,
            wrRst        => '0',
            rdClk        => axilClk,
            rdRst        => axilRst);

      Loop_EventCnt : for i in 0 to NCHANNELS_G-1 generate
         eventCountV(i) <= muxSlVectorArray(eventCount, i);
      end generate;
   end generate;


   process (evrClk)
   begin
      if rising_edge(evrClk) then
         strobe <= strobe(strobe'left-1 downto 0) & evrBus.strobe after TPD_G;
      end if;
   end process;

end mapping;
