#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Embedded timing pattern generator
#-----------------------------------------------------------------------------
# File       : TPGMiniCore.py
# Created    : 2017-04-04
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
    def __init__(self, name="TPGMiniCore", description="Embedded timing pattern generator", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        self.add(pr.Variable(   name         = "TxReset",
                                description  = "Reset transmit link",
                                offset       =  0x00,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "TxPolarity",
                                description  = "Invert transmit link polarity",
                                offset       =  0x00,
                                bitSize      =  1,
                                bitOffset    =  0x01,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "TxLoopback",
                                description  = "Set transmit link loopback",
                                offset       =  0x00,
                                bitSize      =  3,
                                bitOffset    =  0x02,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "TxInhibit",
                                description  = "Set transmit link inhibit",
                                offset       =  0x00,
                                bitSize      =  1,
                                bitOffset    =  0x05,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "BaseControl",
                                description  = "Base rate trigger divisor",
                                offset       =  0x04,
                                bitSize      =  16,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "PulseIdL",
                                description  = "Pulse ID lower word",
                                offset       =  0x08,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "PulseIdU",
                                description  = "Pulse ID upper word",
                                offset       =  0x0C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "TStampL",
                                description  = "Time stamp lower word",
                                offset       =  0x10,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "TStampU",
                                description  = "Time stamp upper word",
                                offset       =  0x14,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(10):
            self.add(pr.Variable(   name         = "FixedRateDiv_%.*i" % (2, i),
                                    description  = "Fixed rate marker divisors %.*i" % (2, i),
                                    offset       =  0x18 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        self.add(pr.Variable(   name         = "RateReload",
                                description  = "Loads cached fixed rate marker divisors",
                                offset       =  0x40,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "WO",
                            ))

        self.add(pr.Variable(   name         = "NBeamSeq",
                                description  = "Number of beam request engines",
                                offset       =  0x4C,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "NControlSeq",
                                description  = "Number of control sequence engines",
                                offset       =  0x4D,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "NArraysBsa",
                                description  = "Number of BSA arrays",
                                offset       =  0x4E,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "SeqAddrLen",
                                description  = "Number of beam sequence engines",
                                offset       =  0x4F,
                                bitSize      =  4,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "NAllowSeq",
                                description  = "Number of beam allow engines",
                                offset       =  0x4F,
                                bitSize      =  4,
                                bitOffset    =  0x04,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "BsaCompleteL",
                                description  = "BSA complete lower word",
                                offset       =  0x50,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "BsaCompleteU",
                                description  = "BSA complete upper word",
                                offset       =  0x54,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(64):
            self.add(pr.Variable(   name         = "BsaRateSel_%.*i" % (2, i),
                                    description  = "BSA def rate selection %.*i" % (2, i),
                                    offset       =  0x200 + (i * 0x08),
                                    bitSize      =  13,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(64):
            self.add(pr.Variable(   name         = "BsaDestSel_%.*i" % (2, i),
                                    description  = "BSA def destination selection %.*i" % (2, i),
                                    offset       =  0x201 + (i * 0x08),
                                    bitSize      =  19,
                                    bitOffset    =  0x05,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(64):
            self.add(pr.Variable(   name         = "BsaNtoAvg_%.*i" % (2, i),
                                    description  = "BSA def num acquisitions to average %.*i" % (2, i),
                                    offset       =  0x204 + (i * 0x08),
                                    bitSize      =  16,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(64):
            self.add(pr.Variable(   name         = "BsaAvgToWr_%.*i" % (2, i),
                                    description  = "BSA def num averages to record %.*i" % (2, i),
                                    offset       =  0x206 + (i * 0x08),
                                    bitSize      =  16,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        self.add(pr.Variable(   name         = "PllCnt",
                                description  = "Count of PLL status changes",
                                offset       =  0x500,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "ClkCnt",
                                description  = "Count of local 186M clock",
                                offset       =  0x504,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "SyncErrCnt",
                                description  = "Count of 71k sync errors",
                                offset       =  0x508,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "CountInterval",
                                description  = "Interval counters update period",
                                offset       =  0x50C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "BaseRateCount",
                                description  = "Count of base rate triggers",
                                offset       =  0x510,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

