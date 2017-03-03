-------------------------------------------------------------------------------
-- File       : EvrV1CoreIrqCtrl.vhd
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-06-11
-- Last update: 2017-03-02
-------------------------------------------------------------------------------
-- Description: 
-------------------------------------------------------------------------------
-- This file is part of 'LCLS1 Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS1 Timing Core', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;

use work.StdRtlPkg.all;
use work.AxiStreamPkg.all;
use work.SsiPkg.all;
use work.AxiLitePkg.all;
use work.AxiLiteMasterPkg.all;

entity EvrV1CoreIrqCtrl is
   generic (
      TPD_G             : time                := 1 ns;
      TIMEOUT_EN_G      : boolean             := false;
      BRAM_EN_G         : boolean             := true;
      FIFO_ADDR_WIDTH_G : positive            := 9;
      AXI_ERROR_RESP_G   : slv(1 downto 0)        := AXI_RESP_SLVERR_C;
      AXIS_CONFIG_G     : AxiStreamConfigType := ssiAxiStreamConfig(4));
   port (
      -- AXI-Lite and 
      axilClk          : in  sl;
      axilRst          : in  sl;
      axilReadMaster   : in  AxiLiteReadMasterType;
      axilReadSlave    : out AxiLiteReadSlaveType;
      axilWriteMaster  : in  AxiLiteWriteMasterType;
      axilWriteSlave   : out AxiLiteWriteSlaveType;
      mAxilReadMaster  : out AxiLiteReadMasterType;
      mAxilReadSlave   : in  AxiLiteReadSlaveType;
      mAxilWriteMaster : out AxiLiteWriteMasterType;
      mAxilWriteSlave  : in  AxiLiteWriteSlaveType;
      mAxisMaster      : out AxiStreamMasterType;
      mAxisSlave       : in  AxiStreamSlaveType;
      -- IRQ Interface
      irqActive        : out sl;
      irqEnable        : in  sl;
      irqReq           : in  sl;
      -- EVR Interface
      evrClk           : in  sl;
      evrRst           : in  sl;
      gtLinkUp         : in  sl;
      gtRxData         : in  slv(15 downto 0);
      gtRxDataK        : in  slv(1 downto 0);
      gtRxDispErr      : in  slv(1 downto 0);
      gtRxDecErr       : in  slv(1 downto 0);
      rxLinkUp         : out sl;
      rxError          : out sl;
      rxData           : out slv(15 downto 0);
      rxDataK          : out slv(1 downto 0));
end EvrV1CoreIrqCtrl;

architecture rtl of EvrV1CoreIrqCtrl is

   constant TIMEOUT_C     : positive            := 156250;  -- 1ms
   constant AXIS_CONFIG_C : AxiStreamConfigType := ssiAxiStreamConfig(4);

   type StateType is (
      IDLE_S,
      IRQ_SET_S,
      IRQ_CLR_S);

   type RegType is record
      timer          : natural range 0 to TIMEOUT_C;
      irqActive      : sl;
      axilReadSlave  : AxiLiteReadSlaveType;
      axilWriteSlave : AxiLiteWriteSlaveType;
      txMaster       : AxiStreamMasterType;
      req            : AxiLiteMasterReqType;
      state          : StateType;
   end record RegType;
   constant REG_INIT_C : RegType := (
      timer          => 0,
      irqActive      => '0',
      axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
      axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C,
      txMaster       => AXI_STREAM_MASTER_INIT_C,
      req            => AXI_LITE_MASTER_REQ_INIT_C,
      state          => IDLE_S);

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal dataValid : sl;
   signal linkup    : sl;
   signal cnt       : slv(23 downto 0);

   signal txSlave : AxiStreamSlaveType;
   signal ack     : AxiLiteMasterAckType;

