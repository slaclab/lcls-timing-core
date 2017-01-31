-------------------------------------------------------------------------------
-- Title      : SyncDelay
-------------------------------------------------------------------------------
-- File       : SyncDelay.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2016-09-14
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Generates six single clk pulses at a prescaled rate of sysClk.
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
use work.StdRtlPkg.all;

library UNISIM;
use UNISIM.VCOMPONENTS.ALL;

entity SyncDelay is
   port ( 
      -- Clock and reset
      clk                : in  sl;
      rst                : in  sl;
      enable             : in  sl;
      delay              : in  slv(15 downto 0);
      ivalid             : in  sl;
      istrobe            : in  sl;
      ovalid             : out sl;
      ostrobe            : out sl );
end SyncDelay;


-- Define architecture for top level module
architecture rtl of SyncDelay is 

  type RegType is record
    count  : slv(delay'range);
    ivalid : sl;
    ovalid : sl;
    latch  : sl;
    ostrobe: sl;
  end record;
  constant REG_INIT_C : RegType := (
    count  => (others=>'0'),
    ivalid => '0',
    ovalid => '0',
    latch  => '0',
    ostrobe=> '0' );

  signal r : RegType := REG_INIT_C;
  signal rin : RegType;
  
begin

  ovalid  <= r.ovalid;
  ostrobe <= r.ostrobe;
  
  comb: process (r, rst, delay, ivalid, istrobe, enable) is
    variable v : RegType;
  begin
    v := r;
    v.ovalid  := '0';
    v.ostrobe := '0';
    
    if istrobe='1' then
      v.count := (others=>'0');
      v.latch := '1';
      v.ivalid:= ivalid;
    elsif (enable='1' and r.latch='1') then
      if (r.count>=delay) then
        v.count   := (others=>'0');
        v.ostrobe := '1';
        v.ovalid  := r.ivalid;
        v.latch   := '0';
        v.ivalid  := '0';
      else
        v.count := r.count+1;
      end if;
    end if;

    if rst='1' then
      v := REG_INIT_C;
    end if;

    rin <= v;
  end process;

  seq: process(clk) is
  begin
    if rising_edge(clk) then
      r <= rin;
    end if;
  end process;
  
end rtl;
