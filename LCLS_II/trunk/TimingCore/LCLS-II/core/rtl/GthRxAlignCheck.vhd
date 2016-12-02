-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : GthRxAlignCheck.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-08-29
-- Last update: 2016-12-02
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
    locked          : out sl;
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
    RSTDONE_S,
    READ_S,
    ACK_S,
    LOCKED_S );
  
  type RegType is record
    state : StateType;
    drpEn : sl;
    locked: sl;
    rst   : sl;
    rstlen: slv(3 downto 0);
    rstcnt: slv(3 downto 0);
    tgt   : slv(6 downto 0);
    last  : slv(6 downto 0);
    sample: Slv16Array(127 downto 0);
    axiWriteSlave : AxiLiteWriteSlaveType;
    axiReadSlave  : AxiLiteReadSlaveType;
  end record;
  constant REG_INIT_C : RegType := (
    state => READ_S,
    drpEn => '0',
    locked=> '0',
    rst   => '1',
    rstlen=> toSlv(3,4),
    rstcnt=> toSlv(0,4),
    tgt   => toSlv(LOCK_VALUE,7),
    last  => toSlv(0,7),
    sample=> (others=>(others=>'0')),
    axiWriteSlave => AXI_LITE_WRITE_SLAVE_INIT_C,
    axiReadSlave  => AXI_LITE_READ_SLAVE_INIT_C );

  signal r    : RegType := REG_INIT_C;
  signal r_in : RegType;

  component ila_0
    port ( clk : in sl;
           probe0 : in slv(255 downto 0) );
  end component;
  
begin

  locked        <= r.locked;
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
    v.locked  := '0';
    
    -- Determine the transaction type
    axiSlaveWaitTxn(axiWriteMaster, axiReadMaster, v.axiWriteSlave, v.axiReadSlave, axiStatus);

    for i in 0 to 127 loop
      axiSlaveRegister(axiReadMaster, v.axiReadSlave, axiStatus, toSlv(4*(i/2),9), 16*(i mod 2), v.sample(i));
    end loop;
    axiSlaveRegister(axiWriteMaster, axiReadMaster, v.axiWriteSlave, v.axiReadSlave, axiStatus, toSlv(256,9), 0, v.tgt);
    axiSlaveRegister(axiWriteMaster, axiReadMaster, v.axiWriteSlave, v.axiReadSlave, axiStatus, toSlv(256,9),16, v.rstlen);
    axiSlaveRegister(axiReadMaster, v.axiReadSlave, axiStatus, toSlv(260,9), 0, v.last);

    axiSlaveDefault(axiWriteMaster, axiReadMaster, v.axiWriteSlave, v.axiReadSlave, axiStatus, AXI_RESP_OK_C);
    
    case r.state is
      when RESET_S =>
        v.rst := '1';
        if r.rstcnt=r.rstlen then
          v.state := RSTDONE_S;
        else
          v.rstcnt := r.rstcnt+1;
        end if;
      when RSTDONE_S =>
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
          i := conv_integer(drpDo(6 downto 0));
          v.sample(i) := r.sample(i)+1;
          v.last      := drpDo;
          if drpDo(6 downto 0)=r.tgt then
            v.state := LOCKED_S;
          else
            v.rst   := '1';
            v.rstcnt:= (others=>'0');
            v.state := RESET_S;
          end if;
        end if;
      when LOCKED_S => v.locked := '1';
    end case;

    if axiRst='1' or resetIn='1' or resetErr='1' then
      v.rst   := '1';
      v.rstcnt:= (others=>'0');
      v.state := RESET_S;
    end if;

    if (axiStatus.writeEnable='1' and std_match(axiWriteMaster.awaddr(8 downto 0),toSlv(256,9))) then
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
