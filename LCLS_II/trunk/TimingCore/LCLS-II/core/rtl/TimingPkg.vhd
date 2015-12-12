-------------------------------------------------------------------------------
-- Title      : TimingPkg
-------------------------------------------------------------------------------
-- File       : TimingPkg.vhd
-- Author     : Benjamin Reese  <bareese@slac.stanford.edu>
-- Company    : SLAC National Accelerator Laboratory
-- Created    : 2015-09-01
-- Last update: 2015-11-16
-- Platform   : 
-- Standard   : VHDL'93/02
-------------------------------------------------------------------------------
-- Description: 
-------------------------------------------------------------------------------
-- Copyright (c) 2015 SLAC National Accelerator Laboratory
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

use work.StdRtlPkg.all;

package TimingPkg is

   constant D_102_C : slv(7 downto 0) := "01001010";  -- D10.2, 0x4A
   constant D_215_C : slv(7 downto 0) := "10110101";  -- D21.5, 0xB5
   constant K_COM_C : slv(7 downto 0) := "10111100";  -- K28.5, 0xBC
   constant K_SOF_C : slv(7 downto 0) := "11110111";  -- K23.7, 0xF7
   constant K_EOF_C : slv(7 downto 0) := "11111101";  -- K29.7, 0xFD

   constant TIMING_MESSAGE_BITS_C  : integer := 1264;
   constant TIMING_MESSAGE_WORDS_C : integer := TIMING_MESSAGE_BITS_C/16;
   constant TIMING_MESSAGE_VERSION_C : slv(63 downto 0) := x"0000060504030201";

--   type TimingMessageSlv is slv(TIMING_MESSAGE_BITS_C-1 downto 0);

   type TimingMessageType is record
      version         : slv(63 downto 0);
      pulseId         : slv(63 downto 0);
      timeStamp       : slv(63 downto 0);
      fixedRates      : slv(9 downto 0);
      acRates         : slv(5 downto 0);
      acTimeSlot      : slv(2 downto 0);
      acTimeSlotPhase : slv(11 downto 0);
      resync          : sl;
      beamRequest     : slv(31 downto 0);
      syncStatus      : sl;
      bcsFault        : slv(5 downto 0);
      mpsValid        : sl;
      mpsLimits       : slv16Array(0 to 4);
      historyActive   : sl;
      calibrationGap  : sl;
      bsaInit         : slv(63 downto 0);
      bsaActive       : slv(63 downto 0);
      bsaAvgDone      : slv(63 downto 0);
      bsaDone         : slv(63 downto 0);
--      experiment      : slv32Array(0 to 8);
      experiment      : slv16Array(0 to 17);
      partitionAddr   : slv(15 downto 0);
      partitionWord   : Slv32Array(0 to 7);
      crc             : slv(31 downto 0);
   end record;

   constant TIMING_MESSAGE_INIT_C : TimingMessageType := (
      version         => (others => '0'),
      pulseId         => (others => '0'),
      timeStamp       => (others => '0'),
      fixedRates      => (others => '0'),
      acRates         => (others => '0'),
      acTimeSlot      => (others => '0'),
      acTimeSlotPhase => (others => '0'),
      resync          => '0',
      beamRequest     => (others => '0'),
      syncStatus      => '0',
      bcsFault        => (others => '0'),
      mpsValid        => '0',
      mpsLimits       => (others => (others => '0')),
      historyActive   => '0',
      calibrationGap  => '0',
      bsaInit         => (others => '0'),
      bsaActive       => (others => '0'),
      bsaAvgDone      => (others => '0'),
      bsaDone         => (others => '0'),
      experiment      => (others => (others => '0')),
      partitionAddr   => (others => '0'),
      partitionWord   => (others => (others => '0')),
      crc             => (others => '0'));

   function toSlv  (message              : TimingMessageType) return slv;
   function toSlv32(message              : TimingMessageType) return Slv32Array;
   function toTimingMessageType(vector : slv) return TimingMessageType;

   -- LCLS-I Timing Data Type
   type LclsV1TimingDataType is record
      linkUp : sl;
   end record;
   constant LCLS_V1_TIMING_DATA_INIT_C : LclsV1TimingDataType := (
      linkUp => '0');

   -- LCLS-II Timing Data Type
   type LclsV2TimingDataType is record
      linkUp     : sl;
   end record;
   constant LCLS_V2_TIMING_DATA_INIT_C : LclsV2TimingDataType := (
      linkUp     => '0');

   type TimingBusType is record
      strobe  : sl;                     -- 1 MHz timing strobe
      message : TimingMessageType;
      v1      : LclsV1TimingDataType;
      v2      : LclsV2TimingDataType;
   end record;
   constant TIMING_BUS_INIT_C : TimingBusType := (
      strobe  => '0',
      message => TIMING_MESSAGE_INIT_C,
      v1      => LCLS_V1_TIMING_DATA_INIT_C,
      v2      => LCLS_V2_TIMING_DATA_INIT_C);


   type TimingPhyType is record
      dataK : slv(1 downto 0);
      data  : slv(15 downto 0);
      polarity : sl;
   end record;
   constant TIMING_PHY_INIT_C : TimingPhyType := (
      dataK => "00",
      data  => x"0000",
      polarity => '0');

