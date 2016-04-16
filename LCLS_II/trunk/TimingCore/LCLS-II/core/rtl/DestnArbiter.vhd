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
      clk                : in  sl;
      config             : in  TPGConfigType;
      configUpdate       : in  slv(MAXBEAMSEQDEPTH-1 downto 0);
      beamSeq            : in  Slv17Array(MAXBEAMSEQDEPTH-1 downto 0);
      beamSeqO           : out slv(BEAMSEQWIDTH-1 downto 0);
      beamControl        : out slv(15 downto 0)
     );
end DestnArbiter;

architecture DestnArbiter of DestnArbiter is

  type RegType is record
     seqDstn     : Slv4Array   (MAXBEAMSEQDEPTH-1 downto 0);
     seqReqd     : Slv16Array  (MAXBEAMSEQDEPTH-1 downto 0);
     destControl : Slv16Array  (MAXBEAMSEQDEPTH-1 downto 0);
     beamSeqO    : slv(BEAMSEQWIDTH-1 downto 0);
     beamControl : slv(15 downto 0);
  end record;
  constant REG_INIT_C : RegType := (
     seqDstn     => (others=>(others=>'0')),
     seqReqd     => (others=>(others=>'1')),
     destControl => (others=>(others=>'0')),
     beamSeqO    => (others=>'0'),
     beamControl => (others=>'0'));

  signal r   : RegType := REG_INIT_C;
  signal rin : RegType;
  
begin

  beamSeqO    <= r.beamSeqO;
  beamControl <= r.beamControl;
  
  comb: process ( r, config, beamSeq, configUpdate ) is
     variable v    : RegType;
     variable req  : slv(15 downto 0);
     variable idst : integer;
  begin
     v := r;

     v.beamSeqO    := (others=>'0');
     v.beamControl := (others=>'0');

     for i in 0 to MAXBEAMSEQDEPTH-1 loop
       if (configUpdate(i)='1') then
           v.seqDstn(i) := config.seqDestn      (i);
           v.seqReqd(i) := config.seqRequiredSeq(i);
           v.seqReqd(i)(i) := '1';  -- always require self
           idst := conv_integer(config.seqDestn(i));
           v.destControl(idst) := config.destnControl(idst);
        end if;
     end loop;

     req := (others=>'0');
     for i in 0 to MAXBEAMSEQDEPTH-1 loop
        if (beamSeq(i)(16)='1') then
           req(i) := '1';
        end if;
     end loop;

     for i in 0 to MAXBEAMSEQDEPTH-1 loop
        if ((req and r.seqReqd(i))=r.seqReqd(i)) then
           v.beamSeqO(31 downto 16) := beamSeq(i)(15 downto 0);
           v.beamSeqO( 4 downto  1) := r.seqDstn(i);
           v.beamSeqO(0)            := '1';
           v.beamControl            := r.destControl(conv_integer(r.seqDstn(i)));
        end if;
     end loop;

     rin <= v;
  end process;

  seq: process ( clk ) is
  begin
     if rising_edge(clk) then
        r <= rin;
     end if;
  end process seq;
  
end DestnArbiter;
