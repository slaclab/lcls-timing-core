-------------------------------------------------------------------------------
-- File       : TimingSerialDelayTb.vhd
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Simulation Testbed for testing the TimingSerialDelayTb module
--   Validate operation under these conditions
--     Multi-segment frames
--     Coming out of reset in the middle of ...
--     Change delay value in the middle of ...
--     Data corruption in reception
-------------------------------------------------------------------------------
-- This file is part of 'SLAC Firmware Standard Library'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'SLAC Firmware Standard Library', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;

use work.StdRtlPkg.all;
use work.AxiPkg.all;
use work.AxiLitePkg.all;
use work.TimingPkg.all;

entity TimingSerialDelayTb is end TimingSerialDelayTb;

architecture testbed of TimingSerialDelayTb is

   constant CLK_PERIOD_C : time := 10 ns;
   constant TPD_G        : time := CLK_PERIOD_C/4;

--   constant DELAY_C      : integer := 140;    -- in clocks
   constant DELAY_C      : integer := 0;    -- in clocks
   constant FID_PERIOD_C : integer := 66;    -- clks btw fiducials
   
   signal clk  : sl := '0';
   signal rst  : sl := '0';
   signal rstL : sl := '1';

   constant SEGMENT_LEN_C   : integer := 16;  -- in 16b words
   constant SEGMENT_FRM_C   : integer := 1;   -- segments per frame
   constant FRAME_PERIOD_C  : integer := 1;   -- fiducials btw frames
   constant FRAME_LEN_C     : integer := SEGMENT_LEN_C*SEGMENT_FRM_C;
   constant ADVANCE_START_C : integer := 3;   -- clocks after fiducial
   
   type RegType is record
     nword     : integer;
     padvance  : integer;
     nadvance  : integer;
     nfiducial : integer;
     ifiducial : integer;
     nsegment  : integer;
     iframe    : integer;
     advance   : sl;
     stream    : TimingSerialType;
     sclkgen   : slv(15 downto 0);
     sclknow   : slv(15 downto 0);
     strobe    : sl;
   end record;
   constant REG_INIT_C : RegType := (
     nword     => 0,
     padvance  => 0,
     nadvance  => 0,
     nfiducial => 0,
     ifiducial => 0,
     nsegment  => 0,
     iframe    => 0,
     advance   => '0',
     stream    => TIMING_SERIAL_INIT_C,
     sclkgen   => (others=>'0'),
     sclknow   => (others=>'0'),
     strobe    => '0' );

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal frame    : slv(16*FRAME_LEN_C-1 downto 0);
   signal fiducial : sl;
   signal strobe   : sl;
   signal valid    : sl;
   signal overflow : sl;
   signal l0Reset  : sl;
   
begin

  assert FRAME_PERIOD_C >= SEGMENT_FRM_C report "FRAME_PERIOD_C must be >= SEGMENT_FRM_C";
  
   ---------------------------
   -- Generate clock and reset
   ---------------------------
   U_ClkRst : entity work.ClkRst
      generic map (
         CLK_PERIOD_G      => CLK_PERIOD_C,
         RST_START_DELAY_G => 0 ns,  -- Wait this long into simulation before asserting reset
         RST_HOLD_TIME_G   => 1000 ns)  -- Hold reset for this long)
      port map (
         clkP => clk,
         clkN => open,
         rst  => rst,
         rstL => rstL);

   U_Fiduial : entity work.Divider
     generic map (TPD_G => TPD_G,
                  Width => 10 )
     port map ( sysClk   => clk,
                sysReset => rst,
                enable   => '1',
                clear    => '0',
                divisor  => toSlv(FID_PERIOD_C,10),
                trigO    => fiducial );

   U_L0Reset : entity work.Divider
     generic map ( Width => 16 )
     port map ( sysClk   => clk,
                sysReset => rst,
                enable   => '1',
                clear    => '0',
                divisor  => toSlv(FID_PERIOD_C*10,16),
                trigO    => l0Reset );
  
   U_DUT : entity work.TimingSerialDelay
     generic map ( TPD_G    => TPD_G,
                   NWORDS_G => FRAME_LEN_C,
                   FDEPTH_G => 100 )
     port map ( clk        => clk,
                rst        => l0Reset,
                delay      => toSlv(DELAY_C,20),
                fiducial_i => fiducial,
                advance_i  => r.advance,
                stream_i   => r.stream,
                frame_o    => frame,
                strobe_o   => strobe,
                valid_o    => valid,
                overflow_o => overflow );

   comb : process ( r, rst, fiducial, frame, strobe, valid, overflow ) is
     variable v : RegType;
     variable clknow : integer;
     variable clkgen : integer;
     variable ferror : boolean;
   begin
     v := r;

     --  Generate stream --
     v.advance   := '0';
     v.ifiducial := r.ifiducial+1;
     
     if r.padvance = ADVANCE_START_C then
       v.nadvance := r.nadvance+1;
       if r.nadvance = SEGMENT_LEN_C then
         if r.nsegment = FRAME_PERIOD_C-1 then
           v.nsegment      := 0;
           v.nword         := 0;
         else
           v.nsegment      := r.nsegment+1;
         end if;
       elsif (r.nadvance < SEGMENT_LEN_C and
              r.nsegment < SEGMENT_FRM_C) then
         v.stream.ready := '1';
         if r.nsegment = SEGMENT_FRM_C-1 then
           v.stream.last   := '1';
         else
           v.stream.last   := '0';
         end if;
         v.advance  := '1';
         v.nword    := r.nword+1;
         if r.nadvance = 0 and r.nsegment = 0 then
           v.stream.data(15 downto 8) := toSlv(r.nfiducial,8);
         else
           v.stream.data(15 downto 8) := toSlv(0,8);
         end if;
         v.stream.data(7 downto 0) := toSlv(r.nword,8);
       end if;
     else
       v.padvance := r.padvance+1;
     end if;
     
     if fiducial = '1' then  -- done with previous frame
       v.stream.ready   := '0';
       v.padvance       := 0;
       v.nadvance       := 0;
       v.ifiducial      := 0;
       v.nfiducial      := r.nfiducial+1;
     end if;

     clknow := r.nfiducial*FID_PERIOD_C + r.ifiducial;
     clkgen := (conv_integer(frame(15 downto 8))+SEGMENT_FRM_C)*FID_PERIOD_C+DELAY_C;
     v.sclknow := toSlv(clknow,16);
     v.sclkgen := toSlv(clkgen,16);
     v.strobe  := strobe;
     
     --  Validate delayed frame --
     if strobe = '1' then
       ferror := false;
       for i in 0 to FRAME_LEN_C-1 loop
         if frame(16*i+7 downto 16*i) /= toSlv(i,8) then
           ferror := true;
         end if;
       end loop;
       assert ferror = false report "Frame error";
     end if;

     assert overflow /= '1' report "FIFO overflow";

     assert (r.strobe='0' or r.sclknow = r.sclkgen+4) report "Unexpected frame delay";
     
     if rst = '1' then
       v := REG_INIT_C;
     end if;
     
     rin <= v;
   end process comb;

   seq : process (clk) is
   begin
     if rising_edge(clk) then
       r <= rin;
     end if;
   end process seq;
   
end testbed;
