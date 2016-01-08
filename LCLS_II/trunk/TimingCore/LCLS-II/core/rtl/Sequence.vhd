-------------------------------------------------------------------------------
-- Title      : Sequence
-------------------------------------------------------------------------------
-- File       : Sequence.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2015-11-05
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Sequence engine for timing generator.
--
--  Sequencer instruction word bits:
--    (31:30)="10"  Fixed Rate Sync
--       (19:16)=marker_id
--       (11:0)=occurrence
--    (31:30)="11"  AC Rate Sync
--       (29:24)=timeslot_mask
--       (19:16)=marker_id
--       (11:0)=occurrence
--    (31:30)="01"  Checkpoint/Notify
--    (31:30)="00"  Branch
--       (28:27)=counter
--       (24)=unconditional
--       (23:16)=test_value
--       (9:0)=address
--
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

entity Sequence is
   port (
      -- Clock and reset
      clkA         : in  sl;
      rstA         : in  sl;
      wrEnA        : in  sl;
      indexA       : in  SeqAddrType;
      rdStepA      : out slv(31 downto 0);
      wrStepA      : in  slv(31 downto 0);
      clkB         : in  sl;
      rstB         : in  sl;
      rdEnB        : in  sl;
      waitB        : in  sl;
      acTS         : in  slv(2 downto 0);
      acRate       : in  slv(5 downto 0);
      fixedRate    : in  slv(9 downto 0);
      seqReset     : in  sl;
      startAddr    : in  SeqAddrType;
      seqState     : out SequencerState;
      seqNotify    : out SeqAddrType;
      seqNotifyWr  : out sl;
      seqNotifyAck : in  sl;
      dataO        : out slv(31 downto 0);

      monReset : in  sl;
      monCount : out slv(31 downto 0);

      debug0 : out slv(63 downto 0);
      debug1 : out slv(63 downto 0)
      );
end Sequence;

-- Define architecture for top level module
architecture ISequence of Sequence is

   type SEQ_STATE is (SEQ_STOPPED, SEQ_LOAD, SEQ_TEST_BRANCH, SEQ_TEST_OCC, SEQ_STEP_WAIT, SEQ_STEP_LOAD, SEQ_STEP_EXEC);

   type RegType is
   record
      index      : slv(SEQADDRLEN-1 downto 0);
      delaycount : slv(15 downto 0);
      count      : Slv8Array(3 downto 0);
      data       : slv(31 downto 0);
      counter    : slv(7 downto 0);
      counterI   : integer range 0 to 3;
      jump       : sl;
      notify     : sl;
      notifyaddr : slv(SEQADDRLEN-1 downto 0);
      state      : SEQ_STATE;
      monCount   : slv(31 downto 0);
   end record RegType;

   constant REG_INIT_C : RegType := (
      index      => (others => '0'),
      delaycount => (others => '0'),
      count      => (others => (others => '0')),
      data       => (others => '0'),
      counter    => (others => '0'),
      counterI   => 0,
      jump       => '0',
      notify     => '0',
      notifyaddr => (others => '0'),
      state      => SEQ_STOPPED,
      monCount   => (others => '0'));

   signal rdStepB : slv(31 downto 0);

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

