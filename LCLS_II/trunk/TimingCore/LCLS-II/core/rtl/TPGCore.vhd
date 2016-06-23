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
    extTrigger : in  slv(4 downto 0);

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

  signal frame                   : TimingMessageType := TIMING_MESSAGE_INIT_C;
  signal diagframe               : TimingMessageType := TIMING_MESSAGE_INIT_C;

  signal trigger360q             : sl;
  signal triggerTS1, triggerTS1q : sl;
  signal triggerResyncq          : sl;
  signal triggerIn               : slv(11 downto 0);
  signal triggerInq              : slv(11 downto 0);
  signal intTrigger              : slv(6 downto 0) := (others=>'0');

  signal baseEnable              : sl;
  signal baseEnabled             : slv(30 downto 0);

  signal pulseIdn                : slv(63 downto 0);

  signal pulseIdWr               : sl;

  signal acTSn                   : slv(2 downto 0);
  signal acTSPhasen              : slv(11 downto 0);

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

  signal pllChanged : slv(31 downto 0) := (others => '0');
  signal count186M  : slv(31 downto 0);
  signal countSyncE : slv(31 downto 0);
  
  -- Interval counters
  signal countRst              : sl;
  signal intervalCnt           : slv(31 downto 0);
  signal countTrig, countTrign : Slv32Array(11 downto 0);
  signal countBRT, countBRTn   : slv(31 downto 0);
  signal countSeq              : Slv32Array(MAXSEQDEPTH-1 downto 0);

  signal rxCounters            : SlVectorArray(13 downto 0, 31 downto 0);
  signal rxClkToggle           : slv(1 downto 0) := "00";
  signal debug                 : slv(1 downto 0);

  -- Delay registers (for closing timing)
  signal status : TPGStatusType;
  signal config : TPGConfigType;

  -- Raw diagnostics
  signal seqstate0 : SequencerState := SEQUENCER_STATE_INIT_C;
  signal tvalid, tlast    : sl;
  signal tdata : slv(63 downto 0);

  -- Async messaging
  signal obDebugMaster : AxiStreamMasterType := AXI_STREAM_MASTER_INIT_C;     

  -- Register delay for simulation
  constant tpd : time := 0.5 ns;

  constant TPG_ID : integer := 0;
  
  signal streams   : TimingSerialArray(0 downto 0);
  signal streamIds : Slv4Array(0 downto 0);
  signal advance   : slv(0 downto 0);

