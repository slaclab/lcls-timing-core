-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2BsaControl.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2016-01-24
-- Platform   : 
-- Standard   : VHDL'93/02
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
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;

use work.StdRtlPkg.all;
use work.TimingPkg.all;
use work.EvrV2Pkg.all;

entity EvrV2BsaControl is
  generic (
    TPD_G   : time    := 1ns);
  port (
    evrClk        : in  sl;
    evrRst        : in  sl;
    enable        : in  sl;
    strobeIn      : in  sl;
    dataIn        : in  TimingMessageType;
    dmaCntl       : in  EvrV2DmaControlType;
    dmaData       : out EvrV2DmaDataType );
end EvrV2BsaControl;


architecture mapping of EvrV2BsaControl is

  type RegType is record
    strobeOut  : slv(7 downto 0);
    strobeCount : slv(31 downto 0);
    dataOut    : slv(255 downto 0);
  end record;

  constant REG_TYPE_INIT_C : RegType := (
    strobeOut   => (others=>'0'),
    strobeCount => (others=>'0'),
    dataOut     => (others=>'0') );
  
  signal r    : RegType := REG_TYPE_INIT_C;
  signal r_in : RegType;

  signal countResetS : sl;
  
begin  -- mapping

  dmaData.tValid <= r.strobeOut(0);
  dmaData.tLast  <= r.strobeOut(0) and not r.strobeOut(1);
  dmaData.tData  <= r.dataOut  (31 downto 0);
  
  process (r, dataIn, strobeIn, evrRst, countResetS)
    variable v : RegType;
  begin  -- process
    v := r;

    v.strobeOut := '0' & r.strobeOut(r.strobeOut'left downto 1);
    v.dataOut   := x"00000000" & r.dataOut(r.dataOut'left downto 32);
    if (strobeIn='1' and enable='1' and
        (uOr(dataIn.bsaInit)='1' or uOr(dataIn.bsaDone)='1')) then
      v.strobeOut   := (others=>'1');
      v.strobeCount := r.strobeCount+1;
      v.dataOut     := dataIn.bsaDone   &
                       dataIn.bsaInit &
                       dataIn.timeStamp &
                       x"0000" & EVRV2_BSA_CONTROL_TAG &
                       slv(conv_unsigned(r.dataOut'length,32));
    end if;

    if evrRst='1' then
      v := REG_TYPE_INIT_C;
    end if;

    if countResetS='1' then
      v.strobeCount := (others=>'0');
    end if;
    
    r_in <= v;
  end process;    

  process (evrClk)
  begin  -- process
    if rising_edge(evrClk) then
      r <= r_in;
    end if;
  end process;

end mapping;
