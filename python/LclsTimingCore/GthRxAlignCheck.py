#-----------------------------------------------------------------------------
# Title      : PyRogue Timing frame phase lock
#-----------------------------------------------------------------------------
# Description:
# PyRogue Timing frame phase lock
#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr

class GthRxAlignCheck(pr.Device):
    def __init__(   self,
            name        = "GthRxAlignCheck",
            description = "Timing frame phase lock",
            **kwargs):
        super().__init__(name=name, description=description, **kwargs)

        ##############################
        # Variables
        ##############################

        # self.addRemoteVariables(
            # name         = "PhaseCount",
            # description  = "Timing frame phase",
            # offset       =  0x00,
            # bitSize      =  16,
            # bitOffset    =  0x00,
            # mode         = "RO",
            # pollInterval = 1,
            # number       =  128,
            # stride       =  2,
            # hidden       =  True,
        # )

        self.addRemoteVariables(
            name         = "PhaseCount",
            description  = "Timing frame phase",
            offset       =  0x00,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
            number       =  64,
            stride       =  4,
            hidden       =  True,
        )

        self.add(pr.RemoteVariable(
            name         = "PhaseTarget",
            description  = "Timing frame phase lock target",
            offset       =  0x100,
            bitSize      =  7,
            bitOffset    =  0x00,
            mode         = "RW",
        ))


        self.add(pr.RemoteVariable(
            name         = "Mask",
            description  = "Mask",
            offset       =  0x100,
            bitSize      =  7,
            bitOffset    =  8,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "ResetLen",
            description  = "Reset length",
            offset       =  0x100,
            bitSize      =  4,
            bitOffset    =  16,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "LastPhase",
            description  = "Last timing frame phase seen",
            offset       =  0x104,
            bitSize      =  7,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "TxClkFreqRaw",
            offset       = 0x108,
            bitSize      = 32,
            bitOffset    = 0,
            mode         = 'RO',
            hidden       = True,
            pollInterval = 1,
        ))

        self.add(pr.LinkVariable(
            name         = "TxClkFreq",
            units        = "MHz",
            mode         = 'RO',
            dependencies = [self.TxClkFreqRaw],
            linkedGet    = lambda: self.TxClkFreqRaw.value() * 1.0e-6,
            disp         = '{:0.3f}',
        ))

        self.add(pr.RemoteVariable(
            name         = "RxClkFreqRaw",
            offset       = 0x10C,
            bitSize      = 32,
            bitOffset    = 0,
            mode         = 'RO',
            hidden       = True,
            pollInterval = 1,
        ))

        self.add(pr.LinkVariable(
            name         = "RxClkFreq",
            units        = "MHz",
            mode         = 'RO',
            dependencies = [self.RxClkFreqRaw],
            linkedGet    = lambda: self.RxClkFreqRaw.value() * 1.0e-6,
            disp         = '{:0.3f}',
        ))
