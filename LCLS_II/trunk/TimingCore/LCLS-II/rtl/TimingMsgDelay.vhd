-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingMsgDelay.vhd
-- Author     : 
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2014-05-02
-- Last update: 2015-09-16
-- Platform   : Vivado 2013.3
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
--
-------------------------------------------------------------------------------
-- Copyright (c) 2014 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;
use work.AxiStreamPkg.all;
use work.SsiPkg.all;

entity TimingMsgDelay is
   generic (
      -- General Configurations
      TPD_G             : time                        := 1 ns;
      BRAM_EN_G         : boolean                     := true;
      FIFO_ADDR_WIDTH_G : positive range 1 to (2**24) := 7);

   port (
      -- Timing Msg interface
      timingClk          : in  sl;
      timingRst          : in  sl;
      timingMsgIn        : in  TimingMsgType;
      timingMsgStrobeIn  : in  sl;
      delay              : in  slv(15 downto 0);
      timingMsgOut       : out TimingMsgType;
      timingMsgStrobeOut : out sl);

end TimingMsgDelay;

architecture rtl of TimingMsgDelay is

   constant TIME_SIZE_C  : integer := 32;
   constant FIFO_WIDTH_C : integer := TIMING_MSG_BITS_C + TIME_SIZE_C;

   type READOUT_RANGE_C is range TIMING_MSG_BITS_C+TIME_SIZE_C-1 downto TIMING_MSG_BITS_C;
   type TIMING_RANGE_C is range TIMING_MSG_BITS_C-1 downto 0;

   type RegType is record
      timeNow            : slv(TIME_SIZE_C-1 downto 0);
      readoutTime        : slv(TIME_SIZE_C-1 downto 0);
      fifoRdEn           : sl;
      timingMsgOut       : TimingMsgType;
      timingMsgStrobeOut : sl;
   end record RegType;

   signal timingMsgSlv    : slv(TIMING_MSG_BITS_C-1 downto 0);
   signal fifoReadoutTime : slv(TIME_SIZE_C-1 downto 0);

begin

   timingMsgSlv <= toSlv(timingMsgIn);

   Fifo_1 : entity work.Fifo
      generic map (
         TPD_G           => TPD_G,
         GEN_SYNC_FIFO_G => true,
         BRAM_EN_G       => BRAM_EN_G,
         FWFT_EN_G       => true,
         USE_DSP48_G     => "no",
         USE_BUILT_IN_G  => false,
         DATA_WIDTH_G    => FIFO_WIDTH_C,
         ADDR_WIDTH_G    => FIFO_ADDR_WIDTH_G)
      port map (
         rst                   => timingRst,
         wr_clk                => timingClk,
         wr_en                 => timingMsgStrobeIn,
         din(READOUT_RANGE_C)  => r.readoutTime,
         din(TIMING_RANGE_C)   => timingMsgSlv,
         rd_clk                => timingClk,
         rd_en                 => r.fifoRdEn,
         dout(READOUT_RANGE_C) => fifoReadoutTime,
         dout(TIMING_RANGE_C)  => fifoTimingMsg,
         valid                 => fifoValid);

   comb : process (delay, fifoReadoutTime, r, timingRst) is
      variable v : RegType;
   begin
      v := r;

      v.timeNow     := r.timeNow + 1;
      v.readoutTime := r.timeNow + delay;

      v.fifoRdEn           := '0';
      v.timingMsgStrobeOut := '0';
      v.timingMsgOut       := toTimingMsgType(fifoTimingMsg);

      if (fifoValid = '1' and r.fifoRdEn = '0') then
         if (fifoReadoutTime = r.timeNow) then
            v.fifoRdEn           := '1';
            v.timingMsgStrobeOut := '1';
         end if;
      end if;

      if (timingRst = '1') then
         v := REG_INIT_C;
      end if;

      rin <= v;

      timingMsgOut       <= r.timingMsgOut;
      timingMsgStrobeOut <= r.timingMsgStrobeOut;

   end process comb;

   seq : process (timingClk) is
   begin
      if (rising_edge(timingClk)) then
         r <= rin after TPD_G;
      end if;
   end process seq;

end rtl;
