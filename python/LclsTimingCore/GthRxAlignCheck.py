#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Timing frame phase lock
#-----------------------------------------------------------------------------
# File       : GthRxAlignCheck.py
# Created    : 2017-04-04
#-----------------------------------------------------------------------------
# Description:
# PyRogue Timing frame phase lock
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

class GthRxAlignCheck(pr.Device):
    def __init__(self, name="GthRxAlignCheck", description="Timing frame phase lock", memBase=None, offset=0x0, hidden=False):
        super(self.__class__, self).__init__(name, description, memBase, offset, hidden)

        ##############################
        # Variables
        ##############################

        for i in range(128):
            self.add(pr.Variable(   name         = "PhaseCount_%.*i" % (3, i),
                                    description  = "Timing frame phase %.*i" % (3, i),
                                    offset       =  0x00 + (i * 0x02),
                                    bitSize      =  16,
                                    bitOffset    =  0x00,
                                    base         = "hex",
                                    mode         = "RO",
                                ))

        self.add(pr.Variable(   name         = "PhaseTarget",
                                description  = "Timing frame phase lock target",
                                offset       =  0x100,
                                bitSize      =  7,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "ResetLen",
                                description  = "Reset length",
                                offset       =  0x102,
                                bitSize      =  4,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RW",
                            ))

        self.add(pr.Variable(   name         = "LastPhase",
                                description  = "Last timing frame phase seen",
                                offset       =  0x104,
                                bitSize      =  7,
                                bitOffset    =  0x00,
                                base         = "hex",
                                mode         = "RO",
                            ))

