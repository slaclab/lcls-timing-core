#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue LCLS-II Timing Receiver module
#-----------------------------------------------------------------------------
# File       : Device.py
# Created    : 2017-04-04
#-----------------------------------------------------------------------------
# Description:
# PyRogue LCLS-II Timing Receiver module
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

class Device(pr.Device):
    def __init__(self, name="Device", description="LCLS-II Timing Receiver module", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        self.add(pr.Variable(   name         = "IrqEnable",
                                description  = "Interrupt Enable",
                                offset       =  0x00,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqStatus",
                                description  = "Interrupt Pending",
                                offset       =  0x04,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "LinkAddr",
                                description  = "Physical link address",
                                offset       =  0x08,
                                bitSize      =  16,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "gtxDebug",
                                description  = "Debug bits from link",
                                offset       =  0x0C,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "CountReset",
                                description  = "Counter reset",
                                offset       =  0x10,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "ModeSel",
                                description  = "Select LCLS-I/LCLS-II Trigger outputs (0/1)",
                                offset       =  0x14,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "DmaFullThr",
                                description  = "Set threshold in bytes for asserting readout full",
                                offset       =  0x18,
                                bitSize      =  24,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "ChannelEnable",
                                description  = "Enable readout channel",
                                offset       =  0x20,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(12):
            self.add(pr.Variable(   name         = "ChannelBsaEnable_%.*i" % (2, i),
                                    description  = "Enable BSA channel %.*i" % (2, i),
                                    offset       =  0x20 + (i * 0x20),
                                    bitSize      =  1,
                                    bitOffset    =  0x01,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "ChannelDmaEnable_%.*i" % (2, i),
                                    description  = "",
                                    offset       =  0x20 + (i * 0x20),
                                    bitSize      =  1,
                                    bitOffset    =  0x02,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        self.add(pr.Variable(   name         = "ChannelRateSel",
                                description  = "",
                                offset       =  0x24,
                                bitSize      =  13,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(12):
            self.add(pr.Variable(   name         = "ChannelDestSel_%.*i" % (2, i),
                                    description  = "Channel event destination selection %.*i" % (2, i),
                                    offset       =  0x25 + (i * 0x20),
                                    bitSize      =  18,
                                    bitOffset    =  0x05,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "ChannelEventCnt_%.*i" % (2, i),
                                    description  = "Channel event counts %.*i" % (2, i),
                                    offset       =  0x28 + (i * 0x20),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "ChannelBsaDelay_%.*i" % (2, i),
                                    description  = "Channel BSA active delay %.*i" % (2, i),
                                    offset       =  0x2C + (i * 0x20),
                                    bitSize      =  20,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "ChannelBsaSetup_%.*i" % (2, i),
                                    description  = "Channel BSA active setup %.*i" % (2, i),
                                    offset       =  0x2E + (i * 0x20),
                                    bitSize      =  12,
                                    bitOffset    =  0x04,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "ChannelBsaWidth_%.*i" % (2, i),
                                    description  = "Channel BSA active width %.*i" % (2, i),
                                    offset       =  0x30 + (i * 0x20),
                                    bitSize      =  20,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        self.add(pr.Variable(   name         = "GlobalEventCnt",
                                description  = "Global Event count",
                                offset       =  0x1A8,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(12):
            self.add(pr.Variable(   name         = "TriggerChannel_%.*i" % (2, i),
                                    description  = "Channel used for event selection %.*i" % (2, i),
                                    offset       =  0x200 + (i * 0x10),
                                    bitSize      =  4,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "TriggerPolarity_%.*i" % (2, i),
                                    description  = "Trigger polarity (0=negative, 1=positive) %.*i" % (2, i),
                                    offset       =  0x202 + (i * 0x10),
                                    bitSize      =  1,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "TriggerEnable_%.*i" % (2, i),
                                    description  = "Trigger enable %.*i" % (2, i),
                                    offset       =  0x203 + (i * 0x10),
                                    bitSize      =  1,
                                    bitOffset    =  0x07,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "TriggerDelay_%.*i" % (2, i),
                                    description  = "Trigger width (186MHz clocks) %.*i" % (2, i),
                                    offset       =  0x208 + (i * 0x10),
                                    bitSize      =  28,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(12):
            self.add(pr.Variable(   name         = "TriggerFineDelay_%.*i" % (2, i),
                                    description  = "Trigger fine delay (82.2 ps steps) %.*i" % (2, i),
                                    offset       =  0x20C + (i * 0x10),
                                    bitSize      =  6,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

