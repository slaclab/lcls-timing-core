-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that exposes the AXI-Lite slave of
--              GthRxAlignCheck as flat S_AXI ports through the surf
--              SlaveAxiLiteIpIntegrator, and its AXI-Lite DRP master as flat
--              M_AXI ports through the surf MasterAxiLiteIpIntegrator. The
--              integer DRP_ADDR_G generic is converted to the slv generic of
--              the entity. This file is never loaded by any ruckus.tcl.
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

entity GthRxAlignCheckWrapper is
   generic (
      TPD_G      : time    := 1 ns;
      GT_TYPE_G  : string  := "GTHE3";
      DRP_ADDR_G : natural := 0);
   port (
      txClk         : in  sl;
      rxClk         : in  sl;
      resetIn       : in  sl;
      resetOut      : out sl;
      resetDone     : in  sl;
      resetErr      : in  sl;
      locked        : out sl;
      axilClk       : in  sl;
      axilRst       : in  sl;
      S_AXI_AWADDR  : in  slv(11 downto 0);
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
      S_AXI_ARADDR  : in  slv(11 downto 0);
      S_AXI_ARPROT  : in  slv(2 downto 0);
      S_AXI_ARVALID : in  sl;
      S_AXI_ARREADY : out sl;
      S_AXI_RDATA   : out slv(31 downto 0);
      S_AXI_RRESP   : out slv(1 downto 0);
      S_AXI_RVALID  : out sl;
      S_AXI_RREADY  : in  sl;
      M_AXI_AWADDR  : out slv(11 downto 0);
      M_AXI_AWPROT  : out slv(2 downto 0);
      M_AXI_AWVALID : out sl;
      M_AXI_AWREADY : in  sl;
      M_AXI_WDATA   : out slv(31 downto 0);
      M_AXI_WSTRB   : out slv(3 downto 0);
      M_AXI_WVALID  : out sl;
      M_AXI_WREADY  : in  sl;
      M_AXI_BRESP   : in  slv(1 downto 0);
      M_AXI_BVALID  : in  sl;
      M_AXI_BREADY  : out sl;
      M_AXI_ARADDR  : out slv(11 downto 0);
      M_AXI_ARPROT  : out slv(2 downto 0);
      M_AXI_ARVALID : out sl;
      M_AXI_ARREADY : in  sl;
      M_AXI_RDATA   : in  slv(31 downto 0);
      M_AXI_RRESP   : in  slv(1 downto 0);
      M_AXI_RVALID  : in  sl;
      M_AXI_RREADY  : out sl);
end entity GthRxAlignCheckWrapper;

architecture mapping of GthRxAlignCheckWrapper is

   signal shimClk          : sl;
   signal shimRst          : sl;
   signal mShimClk         : sl;
   signal mShimRst         : sl;
   signal sAxilReadMaster  : AxiLiteReadMasterType;
   signal sAxilReadSlave   : AxiLiteReadSlaveType;
   signal sAxilWriteMaster : AxiLiteWriteMasterType;
   signal sAxilWriteSlave  : AxiLiteWriteSlaveType;
   signal mAxilReadMaster  : AxiLiteReadMasterType;
   signal mAxilReadSlave   : AxiLiteReadSlaveType;
   signal mAxilWriteMaster : AxiLiteWriteMasterType;
   signal mAxilWriteSlave  : AxiLiteWriteSlaveType;

begin

   U_SlaveShim : entity surf.SlaveAxiLiteIpIntegrator
      generic map (
         EN_ERROR_RESP => true,
         ADDR_WIDTH    => 12)
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
         axilReadMaster  => sAxilReadMaster,
         axilReadSlave   => sAxilReadSlave,
         axilWriteMaster => sAxilWriteMaster,
         axilWriteSlave  => sAxilWriteSlave);

   U_MasterShim : entity surf.MasterAxiLiteIpIntegrator
      generic map (
         EN_ERROR_RESP => true,
         ADDR_WIDTH    => 12)
      port map (
         M_AXI_ACLK      => axilClk,
         M_AXI_ARESETN   => not axilRst,
         M_AXI_AWADDR    => M_AXI_AWADDR,
         M_AXI_AWPROT    => M_AXI_AWPROT,
         M_AXI_AWVALID   => M_AXI_AWVALID,
         M_AXI_AWREADY   => M_AXI_AWREADY,
         M_AXI_WDATA     => M_AXI_WDATA,
         M_AXI_WSTRB     => M_AXI_WSTRB,
         M_AXI_WVALID    => M_AXI_WVALID,
         M_AXI_WREADY    => M_AXI_WREADY,
         M_AXI_BRESP     => M_AXI_BRESP,
         M_AXI_BVALID    => M_AXI_BVALID,
         M_AXI_BREADY    => M_AXI_BREADY,
         M_AXI_ARADDR    => M_AXI_ARADDR,
         M_AXI_ARPROT    => M_AXI_ARPROT,
         M_AXI_ARVALID   => M_AXI_ARVALID,
         M_AXI_ARREADY   => M_AXI_ARREADY,
         M_AXI_RDATA     => M_AXI_RDATA,
         M_AXI_RRESP     => M_AXI_RRESP,
         M_AXI_RVALID    => M_AXI_RVALID,
         M_AXI_RREADY    => M_AXI_RREADY,
         axilClk         => mShimClk,
         axilRst         => mShimRst,
         axilReadMaster  => mAxilReadMaster,
         axilReadSlave   => mAxilReadSlave,
         axilWriteMaster => mAxilWriteMaster,
         axilWriteSlave  => mAxilWriteSlave);

   U_GthRxAlignCheck : entity lcls_timing_core.GthRxAlignCheck
      generic map (
         TPD_G      => TPD_G,
         GT_TYPE_G  => GT_TYPE_G,
         DRP_ADDR_G => toSlv(DRP_ADDR_G, 32))
      port map (
         txClk            => txClk,
         rxClk            => rxClk,
         resetIn          => resetIn,
         resetOut         => resetOut,
         resetDone        => resetDone,
         resetErr         => resetErr,
         locked           => locked,
         axilClk          => shimClk,
         axilRst          => shimRst,
         mAxilReadMaster  => mAxilReadMaster,
         mAxilReadSlave   => mAxilReadSlave,
         mAxilWriteMaster => mAxilWriteMaster,
         mAxilWriteSlave  => mAxilWriteSlave,
         sAxilReadMaster  => sAxilReadMaster,
         sAxilReadSlave   => sAxilReadSlave,
         sAxilWriteMaster => sAxilWriteMaster,
         sAxilWriteSlave  => sAxilWriteSlave);

end architecture mapping;
