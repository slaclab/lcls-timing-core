#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed expectation table for python/LclsTimingCore/EvrV2CoreTriggers.py.

The class declares no variables of its own. It places numTrig
EvrV2ChannelReg groups at i * 0x100 and numTrig EvrV2TriggerReg groups at
0x1000 + i * 0x100, so the table holds child rules only and the leaf tables
stay the single source for the registers. A child flag follows the parent flag
named in args: dmaEnable reaches the channel groups and useTap the trigger
groups.

The constructor accepts tickUnit and passes it to the trigger groups; it has no
effect on the register layout, so no argument set varies it.
"""

from tests.common.register_tables import ArgSet, Child

CLASS = "EvrV2CoreTriggers"

ROWS = ()

CHILDREN = (
    Child("EvrV2ChannelReg[{i}]", "EvrV2ChannelReg", 0x000, number="numTrig", stride=0x100,
          args={"dmaEnable": "dmaEnable"}),
    Child("EvrV2TriggerReg[{i}]", "EvrV2TriggerReg", 0x1000, number="numTrig", stride=0x100,
          args={"useTap": "useTap"}),
)

DEFAULTS = {"numTrig": 1}

ARG_SETS = (
    ArgSet("default", {}),
    ArgSet("numTrig16", {"numTrig": 16}),
    ArgSet("dmaEnable", {"dmaEnable": True}, ("dmaEnable",)),
    ArgSet("useTap", {"useTap": True}, ("useTap",)),
)
