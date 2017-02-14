------------------------------------------------------------------------------
-- Title         : Timing pattern generator
-- Project       : LCLS-II Timing System
-------------------------------------------------------------------------------
-- File          : TPGCore.vhd
-- Author        : Matt Weaver, weaver@slac.stanford.edu
-- Created       : 09/15/2015
-------------------------------------------------------------------------------
-- Description:
-- Timing pattern generator core
-- The base rate trigger ("baseEnable") runs at 1/200th of the tx interface
--    The sequence of evaluations is:
--    ==  baseEnable='1':
--    latch and serialize the outgoing frame;
--    update pulseId, timestamp, resync, syncStatus, acRates, fixedRates;
--    == baseEnable='1' +1 clks: 
--    latch new jumps;
--    == baseEnable='1' +2 clks: 
--    read next sequence instruction and sequence results;
--    == baseEnable='1' +5 clks: 
--    test sequence sync conditions (depends on markers)
--    == baseEnable='1' +19 clks:
--    update bsa control words (depends on sequence results)
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
-- 09/15/2015: created.
-------------------------------------------------------------------------------
library ieee;
use work.all;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.all;
use work.TPGPkg.all;
use work.StdRtlPkg.all;
use work.TimingPkg.all;
use work.AxiStreamPkg.all;
use work.AmcCarrierPkg.all;

entity TPGCore is
  generic (
    ASYNC_REGCLK_G : boolean := false;
    ALLOWSEQDEPTH: integer := 2;
    BEAMSEQDEPTH : integer := 2;
    EXPSEQDEPTH  : integer := 1;
    NARRAYSBSA   : integer := 2
    );
  port (
    -- Clock and reset
    sysClk   : in sl;
    sysReset : in sl;

    statusO : out TPGStatusType;
    configI : in  TPGConfigType;

    txClk      : in  sl;
    txRst      : in  sl;
    txRdy      : in  sl;
    txData     : out slv(15 downto 0);
    txDataK    : out slv(1 downto 0);
    txPolarity : out sl;
    extTrigger : in  ExternalTrigType;
    
    adcData    : in  Slv32Array(2 downto 0) := (others=>x"00000000");
    adcValid   : in  slv       (2 downto 0) := "000";
    
    mps        : in  MpsMitigationMsgType := MPS_MITIGATION_MSG_INIT_C;
    bcs        : in  sl := '0';
    
    rxClk   : in sl;
    rxRst   : in sl;
    rxData  : in slv(15 downto 0);
    rxDataK : in slv(1 downto 0);
    rxStatus: in slv(31 downto 0);

    diagClk : out sl;
    diagRst : out sl;
    diagBus : out DiagnosticBusType;
    diagMa  : out AxiStreamMasterType );
end TPGCore;