end package TimingPkg;

package body TimingPkg is


   -------------------------------------------------------------------------------------------------
   -- Convert a timing message record into a big long SLV
   -------------------------------------------------------------------------------------------------
   function toSlv (message : TimingMessageType) return slv
   is
      variable vector : slv(TIMING_MESSAGE_BITS_C-1 downto 0) := (others => '0');
      variable i      : integer                               := 0;
   begin
      assignSlv(i, vector, message.version);
      assignSlv(i, vector, message.pulseId);
      assignSlv(i, vector, message.timeStamp);
      assignSlv(i, vector, message.fixedRates);
      assignSlv(i, vector, message.acRates);
      assignSlv(i, vector, message.acTimeSlot);
      assignSlv(i, vector, message.acTimeSlotPhase);
      assignSlv(i, vector, message.resync);
      assignSlv(i, vector, message.beamRequest);
      assignSlv(i, vector, message.syncStatus);
      assignSlv(i, vector, message.bcsFault);
      assignSlv(i, vector, message.mpsValid);
      assignSlv(i, vector, "00000000");        -- 8 unused bits
      for j in message.mpsLimits'range loop
         assignSlv(i, vector, message.mpsLimits(j));
      end loop;
      assignSlv(i, vector, message.historyActive);
      assignSlv(i, vector, message.calibrationGap);
      assignSlv(i, vector, "00000000000000");  -- 14 unused bits
      assignSlv(i, vector, X"000000000000");   -- 3 unused words
      assignSlv(i, vector, message.bsaInit);
      assignSlv(i, vector, message.bsaActive);
      assignSlv(i, vector, message.bsaAvgDone);
      assignSlv(i, vector, message.bsaDone);
      for j in message.experiment'range loop
         assignSlv(i, vector, message.experiment(j));
      end loop;
      assignSlv(i, vector, message.partitionAddr);
      for j in message.partitionWord'range loop
         assignSlv(i, vector, message.partitionWord(j));
      end loop;
      assignSlv(i, vector, message.crc);
      return vector;
   end function;

   -------------------------------------------------------------------------------------------------
   -- Convert a timing message record into a big long SLV
   -------------------------------------------------------------------------------------------------
   function toSlv32 (message : TimingMessageType) return Slv32Array
   is
      variable vector : slv(TIMING_MESSAGE_BITS_C-1 downto 0) := (others => '0');
      variable vec32  : Slv32Array(31 downto 0) := (others => x"00000000");
      variable i      : integer                 := 0;
   begin
     vector := toSlv(message);
     if TIMING_MESSAGE_BITS_C > 32*32 then
       for j in 0 to 31 loop
         vec32(j) := vector(j*32+31 downto j*32);
       end loop;  -- j
     else
       for j in 0 to TIMING_MESSAGE_BITS_C/32-1 loop
         vec32(j) := vector(j*32+31 downto j*32);
       end loop;  -- j
     end if;
     return vec32;
   end function;

   -------------------------------------------------------------------------------------------------
   -- Convert an SLV into a timing record
   -------------------------------------------------------------------------------------------------
   function toTimingMessageType (vector : slv) return TimingMessageType
   is
      variable message : TimingMessageType;
      variable i       : integer := 0;
   begin
      assignRecord(i, vector, message.version);
      assignRecord(i, vector, message.pulseId);
      assignRecord(i, vector, message.timeStamp);
      assignRecord(i, vector, message.fixedRates);
      assignRecord(i, vector, message.acRates);
      assignRecord(i, vector, message.acTimeSlot);
      assignRecord(i, vector, message.acTimeSlotPhase);
      assignRecord(i, vector, message.resync);
      assignRecord(i, vector, message.beamRequest);
      assignRecord(i, vector, message.syncStatus);
      assignRecord(i, vector, message.bcsFault);
      assignRecord(i, vector, message.mpsValid);
      i := i+ 8;                        -- 8 unused bits
      for j in message.mpsLimits'range loop
         assignRecord(i, vector, message.mpsLimits(j));
      end loop;
      assignRecord(i, vector, message.historyActive);
      assignRecord(i, vector, message.calibrationGap);
      i := i+ 14;                       -- 14 unused bits of word
      i := i+ (16*3);                   -- 3 unused words
      assignRecord(i, vector, message.bsaInit);
      assignRecord(i, vector, message.bsaActive);
      assignRecord(i, vector, message.bsaAvgDone);
      assignRecord(i, vector, message.bsaDone);
      for j in message.experiment'range loop
         assignRecord(i, vector, message.experiment(j));
      end loop;
      assignRecord(i, vector, message.partitionAddr);
      for j in message.partitionWord'range loop
         assignRecord(i, vector, message.partitionWord(j));
      end loop;
      assignRecord(i, vector, message.crc);
      return message;
   end function;


end package body TimingPkg;
