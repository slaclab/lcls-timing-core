#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue Timing pattern sequencer state
#-----------------------------------------------------------------------------
# File       : TPGSeqState.py
# Created    : 2017-04-12
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
    def __init__(   self,       
        name        = "TPGSeqState",
        description = "Timing pattern sequencer state",
        memBase     =  None,
        offset      =  0x00,
        hidden      =  False,
        expand      =  True,
    ):
        super().__init__(
            name        = name,
            description = description,
            memBase     = memBase,
            offset      = offset,
            hidden      = hidden,
            expand      = expand,
        )

        ##############################
        # Variables
        ##############################

        self.add(pr.RemoteVariable(   
            name         = "SeqIndex",
            description  = "Sequencer instruction at offset",
            offset       =  0x00,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RO",
            number       =  50,
            stride       =  8,
        ))

        self.add(pr.RemoteVariable(   
            name         = "SeqCondACount",
            description  = "BSA condition A counter",
            offset       =  0x04,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RO",
            number       =  50,
            stride       =  8,
        ))

        self.add(pr.RemoteVariable(   
            name         = "SeqCondBCount",
            description  = "BSA condition B counter",
            offset       =  0x04,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RO",
            number       =  50,
            stride       =  64,
        ))

        self.add(pr.RemoteVariable(   
            name         = "SeqCondCCount",
            description  = "BSA condition C counter",
            offset       =  0x04,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RO",
            number       =  50,
            stride       =  8,
        ))

        self.add(pr.RemoteVariable(   
            name         = "SeqCondDCount",
            description  = "BSA condition D counter",
            offset       =  0x04,
            bitSize      =  8,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RO",
            number       =  50,
            stride       =  8,
        ))

