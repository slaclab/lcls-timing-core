-------------------------------------------------------------------------------
-- Title      : 
-------------------------------------------------------------------------------
-- File       : TimingMsgAxiRingBuffer.vhd
-- Author     : 
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2014-05-02
-- Last update: 2015-09-15
-- Platform   : Vivado 2013.3
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
--
-------------------------------------------------------------------------------
-- Copyright (c) 2014 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

use work.StdRtlPkg.all;
use work.AxiLitePkg.all;
use work.AxiStreamPkg.all;
use work.SsiPkg.all;

entity TimingMsgAxiRingBuffer is
   generic (
      -- General Configurations
      TPD_G            : time                        := 1 ns;
      BRAM_EN_G        : boolean                     := true;
      REG_EN_G         : boolean                     := true;
      RAM_ADDR_WIDTH_G : positive range 1 to (2**24) := 10);

   port (
      -- Timing Msg interface
      timingClk       : in sl;
      timingRst       : in sl;
      timingMsg       : in TimingMsgType;
      timingMsgStrobe : in sl;

      -- Axi Lite interface for readout
      axilClk         : in  sl;
      axilRst         : in  sl;
      axilReadMaster  : in  AxiLiteReadMasterType  := AXI_LITE_READ_MASTER_INIT_C;
      axilReadSlave   : out AxiLiteReadSlaveType;
      axilWriteMaster : in  AxiLiteWriteMasterType := AXI_LITE_WRITE_MASTER_INIT_C;
      axilWriteSlave  : out AxiLiteWriteSlaveType);

end TimingMsgAxiRingBuffer;

architecture rtl of TimingMsgAxiRingBuffer is

   signal axisMaster : AxiStreamMasterType;

begin

   -- Convert to AxiStream. Easiest way to chunk the timing message into 32 bit segments
   TimingMsgToAxiStream_1 : entity work.TimingMsgToAxiStream
      generic map (
         TPD_G          => TPD_G,
         COMMON_CLOCK_G => true,
         SHIFT_SIZE_G   => 32,
         AXIS_CONFIG_G  => ssiAxiStreamConfig(4))
      port map (
         timingClk       => timingClk,
         timingRst       => timingRst,
         timingMsg       => timingMsg,
         timingMsgStrobe => timingMsgStrobe,
         axisClk         => timingClk,
         axisRst         => timingRst,
         axisMaster      => axisMaster)

      -- Pipe into AxiRingBuffer
      AxiRingBuffer_1 : entity work.AxiRingBuffer
      generic map (
         TPD_G            => TPD_G,
         BRAM_EN_G        => BRAM_EN_G,
         REG_EN_G         => REG_EN_G,
         DATA_WIDTH_G     => 32,
         RAM_ADDR_WIDTH_G => RAM_ADDR_WIDTH_G)
      port map (
         dataClk         => timingClk,
         dataRst         => timingRst,
         dataValid       => axisMaster.tvalid,
         dataValue       => axisMaster.tdata(31 downto 0),
         axilClk         => axilClk,
         axilRst         => axilRst,
         axilReadMaster  => axilReadMaster,
         axilReadSlave   => axilReadSlave,
         axilWriteMaster => axilWriteMaster,
         axilWriteSlave  => axilWriteSlave);

end rtl;
