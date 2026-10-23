-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Delays a 16b serialized frame
-- Inputs:
--   delay      : number of clocks to delay output
--   fiducial_i : delay start marker
--   advance_i  : accept stream input word (precedes fiducial)
--   stream_i   : input stream; ready tested on fiducial
--   frame_o    : Deserialized output
--   strobe_o   : delay expiring
--   valid_o    : output is valid
--   overflow_o : delay FIFO overrun
-------------------------------------------------------------------------------
-- This file is part of 'LCLS Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the
-- top-level directory of this distribution and at:
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
-- No part of 'LCLS Timing Core', including this file,
-- may be copied, modified, propagated, or distributed except according to
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

library surf;
use surf.StdRtlPkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;

entity TimingSerialDelay is
   generic (
      TPD_G    : time    := 1 ns;
      NWORDS_G : integer := 16;         -- frame length in 16b words
      FDEPTH_G : integer := 100;        -- max depth of frame pipeline
      DEBUG_G  : boolean := false);
   port (
      -- Clock and reset
      clk        : in  sl;
      rst        : in  sl;
      delay      : in  slv(19 downto 0);
      fiducial_i : in  sl;
      advance_i  : in  sl;
      stream_i   : in  TimingSerialType;
      frame_o    : out slv(16*NWORDS_G-1 downto 0);
      strobe_o   : out sl;
      valid_o    : out sl;
      overflow_o : out sl);
end TimingSerialDelay;

-- Define architecture for top level module
architecture TimingSerialDelay of TimingSerialDelay is

   constant COUNT_WIDTH_C : integer := 20;
   constant ADDR_WIDTH_C : integer := log2((NWORDS_G+1)*FDEPTH_G);
   constant START_BIT_C : integer := 16;
   constant STOP_BIT_C  : integer := 17;

   type WrStateType is (WR_IDLE_S, WR_MSG_S);
   type RdStateType is (RD_IDLE_S, RD_MSG_S);

   type RegType is record
      count       : slv(19 downto 0);
      target      : slv(19 downto 0);
      wrState     : WrStateType;
      rdState     : RdStateType;
      advance     : sl;
      frame       : Slv16Array(NWORDS_G-1 downto 0);
      strobe      : sl;
      valid       : sl;
      fifoRd      : sl;
      fifoWr      : sl;
      fifoDin     : slv(COUNT_WIDTH_C downto 0);
   end record;

   constant REG_INIT_C : RegType := (
      count       => (others=>'0'),
      target      => toSlv(4,COUNT_WIDTH_C),
      wrState     => WR_IDLE_S,
      rdState     => RD_IDLE_S,
      advance     => '0',
      frame       => (others => (others=>'0')),
      strobe      => '0',
      valid       => '0',
      fifoRd      => '0',
      fifoWr      => '0',
      fifoDin     => (others=>'0') );

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal fifoDout     : slv(COUNT_WIDTH_C downto 0);
   signal fifoValid    : sl;
   signal fifoOverflow : sl;
   signal fifoCount    : slv(ADDR_WIDTH_C-1 downto 0);

   attribute use_dsp48      : string;
   attribute use_dsp48 of r : signal is "yes";

   signal r_wrstate   : slv(1 downto 0);
   signal r_rdstate   : slv(1 downto 0);
   signal r_fifoCount : slv(15 downto 0);

   component ila_0
      port (clk    : in sl;
            probe0 : in slv(255 downto 0));
   end component;

