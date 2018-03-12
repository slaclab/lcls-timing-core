-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2TriggerReg.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2017-04-27
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
use ieee.NUMERIC_STD.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;
use work.EvrV2Pkg.all;

entity EvrV2TriggerReg is
  generic (
    TPD_G      : time    := 1 ns;
    USE_TAP_C  : boolean := false );
  port (
    -- AXI-Lite and IRQ Interface
    axiClk              : in  sl;
    axiRst              : in  sl;
    axilWriteMaster     : in  AxiLiteWriteMasterType;
    axilWriteSlave      : out AxiLiteWriteSlaveType;
    axilReadMaster      : in  AxiLiteReadMasterType;
    axilReadSlave       : out AxiLiteReadSlaveType;
    -- configuration
    triggerConfig       : out EvrV2TriggerConfigType;
    delay_rd            : in  slv(5 downto 0) := (others=>'0') );
end EvrV2TriggerReg;

architecture mapping of EvrV2TriggerReg is

  type RegType is record
    axilReadSlave  : AxiLiteReadSlaveType;
    axilWriteSlave : AxiLiteWriteSlaveType;
    triggerConfig  : EvrV2TriggerConfigType;
    loadShift      : slv(3 downto 0);
  end record;
  constant REG_INIT_C : RegType := (
    axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
    axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C,
    triggerConfig  => EVRV2_TRIGGER_CONFIG_INIT_C,
    loadShift      => (others=>'0') );
  signal r   : RegType := REG_INIT_C;
  signal rin : RegType;

begin  -- mapping

  triggerConfig  <= r.triggerConfig;
  axilReadSlave  <= r.axilReadSlave;
  axilWriteSlave <= r.axilWriteSlave;

  process (axiClk)
  begin  -- process
    if rising_edge(axiClk) then
      r <= rin;
    end if;
  end process;

  process (r,axilReadMaster,axilWriteMaster,axiRst,delay_rd)
    variable v  : RegType;
    variable ep : AxiLiteEndPointType;

    procedure axilSlaveRegisterR (addr : in slv; offset : in integer; reg : in slv) is
    begin
      axiSlaveRegisterR(ep, addr, offset, reg);
    end procedure;
    procedure axilSlaveRegisterW (addr : in slv; offset : in integer; reg : inout slv) is
    begin
      axiSlaveRegister(ep, addr, offset, reg);
    end procedure;
    procedure axilSlaveRegisterW (addr : in slv; offset : in integer; reg : inout sl) is
    begin
      axiSlaveRegister(ep, addr, offset, reg);
    end procedure;
    procedure axilSlaveDefault (
      axilResp : in slv(1 downto 0)) is
    begin
      axiSlaveDefault(ep, v.axilWriteSlave, v.axilReadSlave, axilResp);
    end procedure;
  begin  -- process
    v  := r;
    axiSlaveWaitTxn(ep, axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave);

    axilSlaveRegisterW(slv(conv_unsigned(0,9)),   0, v.triggerConfig.channels);
    axilSlaveRegisterW(slv(conv_unsigned(0,9)),  16, v.triggerConfig.polarity);
    axilSlaveRegisterW(slv(conv_unsigned(0,9)),  31, v.triggerConfig.enabled);
    axilSlaveRegisterW(slv(conv_unsigned(4,9)),   0, v.triggerConfig.delay);
    axilSlaveRegisterW(slv(conv_unsigned(8,9)),   0, v.triggerConfig.width);

    if USE_TAP_C then
      --  Special handling of delay tap
      v.triggerConfig.loadTap := r.loadShift(3);
      v.loadShift := r.loadShift(2 downto 0) & '0';
      axiWrDetect   (ep, slv(conv_unsigned(12,9)), v.loadShift(0));
      axilSlaveRegisterW(slv(conv_unsigned(12,9)), 0, v.triggerConfig.delayTap);
      axilSlaveRegisterR(slv(conv_unsigned(12,9)),16, delay_rd);
    end if;
    
    axilSlaveDefault(AXI_RESP_OK_C);
    rin <= v;
  end process;

end mapping;
