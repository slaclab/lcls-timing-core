-------------------------------------------------------------------------------
-- Title      : Axi-lite interface for Timing trigger pulse 
-------------------------------------------------------------------------------
-- File       : LclsMrTimingTriggerPulseReg.vhd
-- Author     : Uros Legat  <ulegat@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory (Cosylab)
-- Created    : 2015-04-15
-- Last update: 2015-04-15
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description:  Register decoding
--               0x00 - 0x07 (RW)- Opcode mask
--               0x08        (RW)- Pulse delay
--               0x09        (RW)- Pulse width
--               0x0A        (RW)- Bit0: Polarity
-------------------------------------------------------------------------------
-- This file is part of 'LCLS2 LLRF Development'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS2 LLRF Development', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;

entity LclsMrTimingTriggerPulseReg is
   generic (
   -- General Configurations
      TPD_G               : time             := 1 ns;
      AXI_ERROR_RESP_G    : slv(1 downto 0)  := AXI_RESP_SLVERR_C; 
      AXI_ADDR_WIDTH_G    : positive         := 8;
      DELAY_WIDTH_G : integer range 1 to 32  := 16;
      PULSE_WIDTH_G : integer range 1 to 32  := 16
   );    
   port (
    -- AXI Clk
      axiClk_i : in sl;
      axiRst_i : in sl;

    -- Axi-Lite Register Interface (axiClk domain)
      axilReadMaster  : in  AxiLiteReadMasterType  := AXI_LITE_READ_MASTER_INIT_C;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType := AXI_LITE_WRITE_MASTER_INIT_C;
      axilWriteSlave  : out AxiLiteWriteSlaveType;
 
   -- Dev Clk
      devClk_i          : in  sl;
      devRst_i          : in  sl;

   -- Registers
      opcodesReg_o : out slv(255 downto 0);
      delayReg_o   : out slv(DELAY_WIDTH_G-1 downto 0);
      widthReg_o   : out slv(PULSE_WIDTH_G-1 downto 0);
      polarity_o   : out sl
   );   
end LclsMrTimingTriggerPulseReg;

architecture rtl of LclsMrTimingTriggerPulseReg is

   type RegType is record
      -- 
      opcodes : slv(255 downto 0);
      delay   : slv(DELAY_WIDTH_G-1 downto 0);
      width   : slv(PULSE_WIDTH_G-1 downto 0);
      polarity: sl;

      -- AXI lite
      axilReadSlave  : AxiLiteReadSlaveType;
      axilWriteSlave : AxiLiteWriteSlaveType;
   end record;
   
   constant REG_INIT_C : RegType := (
      opcodes  => x"0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000_0000", 
      delay    => (others =>'0'),      
      width    => (others =>'0'),
      polarity => '0', 
     
      axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
      axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C);

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;
   
   -- Integer address
   signal s_RdAddr: natural := 0;
   signal s_WrAddr: natural := 0;

