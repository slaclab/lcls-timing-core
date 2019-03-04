-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2ChannelReg.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2017-12-03
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
use work.TimingPkg.all;
use work.EvrV2Pkg.all;

entity EvrV2ChannelReg is
  generic (
    TPD_G        : time    := 1 ns;
    NCHANNELS_G  : integer := 1;
    DMA_ENABLE_G : boolean := false );
  port (
    -- AXI-Lite and IRQ Interface
    axiClk              : in  sl;
    axiRst              : in  sl;
    axilWriteMaster     : in  AxiLiteWriteMasterType;
    axilWriteSlave      : out AxiLiteWriteSlaveType;
    axilReadMaster      : in  AxiLiteReadMasterType;
    axilReadSlave       : out AxiLiteReadSlaveType;
    -- configuration
    channelConfig       : out EvrV2ChannelConfigArray(NCHANNELS_G-1 downto 0);
    -- status
    eventCount          : in  Slv32Array(NCHANNELS_G-1 downto 0) );
end EvrV2ChannelReg;

architecture mapping of EvrV2ChannelReg is

  type RegType is record
    axilReadSlave  : AxiLiteReadSlaveType;
    axilWriteSlave : AxiLiteWriteSlaveType;
    channelConfig  : EvrV2ChannelConfigArray(NCHANNELS_G-1 downto 0);
  end record;
  constant REG_INIT_C : RegType := (
    axilReadSlave  => AXI_LITE_READ_SLAVE_INIT_C,
    axilWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C,
    channelConfig  => (others=>EVRV2_CHANNEL_CONFIG_INIT_C) );

  signal r   : RegType := REG_INIT_C;
  signal rin : RegType;

begin  -- mapping

  channelConfig  <= r.channelConfig;
  axilReadSlave  <= r.axilReadSlave;
  axilWriteSlave <= r.axilWriteSlave;

  process (axiClk)
  begin  -- process
    if rising_edge(axiClk) then
      r <= rin;
    end if;
  end process;

  process (r,axilReadMaster,axilWriteMaster,axiRst,eventCount)
    variable v : RegType;
    variable axilStatus : AxiLiteStatusType;
    procedure axilSlaveRegisterR (addr : in slv; reg : in slv) is
    begin
      axiSlaveRegister(axilReadMaster, v.axilReadSlave, axilStatus, addr, 0, reg);
    end procedure;
    procedure axilSlaveRegisterR (addr : in slv; reg : in slv; ack : out sl) is
    begin
      if (axilStatus.readEnable = '1') then
         if (std_match(axilReadMaster.araddr(addr'length-1 downto 0), addr)) then
            v.axilReadSlave.rdata(reg'range) := reg;
            axiSlaveReadResponse(v.axilReadSlave);
            ack := '1';
         end if;
      end if;
    end procedure;
    procedure axilSlaveRegisterW (addr : in slv; offset : in integer; reg : inout slv) is
    begin
      axiSlaveRegister(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus, addr, offset, reg);
    end procedure;
    procedure axilSlaveRegisterW (addr : in slv; offset : in integer; reg : inout sl) is
    begin
      axiSlaveRegister(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus, addr, offset, reg);
    end procedure;
    procedure axilSlaveDefault (
      axilResp : in slv(1 downto 0)) is
    begin
      axiSlaveDefault(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus, axilResp);
    end procedure;
  begin  -- process
    v  := r;
    axiSlaveWaitTxn(axilWriteMaster, axilReadMaster, v.axilWriteSlave, v.axilReadSlave, axilStatus);
    for i in 0 to NCHANNELS_G-1 loop
      axilSlaveRegisterW(slv(conv_unsigned(i*256+ 0,17)),  0, v.channelConfig(i).enabled);
      axilSlaveRegisterW(slv(conv_unsigned(i*256+ 4,17)),  0, v.channelConfig(i).rateSel);
      axilSlaveRegisterW(slv(conv_unsigned(i*256+ 4,17)), 13, v.channelConfig(i).destSel);
      axilSlaveRegisterR(slv(conv_unsigned(i*256+ 8,17)),     eventCount(i));

      if DMA_ENABLE_G then
        axilSlaveRegisterW(slv(conv_unsigned(i*256+ 0,17)),  1, v.channelConfig(i).bsaEnabled);
        axilSlaveRegisterW(slv(conv_unsigned(i*256+ 0,17)),  2, v.channelConfig(i).dmaEnabled);
        axilSlaveRegisterW(slv(conv_unsigned(i*256+12,17)),  0, v.channelConfig(i).bsaActiveDelay);
        axilSlaveRegisterW(slv(conv_unsigned(i*256+12,17)), 20, v.channelConfig(i).bsaActiveSetup);
        axilSlaveRegisterW(slv(conv_unsigned(i*256+16,17)),  0, v.channelConfig(i).bsaActiveWidth);
      end if;
    end loop;
    
    axilSlaveDefault(AXI_RESP_OK_C);
    rin <= v;
  end process;

end mapping;
