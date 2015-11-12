-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingFrameRx.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2015-11-09
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
      rxClk     : in sl;
      rxRstDone : in sl;
      rxData    : in slv(15 downto 0);
      rxDataK   : in slv(1 downto 0);
      rxDispErr : in slv(1 downto 0);
      rxDecErr  : in slv(1 downto 0);

      timingMessage       : out TimingMessageType;
      timingMessageStrobe : out sl;

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
      state               : StateType;
      toggleClk           : sl;
      crcReset            : sl;
      crcOut              : slv32Array(0 downto 0);
      sofStrobe           : sl;
      eofStrobe           : sl;
      crcErrorStrobe      : sl;
      timingMessageShift  : slv(TIMING_MESSAGE_BITS_C-1 downto 0);
--      timingMessageOut    : TimingMessageType;
      timingMessageStrobe : sl;
   end record;

   constant REG_INIT_C : RegType := (
      state               => IDLE_S,
      toggleClk           => '0',
      crcReset            => '1',
      crcOut              => (others => (others => '0')),
      sofStrobe           => '0',
      eofStrobe           => '0',
      crcErrorStrobe      => '0',
      timingMessageShift  => (others => '0'),
--      timingMessageOut    => TIMING_MESSAGE_INIT_C,
      timingMessageStrobe => '0');

   constant NO_DELAY : boolean := true;
   
   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal timingMessageOut : TimingMessageType;
   signal timingMessageDelay : slv(15 downto 0);
   signal crcDataValid       : sl;
   signal crcOut             : slv(31 downto 0);

   -------------------------------------------------------------------------------------------------
   -- axilClk Domain
   -------------------------------------------------------------------------------------------------
   type AxilRegType is record
      cntRst         : sl;
      messageDelay   : slv(15 downto 0);
      axilReadSlave  : AxiLiteReadSlaveType;
      axilWriteSlave : AxiLiteWriteSlaveType;
   end record AxilRegType;

   constant AXIL_REG_INIT_C : AxilRegType := (
      cntRst         => '0',
      messageDelay   => toSlv(20000, 16),
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
         BYTE_WIDTH_G => 2,
         CRC_INIT_G   => X"FFFFFFFF",
         TPD_G        => TPD_G)
      port map (
         crcOut              => crcOut,
         crcClk              => rxClk,
         crcDataValid        => crcDataValid,
         crcDataWidth        => "001",
         crcIn(15 downto 0)  => rxData,
         crcReset            => r.crcReset);

   comb : process (crcOut, r, rxData, rxDataK, rxDecErr, rxDispErr) is
      variable v : RegType;
   begin
      v := r;

      v.toggleClk := not r.toggleClk;

      -- Strobed registers
      v.crcReset            := '0';
      v.sofStrobe           := '0';
      v.eofStrobe           := '0';
      v.timingMessageStrobe := '0';
      v.crcErrorStrobe      := '0';


      case (r.state) is
         -- Wait for a new frame to start, then latch out the previous message if it was valid.         
         when IDLE_S =>
            if (rxDataK = "01" and rxData = (D_215_C & K_SOF_C)) then
               v.state          := FRAME_S;
               v.sofStrobe      := '1';
               v.crcReset       := '1';

               v.timingMessageStrobe := '1';  -- always for now, until CRC is fixed
               if (toTimingMessageType(r.timingMessageShift).crc = r.crcOut(0)) then
                  v.timingMessageStrobe := '1';
               else
                  v.crcErrorStrobe := '1';
               end if;

            end if;

         when FRAME_S =>
            if (rxDataK /= "00") then
               v.state := IDLE_S;
               if ((rxDataK = "01" and rxData = (D_215_C & K_EOF_C))) then
                  -- EOF character seen, check crc
                 v.eofStrobe      := '1';
               end if;
            else
               -- Shift in new data if not a K char
               v.timingMessageShift := rxData & r.timingMessageShift(TIMING_MESSAGE_BITS_C-1 downto 16);
               v.crcOut(0)          := crcOut;
            end if;

         when others => null;
      end case;

      if (rxDecErr /= "00" or rxDispErr /= X"00") then
         v.state          := IDLE_S;
      end if;

      timingMessageOut <= toTimingMessageType(r.timingMessageShift);
      rin                 <= v;

   end process comb;

   seq : process (rxClk) is
   begin
      if (rising_edge(rxClk)) then
         r <= rin after TPD_G;
      end if;
   end process seq;

   -------------------------------------------------------------------------------------------------
   -- Delay the timing message
   -------------------------------------------------------------------------------------------------
   GEN_DELAY: if NO_DELAY=false generate
     TimingMsgDelay_1 : entity work.TimingMsgDelay
       generic map (
         TPD_G             => TPD_G,
         BRAM_EN_G         => true,
         FIFO_ADDR_WIDTH_G => 9)
       port map (
         timingClk              => rxClk,
         timingRst              => '0',
         timingMessageIn        => timingMessageOut,
         timingMessageStrobeIn  => r.timingMessageStrobe,
         delay                  => timingMessageDelay,
         timingMessageOut       => timingMessage,
         timingMessageStrobeOut => timingMessageStrobe);
   end generate GEN_DELAY;

   GEN_NODELAY: if NO_DELAY=true generate
     timingMessage       <= timingMessageOut;
     timingMessageStrobe <= r.timingMessageStrobe;
   end generate GEN_NODELAY;
   -------------------------------------------------------------------------------------------------
   -- Synchronize message delay to timing domain
   -------------------------------------------------------------------------------------------------
   SynchronizerFifo_1 : entity work.SynchronizerFifo
      generic map (
         TPD_G        => TPD_G,
         DATA_WIDTH_G => 16)
      port map (
         rst    => axilRst,
         wr_clk => axilClk,
         din    => axilR.messageDelay,
         rd_clk => rxClk,
         dout   => timingMessageDelay);

   -------------------------------------------------------------------------------------------------
   -- AXI-LITE Logic
   -------------------------------------------------------------------------------------------------
   SyncStatusVector_1 : entity work.SyncStatusVector
      generic map (
         TPD_G          => TPD_G,
         IN_POLARITY_G  => "111111",
--         OUT_POLARITY_G => '1'
         USE_DSP48_G    => "no",
--         SYNTH_CNT_G     => SYNTH_CNT_G,
         CNT_RST_EDGE_G => false,
         CNT_WIDTH_G    => 32,
         WIDTH_G        => 6)
      port map (
         statusIn(0)           => r.sofStrobe,
         statusIn(1)           => r.eofStrobe,
         statusIn(2)           => r.timingMessageStrobe,
         statusIn(3)           => r.crcErrorStrobe,
         statusIn(4)           => r.toggleClk,
         statusIn(5)           => rxRstDone,
         statusOut(4 downto 0) => open,
         statusOut(5)          => axilRxLinkUp,
         cntRstIn              => axilR.cntRst,
         rollOverEnIn          => "010111",
         cntOut                => axilStatusCounters,
         wrClk                 => rxClk,
         wrRst                 => '0',
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

      axilSlaveRegisterW(X"1C", 0, v.messageDelay);


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

