#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Timing pattern sequencer jump programming
#-----------------------------------------------------------------------------
# File       : TPGSeqJump.py
# Created    : 2017-04-04
#-----------------------------------------------------------------------------
# Description:
# PyRogue Timing pattern sequencer jump programming
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

class TPGSeqJump(pr.Device):
    def __init__(self, name="TPGSeqJump", description="Timing pattern sequencer jump programming", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        for i in range(1024):
            self.add(pr.Variable(   name         = "StartAddr_%.*i" % (4, i),
                                    description  = "Sequence start offset %.*i" % (4, i),
                                    offset       =  0x00 + (i * 0x04),
                                    bitSize      =  12,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(1024):
            self.add(pr.Variable(   name         = "Class_%.*i" % (4, i),
                                    description  = "Sequence power class %.*i" % (4, i),
                                    offset       =  0x01 + (i * 0x04),
                                    bitSize      =  4,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

        for i in range(1024):
            self.add(pr.Variable(   name         = "StartSync_%.*i" % (4, i),
                                    description  = "Start synchronization condition %.*i" % (4, i),
                                    offset       =  0x02 + (i * 0x04),
                                    bitSize      =  16,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RW",
                                ))

