#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed expectation table for python/LclsTimingCore/EvrV1Isr.py.

The class declares one variable and takes no arguments that change it, so
there is one argument set.
"""

from tests.common.register_tables import ArgSet, Row

CLASS = "EvrV1Isr"

ROWS = (
    Row("IsrSelect", offset=0x00, bit_offset=0, bit_size=1, mode="RW"),
)

CHILDREN = ()

ARG_SETS = (
    ArgSet("default", {}),
)
