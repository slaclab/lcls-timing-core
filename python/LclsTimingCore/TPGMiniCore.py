#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Embedded timing pattern generator
#-----------------------------------------------------------------------------
# File       : TPGMiniCore.py
# Created    : 2017-04-12
#-----------------------------------------------------------------------------
# Description:
# PyRogue Embedded timing pattern generator
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

class TPGMiniCore(pr.Device):
    def __init__(   self,       
                    name        = "TPGMiniCore",
                    description = "Embedded timing pattern generator",
                    memBase     =  None,
                    offset      =  0x00,
                    NARRAYSBSA  =  2,
                    hidden      =  False,
                    expand	    =  True,
                ):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden, expand=expand)  

        ##############################
        # Variables
        ##############################

        self.addVariable(   name         = "TxReset",
                            description  = "Reset transmit link",
                            offset       =  0x00,
                            bitSize      =  1,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "WO",
                        )

        self.addVariable(   name         = "TxPolarity",
                            description  = "Invert transmit link polarity",
                            offset       =  0x00,
                            bitSize      =  1,
                            bitOffset    =  0x01,
                            base         = "hex",
                            mode         = "RW",
                        )

        self.addVariable(   name         = "TxLoopback",
                            description  = "Set transmit link loopback",
                            offset       =  0x00,
                            bitSize      =  3,
                            bitOffset    =  0x02,
                            base         = "hex",
                            mode         = "RW",
                        )

        self.addVariable(   name         = "TxInhibit",
                            description  = "Set transmit link inhibit",
                            offset       =  0x00,
                            bitSize      =  1,
                            bitOffset    =  0x05,
                            base         = "hex",
                            mode         = "RW",
                        )

        self.addVariable(   name         = "BaseControl",
                            description  = "Base rate trigger divisor",
                            offset       =  0x04,
                            bitSize      =  16,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                        )

        self.addVariable(   name         = "PulseIdWr",
                            description  = "Pulse ID write",
                            offset       =  0x08,
                            bitSize      =  64,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "WO",
                        )

        self.addVariable(   name         = "PulseIdRd",
                            description  = "Pulse ID read",
                            offset       =  0x08,
                            bitSize      =  64,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "TStampWr",
                            description  = "Time stamp Write",
                            offset       =  0x10,
                            bitSize      =  64,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "WO",
                        )

        self.addVariable(   name         = "TStampRd",
                            description  = "Time stamp read",
                            offset       =  0x10,
                            bitSize      =  64,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariables(  name         = "FixedRateDiv",
                            description  = "Fixed rate marker divisors",
                            offset       =  0x18,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                            number       =  10,
                            stride       =  4,
                            hidden       =  True,
                        )

        self.addVariable(   name         = "RateReload",
                            description  = "Loads cached fixed rate marker divisors",
                            offset       =  0x40,
                            bitSize      =  1,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "WO",
                        )

        self.addVariable(   name         = "NBeamSeq",
                            description  = "Number of beam request engines",
                            offset       =  0x4C,
                            bitSize      =  8,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "NControlSeq",
                            description  = "Number of control sequence engines",
                            offset       =  0x4C,
                            bitSize      =  8,
                            bitOffset    =  8,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "NArraysBsa",
                            description  = "Number of BSA arrays",
                            offset       =  0x4C,
                            bitSize      =  8,
                            bitOffset    =  16,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "SeqAddrLen",
                            description  = "Number of beam sequence engines",
                            offset       =  0x4C,
                            bitSize      =  4,
                            bitOffset    =  24,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "NAllowSeq",
                            description  = "Number of beam allow engines",
                            offset       =  0x4C,
                            bitSize      =  4,
                            bitOffset    =  28,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "BsaCompleteWr",
                            description  = "BSA complete write",
                            offset       =  0x50,
                            bitSize      =  64,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "WO",
                        )

        self.addVariable(   name         = "BsaCompleteRd",
                            description  = "BSA complete read",
                            offset       =  0x50,
                            bitSize      =  64,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariables(  name         = "BsaRateSel",
                            description  = "BSA def rate selection",
                            offset       =  0x200,
                            bitSize      =  13,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                            number       =  NARRAYSBSA,
                            stride       =  8,
                            hidden       =  True,
                        )

        self.addVariables(  name         = "BsaDestSel",
                            description  = "BSA def destination selection",
                            offset       =  0x200,
                            bitSize      =  19,
                            bitOffset    =  13,
                            base         = "hex",
                            mode         = "RW",
                            number       =  NARRAYSBSA,
                            stride       =  8,
                            hidden       =  True,
                        )

        self.addVariables(  name         = "BsaNtoAvg",
                            description  = "BSA def num acquisitions to average",
                            offset       =  0x204,
                            bitSize      =  16,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                            number       =  NARRAYSBSA,
                            stride       =  8,
                            hidden       =  True,
                        )

        self.addVariables(  name         = "BsaAvgToWr",
                            description  = "BSA def num averages to record",
                            offset       =  0x204,
                            bitSize      =  16,
                            bitOffset    =  16,
                            base         = "hex",
                            mode         = "RW",
                            number       =  NARRAYSBSA,
                            stride       =  8,
                            hidden       =  True,
                        )

        self.addVariable(   name         = "PllCnt",
                            description  = "Count of PLL status changes",
                            offset       =  0x500,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "ClkCnt",
                            description  = "Count of local 186M clock",
                            offset       =  0x504,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "SyncErrCnt",
                            description  = "Count of 71k sync errors",
                            offset       =  0x508,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

        self.addVariable(   name         = "CountInterval",
                            description  = "Interval counters update period",
                            offset       =  0x50C,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RW",
                        )

        self.addVariable(   name         = "BaseRateCount",
                            description  = "Count of base rate triggers",
                            offset       =  0x510,
                            bitSize      =  32,
                            bitOffset    =  0x00,
                            base         = "hex",
                            mode         = "RO",
                        )

