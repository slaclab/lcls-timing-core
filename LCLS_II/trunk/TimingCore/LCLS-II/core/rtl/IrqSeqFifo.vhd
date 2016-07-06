-- Title         : IrqFifo
-- Project       : LCLS-II Timing Pattern Generator
-------------------------------------------------------------------------------
-- File          : IrqFifo.vhd
-- Author        : Matt Weaver, weaver@slac.stanford.edu
-- Created       : 07/17/2015
-------------------------------------------------------------------------------
-- Description:
-- FIFO for asynchronous notification of sequencer progress.
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
-- 07/17/2015: created.
-------------------------------------------------------------------------------
LIBRARY ieee;
use work.all;

USE ieee.std_logic_1164.ALL;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
use work.TPGPkg.all;
use work.StdRtlPkg.all;


entity IrqSeqFifo is
   port ( 
      -- Clock and reset
      rst                : in  sl;
      wrClk              : in  sl;
      wrEn               : in  slv(MAXSEQDEPTH-1 downto 0);
      wrAck              : out slv(MAXSEQDEPTH-1 downto 0);
      wrData             : in  SeqAddrArray(MAXSEQDEPTH-1 downto 0);
      
      rdClk              : in  sl;
      rdEn               : in  sl;
      rdData             : out slv(31 downto 0);

      full               : out sl;
      empty              : out sl
      );
end IrqSeqFifo;

-- Define architecture for top level module
architecture behavior of IrqSeqFifo is 

  signal fullb   : sl;
  signal wrEnQ   : sl;
  signal wrDataQ : slv(31 downto 0);
  signal emptyb  : sl;
  signal wrAckb  : slv(MAXSEQDEPTH-1 downto 0);

   component ila_0
     port ( clk    : in sl;
            probe0 : in slv(255 downto 0) );
     end component;

begin

  U_ILA : ila_0
    port map ( clk                    => wrClk,
               probe0(0)              => '0',
               probe0(1)              => wrEnQ,
               probe0(2)              => fullb,
               probe0(3)              => emptyb,
               probe0(35 downto  4)   => wrDataQ,
               probe0(MAXSEQDEPTH+35 downto 36) => wrEn,
               probe0(2*MAXSEQDEPTH+35 downto MAXSEQDEPTH+36) => wrAckb,
               probe0(255 downto 2*MAXSEQDEPTH+36) => (others=>'0') );

  full  <= fullb;
  empty <= emptyb;
  wrAck <= wrAckb;
  
  U_FIFO : entity work.FifoAsync
    generic map ( DATA_WIDTH_G => 32 )
    port map ( rst    => rst,
               wr_clk => wrClk,
               wr_en  => wrEnQ,
               din    => wrDataQ,
               full   => fullb,
               rd_clk => rdClk,
               rd_en  => rdEn,
               dout   => rdData,
               empty  => emptyb );

  process (wrEn,wrData,fullb)
    variable q : integer;
  begin  -- process
    q := 0;
    Seq_loop: for i in 0 to MAXSEQDEPTH-1 loop
      if wrEn(i)='1' then
        q := i;
      end if;
    end loop Seq_loop;

    wrEnQ   <= wrEn(q) and not fullb;
    wrAckb  <= (others=>'0');
    wrDataQ  <= slv(conv_unsigned(q,32-SEQADDRLEN)) &
                slv(wrData(q));
    if wrEn(q)='1' then
      wrAckb(q) <= not fullb;
    end if;
  end process;
  
end behavior;
