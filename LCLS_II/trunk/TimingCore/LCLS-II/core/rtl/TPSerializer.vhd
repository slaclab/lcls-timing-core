-------------------------------------------------------------------------------
-- Title      : TPSerializer
-------------------------------------------------------------------------------
-- File       : TPSerializer.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2015/09/15
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Generates a 16b serial stream of the LCLS-II timing message.
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
LIBRARY ieee;
use work.all;
USE ieee.std_logic_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
use work.TPGPkg.all;
use work.StdRtlPkg.all;
use work.TimingPkg.all;
use work.CrcPkg.all;
use work.Version.all;

entity TPSerializer is
   port ( 
      -- Clock and reset
      txClk              : in  sl;
      txRst              : in  sl;
      baseEnable         : in  sl;
      msg                : in  TimingMsgType;
      sof                : out sl;
      eof                : out sl;
      txData             : out slv(15 downto 0);
      txDataK            : out slv( 1 downto 0);
      txDataWord         : out slv( 3 downto 0)
      );
end TPSerializer;

-- Define architecture for top level module
architecture TPSerializer of TPSerializer is

  type RegType is record
                    word_stream : slv(TIMING_MSG_BITS_C+15 downto 0);
                    ctrl_stream : slv(TIMING_MSG_WORDS_C   downto 0);
                    word_section: slv(TIMING_MSG_WORDS_C-1 downto 0);
                    sof         : sl;
                    eof         : sl;
                    txData      : slv(15 downto 0);
                    txDataK     : slv( 1 downto 0);
                    txDataWord  : slv( 3 downto 0);
                  end record;

  constant REG_INIT_C : RegType := (
    word_stream => (others=>'0'),
    ctrl_stream => (others=>'0'),
    word_section=> (others=>'0'),
    sof         => '0',
    eof         => '0',
    txData      => (others=>'0'),
    txDataK     => (others=>'0'),
    txDataWord  => x"F" );

  --  A bit for each word that starts a new section
  constant SECTION_INIT_C : slv(TIMING_MSG_WORDS_C-1 downto 0) := "00" & x"01000040004435111";
  signal r : RegType := REG_INIT_C;
  signal rin : RegType;
  signal dataValid : sl;
  signal crc : slv(15 downto 0);
  
begin

  sof        <= r.sof;
  eof        <= r.eof;
  txData     <= r.txData;
  txDataK    <= r.txDataK;
  txDataWord <= r.txDataWord;
  dataValid  <= not rin.txDataK(0);
  
  U_CRC : entity work.Crc16
    generic map ( CRC_INIT_G => x"FFFF" )
    port map ( crcOut       => crc,
               crcClk       => txClk,
               crcDataValid => dataValid,
               crcIn        => rin.txData,
               crcReset     => rin.sof );
  
  comb: process (msg, txRst, baseEnable, r, crc)
    variable v    : RegType;
    variable iword : slv(7 downto 0);
  begin 
    v             := r;

    v.sof         := '0';
    v.eof         := '0';
    
    if baseEnable='1' then
      --  Latch the timing frame into a shift register
      v.word_stream(TIMING_MSG_BITS_C-1 downto 0) := toSlv(msg);
      --  Append the EOF
      v.word_stream(TIMING_MSG_BITS_C+15 downto TIMING_MSG_BITS_C) := D_215_C & K_EOF_C;
      v.ctrl_stream(TIMING_MSG_WORDS_C-1 downto 0) := (others=>'0');
      v.ctrl_stream(v.ctrl_stream'left) := '1';
      v.word_section := SECTION_INIT_C;
      --  Queue the SOF
      v.sof         := '1';
      v.txData      := D_215_C & K_SOF_C;
      v.txDataK     := "01";
      v.txDataWord  := x"F";
    else
      --  Shift out the next word and append the IDLE character
      v.word_stream := D_215_C & K_COM_C & r.word_stream(r.word_stream'left downto 16);
      v.ctrl_stream := '1' & r.ctrl_stream(r.ctrl_stream'left downto 1);
      v.word_section:= '0' & r.word_section(r.word_section'left downto 1);
      v.eof         := r.ctrl_stream(0) and not r.txDataK(0);
      v.txData      := r.word_stream(15 downto 0);
      v.txDataK     := "0" & r.ctrl_stream(0);
      if (r.word_section(0)='1') then
        v.txDataWord := r.txDataWord+1;
      end if;
      if (r.ctrl_stream(1)='1' and r.ctrl_stream(0)='0') then
        v.txData := crc;
      end if;
    end if;

    rin <= v;

  end process;

  process (txClk,txRst)
  begin  -- process
    if txRst='1' then
      r <= REG_INIT_C;
    elsif rising_edge(txClk) then
      r <= rin;
    end if;
  end process;

end TPSerializer;
