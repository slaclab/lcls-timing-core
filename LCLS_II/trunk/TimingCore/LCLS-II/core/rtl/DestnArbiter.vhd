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
      beamSeq            : in  Slv32Array(MAXBEAMSEQDEPTH-1 downto 0);
      beamSeqO           : out std_logic_vector(BEAMSEQWIDTH-1 downto 0)
     );
end DestnArbiter;

architecture DestnArbiter of DestnArbiter is

  signal beamPrioI        : IntegerArray(MAXBEAMSEQDEPTH-1 downto 0);

begin

  process (beamPrio, beamSeq, beamPrioI)
    variable iseq : integer;
  begin  -- process
    
    beamSeqO <= (others=>'0');
    beamPrioI_loop: for i in 0 to MAXBEAMSEQDEPTH-1 loop
      iseq := conv_integer(beamPrio((i+1)*BEAMPRIOBITS-1 downto i*BEAMPRIOBITS));
      if (iseq>=0 and iseq<beamSeq'length) then
        if beamSeq(iseq)(0)='1' then
          beamSeqO <= beamSeq(iseq);
        end if;
      end if;
    end loop beamPrioI_loop;
  end process;
  
end DestnArbiter;
