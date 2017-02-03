-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : EvrV2Core.vhd
-- Author     : Matt Weaver <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2016-01-04
-- Last update: 2016-09-25
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
use ieee.NUMERIC_STD.all;

use work.StdRtlPkg.all;
use work.AxiStreamPkg.all;
use work.SsiPkg.all;
--use work.SsiPciePkg.all;
use work.EvrV2Pkg.all;

entity EvrV2Dma is
  generic (
    TPD_G         : time    := 1 ns;
    CHANNELS_C    : integer := 1;
    AXIS_CONFIG_C : AxiStreamConfigType );
  port (
    clk        :  in sl;
    dmaCntl    : out EvrV2DmaControlArray(CHANNELS_C-1 downto 0);
    dmaData    :  in EvrV2DmaDataArray   (CHANNELS_C-1 downto 0);
    dmaMaster  : out AxiStreamMasterType;
    dmaSlave   :  in AxiStreamSlaveType );
end EvrV2Dma;

architecture mapping of EvrV2Dma is

  type RegType is record
    smaster : AxiStreamMasterType;
  end record;

  constant REG_TYPE_INIT_C : RegType := (
    smaster => AXI_STREAM_MASTER_INIT_C );

  signal r   : RegType := REG_TYPE_INIT_C;
  signal rin : RegType;

begin  -- mapping

  dmaMaster <= r.smaster;
  dmaCntl   <= (others=>EVRV2_DMA_CONTROL_INIT_C);  -- ignored
  
  process (r, dmaData, dmaSlave)
    variable v : RegType;
    variable i : integer;
  begin  -- process
    v := r;
    v.smaster.tValid := '0';
    v.smaster.tLast  := '0';
    v.smaster.tData  := (others=>'0');
    for i in 0 to CHANNELS_C-1 loop
      if dmaData(i).tValid='1' then
        v.smaster.tValid := dmaData(i).tValid;
        v.smaster.tLast  := dmaData(i).tLast;
        v.smaster.tData(dmaData(i).tData'range) := dmaData(i).tData;
        if r.smaster.tValid='0' then
          ssiSetUserSof(AXIS_CONFIG_C, v.smaster, '1');
        end if;
        if dmaData(i).tLast='1' then
          ssiSetUserEofe(AXIS_CONFIG_C, v.smaster, '1');
        end if;
      end if;
    end loop;  -- i
    rin <= v;
  end process;

  process (clk)
  begin  -- process
    if rising_edge(clk) then
      r <= rin;
    end if;
  end process;
end mapping;
