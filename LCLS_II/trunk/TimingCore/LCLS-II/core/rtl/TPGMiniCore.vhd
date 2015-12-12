-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TPGMiniCore.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-11-09
-- Last update: 2015-11-16
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: 
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;
use work.Version.all;
use work.TPGPkg.all;

entity TPGMiniCore is
   generic (
      TPD_G           : time    := 1ns;
      NARRAYSBSA      : natural := 1);
   port (
     txClk           : in  sl;
     txRst           : in  sl;
     txRdy           : in  sl;
     txData          : out slv(15 downto 0);
     txDataK         : out slv( 1 downto 0);
     txPolarity      : out sl;
     axiClk          : in  sl;
     axiRst          : in  sl;
     axiReadMaster   : in  AxiLiteReadMasterType;
     axiReadSlave    : out AxiLiteReadSlaveType;
     axiWriteMaster  : in  AxiLiteWriteMasterType;
     axiWriteSlave   : out AxiLiteWriteSlaveType );
end TPGMiniCore;

architecture rtl of TPGMiniCore is

   signal status : TPGStatusType;
   signal config : TPGConfigType;

   signal regClk            : sl;
   signal regRst            : sl;
   signal regReadMaster     : AxiLiteReadMasterType;
   signal regReadSlave      : AxiLiteReadSlaveType;
   signal regWriteMaster    : AxiLiteWriteMasterType;
   signal regWriteSlave     : AxiLiteWriteSlaveType;

begin  -- rtl

   regClk <= txClk;
   regRst <= txRst;
   txPolarity <= config.txPolarity;
   
   U_AxiLiteAsync : entity work.AxiLiteAsync
      generic map (
         TPD_G => TPD_G)
      port map (
         -- Slave Port
         sAxiClk         => axiClk,
         sAxiClkRst      => axiRst,
         sAxiReadMaster  => axiReadMaster,
         sAxiReadSlave   => axiReadSlave,
         sAxiWriteMaster => axiWriteMaster,
         sAxiWriteSlave  => axiWriteSlave,
         -- Master Port
         mAxiClk         => regClk,
         mAxiClkRst      => regRst,
         mAxiReadMaster  => regReadMaster,
         mAxiReadSlave   => regReadSlave,
         mAxiWriteMaster => regWriteMaster,
         mAxiWriteSlave  => regWriteSlave);     
  
   TPGMiniReg_Inst : entity work.TPGMiniReg
      generic map (
         TPD_G => TPD_G)
      port map (
         axiClk         => regClk,
         axiRst         => regRst,
         axiReadMaster  => regReadMaster,
         axiReadSlave   => regReadSlave,
         axiWriteMaster => regWriteMaster,
         axiWriteSlave  => regWriteSlave,
         status         => status,
         config         => config,
         irqActive      => '0',
         irqEnable      => open,
         irqReq         => open );

   TPGMini_Inst : entity work.TPGMini
      generic map (
         NARRAYSBSA   => NARRAYSBSA )
      port map (
         -- Register Interface
         statusO  => status,
         configI  => config,
         -- TPG Interface
         txClk    => txClk,
         txRst    => txRst,
         txRdy    => txRdy,
         txData   => txData,
         txDataK  => txDataK );

end rtl;
