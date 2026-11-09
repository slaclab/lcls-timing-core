-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the channelConfig array output and
--              the SlVectorArray eventCount input of EvrV2Axi into plain
--              slv ports (config element i in bits 81*i+80 downto 81*i,
--              eventCount row i in bits 32*i+31 downto 32*i, the global
--              count in row CHANNELS_G), and exposes its AXI-Lite slave as
--              flat S_AXI ports through the surf SlaveAxiLiteIpIntegrator
--              with a 9-bit address. This file is never loaded by any
--              ruckus.tcl.
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
use lcls_timing_core.EvrV2Pkg.all;
-- vsg_on use_clause_501

entity EvrV2AxiWrapper is
   generic (
      TPD_G        : time     := 1 ns;
      DMA_ENABLE_G : boolean  := false;
      CHANNELS_G   : positive := 1);
   port (
      axilClk       : in  sl;
      axilRst       : in  sl;
      S_AXI_AWADDR  : in  slv(8 downto 0);
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
      S_AXI_ARADDR  : in  slv(8 downto 0);
      S_AXI_ARPROT  : in  slv(2 downto 0);
      S_AXI_ARVALID : in  sl;
      S_AXI_ARREADY : out sl;
      S_AXI_RDATA   : out slv(31 downto 0);
      S_AXI_RRESP   : out slv(1 downto 0);
      S_AXI_RVALID  : out sl;
      S_AXI_RREADY  : in  sl;
      irqEnable     : out sl;
      channelConfig : out slv(CHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto 0);
      trigSel       : out sl;
      dmaFullThr    : out slv(23 downto 0);
      irqReq        : in  sl                                := '0';
      rstCount      : out sl;
      eventCount    : in  slv((CHANNELS_G+1)*32-1 downto 0) := (others => '0');
      gtxDebug      : in  slv(7 downto 0)                   := (others => '0'));
end entity EvrV2AxiWrapper;

architecture mapping of EvrV2AxiWrapper is

   signal shimClk         : sl;
   signal shimRst         : sl;
   signal axilReadMaster  : AxiLiteReadMasterType;
   signal axilReadSlave   : AxiLiteReadSlaveType;
   signal axilWriteMaster : AxiLiteWriteMasterType;
   signal axilWriteSlave  : AxiLiteWriteSlaveType;

   signal channelConfigArr : EvrV2ChannelConfigArray(CHANNELS_G-1 downto 0);
   signal eventCountArr    : SlVectorArray(CHANNELS_G downto 0, 31 downto 0);

begin

   U_SlaveShim : entity surf.SlaveAxiLiteIpIntegrator
      generic map (
         EN_ERROR_RESP => true,
         ADDR_WIDTH    => 9)
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

   GEN_CHAN : for i in 0 to CHANNELS_G-1 generate
      channelConfig(EVRV2_CHANNEL_CONFIG_BITS_C*i+EVRV2_CHANNEL_CONFIG_BITS_C-1 downto EVRV2_CHANNEL_CONFIG_BITS_C*i) <= toSlv(channelConfigArr(i));
   end generate GEN_CHAN;

   GEN_COUNT_ROW : for i in 0 to CHANNELS_G generate
      GEN_COUNT_BIT : for j in 0 to 31 generate
         eventCountArr(i, j) <= eventCount(32*i+j);
      end generate GEN_COUNT_BIT;
   end generate GEN_COUNT_ROW;

   U_EvrV2Axi : entity lcls_timing_core.EvrV2Axi
      generic map (
         TPD_G        => TPD_G,
         DMA_ENABLE_G => DMA_ENABLE_G,
         CHANNELS_C   => CHANNELS_G)
      port map (
         axiClk          => shimClk,
         axiRst          => shimRst,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         irqEnable       => irqEnable,
         channelConfig   => channelConfigArr,
         trigSel         => trigSel,
         dmaFullThr      => dmaFullThr,
         irqReq          => irqReq,
         rstCount        => rstCount,
         eventCount      => eventCountArr,
         gtxDebug        => gtxDebug);

end architecture mapping;
