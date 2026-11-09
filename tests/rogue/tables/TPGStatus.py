#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed snapshot of python/LclsTimingCore/TPGStatus.py as declared.

Rogue 6.16.0 rejects this class at root.start(), so the tree cannot be built
and the rows are a snapshot of the source, read by tests/common/pyrogue_ast.py
and checked line by line by hand. They are recorded as declared, not as
intended.

CountSeq is an array of 64 counters of 32 bits with a stride of 2 bytes, so
each counter shares two bytes with the next one. The intended stride is
asked in https://github.com/slaclab/lcls-timing-core/issues/228.
"""

from tests.common.register_tables import ArgSet, Row

CLASS = "TPGStatus"

ROWS = (
    Row("BsaStat", offset=0x00, bit_offset=0, bit_size=32, mode="RO", number=64, stride=4),
    Row("CountPLL", offset=0x100, bit_offset=0, bit_size=32, mode="RO"),
    Row("Count186M", offset=0x104, bit_offset=0, bit_size=32, mode="RO"),
    Row("CountSyncE", offset=0x108, bit_offset=0, bit_size=32, mode="RO"),
    Row("CountIntv", offset=0x10C, bit_offset=0, bit_size=32, mode="RW"),
    Row("CountBRT", offset=0x110, bit_offset=0, bit_size=32, mode="RO"),
    Row("CountTrig", offset=0x114, bit_offset=0, bit_size=32, mode="RO", number=12, stride=4),
    Row("CountSeq", offset=0x144, bit_offset=0, bit_size=32, mode="RO", number=64, stride=2),
    Row("CountRxClks", offset=0x248, bit_offset=0, bit_size=32, mode="RW"),
    Row("CountRxDV", offset=0x24C, bit_offset=0, bit_size=32, mode="RW"),
)

CHILDREN = ()

ARG_SETS = (
    ArgSet("default", {}),
)