begin
   
   -- Convert address to integer (lower two bits of address are always '0')
   s_RdAddr <= conv_integer( axilReadMaster.araddr(AXI_ADDR_WIDTH_G-1 downto 2));
   s_WrAddr <= conv_integer( axilWriteMaster.awaddr(AXI_ADDR_WIDTH_G-1 downto 2)); 
   
   comb : process (axilReadMaster, axilWriteMaster, r, axiRst_i, s_RdAddr, s_WrAddr) is
      variable v             : RegType;
      variable axilStatus    : AxiLiteStatusType;
      variable axilWriteResp : slv(1 downto 0);
      variable axilReadResp  : slv(1 downto 0);
   begin
      -- Latch the current value
      v := r;
      
      ----------------------------------------------------------------------------------------------
      -- Axi-Lite interface
      ----------------------------------------------------------------------------------------------
      axiSlaveWaitTxn(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus);

      if (axilStatus.writeEnable = '1') then
         axilWriteResp := ite(axilWriteMaster.awaddr(1 downto 0) = "00", AXI_RESP_OK_C, AXI_ERROR_RESP_G);
         case (s_WrAddr) is
            when 16#00# to 16#07# => -- ADDR (0x0-0x1C)
               for i in 7 downto 0 loop
                  if (axilWriteMaster.awaddr(4 downto 2) = i) then
                     v.opcodes((32*i + 31) downto (32*i)) := axilWriteMaster.wdata;
                  end if;
               end loop; 
            when 16#08# => -- ADDR (20)
               v.delay  := axilWriteMaster.wdata(DELAY_WIDTH_G-1 downto 0);                
            when 16#09# => -- ADDR (24)
               v.width  := axilWriteMaster.wdata(PULSE_WIDTH_G-1 downto 0);
            when 16#0A# => -- ADDR (28)
               v.polarity  := axilWriteMaster.wdata(0);
            when others =>
               axilWriteResp     := AXI_ERROR_RESP_G;
         end case;
         axiSlaveWriteResponse(v.axilWriteSlave);
      end if;

      if (axilStatus.readEnable = '1') then
         axilReadResp := ite(axilReadMaster.araddr(1 downto 0) = "00", AXI_RESP_OK_C, AXI_ERROR_RESP_G);
         v.axilReadSlave.rdata := (others => '0');
         case (s_RdAddr) is
            when 16#00# to 16#07# =>  -- ADDR (0x0-0x1C)
               for i in 7 downto 0 loop
                  if (axilReadMaster.araddr(4 downto 2) = i) then
                     v.axilReadSlave.rdata := r.opcodes((32*i + 31) downto (32*i));
                  end if;
               end loop;
            when 16#08# =>  -- ADDR (20)
               v.axilReadSlave.rdata(DELAY_WIDTH_G-1 downto 0)  := r.delay;               
            when 16#09# =>  -- ADDR (24)
               v.axilReadSlave.rdata(PULSE_WIDTH_G-1 downto 0)  := r.width;
            when 16#0A# =>  -- ADDR (28)
               v.axilReadSlave.rdata(0)  := r.polarity;               
            when others =>
               axilReadResp    := AXI_ERROR_RESP_G;
         end case;
         axiSlaveReadResponse(v.axilReadSlave);
      end if;

      -- Reset
      if (axiRst_i = '1') then
         v := REG_INIT_C;
      end if;

      -- Register the variable for next clock cycle
      rin <= v;

      -- Outputs
      axilReadSlave  <= r.axilReadSlave;
      axilWriteSlave <= r.axilWriteSlave;
      
   end process comb;

   seq : process (axiClk_i) is
   begin
      if rising_edge(axiClk_i) then
         r <= rin after TPD_G;
      end if;
   end process seq;

   SyncFifo_OUT0 : entity work.SynchronizerFifo
   generic map (
      TPD_G        => TPD_G,
      DATA_WIDTH_G => 256
   )
   port map (
      wr_clk => axiClk_i,
      din    => r.opcodes,
      rd_clk => devClk_i,
      dout   => opcodesReg_o
   );
   
   SyncFifo_OUT1 : entity work.SynchronizerFifo
   generic map (
      TPD_G        => TPD_G,
      DATA_WIDTH_G => DELAY_WIDTH_G
   )
   port map (
      wr_clk => axiClk_i,
      din    => r.delay,
      rd_clk => devClk_i,
      dout   => delayReg_o
   );
      
   SyncFifo_OUT2 : entity work.SynchronizerFifo
   generic map (
      TPD_G        => TPD_G,
      DATA_WIDTH_G => PULSE_WIDTH_G
   )
   port map (
      wr_clk => axiClk_i,
      din    => r.width,
      rd_clk => devClk_i,
      dout   => widthReg_o
   );
   
   Sync_OUT3 : entity work.Synchronizer
   generic map (
      TPD_G        => TPD_G
   )
    port map (
      dataIn    => r.polarity,
      clk       => devClk_i,
      dataOut   => polarity_o
   );
   
---------------------------------------------------------------------
end rtl;