begin

   dataO          <= r.data;
   seqState.index <= SeqAddrType(r.index);
   seqState.count <= r.count;
   seqNotifyWr    <= r.notify;
   seqNotify      <= SeqAddrType(r.notifyaddr);
   monCount       <= r.monCount;

   U_Ram : entity work.DualPortRam
      generic map (
         TPD_G        => 1ns,
         DATA_WIDTH_G => 32,
         ADDR_WIDTH_G => 11,
         MODE_G       => "read-first")
      port map (
         clka  => clkA,
         ena   => '1',
         wea   => wrEnA,
         rsta  => rstA,
         addra => slv(indexA),
         dina  => wrStepA,
         douta => rdStepA,
         clkb  => clkB,
         enb   => '1',
         rstb  => rstB,
         addrb => rin.index,
         doutb => rdStepB);

   process (r, seqReset, rdStepB, fixedRate, acRate, acTS, rdEnB, waitB, startAddr, seqNotifyAck, monReset)
      variable v : RegType;
      variable rateI, acTSI : integer;
   begin  -- process

      v := r;

      v.jump := '0';

      if seqNotifyAck = '1' then
         v.notify := '0';
      end if;

      case r.state is
         when SEQ_STOPPED => null;
         when SEQ_LOAD =>
            v.counterI := conv_integer(rdStepB(28 downto 27));
            v.counter  := r.count(v.counterI);
            if (r.count(v.counterI) = rdStepB(23 downto 16)) then
               v.jump := '1';
            end if;
            v.state := SEQ_TEST_BRANCH;
         when SEQ_TEST_BRANCH =>
            case rdStepB(31 downto 30) is
               when "00" =>                                     -- Branch
                  if rdStepB(24) = '1' then
                     v.index := rdStepB(v.index'range);
--            elsif (rdStepB(23 downto 16)=r.counter) then
                  elsif (r.jump = '1') then
                     v.index             := r.index+1;
                     v.count(r.counterI) := (others => '0');
                  else
                     v.index             := rdStepB(v.index'range);
                     v.count(r.counterI) := r.count(r.counterI)+1;
                  end if;
                  v.state := SEQ_LOAD;
               when "01" =>                                     -- Notify
                  v.index      := r.index+1;
                  v.notify     := '1';
                  v.notifyaddr := r.index;
                  v.state      := SEQ_LOAD;
               when others =>                                   -- Sync
                  v.state := SEQ_TEST_OCC;
            end case;
         when SEQ_TEST_OCC =>                                   -- Sync
            if rdStepB(11 downto 0) = r.delaycount then
               v.state := SEQ_STEP_LOAD;
            else
               v.state := SEQ_STEP_WAIT;
            end if;
         when SEQ_STEP_WAIT =>                                  -- Sync
            if waitB = '1' then
               rateI := conv_integer(rdStepB(19 downto 16));
               acTSI := conv_integer(acTS);
               if rdStepB(30) = '0' then                        -- FixedRate
                  if (rateI<fixedRate'length and fixedRate(rateI) = '1') then
                     v.delaycount := r.delaycount+1;
                  end if;
--               elsif (acTSI>0 and acTSI<7 and rdStepB(23+acTSI) = '1') then  -- 29:24
               elsif (rdStepB(23+acTSI) = '1') then  -- 29:24
                  if (rateI<acRate'length and acRate(rateI) = '1') then
                     v.delaycount := r.delaycount+1;
                  end if;
               end if;
               v.state := SEQ_TEST_OCC;
            end if;
         when SEQ_STEP_LOAD =>
            v.index := r.index+1;
            v.state := SEQ_STEP_EXEC;
         when SEQ_STEP_EXEC =>
            v.delaycount := (others => '0');
            v.index      := r.index+1;
            v.state      := SEQ_LOAD;
      end case;

      if rdEnB = '1' then
         v.data := (others => '0');
      elsif r.state = SEQ_STEP_EXEC then
         v.data := rdStepB;
      end if;

      if monReset = '1' then
         v.monCount := (others => '0');
      elsif r.state = SEQ_STEP_EXEC then
         v.monCount := r.monCount+1;
      end if;

      -- from any state
      if seqReset = '1' and rdEnB = '1' then
         v.index      := slv(startAddr);
         v.delaycount := (others => '0');
         v.count      := (others => (others => '0'));
         v.state      := SEQ_LOAD;
      end if;

      rin <= v;

   end process;

   process (clkB)
   begin  -- process
      if rising_edge(clkB) then
         r <= rin;
      end if;
   end process;

   debug0 <= (others=>'0');
   debug1 <= (others=>'0');
   
end ISequence;
