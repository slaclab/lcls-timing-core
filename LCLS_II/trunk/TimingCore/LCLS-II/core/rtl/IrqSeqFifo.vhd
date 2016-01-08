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
  signal wrDataQ : slv(SEQADDRLEN+4 downto 0);

begin

  full <= fullb;
  rdData(31 downto SEQADDRLEN+5) <= (others=>'0');
  
  U_FIFO : entity work.FifoAsync
    generic map ( DATA_WIDTH_G => SEQADDRLEN+5 )
    port map ( rst    => rst,
               wr_clk => wrClk,
               wr_en  => wrEnQ,
               din    => wrDataQ,
               wr_data_count => open,
               wr_ack        => open,
               overflow      => open,
               prog_full     => open,
               full          => fullb,
               not_full      => open,
               rd_clk => rdClk,
               rd_en  => rdEn,
               dout   => rdData(SEQADDRLEN+4 downto 0),
               rd_data_count => open,
               valid         => open,
               underflow     => open,
               prog_empty    => open,
               almost_empty  => open,
               empty         => empty );

  process (wrEn,wrData,fullb)
  begin  -- process
    wrEnQ   <= '0';
    wrAck   <= (others=>'0');
    wrDataQ <= "00000" & slv(wrData(0));
    Seq_loop: for i in 0 to MAXSEQDEPTH-1 loop
      if wrEn(i)='1' then
        wrDataQ  <= slv(conv_unsigned(i,5)) &
                    slv(wrData(i));
        wrAck    <= (others=>'0');
        wrAck(i) <= not fullb;
        wrEnQ    <= not fullb;
      end if;
    end loop Seq_loop;
  end process;
  
end behavior;
