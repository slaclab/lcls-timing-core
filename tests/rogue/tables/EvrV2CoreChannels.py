#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed expectation table for python/LclsTimingCore/EvrV2CoreChannels.py.

The class declares no variables of its own. It places numTrig
EvrV2ChannelReg groups at i * 0x100, so the table holds one child rule and
EvrV2ChannelReg stays the single source for the registers. The dmaEnable flag
reaches the channel groups.

The constructor also accepts useTap and tickUnit but never uses them (they
belong to the trigger groups of EvrV2CoreTriggers), so the useTap argument set
expands exactly like the default one.
"""

from tests.common.register_tables import ArgSet, Child

CLASS = "EvrV2CoreChannels"

ROWS = ()

CHILDREN = (
    Child("EvrV2ChannelReg[{i}]", "EvrV2ChannelReg", 0x000, number="numTrig", stride=0x100,
          args={"dmaEnable": "dmaEnable"}),
)

DEFAULTS = {"numTrig": 1}

ARG_SETS = (
    ArgSet("default", {}),
    ArgSet("numTrig16", {"numTrig": 16}),
    ArgSet("dmaEnable", {"dmaEnable": True}, ("dmaEnable",)),
    ArgSet("useTap", {"useTap": True}),
)
