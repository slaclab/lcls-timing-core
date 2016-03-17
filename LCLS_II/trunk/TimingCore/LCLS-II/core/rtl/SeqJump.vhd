-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : SeqJump.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2016-03-09
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Calculates automated jumps in sequencer instruction RAM.
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
use work.TPGPkg.all;
use work.StdRtlPkg.all;

entity SeqJump is
  port ( 
      -- Clock and reset
      clk                : in  sl;
      rst                : in  sl;
      config             : in  TPGJumpConfigType;
      manReset           : in  sl;
      manAddr            : in  SeqAddrType;
      triggerI           : in  slv(NTRIGGERSIN-1 downto 0);
      bcsFault           : in  slv(BCSWIDTH-1 downto 0);
      mpsFault           : in  slv(4 downto 0);
      jumpRst            : in  sl;
      jumpEn             : out sl;
      jumpAddr           : out SeqAddrType
      );
end SeqJump;

-- Define architecture for top level module
architecture mapping of SeqJump is 

  signal trigEn : slv(NTRIGGERSIN-1 downto 0);
  signal bcsfEn : sl;
  signal bcsEn, manResetQ : sl;
begin

  process (clk, rst, bcsFault)
    variable bcsfd, bcsf : sl;
  begin  -- process
    if noBits(bcsFault,'1') then
      bcsf := '0';
    else
      bcsf := '1';
    end if;
    if rising_edge(clk) then
      if jumpRst='1' then
        trigEn <= triggerI;
        bcsfEn <= bcsf and not bcsfd;
      else
        trigEn <= trigEn or triggerI;
        bcsfEn <= bcsfEn or (bcsf and not bcsfd);
      end if;
      bcsfd  := bcsf;
    end if;
  end process;

  process (clk, rst, manReset)
    variable manResetQd : sl;
  begin
    if rising_edge(clk) then
      if jumpRst='1' and manResetQd='1' then
        manResetQ <= '0';
      end if;
      manResetQd := manResetQ;
    end if;
    if manReset='1' then
      manResetQ  <= '1';
      manResetQd := '0';
    end if;
  end process;

  bcsEn  <= '1' when (config.bcsEn='1' and bcsfEn='1') else
            '0';
  jumpEn <= manResetQ or bcsEn;

  jumpAddr <= manAddr        when (manResetQ='1') else
              config.bcsJump when (bcsEn='1') else
              (others=>'0');
  
end mapping;
