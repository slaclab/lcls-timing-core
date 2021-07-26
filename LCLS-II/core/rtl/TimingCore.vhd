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
use surf.AxiLitePkg.all;
use surf.AxiStreamPkg.all;
use surf.SsiPkg.all;
use surf.EthMacPkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;

entity TimingCore is

   generic (
      TPD_G             : time                := 1 ns;
      DEFAULT_CLK_SEL_G : sl                  := '1';
      CLKSEL_MODE_G     : string              := "SELECT"; -- "LCLSI","LCLSII","LCLSIPIIC","LCLSIIPIC"
      TPGEN_G           : boolean             := false;
      STREAM_L1_G       : boolean             := false;
      ETHMSG_AXIS_CFG_G : AxiStreamConfigType := EMAC_AXIS_CONFIG_C;
      AXIL_RINGB_G      : boolean             := true;
      ASYNC_G           : boolean             := true;
      AXIL_BASE_ADDR_G  : slv(31 downto 0)    := (others => '0');
      USE_TPGMINI_G     : boolean             := true);
   port (

      -- Interface to GT
      gtTxUsrClk : in sl;
      gtTxUsrRst : in sl;

      gtRxRecClk       : in  sl;
      gtRxData         : in  slv(15 downto 0);
      gtRxDataK        : in  slv(1 downto 0);
      gtRxDispErr      : in  slv(1 downto 0);
      gtRxDecErr       : in  slv(1 downto 0);
      gtRxControl      : out TimingPhyControlType;
      gtRxStatus       : in  TimingPhyStatusType;
      gtTxReset        : out sl;
      gtLoopback       : out slv(2 downto 0);
      tpgMiniTimingPhy : out TimingPhyType;
      timingClkSel     : out sl;
      -- Decoded timing message interface
      appTimingClk     : in  sl;
      appTimingRst     : in  sl;
      appTimingBus     : out TimingBusType;
      appTimingMode    : out sl;

      -- AXI Lite interface
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType;
      -- Timing ETH MSG Interface (axilClk domain)
      ibEthMsgMaster  : in  AxiStreamMasterType := AXI_STREAM_MASTER_INIT_C;
      ibEthMsgSlave   : out AxiStreamSlaveType;
      obEthMsgMaster  : out AxiStreamMasterType;
      obEthMsgSlave   : in  AxiStreamSlaveType  := AXI_STREAM_SLAVE_FORCE_C);

end entity TimingCore;

