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


library surf;
use surf.StdRtlPkg.all;

library lcls_timing_core;
use lcls_timing_core.EvrV1Pkg.all;

entity EvrV1EventReceiver is
   generic (
      TPD_G           : time := 1 ns;
      SYNC_POLARITY_G : sl   := '1');   -- '1' = active HIGH logic
   port (
      -- AXI-Lite and IRQ Interface
      axiClk         : in  sl;
      axiRst         : in  sl;
      status         : out EvrV1StatusType;
      config         : in  EvrV1ConfigType;
      -- Trigger and Sync Port
      sync           : in  sl;
      trigOut        : out slv(11 downto 0);
      eventStreamOut : out slv(7 downto 0);
      -- EVR Interface
      evrClk         : in  sl;
      evrRst         : in  sl;
      rxLinkUp       : in  sl;
      rxError        : in  sl;
      rxData         : in  slv(15 downto 0);
      rxDataK        : in  slv(1 downto 0));
end EvrV1EventReceiver;

architecture rtl of EvrV1EventReceiver is

   constant TIMEOUT_C : natural := 200000000;

   component EvrV1EventReceiverChannel is
      port(
         Clock        : in  sl;
         Reset        : in  sl;
         myEvent      : in  sl;
         myDelay      : in  slv(31 downto 0);
         myWidth      : in  slv(31 downto 0);
         myPreScale   : in  slv(31 downto 0);
         myPolarity   : in  sl;
         trigger      : out sl;
         setPulse     : in  sl;
         resetPulse   : in  sl;
         channelDebug : out slv(102 downto 0));
   end component EvrV1EventReceiverChannel;

   component EvrV1TimeofDayReceiver is
      port(
         Clock        : in  sl;
         Reset        : in  sl;
         EventStream  : in  slv(7 downto 0);
         TimeStamp    : out slv(63 downto 0);
         timeDebug    : out slv(36 downto 0);
         secondsShift : out slv(31 downto 0));
   end component EvrV1TimeofDayReceiver;

   component EvrV1TimeStampGenerator is
      port(
         Clock     : in  sl;
         Reset     : in  sl;
         TimeStamp : out slv(63 downto 0));
   end component EvrV1TimeStampGenerator;

   component EvrV1DbusDecode is
      port(
         Clock       : in  sl;
         EventClock  : in  sl;
         Reset       : in  sl;
         dbus        : in  slv(7 downto 0);
         isK         : in  sl;
         dbRdAddr    : in  slv(8 downto 0);
         dbena       : in  sl;
         dbdis       : in  sl;
         dben        : in  sl;
         rxSize      : out slv(11 downto 0);
         dbrx        : out sl;
         dbrdy       : out sl;
         dbcs        : out sl;
         disBus      : out slv(7 downto 0);
         dataBuffOut : out slv(31 downto 0);
         dbDebug     : out slv(73 downto 0));
   end component EvrV1DbusDecode;

   signal dben     : sl;
   signal dbena    : sl;
   signal dbIntEna : sl;
   signal dbdis    : sl;
   signal dbrdy    : sl;

   signal evrEnable   : sl;
   signal mapRamPage  : sl;
   signal eventChRst  : sl;
   signal preScaleRst : sl;
   signal uSecDivider : slv(31 downto 0);

   signal fifoRst         : sl;
   signal fifoWrEn        : sl;
   signal tsFIFOempty     : sl;
   signal tsFIFOfull      : sl;
   signal tsFIFOfullPulse : sl;
   signal tsFifoWrCnt     : slv(8 downto 0);
   signal tsFifoWrCntInt  : slv(8 downto 0);
   signal tsLatch         : slv(63 downto 0);
   signal latchTs         : sl;
   signal secondsShift    : slv(31 downto 0);

   signal irqClr  : slv(31 downto 0);
   signal intFlag : slv(31 downto 0) := (others => '0');

   signal extEventEn    : sl;
   signal extEventPulse : sl;
   signal extEventCode  : slv(7 downto 0);

   signal intEventEn    : sl;
   signal intEventPulse : sl;
   signal intEventCode  : slv(7 downto 0);
   signal intEventCount : slv(31 downto 0);
   signal intEventCnt   : slv(31 downto 0);

   signal heartBeat      : sl;
   signal heartBeatPulse : sl;
   signal heartBeatCnt   : natural range 0 to TIMEOUT_C;
   signal evrTriggerInt  : slv(11 downto 0);
   signal dbgClkOut      : slv(7 downto 0);

   signal rxLinkUpDly  : sl;
   signal rxLinkUpSync : sl;
   signal rxDataKDly   : slv(1 downto 0);
   signal rxDataDly    : slv(15 downto 0);
   signal rxDataEvent  : slv(15 downto 0);
   signal rxSize       : slv(11 downto 0);

   signal isK            : slv(1 downto 0);
   signal dataStream     : slv(7 downto 0);
   signal memoryEvent    : slv(7 downto 0);
   signal eventStream    : slv(7 downto 0);
   signal eventStreamDly : slv(7 downto 0);
   signal timeStamp      : slv(63 downto 0);
   signal intTimeStamp   : slv(63 downto 0);
   signal timeStampDly   : slv(63 downto 0);

   signal pulseControl  : Slv32Array(11 downto 0);
   signal pulsePrescale : Slv32Array(11 downto 0);
   signal pulseDelay    : Slv32Array(11 downto 0);
   signal pulseWidth    : Slv32Array(11 downto 0);
   signal outputMap     : Slv16Array(11 downto 0);

   signal eventRamResetData : Slv32Array(1 downto 0);
   signal eventRamSetData   : Slv32Array(1 downto 0);
   signal eventRamPulseData : Slv32Array(1 downto 0);
   signal eventRamIntData   : Slv32Array(1 downto 0);

   signal eventRamResetDataInt : slv(31 downto 0);
   signal eventRamSetDataInt   : slv(31 downto 0);
   signal eventRamPulseDataInt : slv(31 downto 0);
   signal eventRamIntDataInt   : slv(31 downto 0);

   -- attribute dont_touch                 : string;
   -- attribute dont_touch of rxDataKDly   : signal is "true";
   -- attribute dont_touch of rxDataDly    : signal is "true";
   -- attribute dont_touch of intFlag      : signal is "true";
   -- attribute dont_touch of irqClr       : signal is "true";
   -- attribute dont_touch of latchTs      : signal is "true";
   -- attribute dont_touch of timeStampDly : signal is "true";

