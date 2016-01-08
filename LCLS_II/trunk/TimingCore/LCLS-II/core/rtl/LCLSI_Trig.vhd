-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : LCLSI_Trig.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2015/09/15
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Simple pulse generation from LCLS-I eventcode stream.
-------------------------------------------------------------------------------
-- This file is part of 'LCLS2 Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS2 Timing Core', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------
LIBRARY ieee;
use work.all;

USE ieee.std_logic_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
use work.StdRtlPkg.all;
use work.TPGPkg.all;

entity LCLSI_Trig is
  
  port (
    rst    : in  sl;
    clk    : in  sl;
    config : in  L1TrigConfig;
    evcode : in  slv(7 downto 0);
    valid  : in  sl;
    trigO  : out sl );

end LCLSI_Trig;

architecture rtl of LCLSI_Trig is

  type TrigState is (IDLE, DELAYED, ACTIVE);
  
  type RegType is record
                    state  : TrigState;
                    delayc : slv(31 downto 0);
                    widthc : slv( 7 downto 0);
                  end record;
  constant REG_INIT_C : RegType := (
    state  => IDLE,
    delayc => (others=>'0'),
    widthc => (others=>'0') );

  constant WIDTH_C : slv(7 downto 0) := x"0F";
  
  signal r : RegType := REG_INIT_C;
  signal rin : RegType;

  attribute mark_debug : string;
  attribute mark_debug of r : signal is "true";

begin  -- rtl

  trigO <= '1' when r.state=ACTIVE else '0';
  
  comb: process (config, rst, evcode, valid, r)
    variable v : RegType;
  begin  -- process comb
    v := r;

    case r.state is
      when IDLE =>
        if (valid='1' and evcode=config.evcode) then
          v.state  := DELAYED;
          v.delayc := config.delay;
        end if;
      when DELAYED =>
        v.delayc := r.delayc-1;
        if r.delayc=x"00000000" then
          v.state  := ACTIVE;
          v.widthc := WIDTH_C;
        end if;
      when ACTIVE =>
        v.widthc := r.widthc-1;
        if r.widthc=x"00" then
          v.state := IDLE;
        end if;
      when others => null;
    end case;

    if rst='1' then
      v := REG_INIT_C;
    end if;
    
    rin <= v;
  end process comb;

  process (clk)
  begin  -- process
    if rising_edge(clk) then
      r <= rin;
    end if;
  end process;
end rtl;