architecture rtl of TimingCore is

   constant USE_TPGMINI_C               : boolean := USE_TPGMINI_G and not TPGEN_G;
   constant FRAME_RX_AXIL_INDEX_C       : natural := 0;
   constant RAW_BUFFER_AXIL_INDEX_C     : natural := 1;
   constant MESSAGE_BUFFER_AXIL_INDEX_C : natural := 2;
   constant FRAME_TX_AXIL_INDEX_C       : natural := 3;
   constant NUM_AXIL_MASTERS_C          : integer := 4;

   constant AXIL_MASTERS_CONFIG_C : AxiLiteCrossbarMasterConfigArray(NUM_AXIL_MASTERS_C-1 downto 0) := (
      FRAME_RX_AXIL_INDEX_C       => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"00000",
         addrBits                 => 16,
         connectivity             => X"FFFF"),
      RAW_BUFFER_AXIL_INDEX_C     => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"10000",
         addrBits                 => 16,
         connectivity             => ite(AXIL_RINGB_G, X"FFFF", x"0000")),
      MESSAGE_BUFFER_AXIL_INDEX_C => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"20000",
         addrBits                 => 16,
         connectivity             => ite(AXIL_RINGB_G, X"FFFF", x"0000")),
      FRAME_TX_AXIL_INDEX_C       => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"30000",
         addrBits                 => 16,
         connectivity             => ite(USE_TPGMINI_C, X"FFFF", x"0000")));

   signal locAxilWriteMasters : AxiLiteWriteMasterArray(NUM_AXIL_MASTERS_C-1 downto 0) := (others => AXI_LITE_WRITE_MASTER_INIT_C);
   signal locAxilWriteSlaves  : AxiLiteWriteSlaveArray (NUM_AXIL_MASTERS_C-1 downto 0) := (others => AXI_LITE_WRITE_SLAVE_EMPTY_DECERR_C);
   signal locAxilReadMasters  : AxiLiteReadMasterArray (NUM_AXIL_MASTERS_C-1 downto 0) := (others => AXI_LITE_READ_MASTER_INIT_C);
   signal locAxilReadSlaves   : AxiLiteReadSlaveArray  (NUM_AXIL_MASTERS_C-1 downto 0) := (others => AXI_LITE_READ_SLAVE_EMPTY_DECERR_C);

   signal timingRx            : TimingRxType;
   signal timingStrobe        : sl;
   signal timingValid         : sl                                          := '1';
   signal timingMessageStrobe : sl;
   signal timingMessageValid  : sl                                          := '1';
   signal timingStreamStrobe  : sl;
   signal timingStreamValid   : sl                                          := '1';
   signal timingMessage       : TimingMessageType;
   signal timingStream        : TimingStreamType;
   signal timingStreamPrompt  : TimingStreamType;
   signal timingFrameSlv      : slv(TIMING_MESSAGE_BITS_C-1 downto 0);
   signal timingFrameSlvShift : slv(TIMING_MESSAGE_BITS_C+31 downto 0)      := (others => '0');
   signal timingFrameSlvValid : slv((TIMING_MESSAGE_BITS_C+31)/32 downto 0) := (others => '0');

   signal appTimingBus_i    : TimingBusType;
   signal appTimingFrameSlv : slv(TIMING_MESSAGE_BITS_C-1 downto 0);

   signal clkSel          : sl;
   signal modeSel             : sl;
   signal modeSelRx           : sl;
   signal modeSelTx           : sl;
   signal modeSelApp          : sl;

   signal linkUpV1 : sl;
   signal linkUpV2 : sl;

   signal itxData  : Slv16Array(1 downto 0);
   signal itxDataK : Slv2Array (1 downto 0);

   signal timingExtension    : TimingExtensionArray;
   signal appTimingExtension : TimingExtensionArray;

