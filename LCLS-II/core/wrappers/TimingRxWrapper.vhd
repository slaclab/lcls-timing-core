-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only wrapper that flattens the TimingRxType input, the
--              TimingPhyStatusType and TimingPhyControlType records, the
--              timing stream, timing message and extension outputs of
--              TimingRx into plain sl and slv ports, and exposes its AXI-Lite
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
use lcls_timing_core.TimingPkg.all;

entity TimingRxWrapper is
   generic (
      TPD_G             : time                 := 1 ns;
      DEFAULT_CLK_SEL_G : natural range 0 to 1 := 1;
      CLKSEL_MODE_G     : string               := "SELECT");
   port (
      rxClk                : in  sl;
      txClk                : in  sl;
      rxData               : in  slv(15 downto 0);
      rxDataK              : in  slv(1 downto 0);
      rxDecErr             : in  slv(1 downto 0) := "00";
      rxDspErr             : in  slv(1 downto 0) := "00";
      rxStatusLocked       : in  sl              := '1';
      rxStatusResetDone    : in  sl              := '1';
      rxStatusBufferByDone : in  sl              := '0';
      rxStatusBufferByErr  : in  sl              := '0';
      rxControlReset       : out sl;
      rxControlInhibit     : out sl;
      rxControlPolarity    : out sl;
      rxControlBufferByRst : out sl;
      rxControlPllReset    : out sl;
      timingClkSel         : out sl;
      timingModeSel        : out sl;
      timingStreamUser     : out slv(TIMING_STREAM_BITS_C-1 downto 0);
      timingStreamPrompt   : out slv(TIMING_STREAM_BITS_C-1 downto 0);
      timingStreamStrobe   : out sl;
      timingStreamValid    : out sl;
      timingMessage        : out slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      timingMessageStrobe  : out sl;
      timingMessageValid   : out sl;
      extensionValid       : out slv(15 downto 1);
      axilClk              : in  sl;
      axilRst              : in  sl;
      S_AXI_AWADDR         : in  slv(11 downto 0);
      S_AXI_AWPROT         : in  slv(2 downto 0);
      S_AXI_AWVALID        : in  sl;
      S_AXI_AWREADY        : out sl;
      S_AXI_WDATA          : in  slv(31 downto 0);
      S_AXI_WSTRB          : in  slv(3 downto 0);
      S_AXI_WVALID         : in  sl;
      S_AXI_WREADY         : out sl;
      S_AXI_BRESP          : out slv(1 downto 0);
      S_AXI_BVALID         : out sl;
      S_AXI_BREADY         : in  sl;
      S_AXI_ARADDR         : in  slv(11 downto 0);
      S_AXI_ARPROT         : in  slv(2 downto 0);
      S_AXI_ARVALID        : in  sl;
      S_AXI_ARREADY        : out sl;
      S_AXI_RDATA          : out slv(31 downto 0);
      S_AXI_RRESP          : out slv(1 downto 0);
      S_AXI_RVALID         : out sl;
      S_AXI_RREADY         : in  sl);
end entity TimingRxWrapper;

architecture mapping of TimingRxWrapper is

   signal shimClk         : sl;
   signal shimRst         : sl;
   signal axilReadMaster  : AxiLiteReadMasterType;
   signal axilReadSlave   : AxiLiteReadSlaveType;
   signal axilWriteMaster : AxiLiteWriteMasterType;
   signal axilWriteSlave  : AxiLiteWriteSlaveType;

   signal rxDataRec  : TimingRxType;
   signal rxStatus   : TimingPhyStatusType;
   signal rxControl  : TimingPhyControlType;
   signal streamUser : TimingStreamType;
   signal streamProm : TimingStreamType;
   signal message    : TimingMessageType;
   signal extension  : TimingExtensionArray;

begin

   rxDataRec.data   <= rxData;
   rxDataRec.dataK  <= rxDataK;
   rxDataRec.decErr <= rxDecErr;
   rxDataRec.dspErr <= rxDspErr;

   rxStatus.locked       <= rxStatusLocked;
   rxStatus.resetDone    <= rxStatusResetDone;
   rxStatus.bufferByDone <= rxStatusBufferByDone;
   rxStatus.bufferByErr  <= rxStatusBufferByErr;

   rxControlReset       <= rxControl.reset;
   rxControlInhibit     <= rxControl.inhibit;
   rxControlPolarity    <= rxControl.polarity;
   rxControlBufferByRst <= rxControl.bufferByRst;
   rxControlPllReset    <= rxControl.pllReset;

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
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave);

   U_TimingRx : entity lcls_timing_core.TimingRx
      generic map (
         TPD_G             => TPD_G,
         DEFAULT_CLK_SEL_G => ite(DEFAULT_CLK_SEL_G = 1, '1', '0'),
         CLKSEL_MODE_G     => CLKSEL_MODE_G)
      port map (
         rxClk               => rxClk,
         rxData              => rxDataRec,
         rxControl           => rxControl,
         rxStatus            => rxStatus,
         timingClkSel        => timingClkSel,
         timingModeSel       => timingModeSel,
         timingStreamUser    => streamUser,
         timingStreamPrompt  => streamProm,
         timingStreamStrobe  => timingStreamStrobe,
         timingStreamValid   => timingStreamValid,
         timingMessage       => message,
         timingMessageStrobe => timingMessageStrobe,
         timingMessageValid  => timingMessageValid,
         timingExtension     => extension,
         txClk               => txClk,
         axilClk             => shimClk,
         axilRst             => shimRst,
         axilReadMaster      => axilReadMaster,
         axilReadSlave       => axilReadSlave,
         axilWriteMaster     => axilWriteMaster,
         axilWriteSlave      => axilWriteSlave);

   timingStreamUser   <= toSlv(streamUser);
   timingStreamPrompt <= toSlv(streamProm);
   timingMessage      <= toSlv(message);

   GEN_EXT : for i in 1 to 15 generate
      extensionValid(i) <= extension(i).valid;
   end generate GEN_EXT;

end architecture mapping;
