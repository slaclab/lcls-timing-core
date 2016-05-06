-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2Core.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2016-04-22
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
use work.AxiStreamPkg.all;
use work.TimingPkg.all;
use work.EvrV2Pkg.all;

entity EvrV2EventDma is
  generic (
    TPD_G      : time    := 1 ns;
    CHANNELS_C : integer := 1 );
  port (
    clk        :  in sl;
    rst        :  in sl;
    strobe     :  in sl;
    eventSel   :  in slv(CHANNELS_C-1 downto 0);
    eventData  :  in TimingMessageType;
    dmaCntl    :  in EvrV2DmaControlType;
    dmaData    : out EvrV2DmaDataType );
end EvrV2EventDma;

architecture mapping of EvrV2EventDma is

--  constant VEC_SZ : integer := 32*((TIMING_MESSAGE_BITS_C-256+31)/32+2);
  constant VEC_SZ : integer := 32*((TIMING_MESSAGE_BITS_C-256+31)/32+2);
  constant WORDS : slv(31 downto 0) := toSlv(VEC_SZ/32,32);
  
  type RegType is record
    channels : slv(15 downto 0);
    strobe   : slv(VEC_SZ/32-1 downto 0);
    last     : sl;
    dataOut  : slv(VEC_SZ-1 downto 0);
  end record;

  constant REG_TYPE_INIT_C : RegType := (
    channels => (others=>'0'),
    strobe   => (others=>'0'),
    last     => '0',
    dataOut  => (others=>'0'));

  signal r   : RegType := REG_TYPE_INIT_C;
  signal rin : RegType;

  signal utestData : slv(23 downto 0);
  
begin  -- mapping

  dmaData.tValid <= r.strobe(0);
  dmaData.tLast  <= r.strobe(0) and not r.strobe(1);
  dmaData.tData  <= r.dataOut(31 downto 0);

  process (r, rst, strobe, eventSel, eventData)
    variable v : RegType;
  begin  -- process
    v := r;

    v.last     := '0';
    v.channels(eventSel'range) := r.channels(eventSel'range) or eventSel;
    v.dataOut  := x"00000000" & r.dataOut(r.dataOut'left downto 32);
    v.strobe   := '0' & r.strobe(r.strobe'left downto 1);
    
    if strobe='1' and uOr(r.channels)='1' then
      v.strobe  := (others=>'1');
      v.dataOut := toSlvNoBsa(eventData) &
                   r.channels &
                   EVRV2_EVENT_TAG &
                   toSlv(r.strobe'length,32);
    end if;

    if rst='1' then
      v.channels := (others=>'0');
    end if;

    rin <= v;
  end process;

  process (clk)
  begin  -- process
    if rising_edge(clk) then
      r <= rin;
    end if;
  end process;
end mapping;