begin

   rxError   <= not(dataValid) and linkUp;
   dataValid <= not (uOr(gtRxDispErr) or uOr(gtRxDecErr));

   process(evrClk)
   begin
      if rising_edge(evrClk) then
         if (evrRst = '1') or (gtLinkUp = '0') or (dataValid = '0') then
            cnt     <= (others => '0') after TPD_G;
            linkup  <= '0'             after TPD_G;
            rxError <= '0'             after TPD_G;
            rxData  <= (others => '0') after TPD_G;
            rxDataK <= (others => '0') after TPD_G;
            if cnt = x"FFFFFF" then
               linkup  <= '1'       after TPD_G;
               rxData  <= gtRxData  after TPD_G;
               rxDataK <= gtRxDataK after TPD_G;
            else
               cnt <= cnt + 1 after TPD_G;
            end if;
         end if;
      end if;
   end process;

   comb : process (axilReadMaster, axilRst, axilWriteMaster, irqEnable, irqReq,
                   r, txSlave) is
      variable v      : RegType;
      variable axilEp : AxiLiteEndpointType;
   begin
      -- Latch the current value
      v := r;

      -- Reset the flags
      if txSlave.tReady = '1' then
         v.txMaster.tValid := '0';
         v.txMaster.tLast  := '0';
         v.txMaster.tUser  := (others => '0');
         v.txMaster.tKeep  := x"000F";  -- --32-bit interface
      end if;

      -- State Machine
      case r.state is
         ----------------------------------------------------------------------
         when IDLE_S =>
            -- Reset the flag
            v.irqActive := '0';
            -- Check for interrupt
            if (irqReq = '1') and (irqEnable = '1') then
               -- Set the flag
               v.irqActive := '1';
               -- Next state
               v.state     := IRQ_SET_S;
            end if;
         ----------------------------------------------------------------------
         when IRQ_SET_S =>
            -- Check if ready to move data
            if (v.txMaster.tValid = '0') then
               -- Send the IRQ message
               v.txMaster.tValid := '1';
               v.txMaster.tLast  := '1';
               v.txMaster.tData  := (others => '0');
               ssiSetUserSof(AXIS_CONFIG_C, v.txMaster, '1');
               -- Next state
               v.state           := IRQ_CLR_S;
            end if;
         ----------------------------------------------------------------------
         when IRQ_CLR_S =>
            -- Check if IRQ has been serviced or 1 ms timeout
            if (irqReq = '0') or (irqEnable = '0') or (r.timer = TIMEOUT_C) then
               -- Reset the counter
               v.timer := 0;
               if (r.timer = TIMEOUT_C) then
                  -- Next state
                  v.state := IRQ_SET_S;
               else
                  -- Next state
                  v.state := IDLE_S;
               end if;
            elsif (TIMEOUT_EN_G = true) then
               -- Increment the counter
               v.timer := r.timer + 1;
            end if;
      ----------------------------------------------------------------------
      end case;

      ------------------------------      
      -- Slave AXI-Lite Transactions
      ------------------------------      
      -- Determine the transaction type
      axiSlaveWaitTxn(axilEp, axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave);
      -- Close out the transaction
      axiSlaveDefault(axilEp, v.axilWriteSlave, v.axilReadSlave, AXI_ERROR_RESP_G);

      -- Reset
      if (axilRst = '1') then
         v := REG_INIT_C;
      end if;

      -- Register the variable for next clock cycle
      rin <= v;

      -- Outputs 
      axilReadSlave  <= r.axilReadSlave;
      axilWriteSlave <= r.axilWriteSlave;

   end process comb;

   seq : process (axilClk) is
   begin
      if rising_edge(axilClk) then
         r <= rin after TPD_G;
      end if;
   end process seq;

   U_AxiLiteMaster : entity work.AxiLiteMaster
      generic map (
         TPD_G => TPD_G)
      port map (
         req             => r.req,
         ack             => ack,
         axilClk         => axilClk,
         axilRst         => axilRst,
         axilWriteMaster => mAxilWriteMaster,
         axilWriteSlave  => mAxilWriteSlave,
         axilReadMaster  => mAxilReadMaster,
         axilReadSlave   => mAxilReadSlave);

   TX_FIFO : entity work.AxiStreamFifoV2
      generic map (
         -- General Configurations
         TPD_G               => TPD_G,
         SLAVE_READY_EN_G    => true,
         VALID_THOLD_G       => 1,
         -- FIFO configurations
         BRAM_EN_G           => BRAM_EN_G,
         GEN_SYNC_FIFO_G     => true,
         FIFO_ADDR_WIDTH_G   => FIFO_ADDR_WIDTH_G,
         -- AXI Stream Port Configurations
         SLAVE_AXI_CONFIG_G  => AXIS_CONFIG_C,
         MASTER_AXI_CONFIG_G => AXIS_CONFIG_G)
      port map (
         -- Slave Port
         sAxisClk    => axilClk,
         sAxisRst    => axilRst,
         sAxisMaster => r.txMaster,
         sAxisSlave  => txSlave,
         -- Master Port
         mAxisClk    => axilClk,
         mAxisRst    => axilRst,
         mAxisMaster => mAxisMaster,
         mAxisSlave  => mAxisSlave);

end rtl;