-- Define architecture for top level module
architecture TPGCore of TPGCore is

  type RegType is record
    extTrigger  : ExternalTrigType;
    seqstate    : SequencerState;
    index       : SeqAddrType;
    master      : AxiStreamMasterType;
    txRdy       : sl;
    count       : slv( 8 downto 0);
    pulseId     : slv(63 downto 0);
    acTS        : slv( 2 downto 0);
    acTSPhase   : slv(11 downto 0);
    baseEnable  : slv(30 downto 0);
    count186M   : slv(31 downto 0);
    countSyncE  : slv(31 downto 0);
    pllChanged  : slv(31 downto 0);
    countTrig   : Slv32Array(11 downto 0);
    countBRT    : slv(31 downto 0);
    intervalCnt : slv(31 downto 0);
    countTrigL  : Slv32Array(11 downto 0);
    countBRTL   : slv(31 downto 0);
    countSeqL   : Slv32Array(MAXSEQDEPTH-1 downto 0);
    ctrvalv     : Slv32Array(MAXCOUNTERS-1 downto 0);
    countRst    : sl;
    outofSync   : sl;
  end record;

  constant REG_INIT_C : RegType := (
    extTrigger  => EXTERNAL_TRIG_INIT_C,
    seqstate    => SEQUENCER_STATE_INIT_C,
    index       => (others=>'0'),
    master      => AXI_STREAM_MASTER_INIT_C,
    txRdy       => '0',
    count       => (others=>'0'),
    pulseId     => (others=>'0'),
    acTS        => "001",
    acTSPhase   => (others=>'0'),
    baseEnable  => (others=>'0'),
    count186M   => (others=>'0'),
    countSyncE  => (others=>'0'),
    pllChanged  => (others=>'0'),
    countTrig   => (others=>(others=>'0')),
    countBRT    => (others=>'0'),
    intervalCnt => (others=>'0'),
    countTrigL  => (others=>(others=>'0')),
    countBRTL   => (others=>'0'),
    countSeqL   => (others=>(others=>'0')),
    ctrvalv     => (others=>(others=>'0')),
    countRst    => '0',
    outofSync   => '0' );

  signal r                       : RegType := REG_INIT_C;
  signal rin                     : RegType;
  
  signal frame                   : TimingMessageType := TIMING_MESSAGE_INIT_C;

  signal trigger360              : sl;  -- 360Hz strobe synced to tx clk
  signal triggerTS1              : sl;  --  60Hz strobe synced to tx clk
  signal extTriggerSync          : ExternalTrigType;
  
  signal baseEnable              : sl;
  signal baseEnableu             : sl;

  constant ACRateWidth           : integer := 8;
  constant ACRateDepth           : integer := ACRATEDEPTH;

  constant FixedRateWidth        : integer := 20;
  constant FixedRateDepth        : integer := FIXEDRATEDEPTH;

  signal SeqNotify    : SeqAddrArray(Seq'range);
  signal SeqNotifyWr  : slv(Seq'range);
  signal SeqNotifyAck : slv(Seq'range);
  signal seqJump      : slv(Seq'range);
  signal seqJumpAddr  : SeqAddrArray(Seq'range);
  signal SeqData      : Slv17Array(Seq'range);
  signal seqReset     : slv(Seq'range);
  signal bcsLatch     : slv(Allow'range);

  signal syncReset : sl;

  -- Interval counters
  signal ctrvalv               : Slv32Array(MAXCOUNTERS-1 downto 0);
  signal countSeq              : Slv32Array(MAXSEQDEPTH-1 downto 0);
  
  signal rxCounters            : SlVectorArray(13 downto 0, 31 downto 0);
  signal rxClkToggle           : slv(1 downto 0) := "00";
  signal debug                 : slv(1 downto 0);

  -- Delay registers (for closing timing)
  signal status : TPGStatusType;
  signal config : TPGConfigType;

  -- Async messaging
  signal obDebugMaster : AxiStreamMasterType := AXI_STREAM_MASTER_INIT_C;     

  -- Register delay for simulation
  constant tpd : time := 0.5 ns;

  constant TPG_ID : integer := 0;
  
  signal streams   : TimingSerialArray(0 downto 0);
  signal streamIds : Slv4Array(0 downto 0);
  signal advance   : slv(0 downto 0);

  signal acDelay   : slv(15 downto 0);

  signal adcDataS  : Slv32Array(2 downto 0);
  signal adcValdS  : slv       (2 downto 0);
  
begin

  --  Diagnostic and BSA data
  diagClk                         <= txClk;
  diagRst                         <= txRst;
  -- synchronize BSA where it is stable
  diagBus.strobe                  <= r.baseEnable(21);
  diagBus.data(26 downto 0)       <= toSlv32(resize(toSlv(frame)(TIMING_MESSAGE_BITS_C-1 downto 16),27*diagBus.data'length));
  diagBus.fixed(26 downto 0)      <= (others=>'1');
  diagBus.sevr (26 downto 0)      <= (others=>"00");

  GEN_ADCDIAG : for i in 0 to 2 generate
    diagBus.data (27+i)           <= adcDataS(i);
    diagBus.fixed(27+i)           <= '0';
    diagBus.sevr (27+i)           <= "00" when adcValdS(i)='1' else "11";
  end generate;
  
  diagBus.data(30)                <= toSlv(0,28) &
                                     r.extTrigger.strobe71k &
                                     r.extTrigger.strobe360 &
                                     r.extTrigger.strobe60  &
                                     r.extTrigger.strobe1Hz;
  diagBus.data (31)               <= x"deadbeef";
  diagBus.fixed(31 downto 30)     <= "11";
  diagBus.sevr (31 downto 30)     <= (others=>"00");

  diagBus.timingMessage           <= frame;

  frame.bcsFault(0)               <= bcsLatch(0);
  frame.beamEnergy                <= config.beamEnergy;
  
  -- Dont know about these inputs yet
  frame.calibrationGap            <= '0';

  txPolarity                      <= config.txPolarity;
  
  -- resources
  status.nbeamseq    <= toSlv(BEAMSEQDEPTH, 6);
  status.nexptseq    <= toSlv(EXPSEQDEPTH , 8);
  status.narraysbsa  <= toSlv(NARRAYSBSA  , 8);
  status.seqaddrlen  <= toSlv(SEQADDRLEN  , 4);
  status.nallowseq   <= toSlv(ALLOWSEQDEPTH,6);

  status.pulseId    <= frame.pulseId;
  status.outOfSync  <= frame.syncStatus;
  status.bcsFault   <= frame.bcsFault;
  status.pllChanged <= r.pllChanged;
  status.count186M  <= r.count186M;
  status.countSyncE <= r.countSyncE;

  acDelay <= ('0' & config.acDelay) when config.acMaster = '0' else
             x"0000";
  
  --  Sample 60Hz strobe each 71kHz cycle
  --  Delay and assert one 186MHz cycle
  --
  U_ACDelay60 : entity work.SyncDelay
    port map ( clk        => txClk,
               rst        => txRst,
               enable     => baseEnable,      -- count enable
               delay      => acDelay,
               ivalid     => r.extTrigger.strobe60,  -- input
               istrobe    => r.extTrigger.strobe71k, -- 71kHz strobe
               ovalid     => triggerTS1 );  -- output asserted

  U_ACDelay360 : entity work.SyncDelay
    port map ( clk        => txClk,
               rst        => txRst,
               enable     => baseEnable,      -- count enable
               delay      => acDelay,
               ivalid     => r.extTrigger.strobe360,  -- input
               istrobe    => r.extTrigger.strobe71k,  -- 71kHz strobe
               ovalid     => trigger360 );  -- output asserted
  
  status.rxClkCnt <= muxSlVectorArray(rxCounters,12);
  status.rxDVCnt  <= muxSlVectorArray(rxCounters,13);

  U_LCLSI_Status : entity work.SyncStatusVector
    generic map (
      TPD_G         => tpd,
      IN_POLARITY_G => "11111111111111",
      CNT_WIDTH_G   => 32,
      WIDTH_G       => 14)
    port map (
      statusIn(11 downto 0)   => rxStatus(11 downto 0),
      statusIn(12)            => rxClkToggle(1),
      statusIn(13)            => '0',
      statusOut(13 downto 12) => debug,
      statusOut(11 downto  0) => status.rxStatus,
      cntRstIn     => '0',
      rollOverEnIn => "11111111111111",
      cntOut       => rxCounters,
      wrClk        => rxClk,
      wrRst        => '0',
      rdClk        => txClk,
      rdRst        => txRst );
  
  U_Resync : entity work.TPGResync
    port map (
      clk       => txClk,
      rst       => txRst,
      forceI    => config.forceSync,
      resyncI   => r.extTrigger.strobe71k,
      baseI     => baseEnable,
      syncReset => syncReset,
      resyncO   => frame.resync,
      outOfSync => frame.syncStatus);

  BaseEnableDivider : entity work.Divider
    generic map (
      Width => 16)
    port map (
      sysClk   => txClk,
      sysReset => syncReset,
      enable   => '1',
      clear    => '0',
      divisor  => config.baseDivisor,
      trigO    => baseEnableu);

  BaseEnableDelay : entity work.SyncDelay
    port map ( clk        => txClk,
               rst        => txRst,
               enable     => '1',
               delay      => config.frameDelay,
               ivalid     => '0',
               istrobe    => baseEnableu,
               ostrobe    => baseEnable );
  
  ACDivider_loop : for i in 0 to ACRateDepth-1 generate
    U_ACDivider_1 : entity work.ACDivider
      generic map (
        Width => ACRateWidth)
      port map (
        sysClk   => txClk,
        sysReset => syncReset,
        enable   => triggerTS1,
        clear    => baseEnable,
        repulse  => trigger360,
        divisor  => config.ACRateDivisors(i),
        trigO    => frame.acRates(i));
  end generate ACDivider_loop;

  FixedDivider_loop : for i in 0 to FixedRateDepth-1 generate
    U_FixedDivider_1 : entity work.Divider
      generic map (
        Width => FixedRateWidth)
      port map (
        sysClk   => txClk,
        sysReset => txRst,
        enable   => baseEnable,
        clear    => '0',
        divisor  => config.FixedRateDivisors(i),
        trigO    => frame.fixedRates(i));
  end generate FixedDivider_loop;

  Seq_loop : for i in Seq'range generate

    --  all jumps
    Seq_Allow: if ((i>=Allow'right and i<Allow'right+ALLOWSEQDEPTH)) generate
      U_Jump_i : entity work.SeqJump
        port map (
          clk      => txClk,
          rst      => txRst,
          config   => config.seqJumpConfig(i),
          manReset => seqReset(i),
          bcsFault => bcs,
          mpsFault => mps.strobe,
          mpsClass => mps.class(i),
          jumpEn   => r.baseEnable(0),
          jumpReq  => seqJump(i),
          jumpAddr => seqJumpAddr(i),
          bcsLatch => bcsLatch(i),
          mpsLimit => frame.mpsLimit(i),
          outClass => frame.mpsClass(i));
    end generate Seq_Allow;

    --  manual jump only
    Seq_Others: if ((i>=Beam 'right and i<Beam 'right+BEAMSEQDEPTH) or
                    (i>=Expt 'right and i<Expt 'right+EXPSEQDEPTH)) generate
      U_Jump_i : entity work.SeqJump
        port map (
          clk      => txClk,
          rst      => txRst,
          config   => config.seqJumpConfig(i),
          manReset => seqReset(i),
          bcsFault => '0',
          mpsFault => '0',
          mpsClass => (others=>'0'),
          jumpEn   => r.baseEnable(0),
          jumpReq  => seqJump(i),
          jumpAddr => seqJumpAddr(i));
    end generate Seq_Others;
    
    Seq_Gen: if ((i>=Allow'right and i<Allow'right+ALLOWSEQDEPTH) or
                 (i>=Beam 'right and i<Beam 'right+BEAMSEQDEPTH) or
                 (i>=Expt 'right and i<Expt 'right+EXPSEQDEPTH)) generate
      --  Latch and synchronously assert the manual reset
      U_SeqRst : entity work.SeqReset
        port map (
          clk      => txClk,
          rst      => txRst,
          config   => config.seqJumpConfig(i),
          frame    => frame,
          strobe   => r.baseEnable(0),
          resetReq => config.SeqRestart(i),
          resetO   => seqReset(i));
      
      U_Seq_i : entity work.Sequence
        port map (
          clkA         => txClk,
          rstA         => txRst,
          wrEnA        => config.seqWrEn(i),
          indexA       => config.seqAddr,
          rdStepA      => status.seqRdData(i),
          wrStepA      => config.seqWrData,
          clkB         => txClk,
          rstB         => txRst,
          rdEnB        => r.baseEnable(1),
          waitB        => r.baseEnable(4),
          acTS         => frame.acTimeSlot,
          acRate       => frame.acRates,
          fixedRate    => frame.fixedRates,
          seqReset     => seqJump(i),
          startAddr    => seqJumpAddr(i),
          seqState     => status.seqState(i),
          seqNotify    => SeqNotify(i),
          seqNotifyWr  => SeqNotifyWr(i),
          seqNotifyAck => SeqNotifyAck(i),
          dataO        => SeqData(i),
          monReset     => r.countRst,
          monCount     => countSeq(i));
    end generate;

    NoSeq_Gen: if not ((i>=Allow'right and i<Allow'right+ALLOWSEQDEPTH) or
                 (i>=Beam 'right and i<Beam 'right+BEAMSEQDEPTH) or
                 (i>=Expt 'right and i<Expt 'right+EXPSEQDEPTH)) generate
      status.seqRdData(i) <= (others=>'0');
      status.seqState (i) <= SEQUENCER_STATE_INIT_C;
      SeqNotify       (i) <= (others=>'0');
      SeqNotifyWr     (i) <= '0';
      countSeq        (i) <= (others=>'0');
      SeqData         (i) <= (others=>'0');
    end generate;

    NoMps_Gen: if (i>=ALLOWSEQDEPTH and i<=Allow'left) generate
      bcsLatch(i) <= '0';
      frame.mpsLimit(i) <= '0';
      frame.mpsClass(i) <= (others=>'0');
    end generate;
  end generate Seq_loop;

  GEN_EXPT_DATA: for i in MAXEXPSEQDEPTH-1 downto 0 generate
    frame.control(i) <= SeqData(Expt'right+i)(15 downto 0);
  end generate GEN_EXPT_DATA;

  U_DestnArbiter : entity work.DestnArbiter
    port map ( clk          => txClk,
               config       => config,
               configUpdate => config.seqRestart(Beam'range),
               allowSeq     => SeqData(Allow'range),
               beamSeq      => SeqData(Beam'range),
               beamSeqO     => frame.beamRequest,
               beamControl  => open );

  CtrLoop : for i in 0 to MAXCOUNTERS-1 generate
    U_CtrControl : entity work.CtrControl
      generic map (ASYNC_REGCLK_G => ASYNC_REGCLK_G)
      port map (
        sysclk     => txClk,
        sysrst     => txRst,
        ctrdef     => config.ctrdefv(i),
        ctrrst     => r.countRst,
        txclk      => txClk,
        txrst      => txRst,
        enable     => r.baseEnable(19),
        fixedRate  => frame.fixedRates,
        acRate     => frame.acRates,
        acTS       => frame.acTimeSlot,
        beamSeq    => frame.beamRequest,
        expSeq     => frame.control,
        count      => ctrvalv(i) );
  end generate CtrLoop;

  BsaLoop : for i in 0 to NARRAYSBSA-1 generate
    U_BsaControl : entity work.BsaControl
      generic map (ASYNC_REGCLK_G => ASYNC_REGCLK_G)
      port map (
        sysclk     => txClk,
        sysrst     => txRst,
        bsadef     => config.bsadefv(i),
        tmocnt     => config.bsatmo,
        nToAvgOut  => status.bsaStatus(i)(15 downto 0),
        avgToWrOut => status.bsaStatus(i)(31 downto 16),
        txclk      => txClk,
        txrst      => txRst,
        enable     => r.baseEnable(19),
        fixedRate  => frame.fixedRates,
        acRate     => frame.acRates,
        acTS       => frame.acTimeSlot,
        beamSeq    => frame.beamRequest,
        expSeq     => frame.control,
        bsaInit    => frame.bsaInit(i),
        bsaActive  => frame.bsaActive(i),
        bsaAvgDone => frame.bsaAvgDone(i),
        bsaDone    => frame.bsaDone(i));
  end generate BsaLoop;
  
  status.bsaStatus(63 downto NARRAYSBSA) <= (others => (others => '0'));
  frame.bsaInit   (59 downto NARRAYSBSA) <= (others => '0');
  frame.bsaActive (59 downto NARRAYSBSA) <= (others => '0');
  frame.bsaAvgDone(59 downto NARRAYSBSA) <= (others => '0');
  frame.bsaDone   (59 downto NARRAYSBSA) <= (others => '0');

  U_BeamDiag : entity work.BeamDiagControl
    generic map ( NBUFFERS => 4 )
    port map ( clk       => txClk,
               rst       => txRst,
               strobe    => r.baseEnable(0),
               config    => config.beamDiag,
               mpsfault  => mps,
               bcsfault  => bcs,
               status    => status.beamDiag,
               bsaInit   => frame.bsaInit   (63 downto 60),
               bsaActive => frame.bsaActive (63 downto 60),
               bsaAvgDone=> frame.bsaAvgDone(63 downto 60),
               bsaDone   => frame.bsaDone   (63 downto 60) );
  
  U_TSerializer : entity work.TimingSerializer
    generic map ( STREAMS_C => 1 )
    port map ( clk       => txClk,
               rst       => txRst,
               fiducial  => r.baseEnable(0),
               streams   => streams,
               streamIds => streamIds,
               advance   => advance,
               data      => txData,
               dataK     => txDataK );
 
  U_TPSerializer : entity work.TPSerializer
    generic map ( Id => TPG_ID )
    port map (
      txClk      => txClk,
      txRst      => txRst,
      fiducial   => baseEnable,
      msg        => frame,
      advance    => advance  (0),
      stream     => streams  (0),
      streamId   => streamIds(0));

  U_IrqSeqFifo : entity work.IrqSeqFifo
    port map (
      rst    => txRst,
      wrClk  => txClk,
      wrEn   => SeqNotifyWr,
      wrAck  => SeqNotifyAck,
      wrData => SeqNotify,
      rdClk  => sysClk,
      rdEn   => config.irqFifoRd,
      rdData => status.irqFifoData,
      full   => status.irqFifoFull,
      empty  => status.irqFifoEmpty);

  process (rxClk)
  begin
    if rising_edge(rxClk) then
      rxClkToggle <= rxClkToggle+1;
    end if;
  end process;

  comb: process ( r, txRst, txRdy, extTriggerSync, baseEnable,
                  ctrvalv, frame, status, config, countSeq,
                  triggerTS1, trigger360 ) is
    variable v : RegType;
    variable s : SequencerState;
  begin
    v := r;

    v.baseEnable := r.baseEnable(r.baseEnable'left-1 downto 0) & baseEnable;
    v.txRdy      := txRdy;
    v.outOfSync  := frame.syncStatus;
    
    --  Latch external triggers and clear
    if r.baseEnable(0) = '1' and frame.fixedRates(1) = '1' then
      v.extTrigger.strobe360 := '0';
      v.extTrigger.strobe60  := '0';
      v.extTrigger.strobe1Hz := '0';
    end if;
    
    if r.baseEnable(0) = '1' then
      v.extTrigger.strobe71k := '0';
    end if;

    v.extTrigger.strobe71k := v.extTrigger.strobe71k or extTriggerSync.strobe71k;
    v.extTrigger.strobe360 := v.extTrigger.strobe360 or extTriggerSync.strobe360;
    v.extTrigger.strobe60  := v.extTrigger.strobe60  or extTriggerSync.strobe60 ;
    v.extTrigger.strobe1Hz := v.extTrigger.strobe1Hz or extTriggerSync.strobe1Hz;

    s            := status.seqState(conv_integer(config.diagSeq));
    v.index      := s.index;

    v.master.tValid    := '0';
    v.master.tLast     := '0';
    if r.index /= s.index then
      v.master.tValid  := '1';
      if r.count = toSlv(511,9) then
        v.count        := (others=>'0');
        v.master.tLast := '1';
      else
        v.count        := r.count + 1;
      end if;
    end if;

    v.master.tData(63 downto 0) := r.count186M(19 downto 0) &
                                   '0' & slv(s.index) &
                                   s.count(3) &
                                   s.count(2) &
                                   s.count(1) &
                                   s.count(0);
    v.master.tKeep              := x"00FF";
    v.master.tDest              := x"00";
    v.master.tId                := x"00";
    v.master.tUser              := (others=>'0');
    v.master.tStrb              := (others=>'0');

    if config.pulseIdWrEn = '1' then
      v.pulseId                 := config.pulseId;
    elsif baseEnable = '1' then
      v.pulseId                 := r.pulseId+1;
    end if;

    if triggerTS1 = '1' then
      v.acTS := "001";
    elsif trigger360 = '1' then
      v.acTS := r.acTS+1;
    end if;
    
    if trigger360 = '1' then
      v.acTSPhase := (others=>'0');
    elsif baseEnable = '1' then
      v.acTSPhase := r.acTSPhase+1;
    end if;

    v.count186M    := r.count186M+1;
    if (frame.syncStatus = '1' and r.outOfSync = '0') then
      v.countSyncE := r.countSyncE+1;
    end if;

    if txRdy /= r.txRdy then
      v.pllChanged := r.pllChanged+1;
    end if;

    if v.extTrigger.strobe71k = '1' and r.extTrigger.strobe71k = '0' then
      v.countTrig(0) := r.countTrig(0)+1;
    end if;
    if v.extTrigger.strobe360 = '1' and r.extTrigger.strobe360 = '0' then
      v.countTrig(1) := r.countTrig(1)+1;
    end if;
    if v.extTrigger.strobe60 = '1' and r.extTrigger.strobe60 = '0' then
      v.countTrig(2) := r.countTrig(2)+1;
    end if;

    if r.intervalCnt = toSlv(0,32) then
      v.countRst       := '1';
      v.intervalCnt    := config.interval;
      v.countTrigL     := r.countTrig;
      v.countBRTL      := r.countBRT;
      v.countSeqL      := countSeq;
    else
      v.countRst       := '0';
      v.intervalCnt    := r.intervalCnt-1;
    end if;
    
    if r.countRst = '1' then
      v.countTrig := (others=>(others=>'0'));
      v.countBRT  := (others=>'0');
    elsif baseEnable = '1' then
      v.countBRT  := r.countBRT+1;    
    end if;

    if config.ctrlock = '0' then
      v.ctrvalv        := ctrvalv;
    end if;
    
    if txRst = '1' then
      v                := REG_INIT_C;
    end if;

    if config.intervalRst = '1' then
      v.intervalCnt := (others=>'0');
    end if;
    
    rin <= v;

    frame.pulseId         <= r.pulseId;
    frame.acTimeSlot      <= r.acTS;
    frame.acTimeSlotPhase <= r.acTSPhase;
    status.countTrig      <= r.countTrigL;
    status.countBRT       <= r.countBRTL;
    status.countSeq       <= r.countSeqL;
    status.ctrvalv        <= r.ctrvalv;
    diagMa                <= r.master;
  end process comb;

  seq: process ( txClk ) is
  begin
    if rising_edge(txClk) then
      r <= rin;
    end if;
  end process seq;
    
  process (txClk, txRst, r, frame)
    variable countUpdate : slv(1 downto 0);
    variable bsaComplete : Slv64Array(1 downto 0);
    variable bsaDoneQ    : slv(63 downto 0);
  begin  -- process
    bsaDoneQ                      := (others => '0');
    bsaDoneQ(frame.bsaDone'range) := frame.bsaDone;

    if rising_edge(txClk) then
      status.countUpdate <= countUpdate(1);
      countUpdate        := countUpdate(0) & '0';
      status.bsaComplete <= bsaComplete(1);
      bsaComplete        := (bsaComplete(0), (others => '0'));
    end if;
    if txRst = '1' then
      status.countUpdate <= '0';
      status.bsaComplete <= (others => '0');
    end if;
    if r.countRst = '1' then
      countUpdate := "01";
    end if;
    bsaComplete(1) := bsaComplete(1) and not bsaDoneQ;
    bsaComplete(0) := bsaComplete(0) or bsaDoneQ;
  end process;

  
  U_ClockTime : entity work.ClockTime
    generic map (
      FRACTION_DEPTH_G => config.clock_remainder'length )
    port map (
      step      => config.clock_step,
      remainder => config.clock_remainder,
      divisor   => config.clock_divisor,
      rst    => sysReset,
      clkA   => sysClk,
      wrEnA  => config.timeStampWrEn,
      wrData => config.timeStamp,
      rdData => status.timeStamp,
      clkB   => txClk,
      wrEnB  => baseEnable,
      dataO  => frame.timeStamp);

  
  SYNC_71k : entity work.RstSync
    port map ( clk => txClk, asyncRst => extTrigger.strobe71k, syncRst => extTriggerSync.strobe71k);
  SYNC_360 : entity work.RstSync
    port map ( clk => txClk, asyncRst => extTrigger.strobe360, syncRst => extTriggerSync.strobe360);
  SYNC_60  : entity work.RstSync
    port map ( clk => txClk, asyncRst => extTrigger.strobe60 , syncRst => extTriggerSync.strobe60 );
  SYNC_1Hz : entity work.RstSync
    port map ( clk => txClk, asyncRst => extTrigger.strobe1Hz, syncRst => extTriggerSync.strobe1Hz);

  GEN_SYNC_ADC : for i in 0 to 2 generate
    SYNC_ADC : entity work.SynchronizerVector
      generic map ( WIDTH_G => 32 )
      port map ( clk     => txClk,
                 dataIn  => adcData(i),
                 dataOut => adcDataS(i) );
  end generate;

  SYNC_ADCV : entity work.SynchronizerVector
    generic map ( WIDTH_G => 3 )
    port map ( clk     => txClk,
               dataIn  => adcValid,
               dataOut => adcValdS );
  
  GEN_ASYNC: if ASYNC_REGCLK_G=true generate
    U_StatusSync : entity work.StatusSynchronizer
      port map (
        clk     => sysClk,
        rst     => sysReset,
        dataIn  => status,
        dataOut => statusO);
    U_ConfigSync : entity work.ConfigSynchronizer
      port map (
        clk     => txClk,
        rst     => txRst,
        dataIn  => configI,
        dataOut => config);
  end generate GEN_ASYNC;

  GEN_SYNC: if ASYNC_REGCLK_G=false generate
    statusO <= status;
    config  <= configI;
  end generate GEN_SYNC;

end TPGCore;

