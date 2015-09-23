-------------------------------------------------------------------------------
-- Title      : ACDivider
-------------------------------------------------------------------------------
-- File       : ACDivider.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2015/09/15
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Generates six single clk pulses at a prescaled rate of sysClk.
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

entity ACDivider is
   generic ( Width    : integer := 4 );
   port ( 
      -- Clock and reset
      sysClk             : in  std_logic;
      sysReset           : in  std_logic;
      enable             : in  std_logic;
      clear              : in  std_logic;
      repulse            : in  std_logic;
      divisor            : in  std_logic_vector(Width-1 downto 0);
      trigO              : out std_logic
      );
end ACDivider;


-- Define architecture for top level module
architecture ACDivider of ACDivider is 

  component Divider
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
  end component;

  signal trig     : std_logic;
  signal enabled  : std_logic;
  signal count    : std_logic_vector(2 downto 0);

  -- Register delay for simulation
  constant tpd:time := 0.5 ns;
  
begin

  U_Divider : Divider
    generic map ( Width => Width )
    port map ( sysClk   => sysClk,
               sysReset => sysReset,
               enable   => enable,
               clear    => clear,
               divisor  => divisor,
               trigO    => trig );

  process (sysClk, sysReset)
  begin  -- process
    if sysReset = '1' then
      count     <= "101";
      enabled   <= '0';
    elsif rising_edge(sysClk) then
      if trig='1' then
        count   <= "000" after tpd;
        enabled <= '0' after tpd;
      elsif repulse='1' and count /= "101" then
        count   <= count+1 after tpd;
        enabled <= '1' after tpd;
      elsif clear='1' then
        enabled <= '0' after tpd;
      end if;
    end if;
  end process;

  trigO <= '1' when (trig='1' or enabled='1') else '0';
  
end ACDivider;
