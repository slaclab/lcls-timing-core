-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingFrameRx.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2015-09-18
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: 
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
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
      timingClk       : in  sl;
      timingRst       : in  sl;
      rxData          : in  slv(15 downto 0);
      rxDataK         : in  slv(1 downto 0);
      rxError         : in  sl;
      rxLinkUp        : in  sl;
      timingMsg       : out TimingMsgType;
      timingMsgStrobe : out sl;

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
   -- timingClk Domain
   -------------------------------------------------------------------------------------------------
   type StateType is (IDLE_S, FRAME_S);

   type RegType is record
      state           : StateType;
      lastFrameValid  : sl;
      crcReset        : sl;
      crcOut          : slv32Array(1 downto 0);
      sofStrobe       : sl;
      eofStrobe       : sl;
      crcErrorStrobe  : sl;
      timingMsgShift  : slv(TIMING_MSG_BITS_C-1 downto 0);
      timingMsgOut    : TimingMsgType;
      timingMsgStrobe : sl;
   end record;

   constant REG_INIT_C : RegType := (
      state           => IDLE_S,
      lastFrameValid  => '0',
      crcReset        => '1',
      crcOut          => (others => (others => '0')),
      sofStrobe       => '0',
      eofStrobe       => '0',
      crcErrorStrobe  => '0',
      timingMsgShift  => (others => '0'),
      timingMsgOut    => TIMING_MSG_INIT_C,
      timingMsgStrobe => '0');

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal crcDataValid : sl;
   signal crcOut       : slv(31 downto 0);

   -------------------------------------------------------------------------------------------------
   -- axilClk Domain
   -------------------------------------------------------------------------------------------------
   type AxilRegType is record
      cntRst         : sl;
      axilReadSlave  : AxiLiteReadSlaveType;
      axilWriteSlave : AxiLiteWriteSlaveType;
   end record AxilRegType;

   constant AXIL_REG_INIT_C : AxilRegType := (
      cntRst         => '0',
      axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
      axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C);

   signal axilR   : AxilRegType := AXIL_REG_INIT_C;
   signal axilRin : AxilRegType;

   constant NUM_COUNTERS_C  : integer := 6;
   constant COUNTER_WIDTH_C : integer := 32;

   -- Synchronized to AXIL clk
   signal axilStatusCounters : SlVectorArray(NUM_COUNTERS_C-1 downto 0, COUNTER_WIDTH_C-1 downto 0);
   signal axilRxLinkUp       : sl;

begin

   -- Any word without K chars added to CRC
   crcDataValid <= '1' when rxDataK = "00" else '0';
   Crc32Parallel_1 : entity work.Crc32Parallel
      generic map (
         BYTE_WIDTH_G => 4,
         CRC_INIT_G   => X"FFFFFFFF",
         TPD_G        => TPD_G)
      port map (
         crcOut              => crcOut,
         crcClk              => timingClk,
         crcDataValid        => crcDataValid,
         crcDataWidth        => "001",
         crcIn(31 downto 16) => (others => '0'),
         crcIn(15 downto 0)  => rxData,
         crcReset            => r.crcReset);

   comb : process (crcOut, r, rxData, rxDataK, rxError, rxLinkUp, timingRst) is
      variable v : RegType;
   begin
      v := r;

      -- Save CRC from 2 cycles ago so that transmitted CRC not inculded in CRC calc once you see EOF
      v.crcOut(0) := crcOut;
      v.crcOut(1) := r.crcOut(0);

      -- Strobed registers
      v.crcReset        := '0';
      v.sofStrobe       := '0';
      v.eofStrobe       := '0';
      v.timingMsgStrobe := '0';
      v.crcErrorStrobe  := '0';


      case (r.state) is
         -- Wait for a new frame to start, then latch out the previous message if it was valid.         
         when IDLE_S =>
            if (rxDataK = "01" and rxData = (D_215_C & K_SOF_C)) then
               v.state          := FRAME_S;
               v.sofStrobe      := '1';
               v.lastFrameValid := '0';  -- reset for next frame
               v.crcReset       := '1';

               if (r.lastFrameValid = '1') then
                  v.timingMsgOut    := toTimingMsgType(r.timingMsgShift);
                  v.timingMsgStrobe := '1';
               end if;

            end if;

         when FRAME_S =>
            if (rxDataK /= "00") then
               -- Error, go back to IDLE_S without marking the frame as valid
               v.state := IDLE_S;

               if ((rxDataK = "01" and rxData = (D_215_C & K_EOF_C))) then
                  -- EOF character seen, check crc
                  v.eofStrobe      := '1';
                  v.lastFrameValid := toSl(toTimingMsgType(r.timingMsgShift).crc = r.crcOut(0));
                  v.crcErrorStrobe := not v.lastFrameValid;
               end if;
            else
               -- Shift in new data if not a K char
               v.timingMsgShift := rxData & r.timingMsgShift(TIMING_MSG_BITS_C-1 downto 16);
            end if;

         when others => null;
      end case;

      if (rxLinkUp = '0' or rxError = '1') then
         v.state          := IDLE_S;
         v.lastFrameValid := '0';
      end if;

      if (timingRst = '1') then
         v := REG_INIT_C;
      end if;

      timingMsg       <= r.timingMsgOut;
      timingMsgStrobe <= r.timingMsgStrobe;
      rin             <= v;

   end process comb;

   seq : process (timingClk) is
   begin
      if (rising_edge(timingClk)) then
         r <= rin after TPD_G;
      end if;
   end process seq;

   -------------------------------------------------------------------------------------------------
   -- AXI-LITE Logic
   -------------------------------------------------------------------------------------------------
   SyncStatusVector_1 : entity work.SyncStatusVector
      generic map (
         TPD_G          => TPD_G,
         IN_POLARITY_G  => "011111",
--         OUT_POLARITY_G => '1'
         USE_DSP48_G    => "no",
--         SYNTH_CNT_G     => SYNTH_CNT_G,
         CNT_RST_EDGE_G => false,
         CNT_WIDTH_G    => 32,
         WIDTH_G        => 6)
      port map (
         statusIn(0)           => r.sofStrobe,
         statusIn(1)           => r.eofStrobe,
         statusIn(2)           => r.timingMsgStrobe,
         statusIn(3)           => r.crcErrorStrobe,
         statusIn(4)           => rxError,
         statusIn(5)           => rxLinkUp,
         statusOut(4 downto 0) => open,
         statusOut(5)          => axilRxLinkUp,
         cntRstIn              => axilR.cntRst,
         rollOverEnIn          => (others => '0'),
         cntOut                => axilStatusCounters,
         wrClk                 => timingClk,
         wrRst                 => timingRst,
         rdClk                 => axilClk,
         rdRst                 => axilRst);

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

      axilSlaveRegisterW(X"18", 0, v.cntRst);
      axilSlaveRegisterR(X"18", 1, axilRxLinkUp);


      axilSlaveDefault(AXIL_ERROR_RESP_G);

      ----------------------------------------------------------------------------------------------
      -- Reset
      ----------------------------------------------------------------------------------------------
      if (axilRst = '1') then
         v := AXIL_REG_INIT_C;
      end if;

      axilRin <= v;

      axilReadSlave  <= axilR.axilReadSlave;
      axilWriteSlave <= axilR.axilWriteSlave;

   end process;

   axilSeq : process (axilClk) is
   begin
      if (rising_edge(axilClk)) then
         axilR <= axilRin after TPD_G;
      end if;
   end process;
   
end architecture rtl;

