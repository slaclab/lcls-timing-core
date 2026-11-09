//////////////////////////////////////////////////////////////////////////////
// This file is part of 'LCLS Timing Core'.
// It is subject to the license terms in the LICENSE.txt file found in the
// top-level directory of this distribution and at:
//    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
// No part of 'LCLS Timing Core', including this file,
// may be copied, modified, propagated, or distributed except according to
// the terms contained in the LICENSE.txt file.
//////////////////////////////////////////////////////////////////////////////
// MODEL (test only, not production)
//
// Behavioral stand-in for the VHDL entity EvrV1Databuff so that the Verilog
// EvrV1DbusDecode can be simulated under Icarus Verilog, which cannot
// elaborate the VHDL RAM. It is never loaded by any ruckus.tcl and never
// part of a firmware build.
//
// Contract: LCLS-I/evr/EvrV1Databuff.vhd (same module name and ports).
// Proof:    tests/lcls1_evr/databuff_vectors.py runs against both the
//           production RAM under GHDL and this model under Icarus with
//           identical assertions.
//
// Behavior: byte addra(1:0) of word addra(10:2) is written on a clka rising
// edge when wea[0] is high. Port B returns the whole 32 bit word, byte lane 0
// in bits 7:0, registered on a clkb rising edge. Memory and doutb start at 0.
//////////////////////////////////////////////////////////////////////////////
`timescale 1ns/100ps
module EvrV1Databuff(addra, addrb, clka, clkb, dina, doutb, wea);
   input         clka;
   input  [0:0]  wea;
   input  [10:0] addra;
   input  [7:0]  dina;
   input         clkb;
   input  [8:0]  addrb;
   output [31:0] doutb;

   reg [31:0]    doutb;
   reg [7:0]     mem [0:2047];
   integer       i;

   initial
   begin
      for (i = 0; i < 2048; i = i + 1) mem[i] = 8'h00;
      doutb = 32'h0;
   end

   always @ (posedge clka)
   begin
      if (wea[0]) mem[addra] <= dina;
   end

   always @ (posedge clkb)
   begin
      doutb <= {mem[{addrb, 2'b11}], mem[{addrb, 2'b10}],
                mem[{addrb, 2'b01}], mem[{addrb, 2'b00}]};
   end

endmodule
