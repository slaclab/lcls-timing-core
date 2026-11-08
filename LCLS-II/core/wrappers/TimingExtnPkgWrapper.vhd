-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only combinational wrapper that flattens the default
--              ExptMessageType conversions of TimingExtnPkg. The package in
--              LCLS-II/core/rtl/default/ is not part of any ruckus.tcl
--              import, so it reaches the simulator only through the explicit
--              extra source list of the test that uses this wrapper. This
--              file is never loaded by any ruckus.tcl.
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
use lcls_timing_core.TimingExtnPkg.all;

entity TimingExtnPkgWrapper is
   port (
      encBaseRateSince1Hz : in  slv(31 downto 0);
      encBaseRateSinceTM  : in  slv(31 downto 0);
      encIrigTimeCode     : in  slv(255 downto 0);
      encExpt             : out slv(EXPT_MESSAGE_BITS_C-1 downto 0);
      decExpt             : in  slv(EXPT_MESSAGE_BITS_C-1 downto 0);
      decBaseRateSince1Hz : out slv(31 downto 0);
      decBaseRateSinceTM  : out slv(31 downto 0);
      decIrigTimeCode     : out slv(255 downto 0);
      exptStreamId        : out slv(3 downto 0));
end entity TimingExtnPkgWrapper;

architecture mapping of TimingExtnPkgWrapper is

   signal encRec : ExptMessageType;
   signal decRec : ExptMessageType;

begin

   encRec.baseRateSince1Hz <= encBaseRateSince1Hz;
   encRec.baseRateSinceTM  <= encBaseRateSinceTM;
   encRec.irigTimeCode     <= encIrigTimeCode;

   encExpt <= toSlv(encRec);

   decRec <= toExptMessageType(decExpt);

   decBaseRateSince1Hz <= decRec.baseRateSince1Hz;
   decBaseRateSinceTM  <= decRec.baseRateSinceTM;
   decIrigTimeCode     <= decRec.irigTimeCode;

   exptStreamId <= EXPT_STREAM_ID;

end architecture mapping;
