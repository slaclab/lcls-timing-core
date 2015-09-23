-------------------------------------------------------------------------------
-- Title      : Divider
-------------------------------------------------------------------------------
-- File       : Divider.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2015/09/15
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Generates a single clk pulse at a prescaled rate of sysClk.
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
LIBRARY ieee;
use work.all;

USE ieee.std_logic_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;

entity Divider is
   generic ( Width    : integer := 4 );
   port ( 
      -- Clock and reset
      sysClk             : in  std_logic;
      sysReset           : in  std_logic;
      enable             : in  std_logic;
      clear              : in  std_logic;
      divisor            : in  std_logic_vector(Width-1 downto 0);
      trigO              : out std_logic
      );
end Divider;

-- Define architecture for top level module
architecture Divider of Divider is 

  signal count : std_logic_vector(Width-1 downto 0);

  -- Register delay for simulation
  constant tpd:time := 0.5 ns;
  
begin
  process (sysClk, sysReset)
  begin
    if sysReset='1' then
      count(Width-1 downto 1) <= (others=>'0');
      count(0)  <= '1';
      trigO     <= '0';
    elsif rising_edge(sysClk) then
      if enable='1' then
        if count=divisor then
          count(Width-1 downto 1) <= (others=>'0') after tpd; 
          count(0)  <= '1' after tpd;
          trigO     <= '1' after tpd;
        else
          count     <= count+1 after tpd;
          trigO     <= '0' after tpd;
        end if;
      elsif clear='1' then
        trigO <= '0' after tpd;
      end if;
    end if;
  end process;

end Divider;
