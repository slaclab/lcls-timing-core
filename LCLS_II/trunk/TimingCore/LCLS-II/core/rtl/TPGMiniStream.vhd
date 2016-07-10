-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TPGMiniStream.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-11-09
-- Last update: 2016-07-09
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
use work.all;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.all;
use work.TPGPkg.all;
use work.StdRtlPkg.all;
use work.TimingPkg.all;

entity TPGMiniStream is
  port (
    config     : in  TPGConfigType;

    txClk      : in  sl;
    txRst      : in  sl;
    txRdy      : in  sl;
    txData     : out slv(15 downto 0);
    txDataK    : out slv(1 downto 0)
    );
end TPGMiniStream;


-- Define architecture for top level module
architecture TPGMiniStream of TPGMiniStream is

  type RegType is record
    pulseId     : slv(31 downto 0);
  end record;
  constant REG_INIT_C : RegType := (
    pulseId     => (others=>'0'));

  signal r   : RegType := REG_INIT_C;
  signal rin : RegType;

  constant SbaseDivisor : slv(18 downto 0) := toSlv(119000000/360,19);
--  constant SbaseDivisor : slv(18 downto 0) := toSlv(1190000/360,19); -- for simulation

  constant FixedRateDiv : IntegerArray(0 to 6) := ( 3, 6, 12, 36, 72, 360, 720 );
  signal fixedRates : slv(FixedRateDiv'range);
  
  signal baseEnable : sl; -- 360Hz
  signal baseEnabled : slv(3 downto 0);
  signal dataBuff   : TimingDataBuffType := TIMING_DATA_BUFF_INIT_C;
  signal eventCodes : slv(255 downto 0)  := (others=>'0');
  signal epicsTime  : slv(63 downto 0);
  
begin

  dataBuff.epicsTime <= epicsTime(63 downto 17) &
                        (r.pulseId(16 downto 0)+toSlv(2,17));
  
  BaseEnableDivider : entity work.Divider
    generic map (
      Width => SbaseDivisor'length)
    port map (
      sysClk   => txClk,
      sysReset => '0',
      enable   => '1',
      clear    => '0',
      divisor  => SbaseDivisor,
      trigO    => baseEnable);

  eventCodes(1) <= '1';
  eventCodes(9) <= '1';
  
  FixedDivider_loop : for i in 0 to FixedRateDiv'length-1 generate
    U_FixedDivider_1 : entity work.Divider
      generic map (
        Width => log2(FixedRateDiv(i)))
      port map (
        sysClk   => txClk,
        sysReset => txRst,
        enable   => baseEnable,
        clear    => '0',
        divisor  => toSlv(FixedRateDiv(i),log2(FixedRateDiv(i))),
        trigO    => eventCodes(40+i));
  end generate FixedDivider_loop;

  U_TSerializer : entity work.TimingStreamTx
    port map ( clk       => txClk,
               rst       => txRst,
               fiducial  => baseEnable,
               dataBuff  => dataBuff,
               pulseId   => r.pulseId,
               eventCodes=> eventCodes,
               data      => txData,
               dataK     => txDataK );

  comb: process (r,baseEnable) is
    variable v : RegType;
  begin
    v := r;

    if baseEnable='1' then
      if r.pulseId=x"0001FFDF" then
        v.pulseId := (others=>'0');
      else
        v.pulseId := r.pulseId+1;
      end if;
    end if;

    rin <= v;
  end process;
         
  seq: process (txClk) is
  begin
    if rising_edge(txClk) then
      r <= rin;
    end if;
  end process;

  U_ClockTime : entity work.ClockTime
    port map (
      step      => toSlv(8,5),
      remainder => toSlv(2,5),
      divisor   => toSlv(5,5),
      rst    => txRst,
      clkA   => txClk,
      wrEnA  => config.timeStampWrEn,
      wrData => config.timeStamp,
      rdData => open,
      clkB   => txClk,
      wrEnB  => baseEnable,
      dataO  => epicsTime);

end TPGMiniStream;
