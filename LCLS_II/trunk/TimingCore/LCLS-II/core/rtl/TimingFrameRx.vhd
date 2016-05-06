-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingFrameRx.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2016-05-02
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
      rxClk      : in  sl;
      rxRstDone  : in  sl;
      rxData     : in  TimingRxType;
      rxPolarity : out sl;
      rxReset    : out sl;
      loopback   : out slv(2 downto 0);

      timingMessage       : out TimingMessageType;
      timingMessageStrobe : out sl;
      timingMessageValid  : out sl;

      exptMessage         : out ExptMessageType;
      exptMessageValid    : out sl;
      
      txClk      : in  sl;

      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType
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

   signal fiducial  : sl;
   signal streams   : TimingSerialArray(1 downto 0);
   signal streamIds : Slv4Array        (1 downto 0) := ( x"1", x"0" );
   signal advance   : slv              (1 downto 0);
   signal sof, eof, crcErr : sl;

   signal rxDecErrSum        : sl;
   signal rxDspErrSum        : sl;

   signal rxClkCnt,txClkCnt : slv(3 downto 0) := (others=>'0');
   
   -------------------------------------------------------------------------------------------------
   -- axilClk Domain
   -------------------------------------------------------------------------------------------------
   type AxilRegType is record
      cntRst         : sl;
      rxPolarity     : sl;
      rxReset        : sl;
      loopback       : sl;
      messageDelay   : slv(15 downto 0);
      axilReadSlave  : AxiLiteReadSlaveType;
      axilWriteSlave : AxiLiteWriteSlaveType;
   end record AxilRegType;

   constant AXIL_REG_INIT_C : AxilRegType := (
      cntRst         => '0',
      rxPolarity     => '0',
      rxReset        => '0',
      loopback       => '0',
      messageDelay   => toSlv(20000, 16),
      axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
      axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C);

   signal axilR   : AxilRegType := AXIL_REG_INIT_C;
   signal axilRin : AxilRegType;

   constant NUM_COUNTERS_C  : integer := 8;
   constant COUNTER_WIDTH_C : integer := 32;

   -- Synchronized to AXIL clk
   signal axilStatusCounters : SlVectorArray(NUM_COUNTERS_C-1 downto 0, COUNTER_WIDTH_C-1 downto 0);
   signal axilRxLinkUp       : sl;
   signal stv                : slv(NUM_COUNTERS_C-1 downto 0);
   signal txClkCntS          : slv(COUNTER_WIDTH_C-1 downto 0);
