-------------------------------------------------------------------------------
-- Title         : BeamDiagControl
-- Project       : LCLS-II Timing Pattern Generator
-------------------------------------------------------------------------------
-- File          : BeamDiagControl.vhd
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
library ieee;
use work.all;
use work.TPGPkg.all;
use work.AmcCarrierPkg.all;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.all;
use work.StdRtlPkg.all;

entity BeamDiagControl is
  generic ( NBUFFERS : integer := 4 );
  port (
      clk        : in  sl;
      rst        : in  sl;
      strobe     : in  sl;
      config     : in  BeamDiagControlType;
      mpsfault   : in  MpsMitigationMsgType;
      bcsfault   : in  sl;
      status     : out BeamDiagStatusType;
      bsaInit    : out slv(NBUFFERS-1 downto 0);
      bsaActive  : out slv(NBUFFERS-1 downto 0);
      bsaAvgDone : out slv(NBUFFERS-1 downto 0);
      bsaDone    : out slv(NBUFFERS-1 downto 0)
      );
end BeamDiagControl;

architecture BeamDiagControl of BeamDiagControl is

   type RegType is record
     init         : slv(NBUFFERS-1 downto 0);
     active       : slv(NBUFFERS-1 downto 0);
     done         : slv(NBUFFERS-1 downto 0);
     index        : integer;
     mpslatch     : sl;
     bcslatch     : sl;
     manlatch     : sl;
     manfault     : sl;
     mpstag       : slv(15 downto 0);
     latchtag     : slv(11 downto 0);
     bufferUsed   : slv(NBUFFERS-1 downto 0);
     bufferStatus : Slv32Array(NBUFFERS-1 downto 0);
   end record;
   constant REG_INIT_C : RegType := (
     init         => toSlv(1,NBUFFERS),
     active       => (others=>'0'),
     done         => (others=>'0'),
     index        => 0,
     mpslatch     => '0',
     bcslatch     => '0',
     manlatch     => '0',
     manfault     => '0',
     mpstag       => (others=>'0'),
     latchtag     => (others=>'0'),
     bufferUsed   => toSlv(1,NBUFFERS),
     bufferStatus  => (others=>(others=>'0')));
   
   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

begin

  bsaInit     <= r.init;
  bsaActive   <= r.active;
  bsaAvgDone  <= r.active;
  bsaDone     <= r.done;

  status.buffers(NBUFFERS-1 downto 0) <= r.bufferStatus;
  
  comb: process (r, rst, strobe, config, mpsfault, bcsfault ) is
    variable v : RegType;
    variable nindex : integer;
  begin
    v := r;
    v.manfault   := config.manfault;

    for i in 0 to NBUFFERS-1 loop
      if (config.clear(i)='1' and i/=r.index) then
        v.bufferUsed  (i) := '0';
        v.bufferStatus(i) := (others=>'0');
      end if;
    end loop;
    
    if strobe='1' then
      v.active          := (others=>'0');
      v.active(r.index) := '1';
      v.init            := (others=>'0');
      v.done            := (others=>'0');
      if (r.mpslatch='1' or r.bcslatch='1' or r.manlatch='1') then
        if not allBits(r.bufferUsed,'1') then
          nindex := 0;
          for i in NBUFFERS-1 downto 0 loop
            if r.bufferUsed(i)='0' then
              nindex := i;
            end if;
          end loop;

          v.bufferStatus(r.index) := r.manlatch & r.bcslatch & r.mpslatch & '0' &
                                     r.latchtag &
                                     r.mpstag;
          v.bufferUsed(nindex)    := '1';
          v.index           := nindex;
          v.latchtag        := r.latchtag+1;
          v.done(r.index)   := '1';
          v.init(nindex)    := '1';
        end if;

        v.manlatch := '0';
        v.bcslatch := '0';
        v.mpslatch := '0';
      end if;
    end if;
      
    if (mpsfault.strobe='1' and mpsfault.latchDiag='1') then
      v.mpslatch := '1';
      v.mpstag   := mpsfault.tag;
    end if;

    if (bcsfault='1') then
      v.bcslatch := '1';
    end if;

    if (config.manfault='1' and r.manfault='0') then
      v.manlatch := '1';
    end if;

    if (rst='1') then
      v := REG_INIT_C;
    end if;

    rin <= v;
  end process comb;

  seq: process (clk) is
  begin
    if rising_edge(clk) then
      r <= rin;
    end if;
  end process seq;
  
end BeamDiagControl;

