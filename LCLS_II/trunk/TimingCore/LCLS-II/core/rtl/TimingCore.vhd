-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingCore.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-25
-- Last update: 2016-03-21
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

entity TimingCore is

   generic (
      TPD_G             : time             := 1 ns;
      TPGEN_G           : boolean          := false;
      AXIL_BASE_ADDR_G  : slv(31 downto 0) := (others => '0');
      AXIL_ERROR_RESP_G : slv(1 downto 0)  := AXI_RESP_OK_C;
      LCLSV1_G          : boolean          := false);
   port (

      -- Interface to GT
      gtTxUsrClk : in sl;
      gtTxUsrRst : in sl;

      gtRxRecClk    : in  sl;
      gtRxData      : in  slv(15 downto 0);
      gtRxDataK     : in  slv(1 downto 0);
      gtRxDispErr   : in  slv(1 downto 0);
      gtRxDecErr    : in  slv(1 downto 0);
      gtRxReset     : out sl;
      gtRxResetDone : in  sl;
      gtRxPolarity  : out sl;
      timingPhy     : out TimingPhyType;
      -- Decoded timing message interface
      appTimingClk  : in  sl;
      appTimingRst  : in  sl;
      appTimingBus  : out TimingBusType;

      -- AXI Lite interface
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType);


end entity TimingCore;

architecture rtl of TimingCore is

   constant NUM_AXIL_MASTERS_C : integer := 4;

   constant FRAME_RX_AXIL_INDEX_C       : natural := 0;
   constant RAW_BUFFER_AXIL_INDEX_C     : natural := 1;
   constant MESSAGE_BUFFER_AXIL_INDEX_C : natural := 2;
   constant FRAME_TX_AXIL_INDEX_C       : natural := 3;

   constant AXIL_MASTERS_CONFIG_C : AxiLiteCrossbarMasterConfigArray := (
      FRAME_RX_AXIL_INDEX_C       => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"00000",
         addrBits                 => 16,
         connectivity             => X"FFFF"),
      RAW_BUFFER_AXIL_INDEX_C     => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"10000",
         addrBits                 => 16,
         connectivity             => X"FFFF"),
      MESSAGE_BUFFER_AXIL_INDEX_C => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"20000",
         addrBits                 => 16,
         connectivity             => X"FFFF"),
      FRAME_TX_AXIL_INDEX_C       => (
         baseAddr                 => AXIL_BASE_ADDR_G + X"30000",
         addrBits                 => 16,
         connectivity             => X"FFFF"));

   signal locAxilWriteMasters : AxiLiteWriteMasterArray(NUM_AXIL_MASTERS_C-1 downto 0);
   signal locAxilWriteSlaves  : AxiLiteWriteSlaveArray(NUM_AXIL_MASTERS_C-1 downto 0);
   signal locAxilReadMasters  : AxiLiteReadMasterArray(NUM_AXIL_MASTERS_C-1 downto 0);
   signal locAxilReadSlaves   : AxiLiteReadSlaveArray(NUM_AXIL_MASTERS_C-1 downto 0);

   constant TIMING_FRAME_LEN_C : integer := ite(LCLSV1_G, TIMING_STREAM_BITS_C, TIMING_MESSAGE_BITS_C);
   signal timingMessageStrobe  : sl;
   signal timingMessage        : TimingMessageType;
   signal timingStream         : TimingStreamType;
   signal timingFrameSlv       : slv(TIMING_FRAME_LEN_C-1 downto 0);
   signal appTimingFrameSlv    : slv(TIMING_FRAME_LEN_C-1 downto 0);

