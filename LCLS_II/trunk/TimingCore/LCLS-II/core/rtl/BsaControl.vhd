-------------------------------------------------------------------------------
-- Title         : BsaControl
-- Project       : LCLS-II Timing Pattern Generator
-------------------------------------------------------------------------------
-- File          : BsaControl.vhd
-- Author        : Matt Weaver, weaver@slac.stanford.edu
-- Created       : 07/17/2015
-------------------------------------------------------------------------------
-- Description:
-- Translation of BSA DEF to control bits in timing pattern
-------------------------------------------------------------------------------
-- Copyright (c) 2015 by SLAC National Accelerator Laboratory. All rights reserved.
-------------------------------------------------------------------------------
-- Modification history:
-- 07/17/2015: created.
-------------------------------------------------------------------------------
library ieee;
use work.all;
use work.TPGPkg.all;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.all;
use work.StdRtlPkg.all;

entity BsaControl is
   port (
      sysclk     : in  sl;
      sysrst     : in  sl;
      bsadef     : in  BsaDefType;
      nToAvgOut  : out slv(15 downto 0);
      avgToWrOut : out slv(15 downto 0);

      txclk      : in  sl;
      txrst      : in  sl;
      enable     : in  sl;
      fixedRate  : in  slv(FIXEDRATEDEPTH-1 downto 0);
      acRate     : in  slv(ACRATEDEPTH-1 downto 0);
      acTS       : in  slv(2 downto 0);
      beamSeq    : in  slv(31 downto 0);
      expSeq     : in  Slv32Array(MAXEXPSEQDEPTH-1 downto 0);
      bsaInit    : out sl;
      bsaActive  : out sl;
      bsaAvgDone : out sl;
      bsaDone    : out sl
      );
end BsaControl;

architecture BsaControl of BsaControl is

   signal initq, initd, initn               : sl;
   signal done, donen, doned                : sl;
   signal persist                           : sl;
   signal active, rateSel, destSel, avgDone : sl;
   signal nToAvg, nToAvgn                   : slv(15 downto 0);
   signal avgToWr, avgToWrn                 : slv(15 downto 0);
   signal fifoRst                           : sl;
   signal control0, control1                : slv(35 downto 0);
   signal trig0, trig1                      : slv(255 downto 0);

   -- Register delay for simulation
   constant tpd : time := 0.5 ns;

begin

   process (txclk, bsadef, fixedRate, acTS, acRate, expSeq, initd, initq)
      variable rateType : slv(1 downto 0);
   begin
      if bsadef.init = '0' then
         initq   <= '0';
         persist <= '0';
      elsif rising_edge(txclk) then
         if enable = '1' and initq = '0' then
            initq <= '1';
            if bsadef.avgToWr = x"0000" then
               persist <= '1';
            end if;
         end if;
      end if;

      initn <= initq and not initd;

      rateType := bsadef.rateSel(15 downto 14);
      case rateType is
         when "00" => rateSel <= fixedRate(conv_integer(bsadef.rateSel(3 downto 0)));
         when "01" =>
            if (bsadef.rateSel(conv_integer(acTS)+3-1) = '0') then
               -- acTS counts from "1"
               rateSel <= '0';
            else
               rateSel <= acRate(conv_integer(bsadef.rateSel(2 downto 0)));
            end if;
         when "10"   => rateSel <= expSeq(conv_integer(bsadef.rateSel(10 downto 5)))(conv_integer(bsadef.rateSel(4 downto 0)));
         when others => rateSel <= '0';
      end case;
   end process;

   destSel <= '1' when (bsadef.destSel(15) = '1' or
                        bsadef.destSel(conv_integer(beamSeq(7 downto 4))) = '1') else
              '0';
   active <= rateSel and destSel and not done;
   donen  <= '0' when (initn = '1') else
            '1' when (persist = '0' and avgToWr = x"0001" and avgDone = '1') else

            done;
   avgDone <= '1' when (nToAvg = x"0001" and active = '1') else
              '0';
   avgToWrn <= bsadef.avgToWr when (initn = '1') else
               avgToWr-1 when (avgDone = '1') else
               avgToWr;
   nToAvgn <= bsadef.nToAvg when (initn = '1' or avgDone = '1') else
              nToAvg-1 when (active = '1') else
              nToAvg;
   fifoRst <= initq and not initd;

   U_SynchFifo : entity work.SynchronizerFifo
      generic map (DATA_WIDTH_G => 32,
                   ADDR_WIDTH_G => 2)
      port map (rst                => fifoRst,
                wr_clk             => txclk,
                wr_en              => '1',
                din(15 downto 0)   => nToAvg,
                din(31 downto 16)  => avgToWr,
                rd_clk             => sysclk,
                rd_en              => '1',
                valid              => open,
                dout(15 downto 0)  => nToAvgOut,
                dout(31 downto 16) => avgToWrOut);

   process (txclk, txrst)
   begin  -- process
      if txrst = '1' then
         bsaInit    <= '0';
         bsaActive  <= '0';
         bsaAvgDone <= '0';
         bsaDone    <= '0';
         initd      <= '0';
         done       <= '1';
         doned      <= '1';
         nToAvg     <= x"0000";
         avgToWr    <= x"0000";
      elsif rising_edge(txclk) then
         if enable = '1' then
            bsaInit    <= initq and not initd;
            bsaActive  <= active;
            bsaAvgDone <= avgDone;
            bsaDone    <= done and not doned;
            initd      <= initq;
            done       <= donen;
            doned      <= done;
            nToAvg     <= nToAvgn;
            avgToWr    <= avgToWrn;
         end if;
      end if;
   end process;

end BsaControl;

