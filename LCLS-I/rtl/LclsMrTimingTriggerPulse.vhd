-------------------------------------------------------------------------------
-- Title      : Generated pulse after trigger from timing system
-------------------------------------------------------------------------------
-- File       : LclsMrTimingTriggerPulse.vhd
-- Author     : Uros Legat  <ulegat@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-06-08
-- Last update: 2015-06-08
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description:  Triggered if opcode received.
--               Opcode = oth 0 (Disabled)
--               Minimum pulse latency = 2c-c 
--               Delay0: Minimum+0
--               Delay1: Minimum+1              
--               Delay2: Minimum+2               
--               ...
--               Width0: 1 c-c
--               Width1: 2 c-c             
--               Width2: 3 c-c                
--               ...         
--                    
------------------------------------------------------------------------------
-- This file is part of 'LCLS2 LLRF Development'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS2 LLRF Development', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;


entity LclsMrTimingTriggerPulse is
   generic (
      TPD_G             : time     := 1 ns;
      AXI_ERROR_RESP_G  : slv(1 downto 0)       := AXI_RESP_DECERR_C;
      DELAY_WIDTH_G     : integer range 1 to 32 := 32;
      PULSE_WIDTH_G     : integer range 1 to 32 := 32
   );
   port (

      -- Timing clock
      clk          : in  sl;
      rst          : in  sl;
      
      -- AXI lite
      axilClk : in sl;
      axilRst : in sl;
      axilReadMaster  : in  AxiLiteReadMasterType  := AXI_LITE_READ_MASTER_INIT_C;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType := AXI_LITE_WRITE_MASTER_INIT_C;
      axilWriteSlave  : out AxiLiteWriteSlaveType;

      -- Opcodes (events)
      opcodes_i    : in  slv(255 downto 0);
      strobe_i     : in  sl;
      
      -- Trigger pulse output 
      pulse_o    : out  sl
   );
end LclsMrTimingTriggerPulse;

architecture rtl of LclsMrTimingTriggerPulse is

   type StateType is (
      --
      WAIT_TRIG_S,
      WAIT_DELAY_S,
      WAIT_WIDTH_S
   );

   type RegType is record
      cnt      : slv(31 downto 0);
      pulse    : sl;
      delayReg : slv(DELAY_WIDTH_G-1 downto 0);
      widthReg : slv(PULSE_WIDTH_G-1 downto 0);
      
      -- State Machine
      state   : StateType;
   end record RegType;

   constant REG_INIT_C : RegType := (
      cnt      => (others => '0'),
      pulse    => '0',
      delayReg => (others => '0'),
      widthReg => (others => '0'),
      -- State machine       
      state => WAIT_TRIG_S
   );
   
   -- Internal signals
   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   -- Register controls
   signal s_opcodesReg : slv(255 downto 0);
   signal s_delayReg   : slv(DELAY_WIDTH_G-1 downto 0);
   signal s_widthReg   : slv(PULSE_WIDTH_G-1 downto 0);
   signal s_polarity   : sl;
-----
begin
   
   U_LclsMrTimingTriggerPulseReg: entity work.LclsMrTimingTriggerPulseReg
   generic map (
      TPD_G            => TPD_G,
      AXI_ERROR_RESP_G => AXI_ERROR_RESP_G,
      DELAY_WIDTH_G    => DELAY_WIDTH_G,
      PULSE_WIDTH_G    => PULSE_WIDTH_G)
   port map (
      axiclk_i        => axilClk,
      axirst_i        => axilRst,
      axilReadMaster  => axilReadMaster,
      axilReadSlave   => axilReadSlave,
      axilWriteMaster => axilWriteMaster,
      axilWriteSlave  => axilWriteSlave,
      devclk_i        => clk,
      devrst_i        => rst,
      opcodesReg_o    => s_opcodesReg,
      delayReg_o      => s_delayReg,
      widthReg_o      => s_widthReg,
      polarity_o      => s_polarity);

   
   ----------------------------------------------------------------------------------------------- 
   comb : process (r, rst, opcodes_i, strobe_i, s_opcodesReg, s_delayReg, s_widthReg) is
      
      variable v : RegType;

   begin
      v := r;

      case r.state is
         ----------------------------------------------------------------------
         when WAIT_TRIG_S =>
            v.cnt   := (others => '0');
            v.pulse := s_polarity; -- Pulse NOT active
            v.delayReg := s_delayReg;
            v.widthReg := s_widthReg;
            
            -- 
            if ( (opcodes_i and s_opcodesReg) /= 0 and
                 strobe_i     = '1'
            ) then
              --
              v.state      := WAIT_DELAY_S;
            end if;
         ----------------------------------------------------------------------
         when WAIT_DELAY_S =>
            v.cnt := r.cnt + 1;
            v.pulse := s_polarity; -- Pulse NOT active
            -- 
            if r.cnt = r.delayReg then
               v.cnt    := (others => '0');
               v.state  := WAIT_WIDTH_S;
            end if;
         ----------------------------------------------------------------------
         when WAIT_WIDTH_S =>
            v.cnt := r.cnt + 1;
            v.pulse := not s_polarity; -- Pulse active
            -- 
            if r.cnt = r.widthReg then
               v.state      := WAIT_TRIG_S;
            end if;

         ----------------------------------------------------------------------
         when others =>
            --
            v := REG_INIT_C;
           
      ----------------------------------------------------------------------
      end case;

      -- Synchronous Reset
      if (rst = '1') then
         v := REG_INIT_C;
      end if;
      
      -- Output assignment
      rin     <= v;
      pulse_o <= r.pulse;
      
   end process comb;

   seq : process (clk) is
   begin
      if (rising_edge(clk)) then
         r <= rin after TPD_G;
      end if;
   end process seq;
   ---------------------------------------------------------------------
end architecture rtl;