begin

   AxiLiteCrossbar_1 : entity work.AxiLiteCrossbar
      generic map (
         TPD_G              => TPD_G,
         NUM_SLAVE_SLOTS_G  => 1,
         NUM_MASTER_SLOTS_G => NUM_AXIL_MASTERS_C,
         DEC_ERROR_RESP_G   => AXI_RESP_DECERR_C,
         MASTERS_CONFIG_G   => AXIL_MASTERS_CONFIG_C,
         DEBUG_G            => true)
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
   LCLSV1_RX : if (LCLSV1_G = true) generate
      TimingStreamRx_1 : entity work.TimingStreamRx
         generic map (
            TPD_G             => TPD_G,
            AXIL_ERROR_RESP_G => AXI_RESP_DECERR_C)
         port map (
            txClk               => gtTxUsrClk,
            rxClk               => gtRxRecClk,
            rxRstDone           => gtRxResetDone,
            rxData              => gtRxData,
            rxDataK             => gtRxDataK,
            rxDispErr           => gtRxDispErr,
            rxDecErr            => gtRxDecErr,
            rxPolarity          => gtRxPolarity,
            rxReset             => gtRxReset,
            timingMessage       => timingStream,
            timingMessageStrobe => timingMessageStrobe,
            axilClk             => axilClk,
            axilRst             => axilRst,
            axilReadMaster      => locAxilReadMasters(FRAME_RX_AXIL_INDEX_C),
            axilReadSlave       => locAxilReadSlaves(FRAME_RX_AXIL_INDEX_C),
            axilWriteMaster     => locAxilWriteMasters(FRAME_RX_AXIL_INDEX_C),
            axilWriteSlave      => locAxilWriteSlaves(FRAME_RX_AXIL_INDEX_C));
   end generate LCLSV1_RX;

   LCLSV2_RX : if (LCLSV1_G = false) generate
      TimingFrameRx_1 : entity work.TimingFrameRx
         generic map (
            TPD_G             => TPD_G,
            AXIL_ERROR_RESP_G => AXI_RESP_DECERR_C)
         port map (
            txClk               => gtTxUsrClk,
            rxClk               => gtRxRecClk,
            rxRstDone           => gtRxResetDone,
            rxData              => gtRxData,
            rxDataK             => gtRxDataK,
            rxDispErr           => gtRxDispErr,
            rxDecErr            => gtRxDecErr,
            rxPolarity          => gtRxPolarity,
            rxReset             => gtRxReset,
            timingMessage       => timingMessage,
            timingMessageStrobe => timingMessageStrobe,
            axilClk             => axilClk,
            axilRst             => axilRst,
            axilReadMaster      => locAxilReadMasters(FRAME_RX_AXIL_INDEX_C),
            axilReadSlave       => locAxilReadSlaves(FRAME_RX_AXIL_INDEX_C),
            axilWriteMaster     => locAxilWriteMasters(FRAME_RX_AXIL_INDEX_C),
            axilWriteSlave      => locAxilWriteSlaves(FRAME_RX_AXIL_INDEX_C));
   end generate LCLSV2_RX;

   -------------------------------------------------------------------------------------------------
   -- Ring buffer to log raw GT words
   -------------------------------------------------------------------------------------------------
   AxiLiteRingBuffer_1 : entity work.AxiLiteRingBuffer
      generic map (
         TPD_G            => TPD_G,
         BRAM_EN_G        => true,
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
         axilReadMaster          => locAxilReadMasters(RAW_BUFFER_AXIL_INDEX_C),
         axilReadSlave           => locAxilReadSlaves(RAW_BUFFER_AXIL_INDEX_C),
         axilWriteMaster         => locAxilWriteMasters(RAW_BUFFER_AXIL_INDEX_C),
         axilWriteSlave          => locAxilWriteSlaves(RAW_BUFFER_AXIL_INDEX_C));

   -------------------------------------------------------------------------------------------------
   -- Ring buffer to log received timing messages
   -------------------------------------------------------------------------------------------------
   TimingMsgAxiRingBuffer_1 : entity work.TimingMsgAxiRingBuffer
      generic map (
         TPD_G            => TPD_G,
         BRAM_EN_G        => true,
         REG_EN_G         => true,
         RAM_ADDR_WIDTH_G => 13,
         VECTOR_SIZE_G    => TIMING_FRAME_LEN_C)
      port map (
         timingClk           => gtRxRecClk,
         timingRst           => '0',
         timingMessage       => timingFrameSlv,
         timingMessageStrobe => timingMessageStrobe,
         axilClk             => axilClk,
         axilRst             => axilRst,
         axilReadMaster      => locAxilReadMasters(MESSAGE_BUFFER_AXIL_INDEX_C),
         axilReadSlave       => locAxilReadSlaves(MESSAGE_BUFFER_AXIL_INDEX_C),
         axilWriteMaster     => locAxilWriteMasters(MESSAGE_BUFFER_AXIL_INDEX_C),
         axilWriteSlave      => locAxilWriteSlaves(MESSAGE_BUFFER_AXIL_INDEX_C));

   GEN_MINICORE : if (TPGEN_G = false and LCLSV1_G = false) generate
      TPGMiniCore_1 : entity work.TPGMiniCore
         generic map (
            NARRAYSBSA => 2)
         port map (
            txClk          => gtTxUsrClk,
            txRst          => gtTxUsrRst,
            txRdy          => '1',
            txData         => timingPhy.data,
            txDataK        => timingPhy.dataK,
            txPolarity     => timingPhy.polarity,
            axiClk         => axilClk,
            axiRst         => axilRst,
            axiReadMaster  => locAxilReadMasters (FRAME_TX_AXIL_INDEX_C),
            axiReadSlave   => locAxilReadSlaves (FRAME_TX_AXIL_INDEX_C),
            axiWriteMaster => locAxilWriteMasters(FRAME_TX_AXIL_INDEX_C),
            axiWriteSlave  => locAxilWriteSlaves (FRAME_TX_AXIL_INDEX_C));
   end generate GEN_MINICORE;

   NOGEN_MINICORE : if (TPGEN_G = true or LCLSV1_G = true) generate
      timingPhy.data     <= (others => '0');
      timingPhy.dataK    <= "00";
      timingPhy.polarity <= '0';
      U_AxiLiteEmpty : entity work.AxiLiteEmpty
         generic map (
            TPD_G => TPD_G)
         port map (
            -- AXI-Lite Bus
            axiClk         => axilClk,
            axiClkRst      => axilRst,
            axiReadMaster  => locAxilReadMasters (FRAME_TX_AXIL_INDEX_C),
            axiReadSlave   => locAxilReadSlaves (FRAME_TX_AXIL_INDEX_C),
            axiWriteMaster => locAxilWriteMasters(FRAME_TX_AXIL_INDEX_C),
            axiWriteSlave  => locAxilWriteSlaves (FRAME_TX_AXIL_INDEX_C));

   end generate NOGEN_MINICORE;

   -------------------------------------------------------------------------------------------------
   -- Synchronize timing message to appTimingClk
   -------------------------------------------------------------------------------------------------

   GEN_LCLSV1 : if (LCLSV1_G = true) generate
      timingFrameSlv       <= toSlv(timingStream);
      appTimingBus.stream  <= toTimingStreamType(appTimingFrameSlv);
      appTimingBus.message <= TIMING_MESSAGE_INIT_C;
   end generate GEN_LCLSV1;

   GEN_LCLSV2 : if (LCLSV1_G = false) generate
      timingFrameSlv       <= toSlv(timingMessage);
      appTimingBus.message <= toTimingMessageType(appTimingFrameSlv);
      appTimingBus.stream  <= TIMING_STREAM_INIT_C;
   end generate GEN_LCLSV2;

   SynchronizerFifo_1 : entity work.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => TIMING_FRAME_LEN_C)
      port map (
         rst    => appTimingRst,
         wr_clk => gtRxRecClk,
         wr_en  => timingMessageStrobe,
         din    => timingFrameSlv,
         rd_clk => appTimingClk,
         valid  => appTimingBus.strobe,
         dout   => appTimingFrameSlv);

   appTimingBus.v1 <= LCLS_V1_TIMING_DATA_INIT_C;
   appTimingBus.v2 <= LCLS_V2_TIMING_DATA_INIT_C;

end architecture rtl;
