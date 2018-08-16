-------------------------------------------------------------------------------
-- File       : TimingExtnPkg.vhd
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2018-08-15
-------------------------------------------------------------------------------
-- Description: 
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

package TimingExtnPkg is

   constant TIMING_EXTN_BITS_C : positive := 1;

   type TimingExtnType is record
      dummy   : sl;
   end record;
   constant TIMING_EXTN_INIT_C : TimingExtnType := (
      dummy => '0' );

end package TimingExtnPkg;

