-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : StatusSynchronizer.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2016-04-13
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Synchronizer for TPG status record.
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
use ieee.std_logic_1164.all;

use work.StdRtlPkg.all;
use work.TPGPkg.all;

entity StatusSynchronizer is
   generic (
      TPD_G          : time     := 1 ns;
      RST_POLARITY_G : sl       := '1';    -- '1' for active HIGH reset, '0' for active LOW reset
      RST_ASYNC_G    : boolean  := false;  -- Reset is asynchronous
      STAGES_G       : positive := 2;
      BYPASS_SYNC_G  : boolean  := false);  -- Bypass Synchronizer module for synchronous data configuration      
   port (
      clk     : in  sl;                      -- clock to be SYNC'd to
      rst     : in  sl := not RST_POLARITY_G;-- Optional reset
      dataIn  : in  TPGStatusType;                      -- Data to be 'synced'
      dataOut : out TPGStatusType);                     -- synced data
end StatusSynchronizer;

architecture rtl of StatusSynchronizer is

   type TPGStatusArray  is array (natural range <>) of TPGStatusType;

   constant INIT_C : TPGStatusArray(STAGES_G-1 downto 0) := (others=>TPG_STATUS_INIT_C);

   signal crossDomainSyncReg : TPGStatusArray(STAGES_G-1 downto 0) := INIT_C;
   signal rin                : TPGStatusArray(STAGES_G-1 downto 0);

   -------------------------------
   -- XST/Synplify Attributes
   -------------------------------

   -- Synplify Pro: disable shift-register LUT (SRL) extraction
   attribute syn_srlstyle                       : string;
   attribute syn_srlstyle of crossDomainSyncReg : signal is "registers";

   -- These attributes will stop timing errors being reported on the target flip-flop during back annotated SDF simulation.
   attribute MSGON                       : string;
   attribute MSGON of crossDomainSyncReg : signal is "FALSE";

   -- These attributes will stop XST translating the desired flip-flops into an
   -- SRL based shift register.
   attribute shreg_extract                       : string;
   attribute shreg_extract of crossDomainSyncReg : signal is "no";

   -- Don't let register balancing move logic between the register chain
   attribute register_balancing                       : string;
   attribute register_balancing of crossDomainSyncReg : signal is "no";

   -------------------------------
   -- Altera Attributes 
   ------------------------------- 
   attribute altera_attribute                       : string;
   attribute altera_attribute of crossDomainSyncReg : signal is "-name AUTO_SHIFT_REGISTER_RECOGNITION OFF";
   
begin

   assert (STAGES_G >= 2) report "STAGES_G must be >= 2" severity failure;

   GEN_ASYNC : if (BYPASS_SYNC_G = false) generate

      comb : process (crossDomainSyncReg, dataIn, rst) is
        variable dOut : TPGStatusType;
      begin
         rin <= crossDomainSyncReg(STAGES_G-2 downto 0) & dataIn;

         -- Synchronous Reset
         if (RST_ASYNC_G = false and rst = RST_POLARITY_G) then
            rin <= INIT_C;
         end if;

         dOut := crossDomainSyncReg(STAGES_G-1);
         -- synchronous fields
         dOut.irqFifoData  := dataIn.irqFifoData;
         dOut.irqFifoFull  := dataIn.irqFifoFull;
         dOut.irqFifoEmpty := dataIn.irqFifoEmpty;
         dOut.timeStamp    := dataIn.timeStamp;
         
         dataOut <= dOut;

      end process comb;

      seq : process (clk, rst) is
      begin
         if (rising_edge(clk)) then
            crossDomainSyncReg <= rin after TPD_G;
         end if;
         if (RST_ASYNC_G and rst = RST_POLARITY_G) then
            crossDomainSyncReg <= INIT_C after TPD_G;
         end if;
      end process seq;

   end generate;

   GEN_SYNC : if (BYPASS_SYNC_G = true) generate

      dataOut <= dataIn;
      
   end generate;

end architecture rtl;
