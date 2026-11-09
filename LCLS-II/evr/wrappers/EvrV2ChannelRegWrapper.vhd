-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the channelConfig array output and
--              the eventCount input of EvrV2ChannelReg into plain slv ports,
--              with element i in bits 81*i+80 downto 81*i (config) and
--              32*i+31 downto 32*i (eventCount), and exposes its AXI-Lite
--              slave as flat S_AXI ports through the surf
--              SlaveAxiLiteIpIntegrator. This file is never loaded by any
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

entity EvrV2ChannelRegWrapper is
   generic (
      TPD_G        : time     := 1 ns;
      NCHANNELS_G  : positive := 1;
      EVR_CARD_G   : boolean  := false;
      DMA_ENABLE_G : boolean  := false);
   port (
      axilClk       : in  sl;
      axilRst       : in  sl;
      S_AXI_AWADDR  : in  slv(15 downto 0);
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
      S_AXI_ARADDR  : in  slv(15 downto 0);
      S_AXI_ARPROT  : in  slv(2 downto 0);
      S_AXI_ARVALID : in  sl;
      S_AXI_ARREADY : out sl;
      S_AXI_RDATA   : out slv(31 downto 0);
      S_AXI_RRESP   : out slv(1 downto 0);
      S_AXI_RVALID  : out sl;
      S_AXI_RREADY  : in  sl;
      channelConfig : out slv(NCHANNELS_G*EVRV2_CHANNEL_CONFIG_BITS_C-1 downto 0);
      eventCount    : in  slv(NCHANNELS_G*32-1 downto 0) := (others => '0'));
end entity EvrV2ChannelRegWrapper;

architecture mapping of EvrV2ChannelRegWrapper is

   signal shimClk         : sl;
   signal shimRst         : sl;
   signal axilReadMaster  : AxiLiteReadMasterType;
   signal axilReadSlave   : AxiLiteReadSlaveType;
   signal axilWriteMaster : AxiLiteWriteMasterType;
   signal axilWriteSlave  : AxiLiteWriteSlaveType;

   signal channelConfigArr : EvrV2ChannelConfigArray(NCHANNELS_G-1 downto 0);
   signal eventCountArr    : Slv32Array(NCHANNELS_G-1 downto 0);

begin

   U_SlaveShim : entity surf.SlaveAxiLiteIpIntegrator
      generic map (
         EN_ERROR_RESP => true,
         ADDR_WIDTH    => 16)
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

   GEN_CHAN : for i in 0 to NCHANNELS_G-1 generate
      channelConfig(EVRV2_CHANNEL_CONFIG_BITS_C*i+EVRV2_CHANNEL_CONFIG_BITS_C-1 downto EVRV2_CHANNEL_CONFIG_BITS_C*i) <= toSlv(channelConfigArr(i));
      eventCountArr(i)                                                                                                <= eventCount(32*i+31 downto 32*i);
   end generate GEN_CHAN;

   U_EvrV2ChannelReg : entity lcls_timing_core.EvrV2ChannelReg
      generic map (
         TPD_G        => TPD_G,
         NCHANNELS_G  => NCHANNELS_G,
         EVR_CARD_G   => EVR_CARD_G,
         DMA_ENABLE_G => DMA_ENABLE_G)
      port map (
         axiClk          => shimClk,
         axiRst          => shimRst,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         channelConfig   => channelConfigArr,
         eventCount      => eventCountArr);

end architecture mapping;