begin

   GEN_DEBUG : if DEBUG_G generate
      r_wrstate <= "00" when r.wrState = WR_IDLE_S else
                   "01" when r.wrState = WR_MSG_S else
                   "11";
      r_rdstate <= "00" when r.rdState = RD_IDLE_S else
                   "01" when r.rdState = RD_MSG_S else
                   "11";
      r_fifoCount <= resize(fifoCount,16);

      U_ILA : ila_0
         port map (
            clk                   => clk,
            probe0(0)             => rst,
            probe0(1)             => fiducial_i,
            probe0(2)             => advance_i,
            probe0(3)             => stream_i.last,
            probe0(4)             => '0',
            probe0(5)             => r.strobe,
            probe0(6)             => r.valid,
            probe0(26 downto  7)  => r.target,
            probe0(46 downto 27)  => r.count,
            probe0(48 downto 47)  => r_wrstate,
            probe0(50 downto 49)  => r_rdstate,
	    probe0(51)            => fifoValid,
	    probe0(67 downto 52)  => r_fifoCount,
            probe0(255 downto 68) => (others => '0'));
   end generate;

   GEN_FRAME : for i in 0 to NWORDS_G-1 generate
      frame_o(16*i+15 downto 16*i) <= r.frame(i);
   end generate;

   strobe_o   <= r.strobe;
   valid_o    <= r.valid;
   overflow_o <= fifoOverflow;

   U_MsgDelay : entity surf.FifoSync
      generic map (
         TPD_G        => TPD_G,
         FWFT_EN_G    => true,
         DATA_WIDTH_G => COUNT_WIDTH_C+1,
         ADDR_WIDTH_G => ADDR_WIDTH_C)
      port map (
         rst               => rst,
         clk               => clk,
         wr_en             => rin.fifoWr,
	 din               => rin.fifoDin,
         rd_en             => rin.fifoRd,
	 dout              => fifoDout,
         valid             => fifoValid,
         overflow          => fifoOverflow,
         data_count        => fifoCount);

   process (rst, r, advance_i, delay, fifoDout, fifoValid, fiducial_i, stream_i ) is
      variable v : RegType;
   begin
      v := r;

      v.count   := r.count+1;
      v.target  := r.count+5+delay;     -- need extra fixed delay for cntdelay fifo

      v.fifoWr  := '0';
      v.fifoRd  := '0';

      v.strobe  := '0';
      v.advance := advance_i;

      case (r.wrState) is
         --  Can fiducial_i and advance_i assert at the same time??
         when WR_IDLE_S =>
	    if fiducial_i = '1' then
      	       v.fifoWr  := '1';
	       v.fifoDin := '1' & r.target;
	       v.wrState := WR_MSG_S;
	    end if;
         when WR_MSG_S =>
	    if advance_i = '1' then
               v.fifoWr  := '1';
               v.fifoDin := resize(stream_i.data,COUNT_WIDTH_C+1);
               v.fifoDin(START_BIT_C) := r.fifoDin(COUNT_WIDTH_C);
	    elsif r.advance = '1' then
               v.fifoWr  := '1';
               v.fifoDin := (others=>'0');
               v.fifoDin(STOP_BIT_C) := '1';
	       v.wrState := WR_IDLE_S;
	    end if;
      end case;

      case (r.rdState) is
         when RD_IDLE_S =>
            if fifoValid = '1' then
               if fifoDout(fifoDout'left) = '1' then
                  if (fifoDout(COUNT_WIDTH_C-1 downto 0) = r.count) then
                    v.fifoRd := '1';
                    v.strobe := r.valid;
                    v.rdState := RD_MSG_S;
                  end if;
               else  -- unexpected word
                  v.fifoRd := '1';
                  v.valid  := '0';
               end if;
            end if;
         when RD_MSG_S =>
            if fifoValid = '1' then
               if fifoDout(fifoDout'left) = '1' then
                  v.fifoRd  := '1';
                  v.valid   := '0';
                  v.rdState := RD_IDLE_S;
               elsif fifoDout(STOP_BIT_C) = '1' then
                  v.fifoRd  := '1';
                  v.valid   := '1';
                  v.rdState := RD_IDLE_S;
               else
  	          v.fifoRd := '1';
	          v.frame  := fifoDout(15 downto 0) & r.frame(r.frame'left downto 1);
               end if;
            end if;
      end case;

      if (rst = '1') then
         v := REG_INIT_C;
      end if;

      rin <= v;
   end process;

   process (clk) is
   begin
      if rising_edge(clk) then
         r <= rin after TPD_G;
      end if;
   end process;

end TimingSerialDelay;
