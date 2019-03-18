-------------------------------------------------------------------------------
-- Title      : WordSerializer
-------------------------------------------------------------------------------
-- File       : WordSerializer.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2019-02-18
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Generates a 16b serial stream of the LCLS-II timing message.
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
use work.StdRtlPkg.all;
use work.TimingPkg.all;

entity WordSerializer is
   generic ( NWORDS_G : integer := 0 );
   port (
      -- Clock and reset
      txClk      : in  sl;
      txRst      : in  sl;
      fiducial   : in  sl;
      words      : in  slv(16*NWORDS_G-1 downto 0);
      ready      : in  sl;
      advance    : in  sl;
      stream     : out TimingSerialType
      );
end WordSerializer;

-- Define architecture for top level module
architecture mapping of WordSerializer is

   type RegType is record
      word_stream  : Slv16Array(words'range);
      word_cnt     : slv(bitSize(NWORDS_G)-1 downto 0);
      ready        : sl;
   end record;
   constant REG_INIT_C : RegType := (
      word_stream  => (others => x"0000"),
      word_cnt     => (others => '0'),
      ready        => '0');

  signal r : RegType := REG_INIT_C;
  signal rin : RegType;
  
  attribute use_dsp48      : string;
  attribute use_dsp48 of r : signal is "yes";   
  
begin

  stream.ready  <= r.ready;
  stream.data   <= r.word_stream(0);
  stream.offset <= (others=>'0');
  stream.last   <= '1';
  
  comb: process (r, words, ready, txRst, fiducial, advance)
    variable v    : RegType;
  begin 
    v := r;

    if fiducial='1' then
      --  Latch the timing frame into a shift register
      for i in 0 to NWORDS_G-1 loop
        v.word_stream(i) := words(16*i+15 downto 16*i);
      end loop;
      v.word_cnt    := (others=>'0');
      if ready = '0' then 
        v.ready := '0';
      else
        v.ready := '1';
      end if;
    elsif advance='1' then
      --  Shift out the next word
      v.word_stream  := x"0000" & r.word_stream(r.word_stream'left downto 1);
      if (r.word_cnt=NWORDS_G-1) then
        v.ready := '0';
      else
        v.ready    := '1';
        v.word_cnt := r.word_cnt+1;
      end if;
    end if;

    if txRst='1' then
      v := REG_INIT_C;
    end if;
    
    rin <= v;

  end process;

  process (txClk)
  begin  -- process
    if rising_edge(txClk) then
      r <= rin;
    end if;
  end process;

end mapping;
