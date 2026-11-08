-------------------------------------------------------------------------------
-- Company    : SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
-- Description: Cocotb-only combinational wrapper that exposes the TimingPkg
--              conversion functions field by field. The encode side builds a
--              TimingMessageType and a TimingStreamType from flat inputs and
--              returns toSlv, toSlvNoBsa and the data buffer vector. The
--              decode side runs toTimingMessageType and toTimingStreamType on
--              flat vectors and returns each field. nbRoundTrip is
--              toSlv(toTimingMessageType(decMessageNoBsa)), so the fields the
--              672-bit decode never assigns stay visible as unresolved bits.
--              This file is never loaded by any ruckus.tcl.
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

library lcls_timing_core;
use lcls_timing_core.TimingPkg.all;

entity TimingPkgConversionsWrapper is
   port (
      -- Message encode: field inputs
      encVersion          : in  slv(15 downto 0);
      encPulseId          : in  slv(63 downto 0);
      encTimeStamp        : in  slv(63 downto 0);
      encFixedRates       : in  slv(9 downto 0);
      encAcRates          : in  slv(5 downto 0);
      encAcTimeSlot       : in  slv(2 downto 0);
      encAcTimeSlotPhase  : in  slv(11 downto 0);
      encResync           : in  sl;
      encBeamRequest      : in  slv(31 downto 0);
      encBeamEnergy       : in  slv(4*16-1 downto 0);
      encPhotonWavelen    : in  slv(2*16-1 downto 0);
      encSyncStatus       : in  sl;
      encMpsValid         : in  sl;
      encBcsFault         : in  sl;
      encMpsLimit         : in  slv(15 downto 0);
      encMpsClass         : in  slv(16*4-1 downto 0);
      encBsaInit          : in  slv(63 downto 0);
      encBsaActive        : in  slv(63 downto 0);
      encBsaAvgDone       : in  slv(63 downto 0);
      encBsaDone          : in  slv(63 downto 0);
      encControl          : in  slv(18*16-1 downto 0);
      -- Message encode: vectors
      encMessage          : out slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      encMessageNoBsa     : out slv(TIMING_MESSAGE_BITS_NO_BSA_C-1 downto 0);
      -- Message decode: vectors in, fields out
      decMessage          : in  slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      decVersion          : out slv(15 downto 0);
      decPulseId          : out slv(63 downto 0);
      decTimeStamp        : out slv(63 downto 0);
      decFixedRates       : out slv(9 downto 0);
      decAcRates          : out slv(5 downto 0);
      decAcTimeSlot       : out slv(2 downto 0);
      decAcTimeSlotPhase  : out slv(11 downto 0);
      decResync           : out sl;
      decBeamRequest      : out slv(31 downto 0);
      decBeamEnergy       : out slv(4*16-1 downto 0);
      decPhotonWavelen    : out slv(2*16-1 downto 0);
      decSyncStatus       : out sl;
      decMpsValid         : out sl;
      decBcsFault         : out sl;
      decMpsLimit         : out slv(15 downto 0);
      decMpsClass         : out slv(16*4-1 downto 0);
      decBsaInit          : out slv(63 downto 0);
      decBsaActive        : out slv(63 downto 0);
      decBsaAvgDone       : out slv(63 downto 0);
      decBsaDone          : out slv(63 downto 0);
      decControl          : out slv(18*16-1 downto 0);
      -- No-BSA decode round trip
      decMessageNoBsa     : in  slv(TIMING_MESSAGE_BITS_NO_BSA_C-1 downto 0);
      nbRoundTrip         : out slv(TIMING_MESSAGE_BITS_C-1 downto 0);
      -- Stream and data buffer encode
      encStreamPulseId    : in  slv(31 downto 0);
      encStreamEventCodes : in  slv(255 downto 0);
      encDbuffDtype       : in  slv(15 downto 0);
      encDbuffVersion     : in  slv(15 downto 0);
      encDbuffDmod        : in  slv(191 downto 0);
      encDbuffEpicsTime   : in  slv(63 downto 0);
      encDbuffEdefAvgDn   : in  slv(31 downto 0);
      encDbuffEdefMinor   : in  slv(31 downto 0);
      encDbuffEdefMajor   : in  slv(31 downto 0);
      encDbuffEdefInit    : in  slv(31 downto 0);
      encStream           : out slv(TIMING_STREAM_BITS_C-1 downto 0);
      encDbuff            : out slv(TIMING_DATABUFF_BITS_C-1 downto 0);
      -- Stream decode
      decStream           : in  slv(TIMING_STREAM_BITS_C-1 downto 0);
      decStreamPulseId    : out slv(31 downto 0);
      decStreamEventCodes : out slv(255 downto 0);
      decDbuffDtype       : out slv(15 downto 0);
      decDbuffVersion     : out slv(15 downto 0);
      decDbuffDmod        : out slv(191 downto 0);
      decDbuffEpicsTime   : out slv(63 downto 0);
      decDbuffEdefAvgDn   : out slv(31 downto 0);
      decDbuffEdefMinor   : out slv(31 downto 0);
      decDbuffEdefMajor   : out slv(31 downto 0);
      decDbuffEdefInit    : out slv(31 downto 0));
