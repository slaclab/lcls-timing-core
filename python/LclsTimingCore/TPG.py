#-----------------------------------------------------------------------------
# Title      : PyRogue Timing generator module for AMC Carrier
#-----------------------------------------------------------------------------
# Description:
# PyRogue Timing generator module for AMC Carrier
#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue        as pr
import LclsTimingCore as lclsTiming

class TPG(pr.Device):
    def __init__(   self,
            name        = "TPG",
            description = "Timing generator module for AMC Carrier",
            **kwargs):
        super().__init__(name=name, description=description, **kwargs)

        ##############################
        # Variables
        ##############################

        self.add(lclsTiming.TPGControl(
            offset       =  0x00000000,
        ))

        self.add(lclsTiming.TPGStatus(
            offset       =  0x00000400,
        ))

        self.add(lclsTiming.TPGSeqState(
            offset       =  0x00000800,
        ))

        self.add(lclsTiming.TPGSeqJump(
            offset       =  0x00000400,
        ))
