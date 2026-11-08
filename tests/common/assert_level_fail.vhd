-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Test-only DUT that exists to prove an error-level assertion
-- fails a regression case. After 5 ns it fires a failing assertion and then
-- waits forever.
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

entity AssertLevelFail is
   port (
      clk : in std_logic
   );
end entity AssertLevelFail;

architecture sim of AssertLevelFail is

begin

   p_check : process is
   begin
      wait for 5 ns;
      assert false
         report "deliberate failure"
         severity error;
      wait;
   end process p_check;

end architecture sim;
