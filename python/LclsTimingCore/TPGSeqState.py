#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Timing pattern sequencer state
#-----------------------------------------------------------------------------
# File       : TPGSeqState.py
# Created    : 2017-04-04
#-----------------------------------------------------------------------------
# Description:
# PyRogue Timing pattern sequencer state
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

class TPGSeqState(pr.Device):
    def __init__(self, name="TPGSeqState", description="Timing pattern sequencer state", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        for i in range(50):
            self.add(pr.Variable(   name         = "SeqIndex_%.*i" % (2, i),
                                    description  = "Sequencer instruction at offset %.*i" % (2, i),
                                    offset       =  0x00 + (i * 0x08),
                                    bitSize      =  32,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        for i in range(50):
            self.add(pr.Variable(   name         = "SeqCondACount_%.*i" % (2, i),
                                    description  = "BSA condition A counter %.*i" % (2, i),
                                    offset       =  0x04 + (i * 0x08),
                                    bitSize      =  8,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        for i in range(50):
            self.add(pr.Variable(   name         = "SeqCondBCount_%.*i" % (2, i),
                                    description  = "BSA condition B counter %.*i" % (2, i),
                                    offset       =  0x04 + (i * 0x40),
                                    bitSize      =  8,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        for i in range(50):
            self.add(pr.Variable(   name         = "SeqCondCCount_%.*i" % (2, i),
                                    description  = "BSA condition C counter %.*i" % (2, i),
                                    offset       =  0x04 + (i * 0x08),
                                    bitSize      =  8,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        for i in range(50):
            self.add(pr.Variable(   name         = "SeqCondDCount_%.*i" % (2, i),
                                    description  = "BSA condition D counter %.*i" % (2, i),
                                    offset       =  0x04 + (i * 0x08),
                                    bitSize      =  8,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

