-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description:
-- Pipeline of trigger output state.  The trigger output activates config.delay
-- plus 5 clk ticks after fire is asserted and deasserts after config.width clk
-- ticks.  The FIFO allows up to 127 triggers to be pipelined.  Individual
-- trigger delays and widths have 20 bits range, provided the 127 trigger
-- pipelining is not exceeded.
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

library lcls_timing_core;
use lcls_timing_core.TPGPkg.all;

library surf;
use surf.StdRtlPkg.all;
use lcls_timing_core.TimingPkg.all;
use lcls_timing_core.EvrV2Pkg.all;

entity EvrV2Trigger is
  generic ( TPD_G        : time := 1 ns;
            CHANNELS_C   : integer := 1;
            TRIG_DEPTH_C : integer := 16;
            TRIG_WIDTH_C : integer := EVRV2_TRIG_WIDTH_C; -- bit size of
                                                        -- width,delay counters
            USE_MASK_G   : boolean := false);
  port (
      clk        : in  sl;
      rst        : in  sl;
      config     : in  EvrV2TriggerConfigType;
      arm        : in  slv(CHANNELS_C-1 downto 0);
      fire       : in  sl;
      trigstate  : out sl );
end EvrV2Trigger;

architecture rtl of EvrV2Trigger is

   type PushState is (DISABLED_S, ENABLED_S, ARMED_S, PUSHING_S);
  
   type RegType is record
     fifo_delay     : slv(TRIG_WIDTH_C-1 downto 0);      -- clks until trigger fifo is empty
     push_state     : PushState;
     duration       : slv(TRIG_WIDTH_C-1 downto 0);
     state          : sl;
     next_state     : sl;
     fifoReset      : sl;
     fifoWr         : sl;
     fifoRd         : sl;
     fifoDin        : slv(TRIG_WIDTH_C downto 0);
   end record;

   constant REG_INIT_C : RegType := (
     fifo_delay => (others=>'0'),
     push_state => DISABLED_S,
     duration   => (others=>'0'),
     state      => '0',
     next_state => '0',
     fifoReset  => '1',
     fifoWr     => '0',
     fifoRd     => '0',
     fifoDin    => (others=>'0'));

   constant FIFO_AWIDTH_C : natural := bitSize( TRIG_DEPTH_C );

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal fifoValid : sl;

   signal fifoDout  : slv(TRIG_WIDTH_C downto 0);
   signal fifoCount : slv(FIFO_AWIDTH_C-1 downto 0);

   signal fifoCountDbg : slv(6 downto 0);

begin

   trigstate <= r.state;

   GEN_NO_FIFO : if TRIG_DEPTH_C = 0 generate
     fifoDout  <= r.fifoDin;
     fifoValid <= r.fifoWr;
   end generate;

   GEN_FIFO : if TRIG_DEPTH_C > 0 generate
     --  A fifo of delays before the next trigger edge
     U_Fifo : entity surf.FifoSync
       generic map ( TPD_G        => TPD_G,
                     DATA_WIDTH_G => TRIG_WIDTH_C+1,
                     ADDR_WIDTH_G => FIFO_AWIDTH_C,
                     FWFT_EN_G    => true )
       port map (    rst   => r.fifoReset,
                     clk   => clk,
                     wr_en => rin.fifoWr,
                     rd_en => rin.fifoRd,
                     din   => rin.fifoDin,
                     dout  => fifoDout,
                     valid => fifoValid,
                     data_count => fifoCount );
   end generate;

   process (r, arm, fire, rst, config, fifoValid, fifoDout)
      variable v : RegType;
      variable x : slv(TRIG_WIDTH_C-1 downto 0);
   begin
      v := r;

      v.fifoReset := '0';
      v.fifoRd    := '0';
      v.fifoWr    := '0';

      if allBits(r.duration,'0') then
        v.state := r.next_state;
        --  Transition done.  Wait for next fifo entry.
        if fifoValid = '1' then
          v.next_state := fifoDout(fifoDout'left);
          x := fifoDout(fifoDout'left-1 downto 0);
          if x = 0 then
            v.state := v.next_state;
          else
            v.duration := x-1;
          end if;
          v.fifoRd     := '1';
        end if;
      else
        v.duration := r.duration-1;
      end if;

      if not allBits(r.fifo_delay,'0') then
        v.fifo_delay := r.fifo_delay - 1;
      end if;

      case r.push_state is
        when DISABLED_S =>
          if config.enabled = '1' then
            -- set the polarity
            v.push_state := ENABLED_S;
            v.fifoWr     := '1';
            v.fifoDin    := not config.polarity & toSlv(0,TRIG_WIDTH_C);
          end if;
        when ENABLED_S  =>
          --  Trigger input logic
          if ((arm(conv_integer(config.channel)) = '1' and not USE_MASK_G) or
              ((arm and config.channels(CHANNELS_C-1 downto 0)) /= toSlv(0,CHANNELS_C) and USE_MASK_G)) then
            v.push_state := ARMED_S;
          end if;
        when ARMED_S =>
          if fire = '1' then
            -- If the configured delay has been reduced such that this
            -- trigger would precede one already in the fifo, eat it.
            if (r.fifo_delay > config.delay(TRIG_WIDTH_C-1 downto 0) or
                config.width(TRIG_WIDTH_C-1 downto 0) = 0) then
              v.push_state := ENABLED_S;
            else
              --  Push the delay until trigger edge into the fifo
              v.push_state := PUSHING_S;
              v.fifoWr     := '1';
              v.fifoDin    := config.polarity & (config.delay(TRIG_WIDTH_C-1 downto 0) - r.fifo_delay);
              v.fifo_delay := config.delay(TRIG_WIDTH_C-1 downto 0) + config.width(TRIG_WIDTH_C-1 downto 0) - 1;
            end if;
          end if;
        when PUSHING_S =>
          --  Push the width into the fifo
          x := config.width(TRIG_WIDTH_C-1 downto 0);
          if config.delay(TRIG_WIDTH_C-1 downto 0) = 0 then
            x := x-1;
          end if;
          v.fifoWr     := '1';
          v.fifoDin    := not config.polarity & x;
          v.push_state := ENABLED_S;
        when others => NULL;
      end case;

      if rst='1' or config.enabled='0' then
         v := REG_INIT_C;
      end if;

      rin <= v;
   end process;

   process (clk)
   begin
     if rising_edge(clk) then
       r <= rin;
     end if;
   end process;

end rtl;

