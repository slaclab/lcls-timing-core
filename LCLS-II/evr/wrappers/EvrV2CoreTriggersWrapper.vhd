-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that builds the TimingBusType input of
--              EvrV2CoreTriggers from a strobe, a flat message and a flat
--              stream, flattens the TimingTrigType output into plain slv
--              ports, and exposes its AXI-Lite slave as flat S_AXI ports
--              through the surf SlaveAxiLiteIpIntegrator. This file is never
--              loaded by any ruckus.tcl.
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
use lcls_timing_core.TimingPkg.all;
-- vsg_on use_clause_501

entity EvrV2CoreTriggersWrapper is
   generic (
      TPD_G        : time     := 1 ns;
      NCHANNELS_G  : positive := 1;
      NTRIGGERS_G  : positive := 1;
      TRIG_DEPTH_G : natural  := 28;
      TRIG_PIPE_G  : natural  := 0;
      COMMON_CLK_G : boolean  := false;
      EVR_CARD_G   : boolean  := false);
   port (
      axilClk       : in  sl;
      axilRst       : in  sl;
      S_AXI_AWADDR  : in  slv(19 downto 0);
      S_AXI_AWPROT  : in  slv(2 downto 0);
      S_AXI_AWVALID : in  sl;
      S_AXI_AWREADY : out sl;
      S_AXI_WDATA   : in  slv(31 downto 0);
      S_AXI_WSTRB   : in  slv(3 downto 0);
      S_AXI_WVALID  : in  sl;
      S_AXI_WREADY  : out sl;
      S_AXI_BRESP   : out slv(1 downto 0);
      S_AXI_BVALID  : out sl;
      S_AXI_BREADY  : in  sl;
      S_AXI_ARADDR  : in  slv(19 downto 0);
      S_AXI_ARPROT  : in  slv(2 downto 0);
      S_AXI_ARVALID : in  sl;
      S_AXI_ARREADY : out sl;
      S_AXI_RDATA   : out slv(31 downto 0);
      S_AXI_RRESP   : out slv(1 downto 0);
      S_AXI_RVALID  : out sl;
      S_AXI_RREADY  : in  sl;
      evrClk        : in  sl;
      evrRst        : in  sl;
      evrStrobe     : in  sl;
      evrMessage    : in  slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      evrStream     : in  slv(TIMING_STREAM_BITS_C-1 downto 0);
      evrModeSel    : in  sl := '1';
      trigPulse     : out slv(15 downto 0);
      timeStamp     : out slv(63 downto 0);
      bsa           : out slv(127 downto 0);
      dmod          : out slv(191 downto 0));
end entity EvrV2CoreTriggersWrapper;

architecture mapping of EvrV2CoreTriggersWrapper is

   signal shimClk         : sl;
   signal shimRst         : sl;
   signal axilReadMaster  : AxiLiteReadMasterType;
   signal axilReadSlave   : AxiLiteReadSlaveType;
   signal axilWriteMaster : AxiLiteWriteMasterType;
   signal axilWriteSlave  : AxiLiteWriteSlaveType;

   signal evrBus  : TimingBusType;
   signal trigOut : TimingTrigType;

begin

   U_SlaveShim : entity surf.SlaveAxiLiteIpIntegrator
      generic map (
         EN_ERROR_RESP => true,
         ADDR_WIDTH    => 20)
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

   process (evrMessage, evrStrobe, evrStream) is
      variable busV : TimingBusType;
   begin
      busV         := TIMING_BUS_INIT_C;
      busV.strobe  := evrStrobe;
      busV.message := toTimingMessageType(evrMessage);
      busV.stream  := toTimingStreamType(evrStream);
      evrBus       <= busV;
   end process;

   U_EvrV2CoreTriggers : entity lcls_timing_core.EvrV2CoreTriggers
      generic map (
         TPD_G        => TPD_G,
         NCHANNELS_G  => NCHANNELS_G,
         NTRIGGERS_G  => NTRIGGERS_G,
         TRIG_DEPTH_G => TRIG_DEPTH_G,
         TRIG_PIPE_G  => TRIG_PIPE_G,
         COMMON_CLK_G => COMMON_CLK_G,
         EVR_CARD_G   => EVR_CARD_G)
      port map (
         axilClk         => shimClk,
         axilRst         => shimRst,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         evrClk          => evrClk,
         evrRst          => evrRst,
         evrBus          => evrBus,
         trigOut         => trigOut,
         evrModeSel      => evrModeSel);

   trigPulse <= trigOut.trigPulse;
   timeStamp <= trigOut.timeStamp;
   bsa       <= trigOut.bsa;
   dmod      <= trigOut.dmod;

end architecture mapping;