begin

   appTimingBus  <= appTimingBus_i;
   appTimingMode <= modeSelApp;

   AxiLiteCrossbar_1 : entity surf.AxiLiteCrossbar
      generic map (
         TPD_G              => TPD_G,
         NUM_SLAVE_SLOTS_G  => 1,
         NUM_MASTER_SLOTS_G => NUM_AXIL_MASTERS_C,
         DEC_ERROR_RESP_G   => AXI_RESP_DECERR_C,
         MASTERS_CONFIG_G   => AXIL_MASTERS_CONFIG_C)
      port map (
         axiClk              => axilClk,
         axiClkRst           => axilRst,
         sAxiWriteMasters(0) => axilWriteMaster,
         sAxiWriteSlaves(0)  => axilWriteSlave,
         sAxiReadMasters(0)  => axilReadMaster,
         sAxiReadSlaves(0)   => axilReadSlave,
         mAxiWriteMasters    => locAxilWriteMasters,
         mAxiWriteSlaves     => locAxilWriteSlaves,
         mAxiReadMasters     => locAxilReadMasters,
         mAxiReadSlaves      => locAxilReadSlaves);

   -------------------------------------------------------------------------------------------------
   -- Receive and decode timing data frames from GT
   -------------------------------------------------------------------------------------------------
   timingRx.data   <= gtRxData;
   timingRx.dataK  <= gtRxDataK;
   timingRx.decErr <= gtRxDecErr;
   timingRx.dspErr <= gtRxDispErr;
   timingClkSel    <= clkSel;

   U_TimingRx : entity lcls_timing_core.TimingRx
      generic map (
         TPD_G             => TPD_G,
         DEFAULT_CLK_SEL_G => DEFAULT_CLK_SEL_G,
         CLKSEL_MODE_G     => CLKSEL_MODE_G)
      port map (
         txClk               => gtTxUsrClk,
         rxClk               => gtRxRecClk,
         rxStatus            => gtRxStatus,
         rxControl           => gtRxControl,
         rxData              => timingRx,
         timingClkSel        => clkSel,
         timingModeSel       => modeSel,
         timingStreamUser    => timingStream,
         timingStreamPrompt  => timingStreamPrompt,
         timingStreamStrobe  => timingStreamStrobe,
         timingStreamValid   => timingStreamValid,
         timingMessage       => timingMessage,
         timingMessageStrobe => timingMessageStrobe,
         timingMessageValid  => timingMessageValid,
         timingExtension     => timingExtension,
         axilClk             => axilClk,
         axilRst             => axilRst,
         axilReadMaster      => locAxilReadMasters (FRAME_RX_AXIL_INDEX_C),
         axilReadSlave       => locAxilReadSlaves (FRAME_RX_AXIL_INDEX_C),
         axilWriteMaster     => locAxilWriteMasters(FRAME_RX_AXIL_INDEX_C),
         axilWriteSlave      => locAxilWriteSlaves (FRAME_RX_AXIL_INDEX_C));

   GEN_AXIL_RINGB : if AXIL_RINGB_G generate
      -------------------------------------------------------------------------------------------------
      -- Ring buffer to log raw GT words
      -------------------------------------------------------------------------------------------------
      AxiLiteRingBuffer_1 : entity surf.AxiLiteRingBuffer
         generic map (
            TPD_G            => TPD_G,
            MEMORY_TYPE_G    => "block",
            REG_EN_G         => true,
            DATA_WIDTH_G     => 18,
            RAM_ADDR_WIDTH_G => 13)
         port map (
            dataClk                 => gtRxRecClk,
            dataRst                 => '0',
            dataValid               => '1',
            dataValue(15 downto 0)  => gtRxData,
            dataValue(17 downto 16) => gtRxDataK,
            axilClk                 => axilClk,
            axilRst                 => axilRst,
            axilReadMaster          => locAxilReadMasters (RAW_BUFFER_AXIL_INDEX_C),
            axilReadSlave           => locAxilReadSlaves (RAW_BUFFER_AXIL_INDEX_C),
            axilWriteMaster         => locAxilWriteMasters(RAW_BUFFER_AXIL_INDEX_C),
            axilWriteSlave          => locAxilWriteSlaves (RAW_BUFFER_AXIL_INDEX_C));

      -------------------------------------------------------------------------------------------------
      -- Ring buffer to log received timing messages
      -------------------------------------------------------------------------------------------------
      process (gtRxRecClk) is
      begin
         if rising_edge(gtRxRecClk) then
            if timingStrobe = '1' then
               timingFrameSlvShift <= timingFrameSlv & x"deadbeef" after TPD_G;
               timingFrameSlvValid <= (others => '1')              after TPD_G;
            else
               timingFrameSlvShift <= x"00000000" & timingFrameSlvShift(timingFrameSlvShift'left downto 32) after TPD_G;
               timingFrameSlvValid <= '0' & timingFrameSlvValid(timingFrameSlvValid'left downto 1)          after TPD_G;
            end if;
         end if;
      end process;

      AxiLiteRingBuffer_2 : entity surf.AxiLiteRingBuffer
         generic map (
            TPD_G            => TPD_G,
            MEMORY_TYPE_G    => "block",
            REG_EN_G         => true,
            DATA_WIDTH_G     => 32,
            RAM_ADDR_WIDTH_G => 13)
         port map (
            dataClk         => gtRxRecClk,
            dataRst         => '0',
            dataValid       => timingFrameSlvValid(0),
            dataValue       => timingFrameSlvShift(31 downto 0),
            axilClk         => axilClk,
            axilRst         => axilRst,
            axilReadMaster  => locAxilReadMasters (MESSAGE_BUFFER_AXIL_INDEX_C),
            axilReadSlave   => locAxilReadSlaves (MESSAGE_BUFFER_AXIL_INDEX_C),
            axilWriteMaster => locAxilWriteMasters(MESSAGE_BUFFER_AXIL_INDEX_C),
            axilWriteSlave  => locAxilWriteSlaves (MESSAGE_BUFFER_AXIL_INDEX_C));
   end generate;

   tpgMiniTimingPhy.control.pllReset    <= '0';
   tpgMiniTimingPhy.control.reset       <= '0';
   tpgMiniTimingPhy.control.bufferByRst <= '0';

   GEN_MINICORE : if USE_TPGMINI_C generate
      TPGMiniCore_1 : entity lcls_timing_core.TPGMiniCore
         generic map (
            TPD_G      => TPD_G,
            NARRAYSBSA => 2)
         port map (
            txClk          => gtTxUsrClk,
            txRst          => gtTxUsrRst,
            txRdy          => '1',
            txData         => itxData,
            txDataK        => itxDataK,
            txPolarity     => tpgMiniTimingPhy.control.polarity,
            txResetO       => gtTxReset,
            txLoopback     => gtLoopback,
            txInhibit      => tpgMiniTimingPhy.control.inhibit,
            axiClk         => axilClk,
            axiRst         => axilRst,
            axiReadMaster  => locAxilReadMasters (FRAME_TX_AXIL_INDEX_C),
            axiReadSlave   => locAxilReadSlaves (FRAME_TX_AXIL_INDEX_C),
            axiWriteMaster => locAxilWriteMasters(FRAME_TX_AXIL_INDEX_C),
            axiWriteSlave  => locAxilWriteSlaves (FRAME_TX_AXIL_INDEX_C));

      U_SyncModeSel : entity surf.Synchronizer
         generic map (TPD_G=> TPD_G)
        port map ( clk     => gtTxUsrClk,
                   dataIn  => modeSel,
                   dataOut => modeSelTx );

      tpgMiniTimingPhy.data  <= itxData(0) when modeSelTx='0' else
                                itxData(1);
      tpgMiniTimingPhy.dataK <= itxDataK(0) when modeSelTx='0' else
                                itxDataK(1);

   end generate GEN_MINICORE;

   NOGEN_MINICORE : if not USE_TPGMINI_C generate
      tpgMiniTimingPhy.data             <= (others => '0');
      tpgMiniTimingPhy.dataK            <= "00";
      tpgMiniTimingPhy.control.polarity <= '0';
      tpgMiniTimingPhy.control.inhibit  <= '0';
      gtTxReset                         <= '0';
      gtLoopback                        <= "000";
   end generate NOGEN_MINICORE;

   U_SyncModeSel : entity surf.Synchronizer
     generic map (TPD_G=> TPD_G)
     port map ( clk     => gtRxRecClk,
                dataIn  => modeSel,
                dataOut => modeSelRx );

   -------------------------------------------------------------------------------------------------
   -- Synchronize timing message to appTimingClk
   -------------------------------------------------------------------------------------------------

   timingFrameSlv <= toSlv(timingMessage) when modeSelRx = '1' else
                     (slvZero(TIMING_MESSAGE_BITS_C-TIMING_STREAM_BITS_C) & toSlv(timingStream));
   timingStrobe   <= timingMessageStrobe when modeSelRx = '1' else
                     timingStreamStrobe;
   timingValid    <= timingMessageValid when modeSelRx = '1' else
                     timingStreamValid;

   GEN_ASYNC : if ASYNC_G generate
      process (appTimingExtension,appTimingFrameSlv,modeSelApp) is
      begin
         if modeSelApp = '0' then
            appTimingBus_i.stream  <= toTimingStreamType(appTimingFrameSlv(TIMING_STREAM_BITS_C-1 downto 0));
            appTimingBus_i.message <= TIMING_MESSAGE_INIT_C;
         else
            appTimingBus_i.message <= toTimingMessageType(appTimingFrameSlv(TIMING_MESSAGE_BITS_C-1 downto 0));
            appTimingBus_i.stream  <= TIMING_STREAM_INIT_C;
         end if;
         appTimingBus_i.modesel   <= modeSelApp;
         appTimingBus_i.extension <= appTimingExtension;
      end process;

      -- Need to syncrhonize timingClkSelR to appTimingClk so we can use
      -- it to switch between stream and message in appTimingClk domain
      U_Synchronizer_1 : entity surf.Synchronizer
         generic map (
            TPD_G => TPD_G)
         port map (
            clk     => appTimingClk,      -- [in]
            rst     => appTimingRst,      -- [in]
            dataIn  => modeSel,           -- [in]
            dataOut => modeSelApp);       -- [out]

      SynchronizerFifo_1 : entity surf.SynchronizerFifo
         generic map (
            TPD_G        => TPD_G,
            DATA_WIDTH_G => TIMING_MESSAGE_BITS_C+1)
         port map (
            rst                                  => appTimingRst,
            wr_clk                               => gtRxRecClk,
            wr_en                                => timingStrobe,
            din(TIMING_MESSAGE_BITS_C downto 1)  => timingFrameSlv,
            din(0)                               => timingValid,
            rd_clk                               => appTimingClk,
            dout(TIMING_MESSAGE_BITS_C downto 1) => appTimingFrameSlv,
            dout(0)                              => appTimingBus_i.valid,
            valid                                => appTimingBus_i.strobe);

      GEN_EXTENSION_SYNC_FIFOS : for i in 15 downto 1 generate
         SynchronizerFifo_2 : entity surf.SynchronizerFifo
            generic map (
               TPD_G        => TPD_G,
               DATA_WIDTH_G => TIMING_EXTENSION_MESSAGE_BITS_C+1)
            port map (
               rst                                            => appTimingRst,
               wr_clk                                         => gtRxRecClk,
               wr_en                                          => timingStrobe,
               din(TIMING_EXTENSION_MESSAGE_BITS_C downto 1)  => timingExtension(i).data,
               din(0)                                         => timingExtension(i).valid,
               rd_clk                                         => appTimingClk,
               dout(TIMING_EXTENSION_MESSAGE_BITS_C downto 1) => appTimingExtension(i).data,
               dout(0)                                        => appTimingExtension(i).valid);
      end generate GEN_EXTENSION_SYNC_FIFOS;
   end generate;

   NO_GEN_ASYNC : if not ASYNC_G generate
      appTimingBus_i.stream    <= timingStream;
      appTimingBus_i.message   <= timingMessage;
      appTimingBus_i.strobe    <= timingStrobe;
      appTimingBus_i.valid     <= timingValid;
      appTimingBus_i.modesel   <= modeSelRx;
      appTimingBus_i.extension <= timingExtension;
      modeSelApp               <= modeSelRx;
   end generate;

   U_SYNC_LinkV1 : entity surf.Synchronizer
      generic map (
         TPD_G => TPD_G)
      port map (
         clk     => appTimingClk,
         dataIn  => linkUpV1,
         dataOut => appTimingBus_i.v1.linkUp);

   appTimingBus_i.v1.gtRxData    <= gtRxData    when(modeSelRx = '0') else (others => '0');
   appTimingBus_i.v1.gtRxDataK   <= gtRxDataK   when(modeSelRx = '0') else (others => '0');
   appTimingBus_i.v1.gtRxDispErr <= gtRxDispErr when(modeSelRx = '0') else (others => '0');
   appTimingBus_i.v1.gtRxDecErr  <= gtRxDecErr  when(modeSelRx = '0') else (others => '0');

   U_SYNC_LinkV2 : entity surf.Synchronizer
      generic map (
         TPD_G => TPD_G)
      port map (
         clk     => appTimingClk,
         dataIn  => linkUpV2,
         dataOut => appTimingBus_i.v2.linkUp);

   linkUpV1 <= gtRxStatus.locked and not modeSelRx;
   linkUpV2 <= gtRxStatus.locked and modeSelRx;

   U_EthTiming : entity lcls_timing_core.EthTimingModule
      generic map (
         TPD_G             => TPD_G,
         STREAM_L1_G       => STREAM_L1_G,
         ETHMSG_AXIS_CFG_G => ETHMSG_AXIS_CFG_G)
      port map (
         timingClk      => gtRxRecClk,
         timingRst      => appTimingRst,
         timingStrobe   => timingStreamStrobe,
         timingStream   => timingStreamPrompt,
         ethClk         => axilClk,
         ethRst         => axilRst,
         ibEthMsgMaster => ibEthMsgMaster,
         ibEthMsgSlave  => ibEthMsgSlave,
         obEthMsgMaster => obEthMsgMaster,
         obEthMsgSlave  => obEthMsgSlave);

end rtl;
