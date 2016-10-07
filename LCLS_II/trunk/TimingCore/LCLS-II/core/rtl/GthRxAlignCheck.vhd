-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : GthRxAlignCheck.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-08-29
-- Last update: 2016-10-06
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: AXI-Lite to Xilinx DRP Bridge 
-------------------------------------------------------------------------------
-- This file is part of 'SLAC Firmware Standard Library'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'SLAC Firmware Standard Library', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
use ieee.NUMERIC_STD.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;

entity GthRxAlignCheck is
  generic (
    TIMEOUT_G        : positive               := 4096;
    ADDR_WIDTH_G     : positive range 1 to 32 := 16;
    DATA_WIDTH_G     : positive range 1 to 32 := 16);
  port (
    resetIn         : in  sl;
    resetOut        : out sl;
    resetDone       : in  sl;
    resetErr        : in  sl;
    drpClk          : out sl;
    drpRst          : out sl;
    drpRdy          : in  sl;
    drpEn           : out sl;
    drpWe           : out sl;
    drpUsrRst       : out sl;
    drpAddr         : out slv(ADDR_WIDTH_G-1 downto 0);
    drpDi           : out slv(DATA_WIDTH_G-1 downto 0);
    drpDo           : in  slv(DATA_WIDTH_G-1 downto 0);
    axiClk          : in  sl;
    axiRst          : in  sl;
    axiReadMaster   : in  AxiLiteReadMasterType;
    axiReadSlave    : out AxiLiteReadSlaveType;
    axiWriteMaster  : in  AxiLiteWriteMasterType;
    axiWriteSlave   : out AxiLiteWriteSlaveType );
end entity GthRxAlignCheck;

architecture rtl of GthRxAlignCheck is

  constant LOCK_VALUE : integer := 16;
  
  type StateType is (
    RESET_S,
    READ_S,
    ACK_S,
    LOCKED_S );
  
  type RegType is record
    state : StateType;
    drpEn : sl;
    rst   : sl;
    tgt   : slv(6 downto 0);
    sample: Slv16Array(19 downto 0);
    axiWriteSlave : AxiLiteWriteSlaveType;
    axiReadSlave  : AxiLiteReadSlaveType;
  end record;
  constant REG_INIT_C : RegType := (
    state => READ_S,
    drpEn => '0',
    rst   => '1',
    tgt   => toSlv(LOCK_VALUE,7),
    sample=> (others=>(others=>'0')),
    axiWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C,
    axiReadSlave  => AXI_LITE_READ_SLAVE_INIT_C );

  signal r    : RegType := REG_INIT_C;
  signal r_in : RegType;

begin

  axiReadSlave  <= r.axiReadSlave;
  axiWriteSlave <= r.axiWriteSlave;
  
  drpClk    <= axiClk;
  drpRst    <= axiRst;
  drpAddr   <= toSlv(336,drpAddr'length); -- COMMA_ALIGN_LATENCY
  drpDi     <= (others=>'0');
  drpWe     <= '0';
  drpUsrRst <= '0';
  drpEn     <= r.drpEn;
  resetOut  <= r.rst;
  
  process( r, resetIn, resetDone, resetErr, drpRdy, drpDo, axiWriteMaster, axiReadMaster, axiRst ) is
    variable v : RegType;
    variable axiStatus : AxiLiteStatusType;
    variable i : integer;
  begin
    v := r;
    v.rst     := '0';
    v.drpEn   := '0';

    -- Determine the transaction type
    axiSlaveWaitTxn(axiWriteMaster, axiReadMaster, v.axiWriteSlave, v.axiReadSlave, axiStatus);

    for i in 0 to 19 loop
      axiSlaveRegister(axiReadMaster, v.axiReadSlave, axiStatus, toSlv(4*(i/2),8), 16*(i mod 2), r.sample(i));
    end loop;
    axiSlaveRegister(axiWriteMaster, axiReadMaster, v.axiWriteSlave, v.axiReadSlave, axiStatus, toSlv(40,8), 0, v.tgt);

    axiSlaveDefault(axiWriteMaster, axiReadMaster, v.axiWriteSlave, v.axiReadSlave, axiStatus, AXI_RESP_OK_C);
    
    case r.state is
      when RESET_S =>
        if resetDone='0' then
          v.state := READ_S;
        end if;
      when READ_S =>
        if resetDone='1' then
          v.drpEn := '1';
          v.state := ACK_S;
        end if;
      when ACK_S =>
        if drpRdy='1' then
          i := conv_integer(drpDo(4 downto 0));
          v.sample(i) := r.sample(i)+1;
          if drpDo(6 downto 0)=r.tgt then
            v.state := LOCKED_S;
          else
            v.rst   := '1';
            v.state := RESET_S;
          end if;
        end if;
      when LOCKED_S => null;
    end case;

    if axiRst='1' or resetIn='1' or resetErr='1' then
      v.rst   := '1';
      v.state := RESET_S;
    end if;

    if (axiStatus.writeEnable='1' and std_match(axiReadMaster.araddr(7 downto 0),toSlv(40,8))) then
      v.sample:= (others=>(others=>'0'));
    end if;
    
    r_in <= v;
  end process;

  process (axiClk) is
  begin
    if rising_edge(axiClk) then
      r <= r_in;
    end if;
  end process;
end rtl;
