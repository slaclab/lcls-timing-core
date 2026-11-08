-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingDataBuffType input
--              of TimingStreamTx into a plain slv port. This file is never
--              loaded by any ruckus.tcl.
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

library surf;
use surf.StdRtlPkg.all;

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;

entity TimingStreamTxWrapper is
   generic (
      TPD_G : time := 1 ns);
   port (
      clk        : in  sl;
      rst        : in  sl;
      fiducial   : in  sl;
      dataBuff   : in  slv(TIMING_DATABUFF_BITS_C-1 downto 0);
      pulseId    : in  slv(31 downto 0);
      eventCodes : in  slv(255 downto 0);
      data       : out slv(15 downto 0);
      dataK      : out slv(1 downto 0));
end entity TimingStreamTxWrapper;

architecture mapping of TimingStreamTxWrapper is

   signal dataBuffRec : TimingDataBuffType;

begin

   dataBuffRec <= toTimingDataBuffType(dataBuff);

   U_TimingStreamTx : entity lcls_timing_core.TimingStreamTx
      generic map (
         TPD_G => TPD_G)
      port map (
         clk        => clk,
         rst        => rst,
         fiducial   => fiducial,
         dataBuff   => dataBuffRec,
         pulseId    => pulseId,
         eventCodes => eventCodes,
         data       => data,
         dataK      => dataK);

end architecture mapping;
