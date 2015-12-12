-------------------------------------------------------------------------------
-- Title      : TPGPkg
-------------------------------------------------------------------------------
-- File       : TPGPkg.vhd
-- Author     : Matt Weaver  <weaver@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-15
-- Last update: 2015-11-19
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: Package of constants and record definitions for the Timing Geneartor.
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.all;
use IEEE.NUMERIC_STD.all;
use ieee.math_real.all;
use work.StdRtlPkg.all;

package TPGPkg is

  constant FIXEDRATEDEPTH : integer := 10;   -- number of fixed rate markers
  constant ACRATEDEPTH    : integer :=  6;   -- number of ac rate markers
  constant MAXBEAMSEQDEPTH : integer :=  7;   -- max number of beam destination sequences
  constant BEAMSEQWIDTH   : integer := 32;   -- number of bits in beam sequence data
  constant BEAMPRIOBITS   : integer :=  4;   -- number of bits in beam priority word
  constant MAXEXPSEQDEPTH    : integer :=  18;   -- max number of expt sequences
  constant EXPSEQWIDTH    : integer := 32;   -- number of bits in expt sequence
  constant EXPPARTITIONS  : integer :=  8;   -- number of expt partitions
  constant MAXSEQDEPTH       : integer := MAXBEAMSEQDEPTH+MAXEXPSEQDEPTH;
  constant SEQADDRLEN     : integer := 11;  -- sequencer address bus width
  constant SEQCOUNTDEPTH  : integer := 4;   -- counters within a sequencer (depth of nested loops)
  constant BCSWIDTH       : integer := 6;
  constant MPSDEPTH       : integer := 5;
  constant MPSWIDTH       : integer := 6;
  constant MAXARRAYSBSA   : integer := 50;
  constant NTRIGGERSIN    : integer := 12;
  constant MPSCHAN        : integer := 14;
  
  type BsaDefType is record
                   nToAvg  : slv(15 downto 0);
                   avgToWr : slv(15 downto 0);
                   rateSel : slv(15 downto 0);
                   -- Bits(15:14)=(fixed,AC,seq,reserved)
                   -- fixed:  marker = 3:0
                   -- AC   :  marker = 2:0;  TS = 8:3 (mask)
                   -- seq  :  bit    = 5:0;  seq = 10:6
                   destSel : slv(15 downto 0);
                   -- 15:15 = DONT_CARE
                   --  3:0  = Destination
                   init    : sl;
                 end record;

  type BsaDefArray is array(natural range<>) of BsaDefType;

  --  Address into BRAM for sequence engines
  type SeqAddrType is array(SEQADDRLEN-1 downto 0) of sl;
  type SeqAddrArray is array(natural range<>) of SeqAddrType;
  
  type L1TrigConfig is record
                         evcode : slv(7 downto 0);
                         delay  : slv(31 downto 0);
                       end record;
  
  constant L1TRIGCONFIG_INIT_C : L1TrigConfig := (
    evcode => (others=>'1'),
    delay  => (others=>'1') );

  type L1TrigConfigArray  is array (natural range <>) of L1TrigConfig;

  type TPGJumpConfigType is record
                          trgEn   : sl;
                          trgSel  : slv(2 downto 0);
                          trgJump : SeqAddrType;
                          bcsEn   : sl;
                          bcsJump : SeqAddrType;
                          mpsEn   : slv(13 downto 0);
                          mpsJump : SeqAddrArray(MPSCHAN-1 downto 0);
                        end record;

  type TPGJumpConfigArray  is array (natural range <>) of TPGJumpConfigType;

  type SequencerState is record
                              index   : SeqAddrType;
                              count   : Slv8Array(SEQCOUNTDEPTH-1 downto 0);
                            end record;

  type SequencerStateArray  is array (natural range <>) of SequencerState;

  type TPGStatusType is record
                          -- implemented resources
                          nbeamseq      : slv (7 downto 0);
                          nexptseq      : slv (7 downto 0);
                          narraysbsa    : slv (7 downto 0);
                          seqaddrlen    : slv (3 downto 0);
                          fifoaddrlen   : slv (3 downto 0);
                          --
                          pulseId       : slv(63 downto 0);
                          timeStamp     : slv(63 downto 0);
                          bsaComplete   : slv(63 downto 0);  -- single sysclk pulse
                          outOfSync     : sl;
                          irqFifoFull   : sl;
                          irqFifoEmpty  : sl;
                          irqFifoData   : slv(31 downto 0);
                          fifoEmpty     : sl;
                          fifoFull      : sl;
                          fifoData      : slv(31 downto 0);
                          pllChanged    : slv(31 downto 0);
                          count186M     : slv(31 downto 0);
                          countSyncE    : slv(31 downto 0);
                          countBRT      : slv(31 downto 0);
                          countTrig     : Slv32Array(NTRIGGERSIN-1 downto 0);
                          countSeq      : Slv32Array(MAXSEQDEPTH-1 downto 0);
                          countUpdate   : sl;  -- single sysclk pulse
                          rxStatus      : slv(11 downto 0);
                          rxClkCnt      : slv(31 downto 0);
                          rxDVCnt       : slv(31 downto 0);
                          seqRdData     : Slv32Array(MAXSEQDEPTH-1 downto 0);
                          bsaStatus     : Slv32Array(63 downto 0);
                          seqState      : SequencerStateArray(MAXSEQDEPTH-1 downto 0);
                          bcsFault      : slv(BCSWIDTH-1 downto 0);
                        end record;

  constant SEQUENCER_STATE_INIT_C : SequencerState := (
    index   => (others=>'0'),
    count   => (others=>(others=>'0'))
    );
  
  constant TPG_STATUS_INIT_C : TPGStatusType := (
    nbeamseq      => (others=>'0'),
    nexptseq      => (others=>'0'),
    narraysbsa    => (others=>'0'),
    seqaddrlen    => (others=>'0'),
    fifoaddrlen   => (others=>'0'),
    pulseId       => (others=>'0'),
    timeStamp     => (others=>'0'),
    bsaComplete   => (others=>'0'),
    outOfSync     => '0',
    irqFifoFull   => '0',
    irqFifoEmpty  => '0',
    irqFifoData   => (others=>'0'),
    fifoEmpty     => '0',
    fifoFull      => '0',
    fifoData      => (others=>'0'),
    pllChanged    => (others=>'0'),
    count186M     => (others=>'0'),
    countSyncE    => (others=>'0'),
    countBRT      => (others=>'0'),
    countTrig     => (others=>(others=>'0')),
    countSeq      => (others=>(others=>'0')),
    countUpdate   => '0',
    rxStatus      => (others=>'0'),
    rxClkCnt      => (others=>'0'),
    rxDVCnt       => (others=>'0'),
    seqRdData     => (others=>(others=>'0')),
    bsaStatus     => (others=>(others=>'0')),
    seqState      => (others=>SEQUENCER_STATE_INIT_C),
    bcsFault      => (others=>'0') );
    
  type TPGConfigType is record
                          txPolarity    : sl;
                          baseDivisor   : slv(15 downto 0);
                          pulseId       : slv(63 downto 0);
                          pulseIdWrEn   : sl;
                          timeStamp     : slv(63 downto 0);
                          timeStampWrEn : sl;
                          ACRateDivisors    : Slv8Array(5 downto 0);
                          FixedRateDivisors : Slv20Array(9 downto 0);
                          IntTrigger    : L1TrigConfigArray(6 downto 0);
                          SeqRestart    : slv(MAXSEQDEPTH-1 downto 0);
                          SeqRstAddr    : SeqAddrArray(MAXSEQDEPTH-1 downto 0);
                          histActive    : sl;
                          forceSync     : sl;
                          destnPriority : slv(4*MAXBEAMSEQDEPTH-1 downto 0);
                          irqEnable     : sl;
                          irqFifoEnable : sl;
                          irqIntvEnable : sl;
                          irqBsaEnable  : sl;
                          fifoReset     : sl;
                          fifoSel       : slv(15 downto 0);
                          fifoTrig      : slv(11 downto 0);
                          fifoRead      : sl;
                          irqFifoRd     : sl;
                          bsadefv       : BsaDefArray(MAXARRAYSBSA-1 downto 0);
                          interval      : slv(31 downto 0);
                          intervalRst   : sl;
                          seqAddr       : SeqAddrType;
                          seqWrData     : slv(31 downto 0);
                          seqWrEn       : slv(MAXSEQDEPTH-1 downto 0);
                          seqJumpConfig : TPGJumpConfigArray(MAXSEQDEPTH-1 downto 0);
                        end record;

  constant TPG_JUMPCONFIG_INIT_C : TPGJumpConfigType := (
    trgEn   => '0',
    trgSel  => (others=>'0'),
    trgJump => (others=>'0'),
    bcsEn   => '0',
    bcsJump => (others=>'0'),
    mpsEn   => (others=>'0'),
    mpsJump => (others=>(others=>'0'))
    );
  
  constant TPG_CONFIG_INIT_C : TPGConfigType := (
    txPolarity        => '0',
    baseDivisor       => x"00C8",
    pulseId           => (others=>'0'),
    pulseIdWrEn       => '1',
    timeStamp         => (others=>'0'),
    timeStampWrEn     => '0',
    ACRateDivisors    => (x"00", x"3C", x"0C", x"06", x"02", x"01"),
    FixedRateDivisors => (x"00000",
                          x"00000",
                          x"F4240",
                          x"186A0",
                          x"02710",
                          x"003E8",
                          x"00064",
                          x"0000A",
                          x"00002",
                          x"00001"),
    IntTrigger        => (others=>L1TRIGCONFIG_INIT_C),
    SeqRestart        => (others=>'0'),
    SeqRstAddr        => (others=>(others=>'0')),
    histActive        => '1',
    forceSync         => '0',
    destnPriority     => (others=>'0'),
    irqEnable         => '0',
    irqFifoEnable     => '0',
    irqIntvEnable     => '0',
    irqBsaEnable      => '0',
    fifoReset         => '1',
    fifoSel           => (others=>'1'),
    fifoTrig          => (others=>'0'),
    fifoRead          => '0',
    irqFifoRd         => '0',
    bsadefv           => (others=>(x"0000",x"0000",x"0000",x"0000",'0')),
    interval          => x"0000488b",   -- 100 us
    intervalRst       => '1',
    seqAddr           => (others=>'0'),
    seqWrData         => (others=>'0'),
    seqWrEn           => (others=>'0'),
    seqJumpConfig     => (others=>TPG_JUMPCONFIG_INIT_C)
    );

  type TPGConfigArray is array(natural range<>) of TPGConfigType;
  
end TPGPkg;

package body TPGPkg is
end package body TPGPkg;
