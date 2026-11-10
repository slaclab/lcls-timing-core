#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed placement of the child devices of python/LclsTimingCore/TPG.py.

TPG declares no registers of its own: it adds TPGControl, TPGStatus,
TPGSeqState, and TPGSeqJump at fixed offsets. Rogue 6.16.0 rejects the tree
at root.start(), so the rows are empty and CHILDREN is a snapshot of the
placement read from source.

TPGStatus and TPGSeqJump are both placed at 0x400. yaml/TPG.yaml carries the
same placement with "is this correct?" comments; the intent is asked in
https://github.com/slaclab/lcls-timing-core/issues/292.
The leaf tables of the four children are separate modules and are not
expanded for TPG here.
"""

from tests.common.register_tables import ArgSet, Child

CLASS = "TPG"

ROWS = ()

CHILDREN = (
    Child("TPGControl", "TPGControl", 0x000),
    Child("TPGStatus", "TPGStatus", 0x400),
    Child("TPGSeqState", "TPGSeqState", 0x800),
    # Shares 0x400 with TPGStatus.
    Child("TPGSeqJump", "TPGSeqJump", 0x400),
)

ARG_SETS = (
    ArgSet("default", {}),
)
