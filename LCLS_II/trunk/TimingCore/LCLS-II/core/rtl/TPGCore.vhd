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
-------------------------------------------------------------------------------
-- Copyright (c) 2015 by SLAC National Accelerator Laboratory. All rights reserved.
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

entity TPGCore is
  generic (
    ASYNC_REGCLK_G : boolean := false;
    TPFIFODEPTH  : integer := 10;
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
    extTrigger : in  slv(4 downto 0);

    rxClk   : in sl;
    rxRst   : in sl;
    rxData  : in slv(15 downto 0);
    rxDataK : in slv(1 downto 0)
    );
end TPGCore;


-- Define architecture for top level module
architecture TPGCore of TPGCore is

  signal frame : TimingMessageType := TIMING_MESSAGE_INIT_C;

  signal trigger360q             : sl;
  signal triggerTS1, triggerTS1q : sl;
  signal triggerResyncq          : sl;
  signal triggerIn               : slv(11 downto 0);
  signal triggerInq              : slv(11 downto 0);
  signal intTrigger              : slv(6 downto 0);

  signal baseEnable  : sl;
  signal baseEnabled : slv(4 downto 0);

  signal pulseIdn : slv(63 downto 0);

  signal pulseIdWr : sl;

  signal acTSn      : slv(2 downto 0);
  signal acTSPhasen : slv(11 downto 0);

  constant ACRateWidth : integer := 8;
  constant ACRateDepth : integer := ACRATEDEPTH;

  constant FixedRateWidth : integer := 20;
  constant FixedRateDepth : integer := FIXEDRATEDEPTH;

  signal SeqNotify    : SeqAddrArray(MAXSEQDEPTH-1 downto 0);
  signal SeqNotifyWr  : slv(MAXSEQDEPTH-1 downto 0);
  signal SeqNotifyAck : slv(MAXSEQDEPTH-1 downto 0);
  signal seqJump      : slv(MAXSEQDEPTH-1 downto 0);
  signal seqJumpAddr  : SeqAddrArray(MAXSEQDEPTH-1 downto 0);
  signal SeqData      : Slv32Array(MAXSEQDEPTH-1 downto 0);

  constant DestnBits : integer := BEAMPRIOBITS;

  signal sof, eof : sl;

  signal txDataB    : slv(15 downto 0);
  signal txDataKB   : slv(1 downto 0);
  signal txDataWord : slv(3 downto 0);

  signal rxDataValid : sl;

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

  signal configTrigger : L1TrigConfigArray(6 downto 0);

  -- Delay registers (for closing timing)
  signal status : TPGStatusType;
  signal config : TPGConfigType;

  -- Register delay for simulation
  constant tpd : time := 0.5 ns;