begin

   eventStreamOut <= eventStreamDly;

   ---------------------
   -- Synchronize Inputs
   ---------------------
   SyncIn_0 : entity surf.SynchronizerOneShot
      generic map (
         TPD_G          => TPD_G,
         IN_POLARITY_G  => SYNC_POLARITY_G,
         OUT_POLARITY_G => '1')
      port map (
         clk     => evrClk,
         dataIn  => sync,
         dataOut => extEventPulse);

   SyncIn_1 : entity surf.SynchronizerVector
      generic map (
         TPD_G   => TPD_G,
         WIDTH_G => 7)
      port map (
         clk        => evrClk,
         dataIn(0)  => config.dbena,
         dataIn(1)  => config.dbdis,
         dataIn(2)  => config.evrEnable,
         dataIn(3)  => config.dben,
         dataIn(4)  => config.mapRamPage,
         dataIn(5)  => config.intEventEn,
         dataIn(6)  => config.extEventEn,
         dataOut(0) => dbena,
         dataOut(1) => dbdis,
         dataOut(2) => evrEnable,
         dataOut(3) => dben,
         dataOut(4) => mapRamPage,
         dataOut(5) => intEventEn,
         dataOut(6) => extEventEn);

   SyncIn_2 : entity surf.SynchronizerOneShotVector
      generic map (
         TPD_G   => TPD_G,
         WIDTH_G => 32)
      port map (
         clk     => evrClk,
         dataIn  => config.irqClr,
         dataOut => irqClr);

   SyncIn_3 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 32)
      port map (
         wr_clk => axiClk,
         din    => config.intEventCount,
         rd_clk => evrClk,
         dout   => intEventCount);

   SyncIn_4 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 32)
      port map (
         wr_clk => axiClk,
         din    => config.uSecDivider,
         rd_clk => evrClk,
         dout   => uSecDivider);

   SyncIn_5 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 8)
      port map (
         wr_clk => axiClk,
         din    => config.intEventCode,
         rd_clk => evrClk,
         dout   => intEventCode);

   SyncIn_6 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 8)
      port map (
         wr_clk => axiClk,
         din    => config.extEventCode,
         rd_clk => evrClk,
         dout   => extEventCode);

   SyncIn_7 : entity surf.SynchronizerOneShot
      generic map (
         TPD_G => TPD_G)
      port map (
         clk     => evrClk,
         dataIn  => config.latchTs,
         dataOut => latchTs);

   ------------------------
   -- Generate enable dbInt
   ------------------------
   process(evrClk)
   begin
      if rising_edge(evrClk) then
         if evrRst = '1' then
            dbIntEna <= '0' after TPD_G;
         else
            if dbena = '1' then
               dbIntEna <= '1' after TPD_G;
            elsif irqClr(5) = '1' then
               dbIntEna <= '0' after TPD_G;
            end if;
         end if;
      end if;
   end process;

   ----------------------------------
   -- Generate Event Receiver Channel
   ----------------------------------
   GEN_EVENT_RX_CH :
   for i in 11 downto 0 generate

      ----------------------------
      -- Synchronize Configuration
      ----------------------------
      SyncIn_pulseControl : entity surf.SynchronizerFifo
         generic map (
            TPD_G        => TPD_G,
            DATA_WIDTH_G => 32)
         port map (
            wr_clk => axiClk,
            din    => config.pulseControl(i),
            rd_clk => evrClk,
            dout   => pulseControl(i));

      SyncIn_pulsePrescale : entity surf.SynchronizerFifo
         generic map (
            TPD_G        => TPD_G,
            DATA_WIDTH_G => 32)
         port map (
            wr_clk => axiClk,
            din    => config.pulsePrescale(i),
            rd_clk => evrClk,
            dout   => pulsePrescale(i));

      SyncIn_pulseDelay : entity surf.SynchronizerFifo
         generic map (
            TPD_G        => TPD_G,
            DATA_WIDTH_G => 32)
         port map (
            wr_clk => axiClk,
            din    => config.pulseDelay(i),
            rd_clk => evrClk,
            dout   => pulseDelay(i));

      SyncIn_pulseWidth : entity surf.SynchronizerFifo
         generic map (
            TPD_G        => TPD_G,
            DATA_WIDTH_G => 32)
         port map (
            wr_clk => axiClk,
            din    => config.pulseWidth(i),
            rd_clk => evrClk,
            dout   => pulseWidth(i));

      -------------------------
      -- Event Receiver Channel
      -------------------------
      ReceiverChannel_Inst : EvrV1EventReceiverChannel
         port map (
            Clock        => evrClk,
            Reset        => eventChRst,
            myEvent      => eventRamPulseDataInt(i),
            myDelay      => pulseDelay(i),
            myWidth      => pulseWidth(i),
            myPreScale   => pulsePrescale(i),
            myPolarity   => pulseControl(i)(4),
            trigger      => evrTriggerInt(i),
            setPulse     => eventRamSetDataInt(i),
            resetPulse   => eventRamResetDataInt(i),
            channelDebug => open);

   end generate GEN_EVENT_RX_CH;

   preScaleRst <= '1' when(EventStreamDly = x"7B") else '0';
   eventChRst  <= evrRst or not(evrEnable) or not(rxLinkUp);

   ------------------------
   -- Decode the time stamp
   ------------------------
   TimeofDayReceiver_Inst : EvrV1TimeofDayReceiver
      port map (
         Clock        => evrClk,
         Reset        => evrRst,
         EventStream  => eventStream,
         TimeStamp    => timeStamp,
         timeDebug    => open,
         secondsShift => secondsShift);

   -----------------------------
   -- Debug Time Stamp Generator
   -----------------------------
   TimeStampGenerator_Inst : EvrV1TimeStampGenerator
      port map (
         Clock     => evrClk,
         Reset     => evrRst,
         TimeStamp => intTimeStamp);

   -------------------------------------------------------------------
   -- Delay EventStream and TimeStamp by one clock for writing in FIFO
   -------------------------------------------------------------------
   process(evrClk)
   begin
      if rising_edge(evrClk) then
         if evrRst = '1' then
            timeStampDly   <= (others => '0') after TPD_G;
            eventStreamDly <= (others => '0') after TPD_G;
            tsLatch        <= (others => '0') after TPD_G;
         else
            if intEventEn = '1' then
               timeStampDly <= intTimeStamp after TPD_G;
            else
               timeStampDly <= timeStamp after TPD_G;
            end if;
            eventStreamDly <= eventStream after TPD_G;
            if latchTs = '1' then
               tsLatch <= timeStampDly after TPD_G;
            end if;
         end if;
      end if;
   end process;

   TimeStampFIFO_Inst : entity lcls_timing_core.EvrV1TimeStampFIFO
      generic map (
         TPD_G => TPD_G)
      port map (
         -- Asynchronous Reset
         rst                => fifoRst,
         -- Write Ports (wr_clk domain)
         wr_clk             => evrClk,
         wr_en              => fifoWrEn,
         din(71 downto 8)   => timeStampDly,
         din(7 downto 0)    => eventStreamDly,
         wr_data_count      => tsFifoWrCntInt,
         full               => tsFIFOfull,
         -- Read Ports (rd_clk domain)
         rd_clk             => axiClk,
         rd_en              => config.tsFifoRdEna,
         dout(71 downto 40) => status.tsFifoTsLow,
         dout(39 downto 8)  => status.tsFifoTsHigh,
         dout(7 downto 0)   => status.tsFifoEventCode,
         rd_data_count      => open,
         empty              => tsFIFOempty);

   fifoRst  <= evrRst or not(evrEnable) or not(rxLinkUp);
   fifoWrEn <= eventRamIntDataInt(31) and rxLinkUp and evrEnable;

   -----------------------
   -- FIFO Readout Control
   -----------------------
   Sync_WrCnt : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 9)
      port map (
         rst    => fifoRst,
         wr_clk => evrClk,
         din    => tsFifoWrCntInt,
         rd_clk => axiClk,
         dout   => tsFifoWrCnt);

   process(axiClk)
      variable i : natural;
   begin
      if rising_edge(axiClk) then
         if fifoRst = '1' then
            status.tsFifoNext <= '0' after TPD_G;
         else
            if (tsFifoWrCnt > 1) then
               status.tsFifoNext <= '1' after TPD_G;
            else
               status.tsFifoNext <= '0' after TPD_G;
            end if;
         end if;
      end if;
   end process;

   status.tsFifoWrCnt <= tsFifoWrCnt;
   status.tsFifoValid <= not(tsFIFOempty);

   ------------------
   -- Event Insertion
   ------------------
   process(evrRst, extEventCode, extEventEn, extEventPulse, intEventCode, intEventEn, intEventPulse,
           rxData)
   begin
      if evrRst = '1' then
         rxDataEvent <= (others => '0');
      -- Check the Event Enable flags
      elsif (intEventEn = '1') or (extEventEn = '1') then
         -- Check for internal event
         if (intEventEn = '1') and (intEventPulse = '1') then
            rxDataEvent(15 downto 8) <= x"00";
            rxDataEvent(7 downto 0)  <= intEventCode;
         elsif (extEventEn = '1') and (extEventPulse = '1') then
            rxDataEvent(15 downto 8) <= x"00";
            rxDataEvent(7 downto 0)  <= extEventCode;
         else
            rxDataEvent <= (others => '0');
         end if;
      else
         rxDataEvent <= rxData;
      end if;
   end process;

   process(evrClk)
      variable i : natural;
   begin
      if rising_edge(evrClk) then
         if evrRst = '1' then
            rxDataKDly <= (others => '0') after TPD_G;
            rxDataDly  <= (others => '0') after TPD_G;
         else
            -- Shift Registers
            rxDataKDly <= rxDataK     after TPD_G;
            rxDataDly  <= rxDataEvent after TPD_G;
         end if;
      end if;
   end process;

   dataStream  <= rxDataDly(15 downto 8);
   isK         <= rxDataKDly;
   memoryEvent <= x"00" when(rxDataK(0) = '1')    else rxDataEvent(7 downto 0);
   eventStream <= x"00" when(rxDataKDly(0) = '1') else rxDataDly(7 downto 0);

   ---------------------
   -- Generate Event RAM
   ---------------------
   GEN_EVENT_RAM :
   for i in 1 downto 0 generate

      EventRamReset_Inst : entity lcls_timing_core.EvrV1EventRAM256x32
         generic map (
            TPD_G => TPD_G)
         port map (
            -- Port A
            clka  => evrClk,
            ena   => '1',
            wea   => '0',
            addra => memoryEvent,
            dina  => (others => '0'),
            douta => eventRamResetData(i),
            -- Port B
            clkb  => axiClk,
            enb   => config.eventRamCs(i)(3),
            web   => config.eventRamWe(i)(3),
            addrb => config.eventRamAddr,
            dinb  => config.eventRamData,
            doutb => status.eventRamReset(i));

      EventRamSet_Inst : entity lcls_timing_core.EvrV1EventRAM256x32
         generic map (
            TPD_G => TPD_G)
         port map (
            -- Port A
            clka  => evrClk,
            ena   => '1',
            wea   => '0',
            addra => memoryEvent,
            dina  => (others => '0'),
            douta => eventRamSetData(i),
            -- Port B
            clkb  => axiClk,
            enb   => config.eventRamCs(i)(2),
            web   => config.eventRamWe(i)(2),
            addrb => config.eventRamAddr,
            dinb  => config.eventRamData,
            doutb => status.eventRamSet(i));

      EventRamPulse_Inst : entity lcls_timing_core.EvrV1EventRAM256x32
         generic map (
            TPD_G => TPD_G)
         port map (
            -- Port A
            clka  => evrClk,
            ena   => '1',
            wea   => '0',
            addra => memoryEvent,
            dina  => (others => '0'),
            douta => eventRamPulseData(i),
            -- Port B
            clkb  => axiClk,
            enb   => config.eventRamCs(i)(1),
            web   => config.eventRamWe(i)(1),
            addrb => config.eventRamAddr,
            dinb  => config.eventRamData,
            doutb => status.eventRamPulse(i));

      EventRamInt_Inst : entity lcls_timing_core.EvrV1EventRAM256x32
         generic map (
            TPD_G => TPD_G)
         port map (
            -- Port A
            clka  => evrClk,
            ena   => '1',
            wea   => '0',
            addra => memoryEvent,
            dina  => (others => '0'),
            douta => eventRamIntData(i),
            -- Port B
            clkb  => axiClk,
            enb   => config.eventRamCs(i)(0),
            web   => config.eventRamWe(i)(0),
            addrb => config.eventRamAddr,
            dinb  => config.eventRamData,
            doutb => status.eventRamInt(i));

   end generate GEN_EVENT_RAM;

   -----------
   -- Data Mux
   -----------
   process(evrClk)
   begin
      if rising_edge(evrClk) then
         if evrRst = '1' then
            eventRamResetDataInt <= (others => '0') after TPD_G;
            eventRamSetDataInt   <= (others => '0') after TPD_G;
            eventRamPulseDataInt <= (others => '0') after TPD_G;
            eventRamIntDataInt   <= (others => '0') after TPD_G;
         else
            if mapRamPage = '1' then
               eventRamResetDataInt <= eventRamResetData(1) after TPD_G;
               eventRamSetDataInt   <= eventRamSetData(1)   after TPD_G;
               eventRamPulseDataInt <= eventRamPulseData(1) after TPD_G;
               eventRamIntDataInt   <= eventRamIntData(1)   after TPD_G;
            else
               eventRamResetDataInt <= eventRamResetData(0) after TPD_G;
               eventRamSetDataInt   <= eventRamSetData(0)   after TPD_G;
               eventRamPulseDataInt <= eventRamPulseData(0) after TPD_G;
               eventRamIntDataInt   <= eventRamIntData(0)   after TPD_G;
            end if;
         end if;
      end if;
   end process;

   ----------------------
   -- Debug Divided Clock
   ----------------------
   process(evrClk)
   begin
      if rising_edge(evrClk) then
         if evrRst = '1' then
            dbgClkOut <= (others => '0') after TPD_G;
         else
            dbgClkOut <= dbgClkOut + 1 after TPD_G;
         end if;
      end if;
   end process;

   ---------------------------------------
   -- Loop through Output Trigger Channels
   ---------------------------------------
   GEN_TRIG_OUTPUT :
   for i in 11 downto 0 generate
      ----------------------------
      -- Synchronize Configuration
      ----------------------------
      SyncIn_xBarReg : entity surf.SynchronizerFifo
         generic map (
            TPD_G        => TPD_G,
            DATA_WIDTH_G => 16)
         port map (
            wr_clk => axiClk,
            din    => config.outputMap(i),
            rd_clk => evrClk,
            dout   => outputMap(i));
      --------------------------
      -- Output Trigger Crossbar
      --------------------------
      process(dbgClkOut, evrTriggerInt, outputMap)
      begin
         case conv_integer(outputMap(i)) is
            when 0      => trigOut(i) <= evrTriggerInt(0)  after TPD_G;
            when 1      => trigOut(i) <= evrTriggerInt(1)  after TPD_G;
            when 2      => trigOut(i) <= evrTriggerInt(2)  after TPD_G;
            when 3      => trigOut(i) <= evrTriggerInt(3)  after TPD_G;
            when 4      => trigOut(i) <= evrTriggerInt(4)  after TPD_G;
            when 5      => trigOut(i) <= evrTriggerInt(5)  after TPD_G;
            when 6      => trigOut(i) <= evrTriggerInt(6)  after TPD_G;
            when 7      => trigOut(i) <= evrTriggerInt(7)  after TPD_G;
            when 8      => trigOut(i) <= evrTriggerInt(8)  after TPD_G;
            when 9      => trigOut(i) <= evrTriggerInt(9)  after TPD_G;
            when 10     => trigOut(i) <= evrTriggerInt(10) after TPD_G;
            when 11     => trigOut(i) <= evrTriggerInt(11) after TPD_G;
            when 61     => trigOut(i) <= dbgClkOut(7)      after TPD_G;
            when 62     => trigOut(i) <= '1'               after TPD_G;
            when 63     => trigOut(i) <= '0'               after TPD_G;
            when others => trigOut(i) <= '0'               after TPD_G;
         end case;
      end process;
   end generate GEN_TRIG_OUTPUT;

   --------------------
   -- HeartBeat Monitor
   --------------------
   EvrV1HeartBeat_Inst : entity lcls_timing_core.EvrV1HeartBeat
      generic map (
         TPD_G => TPD_G)
      port map (
         reset            => evrRst,
         uSecDividerReg   => uSecDivider,
         eventCode        => eventStream,
         eventClk         => evrClk,
         heartBeatTimeOut => heartBeat);

   --------------
   -- Data Buffer
   --------------
   EvrV1DbusDecode_Inst : EvrV1DbusDecode
      port map (
         Clock       => axiClk,
         EventClock  => evrClk,
         Reset       => evrRst,
         dbus        => dataStream,
         isK         => isK(1),
         dbRdAddr    => config.dbRdAddr,
         dbena       => dbena,
         dbdis       => dbdis,
         dben        => dben,
         rxSize      => rxSize,
         dbrx        => status.dbrx,
         dbrdy       => dbrdy,
         dbcs        => status.dbcs,
         disBus      => open,
         dataBuffOut => status.dbData,
         dbDebug     => open);

   ----------------------
   -- Generate Interrupts
   ----------------------
   Sync_heartbeat : entity surf.SynchronizerOneShot
      generic map (
         TPD_G => TPD_G)
      port map (
         clk     => axiClk,
         dataIn  => heartBeat,
         dataOut => heartBeatPulse);

   process(axiClk)
   begin
      if rising_edge(axiClk) then
         if axiRst = '1' then
            intFlag(2)   <= '0' after TPD_G;
            heartBeatCnt <= 0   after TPD_G;
         else
            if config.irqClr(2) = '1' then
               intFlag(2) <= '0' after TPD_G;
            elsif (config.evrEnable = '1') and (heartBeatPulse = '1') and (rxLinkUpSync = '1') then
               intFlag(2) <= '1' after TPD_G;
            end if;
            if (heartBeatPulse = '1') and (rxLinkUpSync = '1') then
               heartBeatCnt <= 0 after TPD_G;
            elsif (heartBeatCnt = TIMEOUT_C-1) then
               heartBeatCnt <= 0   after TPD_G;
               intFlag(2)   <= '1' after TPD_G;
            else
               -- Increment the counter
               heartBeatCnt <= heartBeatCnt + 1;
            end if;
         end if;
      end if;
   end process;

   Sync_tsFIFOfull : entity surf.SynchronizerOneShot
      generic map (
         TPD_G => TPD_G)
      port map (
         clk     => axiClk,
         dataIn  => tsFIFOfull,
         dataOut => tsFIFOfullPulse);

   process(axiClk)
   begin
      if rising_edge(axiClk) then
         if axiRst = '1' then
            intFlag(1) <= '0' after TPD_G;
         else
            if config.irqClr(1) = '1' then
               intFlag(1) <= '0' after TPD_G;
            elsif (config.evrEnable = '1') and (tsFIFOfullPulse = '1') and (rxLinkUpSync = '1') then
               intFlag(1) <= '1' after TPD_G;
            end if;
         end if;
      end if;
   end process;

   process(axiClk)
   begin
      if rising_edge(axiClk) then
         if axiRst = '1' then
            intFlag(3) <= '0' after TPD_G;
         else
            if config.irqClr(3) = '1' then
               intFlag(3) <= '0' after TPD_G;
            elsif (config.evrEnable = '1') and (tsFIFOempty = '0') and (rxLinkUpSync = '1') then
               intFlag(3) <= '1' after TPD_G;
            else
               intFlag(3) <= '0' after TPD_G;
            end if;
         end if;
      end if;
   end process;

   process(axiClk)
   begin
      if rising_edge(axiClk) then
         if axiRst = '1' then
            intFlag(5) <= '0' after TPD_G;
         else
            if config.irqClr(5) = '1' then
               intFlag(5) <= '0' after TPD_G;
            elsif (config.evrEnable = '1') and (dbrdy = '1') and (rxLinkUpSync = '1') then
               intFlag(5) <= '1' after TPD_G;
            end if;
         end if;
      end if;
   end process;
   status.dbrdy <= dbrdy;

   SyncIn_rxLinkUp : entity surf.RstSync
      generic map (
         TPD_G          => TPD_G,
         IN_POLARITY_G  => '0',
         OUT_POLARITY_G => '0')
      port map (
         clk      => axiClk,
         asyncRst => rxLinkUp,
         syncRst  => rxLinkUpSync);

   process(axiClk)
   begin
      if rising_edge(axiClk) then
         rxLinkUpDly <= rxLinkUpSync after TPD_G;
         if config.irqClr(0) = '1' then
            intFlag(0) <= '0' after TPD_G;
         elsif (config.evrEnable = '1') and (rxLinkUpDly = '1') and (rxLinkUpSync = '0') then
            intFlag(0) <= '1' after TPD_G;
         end if;
      end if;
   end process;

   ---------------------------
   -- Internal Pulse Generator
   ---------------------------
   process(evrClk)
   begin
      if rising_edge(evrClk) then
         if evrRst = '1' then
            intEventPulse <= '0'             after TPD_G;
            intEventCnt   <= (others => '0') after TPD_G;
         else
            if intEventCnt = 0 then
               intEventPulse <= '1'           after TPD_G;
               intEventCnt   <= intEventCount after TPD_G;
            else
               intEventPulse <= '0'             after TPD_G;
               intEventCnt   <= intEventCnt - 1 after TPD_G;
            end if;
         end if;
      end if;
   end process;

   ----------------------
   -- Synchronize Outputs
   ----------------------
   SyncOut_0 : entity surf.SynchronizerVector
      generic map (
         TPD_G   => TPD_G,
         WIDTH_G => 2)
      port map (
         clk        => axiClk,
         dataIn(0)  => intFlag(5),
         dataIn(1)  => dbIntEna,
         dataOut(0) => status.dbInt,
         dataOut(1) => status.dbIntEna);

-- SyncOut_1 : entity surf.SynchronizerVector
-- generic map (
-- TPD_G   => TPD_G,
-- WIDTH_G => 32)
-- port map (
-- clk     => axiClk,
-- dataIn  => intFlag,
-- dataOut => status.intFlag);
   status.intFlag <= intFlag;

   SyncOut_2 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 12)
      port map (
         wr_clk => evrClk,
         din    => rxSize,
         rd_clk => axiClk,
         dout   => status.rxSize);

   SyncOut_3 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 64)
      port map (
         wr_clk => evrClk,
         din    => tsLatch,
         rd_clk => axiClk,
         dout   => status.tsLatch);

   SyncOut_4 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 64)
      port map (
         wr_clk => evrClk,
         din    => timeStampDly,
         rd_clk => axiClk,
         dout   => status.ts);

   SyncOut_5 : entity surf.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 32)
      port map (
         wr_clk => evrClk,
         din    => secondsShift,
         rd_clk => axiClk,
         dout   => status.secondsShift);

end rtl;