begin

  --  Diagnostic and BSA data
  diagClk                         <= txClk;
  diagRst                         <= txRst;
  -- synchronize BSA where it is stable
  diagBus.strobe                  <= baseEnabled(21);
  diagBus.data(31 downto 27)      <= (others=>x"00000000");
  -- test if BSA is latching data on a different clk
  diagBus.data(26)                <= baseEnabled & baseEnable;
  diagBus.data(25 downto  0)      <= toSlv32(toSlv(frame)(26*32+15 downto 16));
  diagBus.timingMessage           <= diagFrame;

  tvalid <= '1' when seqstate0.index /= status.seqState(0).index else
            '0';
  
  tdata <= status.count186M(19 downto 0) &
           '0' & slv(seqstate0.index) &
           seqstate0.count(3) &
           seqstate0.count(2) &
           seqstate0.count(1) &
           seqstate0.count(0);
  diagMa.tData(63 downto 0)       <= tdata;
  diagMa.tData(127 downto 64)     <= (others=>'0');
  diagMa.tKeep                    <= x"00FF";
  diagMa.tValid                   <= tvalid;
  diagMa.tLast                    <= tlast;
  diagMa.tDest                    <= x"00";
  diagMa.tId                      <= x"00";
  diagMa.tUser                    <= (others=>'0');
  diagMa.tStrb                    <= (others=>'0');
  
  frame.bcsFault(0)               <= bcsLatch(0);
  frame.beamEnergy                <= config.beamEnergy;
  
  -- Dont know about these inputs yet
  frame.calibrationGap            <= '0';

  txPolarity <= config.txPolarity;
  
  triggerTS1q <= trigger360q and triggerTS1;

  -- resources
  status.nbeamseq    <= slv(conv_unsigned(BEAMSEQDEPTH, 8));
  status.nexptseq    <= slv(conv_unsigned(EXPSEQDEPTH , 8));
  status.narraysbsa  <= slv(conv_unsigned(NARRAYSBSA  , 8));
  status.seqaddrlen  <= slv(conv_unsigned(SEQADDRLEN  , 4));
  status.nallowseq   <= slv(conv_unsigned(ALLOWSEQDEPTH,4));

  status.pulseId    <= frame.pulseId;
  status.outOfSync  <= frame.syncStatus;
  status.bcsFault   <= frame.bcsFault;
  status.pllChanged <= pllChanged;
  status.count186M  <= count186M;
  status.countSyncE <= countSyncE;

  triggerIn      <= intTrigger & extTrigger;
  triggerResyncq <= triggerInq(0);
  trigger360q    <= triggerInq(1);
  triggerTS1     <= triggerIn (2);
  triggerTS1q    <= triggerTS1 and trigger360q;

  trigger_edge : for i in triggerIn'range generate
    U_edge : entity work.SynchronizerOneShot
      port map (
        clk     => txClk,
        rst     => txRst,
        dataIn  => triggerIn (i),
        dataOut => triggerInq(i));

    countTrign(i) <= (others => '0') when countRst = '1' else
                     countTrig(i)+1 when triggerInq(i) = '1' else
                     countTrig(i);
  end generate trigger_edge;

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
      resyncI   => triggerResyncq,
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
      trigO    => baseEnable);

  ACDivider_loop : for i in 0 to ACRateDepth-1 generate
    U_ACDivider_1 : entity work.ACDivider
      generic map (
        Width => ACRateWidth)
      port map (
        sysClk   => txClk,
        sysReset => syncReset,
        enable   => triggerTS1q,
        clear    => baseEnable,
        repulse  => trigger360q,
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
          jumpEn   => baseEnabled(0),
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
          jumpEn   => baseEnabled(0),
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
          strobe   => baseEnabled(0),
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
          rdEnB        => baseEnabled(1),
          waitB        => baseEnabled(4),
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
          monReset     => countRst,
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

  BsaLoop : for i in 0 to NARRAYSBSA-1 generate
    U_BsaControl : entity work.BsaControl
      generic map (ASYNC_REGCLK_G => ASYNC_REGCLK_G)
      port map (
        sysclk     => txClk,
        sysrst     => txRst,
        bsadef     => config.bsadefv(i),
        nToAvgOut  => status.bsaStatus(i)(15 downto 0),
        avgToWrOut => status.bsaStatus(i)(31 downto 16),
        txclk      => txClk,
        txrst      => txRst,
        enable     => baseEnabled(19),
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
               strobe    => baseEnabled(0),
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
               fiducial  => baseEnabled(0),
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

  pulseIdn <= config.pulseId when pulseIdWr = '1' else
              frame.pulseId+1 when baseEnable = '1' else
              frame.pulseId;

  acTSn <= "001" when triggerTS1q = '1' else
           frame.acTimeSlot+1 when trigger360q = '1' else
           frame.acTimeSlot;

  acTSPhasen <= (others => '0') when trigger360q = '1' else
                frame.acTimeSlotPhase+1 when baseEnable = '1' else
                frame.acTimeSlotPhase;

  countBRTn <= (others => '0') when countRst = '1' else
               countBRT+1 when baseEnable = '1' else
               countBRT;

  process (rxClk)
  begin
    if rising_edge(rxClk) then
      rxClkToggle <= rxClkToggle+1;
    end if;
  end process;

  process (txClk,tvalid)
    variable cnt : slv(2 downto 0) := (others=>'0');
  begin
    if cnt="111" then
      tlast <= tvalid;
    else
      tlast <= '0';
      end if;
    if rising_edge(txClk) then
      seqstate0 <= status.seqState(conv_integer(config.diagSeq));
      if (tvalid='1') then
        cnt := cnt+1;
      end if;
    end if;
  end process;
    
  process (txClk, txRst, txRdy, config)
    variable outOfSyncd : sl;
    variable txRdyd     : sl;
  begin  -- process
    if rising_edge(txClk) then
      frame.pulseId         <= pulseIdn                                              after tpd;
      pulseIdWr             <= '0';
      frame.acTimeSlot      <= acTSn                                                 after tpd;
      frame.acTimeSlotPhase <= acTSPhasen                                            after tpd;
      baseEnabled           <= baseEnabled(baseEnabled'left-1 downto 0) & baseEnable after tpd;
      count186M             <= count186M+1;
      if (frame.syncStatus = '1' and outOfSyncd = '0') then
        countSyncE <= countSyncE+1;
      end if;
      if (txRdy /= txRdyd) then
        pllChanged <= pllChanged+1;
      end if;
      outOfSyncd := frame.syncStatus;
      txRdyd     := txRdy;
      countTrig  <= countTrign;
      countBRT   <= countBRTn;
      if allBits(intervalCnt, '0') then  -- need to execute this when
                                         -- intervalReg is changed
        countRst         <= '1';
        status.countTrig <= countTrig;
        status.countBRT  <= countBRT;
        status.countSeq  <= countSeq;
        intervalCnt      <= config.interval;
      else
        countRst    <= '0';
        intervalCnt <= intervalCnt-1;
      end if;
    end if;
    if txRst = '1' then
      frame.acTimeSlot      <= "001";
      frame.acTimeSlotPhase <= (others => '0');
      baseEnabled           <= (others => '0');
      count186M             <= (others => '0');
      countSyncE            <= (others => '0');
      outOfSyncd            := '1';
      countRst              <= '1';
      status.countTrig      <= (others => (others => '0'));
      status.countBRT       <= (others => '0');
      status.countSeq       <= (others => (others => '0'));
    end if;
    if config.intervalRst = '1' then
      intervalCnt <= (others => '0');
    end if;
    if config.pulseIdWrEn = '1' then
      pulseIdWr <= '0';
    end if;
  end process;

  process (txClk, txRst, countRst, frame)
    variable countUpdate : slv(1 downto 0);
    variable bsaComplete : Slv64Array(1 downto 0);
    variable bsaDoneQ    : slv(63 downto 0);
    variable tmpFrame    : TimingMessageType;
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
    if countRst = '1' then
      countUpdate := "01";
    end if;
    bsaComplete(1) := bsaComplete(1) and not bsaDoneQ;
    bsaComplete(0) := bsaComplete(0) or bsaDoneQ;

    -- Record frame in diagnostics only on the last BSA accumulation
    tmpFrame           := frame;
    tmpFrame.bsaActive := frame.bsaAvgDone;
    diagFrame          <= tmpFrame;
  end process;

  
  U_ClockTime : entity work.ClockTime
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
