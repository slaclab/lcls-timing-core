-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : GthRxAlignCheck.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-08-29
-- Last update: 2016-08-30
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

use work.StdRtlPkg.all;

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
    drpClk          : in  sl;
    drpRst          : in  sl;
    drpRdy          : in  sl;
    drpEn           : out sl;
    drpWe           : out sl;
    drpUsrRst       : out sl;
    drpAddr         : out slv(ADDR_WIDTH_G-1 downto 0);
    drpDi           : out slv(DATA_WIDTH_G-1 downto 0);
    drpDo           : in  slv(DATA_WIDTH_G-1 downto 0));      
end entity GthRxAlignCheck;

architecture rtl of GthRxAlignCheck is

  constant LOCK_VALUE : integer := 0;
  
  type StateType is (
    RESET_S,
    READ_S,
    ACK_S,
    LOCKED_S );
  
  type RegType is record
    state : StateType;
    drpEn : sl;
    rst   : sl;
  end record;
  constant REG_INIT_C : RegType := (
    state => READ_S,
    drpEn => '0',
    rst   => '1' );

  signal r    : RegType := REG_INIT_C;
  signal r_in : RegType;

begin

  drpAddr   <= toSlv(336,drpAddr'length); -- COMMA_ALIGN_LATENCY
  drpDi     <= (others=>'0');
  drpWe     <= '0';
  drpUsrRst <= '0';
  drpEn     <= r.drpEn;
  resetOut  <= r.rst;
  
  process( r, resetIn, resetDone, resetErr, drpRdy, drpDo ) is
    variable v : RegType;
  begin
    v := r;
    v.rst     := '0';
    v.drpEn   := '0';

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
          if drpDo(6 downto 0)=toSlv(LOCK_VALUE,7) then
            v.state := LOCKED_S;
          else
            v.rst   := '1';
            v.state := RESET_S;
          end if;
        end if;
      when LOCKED_S => null;
    end case;

    if drpRst='1' or resetIn='1' or resetErr='1' then
      v.rst   := '1';
      v.state := RESET_S;
    end if;
    
    r_in <= v;
  end process;

  process (drpClk) is
  begin
    if rising_edge(drpClk) then
      r <= r_in;
    end if;
  end process;
end rtl;
