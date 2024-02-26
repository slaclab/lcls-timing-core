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

library lcls_timing_core;
use lcls_timing_core.EvrV2Pkg.all;

entity EvrV2TrigReg is
   generic (
      TPD_G      : time    := 1 ns;
      EVR_CARD_G : boolean := false;  -- false = packs registers in tight 256B for small BAR0 applications, true = groups registers in 4kB boundary to "virtualize" the channels allowing separate processes to memory map the register space for their dedicated channels.
      TRIGGERS_C : integer := 1;
      USE_TAP_C  : boolean := false);
   port (
      -- AXI-Lite and IRQ Interface
      axiClk          : in  sl;
      axiRst          : in  sl;
      axilWriteMaster : in  AxiLiteWriteMasterType;
      axilWriteSlave  : out AxiLiteWriteSlaveType;
      axilReadMaster  : in  AxiLiteReadMasterType;
      axilReadSlave   : out AxiLiteReadSlaveType;
      -- configuration
      triggerConfig   : out EvrV2TriggerConfigArray(TRIGGERS_C-1 downto 0);
      delay_rd        : in  Slv6Array(TRIGGERS_C-1 downto 0) := (others => "000000"));
end EvrV2TrigReg;

architecture rtl of EvrV2TrigReg is

   constant GRP_C    : positive := ite(EVR_CARD_G, 4096, 256);
   constant STRIDE_C : positive := bitSize(TRIGGERS_C*GRP_C-1);

   type RegType is record
      axilReadSlave  : AxiLiteReadSlaveType;
      axilWriteSlave : AxiLiteWriteSlaveType;
      triggerConfig  : EvrV2TriggerConfigArray(TRIGGERS_C-1 downto 0);
      loadShift      : Slv4Array(TRIGGERS_C-1 downto 0);
   end record;
   constant REG_INIT_C : RegType := (
      axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
      axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C,
      triggerConfig  => (others => EVRV2_TRIGGER_CONFIG_INIT_C),
      loadShift      => (others => (others => '0')));

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

begin

   comb : process (axiRst, axilReadMaster, axilWriteMaster, delay_rd, r)
      variable v      : RegType;
      variable axilEp : AxiLiteEndpointType;
      variable i      : natural;
   begin
      -- Latch the current value
      v := r;

      -- Determine the transaction type
      axiSlaveWaitTxn(axilEp, axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave);


      -- Loop through the channels
      for i in 0 to TRIGGERS_C-1 loop
         axiSlaveRegister(axilEp, toSlv(i*GRP_C + 0, STRIDE_C), 0, v.triggerConfig(i).channel);
         axiSlaveRegister(axilEp, toSlv(i*GRP_C + 0, STRIDE_C), 16, v.triggerConfig(i).polarity);
         axiSlaveRegister(axilEp, toSlv(i*GRP_C + 0, STRIDE_C), 28, v.triggerConfig(i).complEn);
         axiSlaveRegister(axilEp, toSlv(i*GRP_C + 0, STRIDE_C), 29, v.triggerConfig(i).complOp);
         axiSlaveRegister(axilEp, toSlv(i*GRP_C + 0, STRIDE_C), 31, v.triggerConfig(i).enabled);
         axiSlaveRegister(axilEp, toSlv(i*GRP_C + 4, STRIDE_C), 0, v.triggerConfig(i).delay);
         axiSlaveRegister(axilEp, toSlv(i*GRP_C + 8, STRIDE_C), 0, v.triggerConfig(i).width);

         --  Special handling of delay tap
         if USE_TAP_C then

            -- Shift Register
            v.triggerConfig(i).loadTap := r.loadShift(i)(3);
            v.loadShift(i)             := r.loadShift(i)(2 downto 0) & '0';

            axiSlaveRegister (axilEp, toSlv(i*GRP_C + 12, STRIDE_C), 0, v.triggerConfig(i).delayTap);
            axiSlaveRegisterR(axilEp, toSlv(i*GRP_C + 12, STRIDE_C),16, delay_rd(i));
            axiWrDetect      (axilEp, toSlv(i*GRP_C + 12, STRIDE_C), v.loadShift(i)(0));

         end if;

      end loop;

      -- Close the transaction
      axiSlaveDefault(axilEp, v.axilWriteSlave, v.axilReadSlave, AXI_RESP_OK_C);

      -- Outputs
      axilReadSlave  <= r.axilReadSlave;
      axilWriteSlave <= r.axilWriteSlave;
      triggerConfig  <= r.triggerConfig;

      -- Reset
      if (axiRst = '1') then
         v := REG_INIT_C;
      end if;

      -- Register the variable for next clock cycle
      rin <= v;

   end process comb;

   seq : process (axiClk) is
   begin
      if (rising_edge(axiClk)) then
         r <= rin after TPD_G;
      end if;
   end process seq;

end architecture rtl;
