#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed snapshot of python/LclsTimingCore/TPGSeqState.py as declared.

Rogue 6.16.0 rejects this class at root.start(), so the tree cannot be built
and the rows are a snapshot of the source, read by tests/common/pyrogue_ast.py
and checked line by line by hand. They are recorded as declared, not as
intended.

Each row is an array of 50 entries. SeqIndex is a 32 bit word every 8 bytes.
The four condition counts (SeqCondACount to SeqCondDCount) are all 8 bits at
byte 4, bit 0. SeqCondACount, SeqCondCCount, and SeqCondDCount have a stride
of 8, so they share one byte in every entry; SeqCondBCount has a stride of 64,
so element i lands on the byte of element 8 * i of the others. The bit
offsets are tracked in
https://github.com/slaclab/lcls-timing-core/issues/221, and the
SeqCondBCount stride is asked in
https://github.com/slaclab/lcls-timing-core/issues/228.
"""

from tests.common.register_tables import ArgSet, Row

CLASS = "TPGSeqState"

ROWS = (
    Row("SeqIndex", offset=0x00, bit_offset=0, bit_size=32, mode="RO", number=50, stride=8),
    Row("SeqCondACount", offset=0x04, bit_offset=0, bit_size=8, mode="RO", number=50, stride=8),
    Row("SeqCondBCount", offset=0x04, bit_offset=0, bit_size=8, mode="RO", number=50, stride=64),
    Row("SeqCondCCount", offset=0x04, bit_offset=0, bit_size=8, mode="RO", number=50, stride=8),
    Row("SeqCondDCount", offset=0x04, bit_offset=0, bit_size=8, mode="RO", number=50, stride=8),
)

CHILDREN = ()

ARG_SETS = (
    ArgSet("default", {}),
)
