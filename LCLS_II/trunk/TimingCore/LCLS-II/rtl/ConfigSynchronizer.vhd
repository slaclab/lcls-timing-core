-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : ConfigSynchronizer.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2015/09/15
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Synchronizer for TPG config record.
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

use work.StdRtlPkg.all;
use work.TPGPkg.all;

entity ConfigSynchronizer is
   generic (
      TPD_G          : time     := 1 ns;
      RST_POLARITY_G : sl       := '1';    -- '1' for active HIGH reset, '0' for active LOW reset
      RST_ASYNC_G    : boolean  := false;  -- Reset is asynchronous
      STAGES_G       : positive := 2;
      BYPASS_SYNC_G  : boolean  := false);  -- Bypass Synchronizer module for synchronous data configuration      
   port (
      clk     : in  sl;                      -- clock to be SYNC'd to
      rst     : in  sl := not RST_POLARITY_G;-- Optional reset
      dataIn  : in  TPGConfigType;                      -- Data to be 'synced'
      dataOut : out TPGConfigType);                     -- synced data
end ConfigSynchronizer;

architecture rtl of ConfigSynchronizer is

   type TPGConfigArray  is array (natural range <>) of TPGConfigType;

   constant INIT_C : TPGConfigArray(STAGES_G-1 downto 0) := (others=>TPG_CONFIG_INIT_C);

   signal crossDomainSyncReg : TPGConfigArray(STAGES_G-1 downto 0) := INIT_C;
   signal rin                : TPGConfigArray(STAGES_G-1 downto 0);

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
        variable dOut : TPGConfigType;
      begin
         rin <= crossDomainSyncReg(STAGES_G-2 downto 0) & dataIn;

         -- Synchronous Reset
         if (RST_ASYNC_G = false and rst = RST_POLARITY_G) then
            rin <= INIT_C;
         end if;

         dOut := crossDomainSyncReg(STAGES_G-1);
         -- synchronous fields
         dOut.irqFifoRd     := dataIn.irqFifoRd;
         dOut.fifoRead      := dataIn.fifoRead;
         dOut.timeStamp     := dataIn.timeStamp;
         dOut.timeStampWrEn := dataIn.timeStampWrEn;
         -- synchronized elsewhere
         dOut.IntTrigger := dataIn.IntTrigger;
         
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
