-------------------------------------------------------------------------------
-- Title         : TPG Resync
-- Project       : LCLS-II Timing Pattern Generator
-------------------------------------------------------------------------------
-- File          : TPGResync.vhd
-- Author        : Matt Weaver, weaver@slac.stanford.edu
-- Created       : 05/29/2015
-------------------------------------------------------------------------------
-- Description:
-- TPG resynchronization validation and status
-------------------------------------------------------------------------------
-- Copyright (c) 2015 by SLAC National Accelerator Laboratory. All rights reserved.
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
     forceI    : in  sl;
     resyncI   : in  sl;
     baseI     : in  sl;

     syncReset : out sl;
     resyncO   : out sl;
     outOfSync : out sl
     );
end TPGResync;

architecture TPGResync of TPGResync is

   component Divider
     generic ( Width    : integer := 4 );
     port ( 
       -- Clock and reset
       sysClk             : in  sl;
       sysReset           : in  sl;
       enable             : in  sl;
       clear              : in  sl;
       divisor            : in  slv(Width-1 downto 0);
       trigO              : out sl
       );
   end component;

   signal resync            : sl;
   signal resyncQ           : sl;
   signal resyncOn          : sl;
   signal resyncOb          : sl;
   signal baseResync        : sl;
   signal baseResync_d      : sl;
   signal syncResetb        : sl;
   signal syncResetNext     : sl;
   signal outOfSyncb        : sl;
   signal outOfSyncNext     : sl;

   -- Register delay for simulation
   constant tpd:time := 0.5 ns;

begin  -- TPGResync

   syncReset     <= syncResetb;
   resyncO       <= resyncOb;
   outOfSync     <= outOfSyncb;
   
   resyncOn      <= '1' when resyncQ='1' else
                    '0' when baseI='1' else
                    resyncOb;
   
   syncResetNext <= '0'        when (forceI='1') else
                    '0'        when (resyncQ='1' and syncResetb='1') else
                    '0'        when (resyncQ='1' and baseResync_d='1') else
                    syncResetb when (resyncQ='0' and baseResync_d='0') else
                    '1';
   outOfSyncNext <= '0' when (resyncQ='1' and baseResync_d='1') else
                    '1' when (resyncQ='1' or  baseResync_d='1') else
                    outOfSyncb;
   
   ResyncCheck : Divider
     generic map ( Width => 12 )
     port map ( sysClk   => clk,
                sysReset => resyncQ,
                enable   => '1',
                clear    => '0',
                divisor  => x"A26",
                trigO    => baseResync );
     
   process (clk, rst)
   begin  -- process
     if rising_edge(clk) then
       syncResetb   <= syncResetNext after tpd;
       outOfSyncb   <= outOfSyncNext after tpd;
       resyncOb     <= resyncOn after tpd;
       resyncQ      <= (resyncI or forceI) and not resync after tpd;
       resync       <= (resyncI or forceI) after tpd;
       baseResync_d <= baseResync after tpd;
     end if;
     if rst = '1' then
       syncResetb   <= '1';
       outOfSyncb   <= '1';
       resync       <= '0';
       resyncQ      <= '0';
       resyncOb     <= '0';
       baseResync_d <= '0';
     end if;
   end process;
   
end TPGResync;
     