end entity TimingPkgConversionsWrapper;

architecture mapping of TimingPkgConversionsWrapper is

   signal encRec    : TimingMessageType;
   signal decRec    : TimingMessageType;
   signal nbRec     : TimingMessageType;
   signal encStrRec : TimingStreamType;
   signal decStrRec : TimingStreamType;

begin

   -------------------------------------------------------------------------
   -- Message encode
   -------------------------------------------------------------------------
   encRec.version         <= encVersion;
   encRec.pulseId         <= encPulseId;
   encRec.timeStamp       <= encTimeStamp;
   encRec.fixedRates      <= encFixedRates;
   encRec.acRates         <= encAcRates;
   encRec.acTimeSlot      <= encAcTimeSlot;
   encRec.acTimeSlotPhase <= encAcTimeSlotPhase;
   encRec.resync          <= encResync;
   encRec.beamRequest     <= encBeamRequest;
   encRec.syncStatus      <= encSyncStatus;
   encRec.mpsValid        <= encMpsValid;
   encRec.bcsFault(0)     <= encBcsFault;
   encRec.mpsLimit        <= encMpsLimit;
   encRec.bsaInit         <= encBsaInit;
   encRec.bsaActive       <= encBsaActive;
   encRec.bsaAvgDone      <= encBsaAvgDone;
   encRec.bsaDone         <= encBsaDone;

   GEN_ENC_BEAM_ENERGY : for i in 0 to 3 generate
      encRec.beamEnergy(i) <= encBeamEnergy(16*i+15 downto 16*i);
   end generate GEN_ENC_BEAM_ENERGY;

   GEN_ENC_PHOTON : for i in 0 to 1 generate
      encRec.photonWavelen(i) <= encPhotonWavelen(16*i+15 downto 16*i);
   end generate GEN_ENC_PHOTON;

   GEN_ENC_MPS_CLASS : for i in 0 to 15 generate
      encRec.mpsClass(i) <= encMpsClass(4*i+3 downto 4*i);
   end generate GEN_ENC_MPS_CLASS;

   GEN_ENC_CONTROL : for i in 0 to 17 generate
      encRec.control(i) <= encControl(16*i+15 downto 16*i);
   end generate GEN_ENC_CONTROL;

   encMessage      <= toSlv(encRec);
   encMessageNoBsa <= toSlvNoBsa(encRec);

   -------------------------------------------------------------------------
   -- Message decode
   -------------------------------------------------------------------------
   decRec <= toTimingMessageType(decMessage);

   decVersion         <= decRec.version;
   decPulseId         <= decRec.pulseId;
   decTimeStamp       <= decRec.timeStamp;
   decFixedRates      <= decRec.fixedRates;
   decAcRates         <= decRec.acRates;
   decAcTimeSlot      <= decRec.acTimeSlot;
   decAcTimeSlotPhase <= decRec.acTimeSlotPhase;
   decResync          <= decRec.resync;
   decBeamRequest     <= decRec.beamRequest;
   decSyncStatus      <= decRec.syncStatus;
   decMpsValid        <= decRec.mpsValid;
   decBcsFault        <= decRec.bcsFault(0);
   decMpsLimit        <= decRec.mpsLimit;
   decBsaInit         <= decRec.bsaInit;
   decBsaActive       <= decRec.bsaActive;
   decBsaAvgDone      <= decRec.bsaAvgDone;
   decBsaDone         <= decRec.bsaDone;

   GEN_DEC_BEAM_ENERGY : for i in 0 to 3 generate
      decBeamEnergy(16*i+15 downto 16*i) <= decRec.beamEnergy(i);
   end generate GEN_DEC_BEAM_ENERGY;

   GEN_DEC_PHOTON : for i in 0 to 1 generate
      decPhotonWavelen(16*i+15 downto 16*i) <= decRec.photonWavelen(i);
   end generate GEN_DEC_PHOTON;

   GEN_DEC_MPS_CLASS : for i in 0 to 15 generate
      decMpsClass(4*i+3 downto 4*i) <= decRec.mpsClass(i);
   end generate GEN_DEC_MPS_CLASS;

   GEN_DEC_CONTROL : for i in 0 to 17 generate
      decControl(16*i+15 downto 16*i) <= decRec.control(i);
   end generate GEN_DEC_CONTROL;

   -------------------------------------------------------------------------
   -- No-BSA decode round trip
   -------------------------------------------------------------------------
   nbRec       <= toTimingMessageType(decMessageNoBsa);
   nbRoundTrip <= toSlv(nbRec);

   -------------------------------------------------------------------------
   -- Stream and data buffer encode
   -------------------------------------------------------------------------
   encStrRec.pulseId         <= encStreamPulseId;
   encStrRec.eventCodes      <= encStreamEventCodes;
   encStrRec.dbuff.dtype     <= encDbuffDtype;
   encStrRec.dbuff.version   <= encDbuffVersion;
   encStrRec.dbuff.dmod      <= encDbuffDmod;
   encStrRec.dbuff.epicsTime <= encDbuffEpicsTime;
   encStrRec.dbuff.edefAvgDn <= encDbuffEdefAvgDn;
   encStrRec.dbuff.edefMinor <= encDbuffEdefMinor;
   encStrRec.dbuff.edefMajor <= encDbuffEdefMajor;
   encStrRec.dbuff.edefInit  <= encDbuffEdefInit;

   encStream <= toSlv(encStrRec);
   encDbuff  <= toSlv(encStrRec.dbuff);

   -------------------------------------------------------------------------
   -- Stream decode
   -------------------------------------------------------------------------
   decStrRec <= toTimingStreamType(decStream);

   decStreamPulseId    <= decStrRec.pulseId;
   decStreamEventCodes <= decStrRec.eventCodes;
   decDbuffDtype       <= decStrRec.dbuff.dtype;
   decDbuffVersion     <= decStrRec.dbuff.version;
   decDbuffDmod        <= decStrRec.dbuff.dmod;
   decDbuffEpicsTime   <= decStrRec.dbuff.epicsTime;
   decDbuffEdefAvgDn   <= decStrRec.dbuff.edefAvgDn;
   decDbuffEdefMinor   <= decStrRec.dbuff.edefMinor;
   decDbuffEdefMajor   <= decStrRec.dbuff.edefMajor;
   decDbuffEdefInit    <= decStrRec.dbuff.edefInit;

end architecture mapping;
