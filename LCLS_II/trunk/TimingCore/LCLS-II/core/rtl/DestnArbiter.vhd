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
-- This file is part of 'LCLS2 Timing Core'.
-- It is subject to the license terms in the LICENSE.txt file found in the 
-- top-level directory of this distribution and at: 
--    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
-- No part of 'LCLS2 Timing Core', including this file, 
-- may be copied, modified, propagated, or distributed except according to 
-- the terms contained in the LICENSE.txt file.
-------------------------------------------------------------------------------
-- Modification history:
-- 07/17/2015: created.
-------------------------------------------------------------------------------
LIBRARY ieee;
use work.all;
USE ieee.std_logic_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
use work.TPGPkg.all;
use work.StdRtlPkg.all;

entity DestnArbiter is
   port (
      beamPrio           : in  std_logic_vector(MAXBEAMSEQDEPTH*BEAMPRIOBITS-1 downto 0);
      beamSeq            : in  Slv17Array(MAXBEAMSEQDEPTH-1 downto 0);
      beamSeqO           : out std_logic_vector(BEAMSEQWIDTH-1 downto 0)
     );
end DestnArbiter;

architecture DestnArbiter of DestnArbiter is

  signal beamPrioI        : IntegerArray(MAXBEAMSEQDEPTH-1 downto 0);

begin

  process (beamPrio, beamSeq, beamPrioI)
    variable iseq : integer;
    variable idst : slv(BEAMPRIOBITS-1 downto 0);
  begin  -- process
    
    beamSeqO <= (others=>'0');
    beamPrioI_loop: for i in 0 to MAXBEAMSEQDEPTH-1 loop
      idst := beamPrio((i+1)*BEAMPRIOBITS-1 downto i*BEAMPRIOBITS);
      iseq := conv_integer(idst);
      if (iseq>=0 and iseq<beamSeq'length) then
        if beamSeq(iseq)(16)='1' then
          beamSeqO(31 downto 16)           <= beamSeq(iseq)(15 downto 0);
          beamSeqO(BEAMPRIOBITS downto  1) <= idst;
          beamSeqO(0)                      <= '1';
        end if;
      end if;
    end loop beamPrioI_loop;
  end process;
  
end DestnArbiter;
