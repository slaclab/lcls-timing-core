-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the EvrV1StatusType input
--              and the EvrV1ConfigType output of EvrV1Reg into plain slv
--              ports, exposes the AXI-Lite slave as S_AXI_* through the surf
--              IP integrator, and fixes the build information so the version
--              words are known. This file is never loaded by any ruckus.tcl.
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
use surf.AxiLitePkg.all;

library lcls_timing_core;
-- vsg_off use_clause_501
use lcls_timing_core.EvrV1Pkg.all;
-- vsg_on use_clause_501

entity EvrV1RegWrapper is
   generic (
      TPD_G              : time    := 1 ns;
      USE_WSTRB_G        : boolean := false;
      LATCH_TS_LATENCY_G : natural := 15);
   port (
      axilClk               : in  sl;
      axilRst               : in  sl;
      S_AXI_AWADDR          : in  slv(14 downto 0);
      S_AXI_AWPROT          : in  slv(2 downto 0);
      S_AXI_AWVALID         : in  sl;
      S_AXI_AWREADY         : out sl;
      S_AXI_WDATA           : in  slv(31 downto 0);
      S_AXI_WSTRB           : in  slv(3 downto 0);
      S_AXI_WVALID          : in  sl;
      S_AXI_WREADY          : out sl;
      S_AXI_BRESP           : out slv(1 downto 0);
      S_AXI_BVALID          : out sl;
      S_AXI_BREADY          : in  sl;
      S_AXI_ARADDR          : in  slv(14 downto 0);
      S_AXI_ARPROT          : in  slv(2 downto 0);
      S_AXI_ARVALID         : in  sl;
      S_AXI_ARREADY         : out sl;
      S_AXI_RDATA           : out slv(31 downto 0);
      S_AXI_RRESP           : out slv(1 downto 0);
      S_AXI_RVALID          : out sl;
      S_AXI_RREADY          : in  sl;
      irqActive             : in  sl                  := '0';
      irqEnable             : out sl;
      irqReq                : out sl;
      statusTs              : in  slv(63 downto 0)    := (others => '0');
      statusSecondsShift    : in  slv(31 downto 0)    := (others => '0');
      statusTsLatch         : in  slv(63 downto 0)    := (others => '0');
      statusTsFifoTsLow     : in  slv(31 downto 0)    := (others => '0');
      statusTsFifoTsHigh    : in  slv(31 downto 0)    := (others => '0');
      statusTsFifoEventCode : in  slv(7 downto 0)     := (others => '0');
      statusTsFifoValid     : in  sl                  := '0';
      statusTsFifoNext      : in  sl                  := '0';
      statusTsFifoWrCnt     : in  slv(8 downto 0)     := (others => '0');
      statusEventRamReset   : in  slv(63 downto 0)    := (others => '0');
      statusEventRamSet     : in  slv(63 downto 0)    := (others => '0');
      statusEventRamPulse   : in  slv(63 downto 0)    := (others => '0');
      statusEventRamInt     : in  slv(63 downto 0)    := (others => '0');
      statusIntFlag         : in  slv(31 downto 0)    := (others => '0');
      statusDbrx            : in  sl                  := '0';
      statusDbrdy           : in  sl                  := '0';
      statusDbcs            : in  sl                  := '0';
      statusRxSize          : in  slv(11 downto 0)    := (others => '0');
      statusDbData          : in  slv(31 downto 0)    := (others => '0');
      statusDbInt           : in  sl                  := '0';
      statusDbIntEna        : in  sl                  := '0';
      configLatchTs         : out sl;
      configPulseControl    : out slv(383 downto 0);
      configPulsePrescale   : out slv(383 downto 0);
      configPulseDelay      : out slv(383 downto 0);
      configPulseWidth      : out slv(383 downto 0);
      configTsFifoRdEna     : out sl;
      configEventRamData    : out slv(31 downto 0);
      configEventRamCs      : out slv(7 downto 0);
      configEventRamAddr    : out slv(7 downto 0);
      configEventRamWe      : out slv(7 downto 0);
      configMapRamPage      : out sl;
      configEvrEnable       : out sl;
      configOutputMap       : out slv(191 downto 0);
      configUSecDivider     : out slv(31 downto 0);
      configIntControl      : out slv(31 downto 0);
      configDbena           : out sl;
      configDbdis           : out sl;
      configDben            : out sl;
      configDbRdAddr        : out slv(8 downto 0);
      configIrqClr          : out slv(31 downto 0);
      configIntEventEn      : out sl;
      configExtEventEn      : out sl;
      configIntEventCode    : out slv(7 downto 0);
      configExtEventCode    : out slv(7 downto 0);
      configIntEventCount   : out slv(31 downto 0));
end entity EvrV1RegWrapper;

architecture mapping of EvrV1RegWrapper is

   constant BUILD_INFO_C : BuildInfoRetType := (
      buildString => (others => (others => '0')),
      fwVersion   => x"A1B2C3D4",
      gitHash     => (others => '0'));

   signal shimClk         : sl;
   signal shimRst         : sl;
   signal axilReadMaster  : AxiLiteReadMasterType;
   signal axilReadSlave   : AxiLiteReadSlaveType;
   signal axilWriteMaster : AxiLiteWriteMasterType;
   signal axilWriteSlave  : AxiLiteWriteSlaveType;

   signal status : EvrV1StatusType;
   signal config : EvrV1ConfigType;

