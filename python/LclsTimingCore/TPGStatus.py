#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Timing pattern generator status
#-----------------------------------------------------------------------------
# File       : TPGStatus.py
# Created    : 2017-04-04
#-----------------------------------------------------------------------------
# Description:
# PyRogue Timing pattern generator status
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

class TPGStatus(pr.Device):
    def __init__(self, name="TPGStatus", description="Timing pattern generator status", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        for i in range(64):
            self.add(pr.Variable(   name         = "BsaStat_%.*i" % (2, i),
                                    description  = "BSA status num averaged/written %.*i" % (2, i),
                                    offset       =  0x00 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        self.add(pr.Variable(   name         = "CountPLL",
                                description  = "PLL Status changes",
                                offset       =  0x100,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "Count186M",
                                description  = "186MHz clock counts / 16",
                                offset       =  0x104,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "CountSyncE",
                                description  = "Sync error counts",
                                offset       =  0x108,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "CountIntv",
                                description  = "Interval timer",
                                offset       =  0x10C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "CountBRT",
                                description  = "Base rate trigger count in interval",
                                offset       =  0x110,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        for i in range(12):
            self.add(pr.Variable(   name         = "CountTrig_%.*i" % (2, i),
                                    description  = "External trigger count in interval %.*i" % (2, i),
                                    offset       =  0x114 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        for i in range(64):
            self.add(pr.Variable(   name         = "CountSeq_%.*i" % (2, i),
                                    description  = "Sequence requests in interval %.*i" % (2, i),
                                    offset       =  0x144 + (i * 0x02),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        self.add(pr.Variable(   name         = "CountRxClks",
                                description  = "Recovered clock count / 16",
                                offset       =  0x248,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "CountRxDV",
                                description  = "Received data valid count",
                                offset       =  0x24C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

