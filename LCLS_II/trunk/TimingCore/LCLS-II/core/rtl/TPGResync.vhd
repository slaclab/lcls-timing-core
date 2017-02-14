-------------------------------------------------------------------------------
-- Title         : TPG Resync
-- Project       : LCLS-II Timing Pattern Generator
-------------------------------------------------------------------------------
-- File          : TPGResync.vhd
-- Author        : Matt Weaver, weaver@slac.stanford.edu
-- Created       : 05/29/2015
-------------------------------------------------------------------------------
-- Description:
-- TPG resynchronization validation and status.
-- This module tests that the 71kHz 'resyncI' strobe occurs at regular intervals
-- of the 929kHz 'baseI' strobe.
-------------------------------------------------------------------------------
-- This file is part of 'LCLS2 Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS2 Timing Core', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------
-- Modification history:
-- 05/29/2015: created.
-------------------------------------------------------------------------------
LIBRARY ieee;
use work.all;
use work.StdRtlPkg.all;
USE ieee.std_logic_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;

entity TPGResync is 
   port (
     clk       : in  sl;
     rst       : in  sl;
     forceI    : in  sl;  -- force output good
     resyncI   : in  sl;  -- 71kHz strobe (test)
     baseI     : in  sl;  -- 929kHz strobe (fiducial), clears resyncO

     syncReset : out sl;  -- level reset until sync confirmed
     resyncO   : out sl;  -- reset strobe (on sync) all counters / subharmonics
     outOfSync : out sl   -- status of test
     );
end TPGResync;

architecture TPGResync of TPGResync is

   type RegType is record
     syncReset : sl;  -- level reset until sync confirmed
     outOfSync : sl;  -- status of test
     resync    : sl;  -- level from resyncI or forceI
     resyncQ   : sl;  -- edge pulse from resyncI or forceI
     resyncO   : sl;  -- pulse from resyncQ until baseI
     resyncD   : sl;  -- expected cycle for resyncQ (edge)
   end record;

   constant REG_INIT_C : RegType := (
     syncReset => '1',
     outOfSync => '1',
     resync    => '0',
     resyncQ   => '0',
     resyncO   => '0',
     resyncD   => '0' );

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;
     
   signal baseResync        : sl;
   
   -- Register delay for simulation
   constant tpd:time := 0.5 ns;

begin  -- TPGResync

   ResyncCheck : entity work.Divider
     generic map ( Width => 12 )
     port map ( sysClk   => clk,
                sysReset => r.resyncQ,
                enable   => '1',
                clear    => '0',
                divisor  => x"A26",  -- 2598 cycles (nominal 2600)
                trigO    => baseResync );

   comb : process ( r, rst, forceI, resyncI, baseI, baseResync ) is
     variable v : RegType;
   begin
     v := r;

     if r.resyncQ = '1' then
       v.resyncO := '1';
     elsif baseI = '1' then
       v.resyncO := '0';
     end if;
     
     if forceI = '1' or (r.resyncQ = '1' and (r.syncReset = '1' or r.resyncD = '1'))  then
       v.syncReset := '0';
     elsif r.resyncQ = '1' or r.resyncD = '1' then
       v.syncReset := '1';
     end if;

     v.resyncQ := (resyncI or forceI) and not r.resync;
     v.resync  := (resyncI or forceI);

     v.resyncD := baseResync;
     
     if r.resyncQ = '1' and r.resyncD = '1' then
       v.outOfSync := '0';
     elsif r.resyncQ = '1' or r.resyncD = '1' then
       v.outOfSync := '1';
     end if;

     if rst = '1' then
       v := REG_INIT_C;
     end if;

     rin <= v;

     syncReset <= r.syncReset;
     resyncO   <= r.resyncO;
     outOfSync <= r.outOfSync;
   end process comb;
   
   seq: process (clk)
   begin  -- process
     if rising_edge(clk) then
       r <= rin;
     end if;
   end process seq;
   
end TPGResync;
     