begin

   status.ts              <= statusTs;
   status.secondsShift    <= statusSecondsShift;
   status.tsLatch         <= statusTsLatch;
   status.tsFifoTsLow     <= statusTsFifoTsLow;
   status.tsFifoTsHigh    <= statusTsFifoTsHigh;
   status.tsFifoEventCode <= statusTsFifoEventCode;
   status.tsFifoValid     <= statusTsFifoValid;
   status.tsFifoNext      <= statusTsFifoNext;
   status.tsFifoWrCnt     <= statusTsFifoWrCnt;
   status.intFlag         <= statusIntFlag;
   status.dbrx            <= statusDbrx;
   status.dbrdy           <= statusDbrdy;
   status.dbcs            <= statusDbcs;
   status.rxSize          <= statusRxSize;
   status.dbData          <= statusDbData;
   status.dbInt           <= statusDbInt;
   status.dbIntEna        <= statusDbIntEna;

   GEN_STATUS_RAM : for i in 0 to 1 generate
      status.eventRamReset(i) <= statusEventRamReset(32*i+31 downto 32*i);
      status.eventRamSet(i)   <= statusEventRamSet(32*i+31 downto 32*i);
      status.eventRamPulse(i) <= statusEventRamPulse(32*i+31 downto 32*i);
      status.eventRamInt(i)   <= statusEventRamInt(32*i+31 downto 32*i);
   end generate GEN_STATUS_RAM;

   configLatchTs       <= config.latchTs;
   configTsFifoRdEna   <= config.tsFifoRdEna;
   configEventRamData  <= config.eventRamData;
   configEventRamAddr  <= config.eventRamAddr;
   configMapRamPage    <= config.mapRamPage;
   configEvrEnable     <= config.evrEnable;
   configUSecDivider   <= config.uSecDivider;
   configIntControl    <= config.intControl;
   configDbena         <= config.dbena;
   configDbdis         <= config.dbdis;
   configDben          <= config.dben;
   configDbRdAddr      <= config.dbRdAddr;
   configIrqClr        <= config.irqClr;
   configIntEventEn    <= config.intEventEn;
   configExtEventEn    <= config.extEventEn;
   configIntEventCode  <= config.intEventCode;
   configExtEventCode  <= config.extEventCode;
   configIntEventCount <= config.intEventCount;

   GEN_CONFIG_PULSE : for i in 0 to 11 generate
      configPulseControl(32*i+31 downto 32*i)  <= config.pulseControl(i);
      configPulsePrescale(32*i+31 downto 32*i) <= config.pulsePrescale(i);
      configPulseDelay(32*i+31 downto 32*i)    <= config.pulseDelay(i);
      configPulseWidth(32*i+31 downto 32*i)    <= config.pulseWidth(i);
      configOutputMap(16*i+15 downto 16*i)     <= config.outputMap(i);
   end generate GEN_CONFIG_PULSE;

   GEN_CONFIG_RAM : for i in 0 to 1 generate
      configEventRamCs(4*i+3 downto 4*i) <= config.eventRamCs(i);
      configEventRamWe(4*i+3 downto 4*i) <= config.eventRamWe(i);
   end generate GEN_CONFIG_RAM;

   U_SlaveShim : entity surf.SlaveAxiLiteIpIntegrator
      generic map (
         EN_ERROR_RESP => true,
         HAS_WSTRB     => 1,
         ADDR_WIDTH    => 15)
      port map (
         S_AXI_ACLK      => axilClk,
         S_AXI_ARESETN   => not axilRst,
         S_AXI_AWADDR    => S_AXI_AWADDR,
         S_AXI_AWPROT    => S_AXI_AWPROT,
         S_AXI_AWVALID   => S_AXI_AWVALID,
         S_AXI_AWREADY   => S_AXI_AWREADY,
         S_AXI_WDATA     => S_AXI_WDATA,
         S_AXI_WSTRB     => S_AXI_WSTRB,
         S_AXI_WVALID    => S_AXI_WVALID,
         S_AXI_WREADY    => S_AXI_WREADY,
         S_AXI_BRESP     => S_AXI_BRESP,
         S_AXI_BVALID    => S_AXI_BVALID,
         S_AXI_BREADY    => S_AXI_BREADY,
         S_AXI_ARADDR    => S_AXI_ARADDR,
         S_AXI_ARPROT    => S_AXI_ARPROT,
         S_AXI_ARVALID   => S_AXI_ARVALID,
         S_AXI_ARREADY   => S_AXI_ARREADY,
         S_AXI_RDATA     => S_AXI_RDATA,
         S_AXI_RRESP     => S_AXI_RRESP,
         S_AXI_RVALID    => S_AXI_RVALID,
         S_AXI_RREADY    => S_AXI_RREADY,
         axilClk         => shimClk,
         axilRst         => shimRst,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave);

   U_EvrV1Reg : entity lcls_timing_core.EvrV1Reg
      generic map (
         TPD_G              => TPD_G,
         BUILD_INFO_G       => toSlv(BUILD_INFO_C),
         USE_WSTRB_G        => USE_WSTRB_G,
         LATCH_TS_LATENCY_G => LATCH_TS_LATENCY_G)
      port map (
         irqActive      => irqActive,
         irqEnable      => irqEnable,
         irqReq         => irqReq,
         axiReadMaster  => axilReadMaster,
         axiReadSlave   => axilReadSlave,
         axiWriteMaster => axilWriteMaster,
         axiWriteSlave  => axilWriteSlave,
         status         => status,
         config         => config,
         axiClk         => shimClk,
         axiRst         => shimRst);

end architecture mapping;
