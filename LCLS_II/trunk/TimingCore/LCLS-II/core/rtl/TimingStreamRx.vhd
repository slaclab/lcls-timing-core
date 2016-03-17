-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingFrameRx.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2016-03-07
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


entity TimingStreamRx is

   generic (
      TPD_G             : time            := 1 ns;
      AXIL_ERROR_RESP_G : slv(1 downto 0) := AXI_RESP_OK_C);

   port (
      rxClk      : in  sl;
      rxRstDone  : in  sl;
      rxData     : in  slv(15 downto 0);
      rxDataK    : in  slv(1 downto 0);
      rxDispErr  : in  slv(1 downto 0);
      rxDecErr   : in  slv(1 downto 0);
      rxPolarity : out sl;
      rxReset    : out sl;

      timingMessage       : out TimingStreamType;
      timingMessageStrobe : out sl;

      txClk           : in  sl;
      
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType
      );

end entity TimingStreamRx;

architecture rtl of TimingStreamRx is

   -------------------------------------------------------------------------------------------------
   -- rxClk Domain
   -------------------------------------------------------------------------------------------------
   type StateType is (IDLE_S, FRAME_S);

   type RegType is record
      dstate              : StateType;
      estate              : StateType;
      sofStrobe           : sl;
      eofStrobe           : sl;
      ecount              : slv(19 downto 0);
      dataBuffEn          : sl;
      dataBuffShift       : slv(TIMING_DATABUFF_BITS_C-1 downto 0);
      pulseIdShift        : slv(31 downto 0);
      eventCodes          : slv(255 downto 0);
      timingStream        : TimingStreamType;
      dataBuffCache       : TimingDataBuffArray(2 downto 0);
      timingMessageStrobe : sl;
   end record;

   constant REG_INIT_C : RegType := (
      dstate              => IDLE_S,
      estate              => IDLE_S,
      sofStrobe           => '0',
      eofStrobe           => '0',
      ecount              => (others => '0'),
      dataBuffEn          => '0',
      dataBuffShift       => (others => '0'),
      pulseIdShift        => (others => '0'),
      eventCodes          => (others => '0'),
      timingStream        => TIMING_STREAM_INIT_C,
      dataBuffCache       => (others=>TIMING_DATA_BUFF_INIT_C),
      timingMessageStrobe => '0');

   constant FRAME_LEN : slv(19 downto 0) := x"036b0";  -- end of EVG stream
   
   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal rxDbuf             : slv(7 downto 0);
   signal rxEcod             : slv(7 downto 0);
   signal timingStreamOut    : TimingStreamType;
   signal rxDecErrSum        : sl;
   signal rxDspErrSum        : sl;

   -------------------------------------------------------------------------------------------------
   -- axilClk Domain
   -------------------------------------------------------------------------------------------------
   type AxilRegType is record
      cntRst         : sl;
      rxPolarity     : sl;
      rxReset        : sl;
      axilReadSlave  : AxiLiteReadSlaveType;
      axilWriteSlave : AxiLiteWriteSlaveType;
   end record AxilRegType;

   constant AXIL_REG_INIT_C : AxilRegType := (
      cntRst         => '0',
      rxPolarity     => '0',
      rxReset        => '0',
      axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
      axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C);

   signal axilR   : AxilRegType := AXIL_REG_INIT_C;
   signal axilRin : AxilRegType;

   signal rxClkCnt : slv(3 downto 0) := (others=>'0');
   
   constant NUM_COUNTERS_C  : integer := 8;
   constant COUNTER_WIDTH_C : integer := 32;

   -- Synchronized to AXIL clk
   signal axilStatusCounters : SlVectorArray(NUM_COUNTERS_C-1 downto 0, COUNTER_WIDTH_C-1 downto 0);
   signal axilRxLinkUp       : sl;
   signal stv                : slv(NUM_COUNTERS_C-1 downto 0);
begin

  rxDbuf <= rxData(15 downto 8);
  rxEcod <= rxData( 7 downto 0);

  comb : process (r, rxDbuf, rxEcod, rxDataK, rxDecErr, rxDispErr) is
    variable v : RegType;
  begin
    v := r;

    -- Strobed registers
    v.sofStrobe           := '0';
    v.eofStrobe           := '0';
    v.timingMessageStrobe := '0';

    case (r.dstate) is
      when IDLE_S =>
        if (rxDataK(1)='1' and rxDbuf=K_280_C) then
          v.dstate     := FRAME_S;
          v.dataBuffEn := '0';
          v.sofStrobe  := '1';
        end if;
      when FRAME_S =>
        if (rxDataK(1)='1' and (rxDbuf=K_COM_C or rxDbuf=K_281_C)) then
          v.dstate        := IDLE_S;
          v.eofStrobe     := '1';
          -- shift data buffer into storage
          v.dataBuffCache := r.dataBuffCache(1 downto 0) & toTimingDataBuffType(r.dataBuffShift);
        elsif (rxDataK(1)='0' and r.dataBuffEn='1') then
          v.dataBuffShift := r.dataBuffShift(r.dataBuffShift'left-8 downto 0) & rxDbuf;
        end if;
        v.dataBuffEn    := not r.dataBuffEn;
      when others => null;
    end case;

    case (r.estate) is
      when IDLE_S =>
        if (rxDataK(0)='0') then
          if (rxEcod=x"7D") then
            v.ecount := (others=>'0');
            v.estate := FRAME_S;
          elsif rxEcod=x"70" then
            v.pulseIdShift := '0' & r.pulseIdShift(31 downto 1);
          elsif rxEcod=x"71" then
            v.pulseIdShift := '1' & r.pulseIdShift(31 downto 1);
          else
            v.eventCodes(conv_integer(rxEcod)) := '1';
          end if;
        end if;
      when FRAME_S =>
        if r.ecount = FRAME_LEN then
          v.estate := IDLE_S;
          v.eventCodes := (others=>'0');
          v.timingStream.pulseId := r.pulseIdShift;
          v.timingStream.eventCodes  := r.eventCodes;
          v.timingStream.dbuff   := r.dataBuffCache(2);
          v.timingMessageStrobe  := '1';
        else
          v.ecount := r.ecount+1;
          if rxDataK(0)='0' then
            v.eventCodes(conv_integer(rxEcod)) := '1';
          end if;
        end if;
      when others =>  null;
    end case;

    
    if (rxDecErr /= "00" or rxDispErr /= X"00") then
      v.dstate := IDLE_S;
    end if;

    rin              <= v;
  end process comb;
  
  timingMessage       <= r.timingStream;
  timingMessageStrobe <= r.timingMessageStrobe;

   seq : process (rxClk) is
   begin
      if (rising_edge(rxClk)) then
         r <= rin after TPD_G;
      end if;
   end process seq;

   -------------------------------------------------------------------------------------------------
   -- AXI-LITE Logic
   -------------------------------------------------------------------------------------------------
   rxDecErrSum  <= rxDecErr(0) or rxDecErr(1);
   rxDspErrSum  <= rxDispErr(0) or rxDispErr(1);
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
         statusIn(0)  => r.sofStrobe,
         statusIn(1)  => r.eofStrobe,
         statusIn(2)  => r.timingMessageStrobe,
         statusIn(3)  => '0',
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

   axilComb : process (axilR, axilReadMaster, axilRst, axilRxLinkUp, axilStatusCounters,
                       axilWriteMaster) is
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
      if (rising_edge(rxClk)) then
         rxClkCnt <= rxClkCnt+1;
      end if;
   end process rxClkCnt_seq;

end architecture rtl;