begin

   U_Deserializer : entity work.TimingDeserializer
      generic map ( STREAMS_C => 2 )
      port map ( clk       => rxClk,
                 rst       => axilR.rxReset,
                 fiducial  => fiducial,
                 streams   => streams,
                 streamIds => streamIds,
                 advance   => advance,
                 data      => rxData,
                 sof       => sof,
                 eof       => eof,
                 crcErr    => crcErr );

   comb: process (r, advance, streams, fiducial) is
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

   -------------------------------------------------------------------------------------------------
   -- AXI-LITE Logic
   -------------------------------------------------------------------------------------------------
   rxDecErrSum  <= rxData.decErr(0) or rxData.decErr(1);
   rxDspErrSum  <= rxData.dspErr(0) or rxData.dspErr(1);
   axilRxLinkUp <= stv(5);

   SyncStatusVector_1 : entity work.SyncStatusVector
      generic map (
         TPD_G          => TPD_G,
         IN_POLARITY_G  => "11111111",
--         OUT_POLARITY_G => '1'
         USE_DSP48_G    => "no",
--         SYNTH_CNT_G     => SYNTH_CNT_G,
         CNT_RST_EDGE_G => false,
         CNT_WIDTH_G    => COUNTER_WIDTH_C,
         WIDTH_G        => NUM_COUNTERS_C)
      port map (
         statusIn(0)  => sof,
         statusIn(1)  => eof,
         statusIn(2)  => fiducial,
         statusIn(3)  => crcErr,
         statusIn(4)  => rxClkCnt(rxClkCnt'left),
         statusIn(5)  => rxRstDone,
         statusIn(6)  => rxDecErrSum,
         statusIn(7)  => rxDspErrSum,
         statusOut    => stv,
         cntRstIn     => axilR.cntRst,
         rollOverEnIn => "00010111",
         cntOut       => axilStatusCounters,
         wrClk        => rxClk,
         wrRst        => '0',
         rdClk        => axilClk,
         rdRst        => axilRst);

   SynchronizerOneShotCnt_1 : entity work.SynchronizerOneShotCnt
     generic map (
       TPD_G          => TPD_G,
       CNT_RST_EDGE_G => false,
       CNT_WIDTH_G    => COUNTER_WIDTH_C )
     port map (
       dataIn       => txClkCnt(txClkCnt'left),
       rollOverEn   => '1',
       cntRst       => axilR.cntRst,
       dataOut      => open,
       cntOut       => txClkCntS,
       wrClk        => txClk,
       wrRst        => '0',
       rdClk        => axilClk,
       rdRst        => axilRst );

   axilComb : process (axilR, axilReadMaster, axilRst, axilRxLinkUp, axilStatusCounters,
                       axilWriteMaster, txClkCntS) is
      variable v          : AxilRegType;
      variable axilStatus : AxiLiteStatusType;

      -- Wrapper procedures to make calls cleaner.
      procedure axilSlaveRegisterW (addr : in slv; offset : in integer; reg : inout slv; cA : in boolean := false; cV : in slv := "0") is
      begin
         axiSlaveRegister(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus, addr, offset, reg, cA, cV);
      end procedure;

      procedure axilSlaveRegisterR (addr : in slv; offset : in integer; reg : in slv) is
      begin
         axiSlaveRegister(axilReadMaster, v.axilReadSlave, axilStatus, addr, offset, reg);
      end procedure;

      procedure axilSlaveRegisterW (addr : in slv; offset : in integer; reg : inout sl) is
      begin
         axiSlaveRegister(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus, addr, offset, reg);
      end procedure;

      procedure axilSlaveRegisterR (addr : in slv; offset : in integer; reg : in sl) is
      begin
         axiSlaveRegister(axilReadMaster, v.axilReadSlave, axilStatus, addr, offset, reg);
      end procedure;

      procedure axilSlaveDefault (
         axilResp : in slv(1 downto 0)) is
      begin
         axiSlaveDefault(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus, axilResp);
      end procedure;

   begin
      -- Latch the current value
      v := axilR;
      v.axilReadSlave.rdata := (others=>'0');

      -- Determine the transaction type
      axiSlaveWaitTxn(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus);

      -- Status Counters
      axilSlaveRegisterR(X"00", 0, muxSlVectorArray(axilStatusCounters, 0));
      axilSlaveRegisterR(X"04", 0, muxSlVectorArray(axilStatusCounters, 1));
      axilSlaveRegisterR(X"08", 0, muxSlVectorArray(axilStatusCounters, 2));
      axilSlaveRegisterR(X"0C", 0, muxSlVectorArray(axilStatusCounters, 3));
      axilSlaveRegisterR(X"10", 0, muxSlVectorArray(axilStatusCounters, 4));
      axilSlaveRegisterR(X"14", 0, muxSlVectorArray(axilStatusCounters, 5));
      axilSlaveRegisterR(X"18", 0, muxSlVectorArray(axilStatusCounters, 6));
      axilSlaveRegisterR(X"1C", 0, muxSlVectorArray(axilStatusCounters, 7));

      axilSlaveRegisterW(X"20", 0, v.cntRst);
      axilSlaveRegisterR(X"20", 1, axilRxLinkUp);
      axilSlaveRegisterW(X"20", 2, v.rxPolarity);
      axilSlaveRegisterW(X"20", 3, v.rxReset);
      axilSlaveRegisterW(X"20", 4, v.loopback);

      axilSlaveRegisterW(X"24", 0, v.messageDelay);
      axilSlaveRegisterR(X"28", 0, txClkCntS);


      axilSlaveDefault(AXIL_ERROR_RESP_G);

      ----------------------------------------------------------------------------------------------
      -- Reset
      ----------------------------------------------------------------------------------------------
      if (axilRst = '1') then
         v := AXIL_REG_INIT_C;
      end if;

      axilRin <= v;

      rxPolarity     <= axilR.rxPolarity;
      rxReset        <= axilR.rxReset;
      loopback       <= '0' & axilR.loopback & '0';
      axilReadSlave  <= axilR.axilReadSlave;
      axilWriteSlave <= axilR.axilWriteSlave;

   end process;

   axilSeq : process (axilClk) is
   begin
      if (rising_edge(axilClk)) then
         axilR <= axilRin after TPD_G;
      end if;
   end process;

   rxClkCnt_seq : process (rxClk) is
   begin
     if rising_edge(rxClk) then
       rxClkCnt <= rxClkCnt+1;
     end if;
   end process rxClkCnt_seq;
   
   txClkCnt_seq : process (txClk) is
   begin
     if rising_edge(txClk) then
       txClkCnt <= txClkCnt+1;
     end if;
   end process txClkCnt_seq;
   
end architecture rtl;

