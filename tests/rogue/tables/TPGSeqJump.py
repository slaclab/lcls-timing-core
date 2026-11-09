#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed snapshot of python/LclsTimingCore/TPGSeqJump.py as declared.

Rogue 6.16.0 rejects this class at root.start(), so the tree cannot be built
and the rows are a snapshot of the source, read by tests/common/pyrogue_ast.py
and checked line by line by hand. They are recorded as declared, not as
intended.

Each row is an array of 1024 words (stride 4). Class is declared at byte 1
with bit offset 0, which puts it at absolute bit 8 of the word, on bits 8 to
11 of StartAddr (12 bits wide). yaml/TPGSeqJump.yaml puts Class at bit 4 of
byte 1, absolute bit 12, which does not overlap StartAddr. Tracked in
https://github.com/slaclab/lcls-timing-core/issues/220.
"""

from tests.common.register_tables import ArgSet, Row

CLASS = "TPGSeqJump"

ROWS = (
    Row("StartAddr", offset=0x00, bit_offset=0, bit_size=12, mode="RW", number=1024, stride=4),
    Row("Class", offset=0x01, bit_offset=0, bit_size=4, mode="RW", number=1024, stride=4),
    Row("StartSync", offset=0x02, bit_offset=0, bit_size=16, mode="RW", number=1024, stride=4),
)

CHILDREN = ()

ARG_SETS = (
    ArgSet("default", {}),
)