begin

  frame.version <= TIMING_MESSAGE_VERSION_C;

  -- Dont know about these inputs yet
  frame.bcsFault <= (others => '0');

  frame.mpsValid       <= '0';
  frame.mpsLimits      <= (others => (others => '0'));
  frame.calibrationGap <= '0';
  frame.historyActive  <= config.histActive;

  txData  <= txDataB;
  txDataK <= txDataKB;

  triggerTS1q <= trigger360q and triggerTS1;

  -- resources
  status.nbeamseq    <= slv(conv_unsigned(BEAMSEQDEPTH, 4));
  status.nexptseq    <= slv(conv_unsigned(EXPSEQDEPTH, 4));
  status.narraysbsa  <= slv(conv_unsigned(NARRAYSBSA, 8));
  status.seqaddrlen  <= slv(conv_unsigned(SEQADDRLEN, 4));
  status.fifoaddrlen <= slv(conv_unsigned(TPFIFODEPTH, 4));

  status.pulseId    <= frame.pulseId;
  status.outOfSync  <= frame.syncStatus;
  status.bcsFault   <= frame.bcsFault;
  status.pllChanged <= pllChanged;
  status.count186M  <= count186M;
  status.countSyncE <= countSyncE;

  rxDataValid <= not rxDataK(0);

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

  int_trigger : for i in intTrigger'range generate

    evcode_async : entity work.SynchronizerFifo
      generic map (
        TPD_G        => tpd,
        DATA_WIDTH_G => 8)
      port map (
        rst    => sysReset,
        wr_clk => sysClk,
        din    => config.IntTrigger(i).evcode,
        rd_clk => rxClk,
        valid  => open,
        dout   => configTrigger(i).evcode);

    delay_async : entity work.SynchronizerFifo
      generic map (
        TPD_G        => tpd,
        DATA_WIDTH_G => 32)
      port map (
        rst    => sysReset,
        wr_clk => sysClk,
        din    => config.IntTrigger(i).delay,
        rd_clk => rxClk,
        valid  => open,
        dout   => configTrigger(i).delay);

    U_LCLSI_Trig : entity work.LCLSI_Trig
      port map (
        rst    => rxRst,
        clk    => rxClk,
        config => configTrigger(i),
        evcode => rxData(7 downto 0),
        valid  => rxDataValid,
        trigO  => intTrigger(i));
  end generate int_trigger;

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

  SeqBeam_loop : for i in 0 to BEAMSEQDEPTH-1 generate

    U_Jump_i : entity work.SeqJump
      port map (
        clk      => txClk,
        rst      => txRst,
        config   => config.seqJumpConfig(i),
        manReset => config.SeqRestart(i),
        manAddr  => config.SeqRstAddr(i),
        triggerI => triggerInq,
        bcsFault => frame.bcsFault,
        mpsFault => (others => '0'),
        jumpRst  => baseEnable,
        jumpEn   => seqJump(i),
        jumpAddr => seqJumpAddr(i));

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
        rdEnB        => baseEnable,
        waitB        => baseEnabled(2),
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
        monCount     => countSeq(i),
        debug0       => open,
        debug1       => open);

  end generate SeqBeam_loop;

  SeqExpt_loop : for i in MAXBEAMSEQDEPTH to MAXBEAMSEQDEPTH+EXPSEQDEPTH-1 generate

    U_Jump_i : entity work.SeqJump
      port map (
        clk      => txClk,
        rst      => txRst,
        config   => config.seqJumpConfig(i),
        manReset => config.SeqRestart(i),
        manAddr  => config.SeqRstAddr(i)(10 downto 0),
        triggerI => triggerInq,
        bcsFault => frame.bcsFault,
        mpsFault => (others => '0'),
        jumpRst  => baseEnable,
        jumpEn   => seqJump(i),
        jumpAddr => seqJumpAddr(i));

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
        rdEnB        => baseEnable,
        waitB        => baseEnabled(2),
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
        monCount     => countSeq(i),
        debug0       => open,
        debug1       => open);

  end generate SeqExpt_loop;

  NoSeqBeam: for i in BEAMSEQDEPTH to MAXBEAMSEQDEPTH-1 generate
    status.seqRdData(i) <= (others=>'0');
    status.seqState (i) <= SEQUENCER_STATE_INIT_C;
    SeqNotify       (i) <= (others=>'0');
    SeqNotifyWr     (i) <= '0';
    countSeq        (i) <= (others=>'0');
    SeqData         (i) <= (others=>'0');
  end generate NoSeqBeam;

  NoSeqExpt: for i in MAXBEAMSEQDEPTH+EXPSEQDEPTH to MAXBEAMSEQDEPTH+MAXEXPSEQDEPTH-1 generate
    status.seqRdData(i) <= (others=>'0');
    status.seqState (i) <= SEQUENCER_STATE_INIT_C;
    SeqNotify       (i) <= (others=>'0');
    SeqNotifyWr     (i) <= '0';
    countSeq        (i) <= (others=>'0');
    SeqData         (i) <= (others=>'0');
  end generate NoSeqExpt;

  frame.experiment <= SeqData(MAXBEAMSEQDEPTH+MAXEXPSEQDEPTH-1 downto MAXBEAMSEQDEPTH);

  U_DestnArbiter : entity work.DestnArbiter
    port map (
      beamPrio => config.destnPriority,
      beamSeq  => SeqData(MAXBEAMSEQDEPTH-1 downto 0),
      beamSeqO => frame.beamRequest);

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
        enable     => baseEnabled(4),
        fixedRate  => frame.fixedRates,
        acRate     => frame.acRates,
        acTS       => frame.acTimeSlot,
        beamSeq    => frame.beamRequest,
        expSeq     => frame.experiment,
        bsaInit    => frame.bsaInit(i),
        bsaActive  => frame.bsaActive(i),
        bsaAvgDone => frame.bsaAvgDone(i),
        bsaDone    => frame.bsaDone(i));
  end generate BsaLoop;

  GEN_NULL_BSA: if NARRAYSBSA<64 generate
    status.bsaStatus(63 downto NARRAYSBSA) <= (others => (others => '0'));
    frame.bsaInit   (63 downto NARRAYSBSA) <= (others => '0');
    frame.bsaActive (63 downto NARRAYSBSA) <= (others => '0');
    frame.bsaAvgDone(63 downto NARRAYSBSA) <= (others => '0');
    frame.bsaDone   (63 downto NARRAYSBSA) <= (others => '0');
  end generate GEN_NULL_BSA;

  U_TPSerializer : entity work.TPSerializer
    port map (
      txClk      => txClk,
      txRst      => txRst,
      baseEnable => baseEnable,
      msg        => frame,
      sof        => sof,
      eof        => eof,
      txData     => txDataB,
      txDataK    => txDataKB,
      txDataWord => txDataWord);

  U_TPFifo : entity work.TPFifo
    generic map (
      LOGDEPTH => TPFIFODEPTH)
    port map (
      rst        => config.fifoReset,
      wrClk      => txClk,
      sof        => sof,
      eof        => eof,
      wrData     => txDataB,
      wrDataWord => txDataWord,
      trig       => config.fifoTrig,
      wsel       => config.fifoSel,
      rdClk      => sysClk,
      rdEn       => config.fifoRead,
      rdData     => status.fifoData,
      full       => status.fifoFull,
      empty      => status.fifoEmpty);

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
  end process;

  U_ClockTime : entity work.ClockTime
    port map (
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
