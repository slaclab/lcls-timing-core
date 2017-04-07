#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Timing pattern generator control
#-----------------------------------------------------------------------------
# File       : TPGControl.py
# Created    : 2017-04-04
#-----------------------------------------------------------------------------
# Description:
# PyRogue Timing pattern generator control
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

class TPGControl(pr.Device):
    def __init__(self, name="TPGControl", description="Timing pattern generator control", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        self.add(pr.Variable(   name         = "NBeamSeq",
                                description  = "Number of beam control sequences",
                                offset       =  0x00,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "NControlSeq",
                                description  = "Number of experiment control sequences",
                                offset       =  0x01,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "NArraysBSA",
                                description  = "Number of BSA arrays",
                                offset       =  0x02,
                                bitSize      =  8,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "SeqAddrLen",
                                description  = "Sequence instruction at offset bus width",
                                offset       =  0x03,
                                bitSize      =  4,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "NAllowSeq",
                                description  = "Number of allow table sequences",
                                offset       =  0x03,
                                bitSize      =  4,
                                bitOffset    =  0x04,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "ClockPeriod",
                                description  = "Period of beam synchronous clock (ns/cycle)",
                                offset       =  0x04,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "BaseControl",
                                description  = "Base rate control divisor",
                                offset       =  0x08,
                                bitSize      =  16,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "ACDelay",
                                description  = "Adjustable delay for power line crossing measurement",
                                offset       =  0x0C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "PulseIdL",
                                description  = "Pulse ID lower word",
                                offset       =  0x10,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "PulseIdU",
                                description  = "Pulse ID upper word",
                                offset       =  0x14,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "TStampL",
                                description  = "Time stamp lower word",
                                offset       =  0x18,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "TStampU",
                                description  = "Time stamp upper word",
                                offset       =  0x1C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(6):
            self.add(pr.Variable(   name         = "ACRateDiv_%i" % (i),
                                    description  = "Power line synch rate marker divisors %i" % (i),
                                    offset       =  0x20 + (i * 0x01),
                                    bitSize      =  8,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(10):
            self.add(pr.Variable(   name         = "FixedRateDiv_%.*i" % (2, i),
                                    description  = "Fixed rate marker divisors% .*i" % (2, i),
                                    offset       =  0x40 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        self.add(pr.Variable(   name         = "RateReload",
                                description  = "Loads cached ac/fixed rate marker divisors",
                                offset       =  0x68,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "WO",
                            ))

        self.add(pr.Variable(   name         = "Sync",
                                description  = "Sync status with 71kHz",
                                offset       =  0x70,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqFifoEnable",
                                description  = "Enable sequence checkpoint interrupt",
                                offset       =  0x74,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqIntvEnable",
                                description  = "Enable interval counter interrupt",
                                offset       =  0x74,
                                bitSize      =  1,
                                bitOffset    =  0x01,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqBsaEnable",
                                description  = "Enable BSA complete interrupt",
                                offset       =  0x74,
                                bitSize      =  1,
                                bitOffset    =  0x02,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqEnable",
                                description  = "Enable interrupts",
                                offset       =  0x77,
                                bitSize      =  1,
                                bitOffset    =  0x07,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqIntvStatus",
                                description  = "Interval counters updated",
                                offset       =  0x78,
                                bitSize      =  1,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "IrqBsaStatus",
                                description  = "BSA complete updated",
                                offset       =  0x78,
                                bitSize      =  1,
                                bitOffset    =  0x01,
                                base         = "hex",
                                mode         = "RO",
                            ))

        self.add(pr.Variable(   name         = "SeqFifoData",
                                description  = "Sequence checkpoint data",
                                offset       =  0x7C,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

        for i in range(16):
            self.add(pr.Variable(   name         = "BeamSeqCntl_%.*i" % (2, i),
                                    description  = "Beam sequence arbitration control %.*i" % (2, i),
                                    offset       =  0x80 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        self.add(pr.Variable(   name         = "SeqResetL",
                                description  = "Sequence restart lower word",
                                offset       =  0x100,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "WO",
                            ))

        self.add(pr.Variable(   name         = "SeqResetU",
                                description  = "Sequence restart upper word",
                                offset       =  0x104,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "WO",
                            ))

        for i in range(4):
            self.add(pr.Variable(   name         = "BeamEnergy_%i" % (i),
                                    description  = "Beam energy meta data %i" % (i),
                                    offset       =  0x120 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        self.add(pr.Variable(   name         = "BeamDiagCntl",
                                description  = "Beam diagnostic buffer control",
                                offset       =  0x1E4,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "WO",
                            ))

        for i in range(4):
            self.add(pr.Variable(   name         = "BeamDiagStat_%i" % (i),
                                    description  = "Beam diagnostic latched status %i" % (i),
                                    offset       =  0x1E8 + (i * 0x04),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        self.add(pr.Variable(   name         = "BsaCompleteL",
                                description  = "Bsa buffers complete lower word",
                                offset       =  0x1F8,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "BsaCompleteU",
                                description  = "Bsa buffers complete upper word",
                                offset       =  0x1FC,
                                bitSize      =  32,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        for i in range(64):
            self.add(pr.Variable(   name         = "BsaEventSel_%.*i" % (2, i),
                                    description  = "Bsa definition rate/destination selection %.*i" % (2, i),
                                    offset       =  0x200 + (i * 0x08),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(64):
            self.add(pr.Variable(   name         = "BsaStatSel_%.*i" % (2, i),
                                    description  = "Bsa definition samples to average/acquire %.*i" % (2, i),
                                    offset       =  0x204 + (i * 0x08),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

