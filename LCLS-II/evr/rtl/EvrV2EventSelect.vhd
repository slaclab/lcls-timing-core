-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description:
-- Translation of BSA DEF to control bits in timing pattern
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

entity EvrV2EventSelect is
  generic ( TPD_G : time := 1 ns );
  port (
      clk        : in  sl;
      rst        : in  sl;
      config     : in  EvrV2ChannelConfig;
      strobeIn   : in  sl;
      dataIn     : in  TimingMessageType;
      selectOut  : out sl;
      dmaOut     : out sl );
end EvrV2EventSelect;

architecture EvrV2EventSelect of EvrV2EventSelect is

   signal rateSel, destSel : sl;
   signal controlWord      : slv(15 downto 0) := (others=>'0');

begin

   process (clk)
      variable controlI : integer;
   begin
      if rising_edge(clk) then

        selectOut <= rateSel and destSel and strobeIn and config.enabled;
        dmaOut    <= rateSel and destSel and strobeIn and config.enabled and config.dmaEnabled;

        controlI := conv_integer(config.rateSel(8 downto 4));
         if controlI<MAXEXPSEQDEPTH then
           controlWord <= dataIn.control(controlI);
         else
           controlWord <= (others=>'0');
         end if;
      end if;
   end process;

   process (config, dataIn, controlWord)
      variable rateType : slv(1 downto 0);
   begin
      rateType := config.rateSel(12 downto 11);
      case rateType is
         when "00" => rateSel <= dataIn.fixedRates(conv_integer(config.rateSel(3 downto 0)));
         when "01" =>
            if (config.rateSel(conv_integer(dataIn.acTimeSlot)+3-1) = '0') then
               -- acTS counts from "1"
               rateSel <= '0';
            else
               rateSel <= dataIn.acRates(conv_integer(config.rateSel(2 downto 0)));
            end if;
         when "10"   => rateSel <= controlWord(conv_integer(config.rateSel(3 downto 0)));
         when others => rateSel <= '0';
      end case;
   end process;

   destSel <= '1' when ((config.destSel(17 downto 16) = "10") or
                        (config.destSel(17 downto 16) = "01" and not (dataIn.beamRequest(0)='1' and config.destSel(conv_integer(dataIn.beamRequest(7 downto 4))) = '1')) or
                        (config.destSel(17 downto 16) = "00" and      dataIn.beamRequest(0)='1' and config.destSel(conv_integer(dataIn.beamRequest(7 downto 4))) = '1')) else
              '0';

end EvrV2EventSelect;

