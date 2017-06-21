#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Timing pattern generator status
#-----------------------------------------------------------------------------
# File       : TPGStatus.py
# Created    : 2017-04-12
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
    def __init__(   self,       
                    name        = "TPGStatus",
                    description = "Timing pattern generator status",
                    memBase     =  None,
                    offset      =  0x00,
                    hidden      =  False,
                ):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden, )

        ##############################
        # Variables
        ##############################

        self.addVariables(  name         = "BsaStat",
                            description  = "BSA status num averaged/written",
                            offset       =  0x00,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                            number       =  64,
                            stride       =  4,
                        )

        self.addVariable(   name         = "CountPLL",
                            description  = "PLL Status changes",
                            offset       =  0x100,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "Count186M",
                            description  = "186MHz clock counts / 16",
                            offset       =  0x104,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "CountSyncE",
                            description  = "Sync error counts",
                            offset       =  0x108,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "CountIntv",
                            description  = "Interval timer",
                            offset       =  0x10C,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                        )

        self.addVariable(   name         = "CountBRT",
                            description  = "Base rate trigger count in interval",
                            offset       =  0x110,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariables(  name         = "CountTrig",
                            description  = "External trigger count in interval",
                            offset       =  0x114,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                            number       =  12,
                            stride       =  4,
                        )

        self.addVariables(  name         = "CountSeq",
                            description  = "Sequence requests in interval",
                            offset       =  0x144,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                            number       =  64,
                            stride       =  2,
                        )

        self.addVariable(   name         = "CountRxClks",
                            description  = "Recovered clock count / 16",
                            offset       =  0x248,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                        )

        self.addVariable(   name         = "CountRxDV",
                            description  = "Received data valid count",
                            offset       =  0x24C,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                        )

