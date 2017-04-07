#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue LCLS-I EVR Registers
#-----------------------------------------------------------------------------
# File       : EvrV1Reg.py
# Created    : 2017-04-04
#-----------------------------------------------------------------------------
# Description:
# PyRogue LCLS-I EVR Registers
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr

class EvrV1Reg(pr.Device):
    def __init__(self, name="EvrV1Reg", description="LCLS-I EVR Registers", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        self.add(pr.Variable(   name         = "Status",
                                description  = "Status Register",
                                offset       =  0x00,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "Control",
                                description  = "Control Register",
                                offset       =  0x04,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqFlag",
                                description  = "Interrupt Flag Register",
                                offset       =  0x08,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqEnable",
                                description  = "Interrupt Enable Register",
                                offset       =  0x0C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "PulseIrqMap",
                                description  = "Mapping register for pulse interrupt",
                                offset       =  0x10,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "PcieIntEna",
                                description  = "PCIe interrupt Enable and state status",
                                offset       =  0x14,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "FWVersion",
                                description  = "Firmware Version Register",
                                offset       =  0x2C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "FWVersionUnmasked",
                                description  = "Firmware Version without 0x1F mask and byte swapped",
                                offset       =  0x30,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "UsecDivider",
                                description  = "Divider to get from Event Clock to 1 MHz",
                                offset       =  0x4C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "SecSR",
                                description  = "Seconds Shift Register",
                                offset       =  0x5C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "SecCounter",
                                description  = "Timestamp Seconds Counter",
                                offset       =  0x60,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "EventCounter",
                                description  = "Timestamp Event Counter",
                                offset       =  0x64,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "SecLatch",
                                description  = "Timestamp Seconds Counter Latch",
                                offset       =  0x68,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "EvCntLatch",
                                description  = "Timestamp Event Counter Latch",
                                offset       =  0x6C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "IntEventEn",
                                description  = "Internal Event Enable",
                                offset       =  0xA0,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IntEventCount",
                                description  = "Internal Event Count",
                                offset       =  0xA4,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IntEventCode",
                                description  = "Internal Event Code",
                                offset       =  0xA8,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "ExtEventEn",
                                description  = "External Event Enable",
                                offset       =  0xAC,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "ExtEventCode",
                                description  = "External Event Code",
                                offset       =  0xB0,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse00_%i" % (i),
                                    description  = "Pulse 0 Registers. Channel %i" % (i),
                                    offset       =  0x200 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse01_%i" % (i),
                                    description  = "Pulse 1 Registers. Channel %i" % (i),
                                    offset       =  0x210 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse02_%i" % (i),
                                    description  = "Pulse 2 Registers. Channel %i" % (i),
                                    offset       =  0x220 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse03_%i" % (i),
                                    description  = "Pulse 3 Registers. Channel %i" % (i),
                                    offset       =  0x230 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse04_%i" % (i),
                                    description  = "Pulse 4 Registers. Channel %i" % (i),
                                    offset       =  0x240 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse05_%i" % (i),
                                    description  = "Pulse 5 Registers. Channel %i" % (i),
                                    offset       =  0x250 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse06_%i" % (i),
                                    description  = "Pulse 6 Registers. Channel %i" % (i),
                                    offset       =  0x260 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse07_%i" % (i),
                                    description  = "Pulse 7 Registers. Channel %i" % (i),
                                    offset       =  0x270 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",

                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse08_%i" % (i),
                                    description  = "Pulse 8 Registers. Channel %i" % (i),
                                    offset       =  0x280 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse09_%i" % (i),
                                    description  = "Pulse 9 Registers. Channel %i" % (i),
                                    offset       =  0x290 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse10_%i" % (i),
                                    description  = "Pulse 10 Registers. Channel %i" % (i),
                                    offset       =  0x2A0 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",

                                ))

        for i in range(4):
            self.add(pr.Variable(   name         = "Pulse11_%i" % (i),
                                    description  = "Pulse 11 Registers. Channel %i" % (i),
                                    offset       =  0x2B0 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",

                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "OutputMap_%.*i" % (2, i),
                                    description  = "Front Panel Output Map Registers [11:0]. Channel %.*i" % (2, i),
                                    offset       =  0x440 + (i * 0x04),
                                    bitSize      =  16,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(1024):
            self.add(pr.Variable(   name         = "MapRam1_%.*i" % (4, i),
                                    description  = "Event Mapping RAM 1 [1023:0]. Channel %.*i" % (4, i),
                                    offset       =  0x4000 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        for i in range(1024):
            self.add(pr.Variable(   name         = "MapRam2_%.*i" % (4, i),
                                    description  = "Event Mapping RAM 2 [1023:0]. Channel %.*i" % (4, i),
                                    offset       =  0x6000 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

