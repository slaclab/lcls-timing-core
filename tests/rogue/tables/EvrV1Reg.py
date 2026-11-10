#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reviewed snapshot of python/LclsTimingCore/EvrV1Reg.py as declared.

Rogue 6.16.0 rejects this class at root.start(), so the tree cannot be built
and the rows are a snapshot of the source, read by tests/common/pyrogue_ast.py
and checked line by line by hand. They are recorded as declared, not as
intended.

Pulse00 to Pulse11 are twelve arrays of four 32 bit words (stride 4), and
OutputMap is twelve 16 bit entries (stride 4). IrqFlagWr (write only) and
IrqFlagRd (read only) are declared on the same word at 0x08, a pairing that
needs overlapEn on both variables; tracked in
https://github.com/slaclab/lcls-timing-core/issues/285. MapRam1 and MapRam2
are commented out in the source and are not declared.
"""

from tests.common.register_tables import ArgSet, Row

CLASS = "EvrV1Reg"

ROWS = (
    Row("Status", offset=0x00, bit_offset=0, bit_size=32, mode="RO"),
    Row("Control", offset=0x04, bit_offset=0, bit_size=32, mode="RW"),
    # IrqFlagWr (WO) and IrqFlagRd (RO) are declared on the same 32 bits of 0x08 without
    # overlapEn, which Rogue rejects: https://github.com/slaclab/lcls-timing-core/issues/285
    Row("IrqFlagWr", offset=0x08, bit_offset=0, bit_size=32, mode="WO"),
    Row("IrqFlagRd", offset=0x08, bit_offset=0, bit_size=32, mode="RO"),
    Row("IrqEnable", offset=0x0C, bit_offset=0, bit_size=32, mode="RW"),
    Row("PulseIrqMap", offset=0x10, bit_offset=0, bit_size=32, mode="RW"),
    Row("PcieIntEna", offset=0x14, bit_offset=0, bit_size=32, mode="RW"),
    Row("FWVersion", offset=0x2C, bit_offset=0, bit_size=32, mode="RO"),
    Row("FWVersionUnmasked", offset=0x30, bit_offset=0, bit_size=32, mode="RO"),
    Row("UsecDivider", offset=0x4C, bit_offset=0, bit_size=32, mode="RW"),
    Row("SecSR", offset=0x5C, bit_offset=0, bit_size=32, mode="RO"),
    Row("SecCounter", offset=0x60, bit_offset=0, bit_size=32, mode="RO"),
    Row("EventCounter", offset=0x64, bit_offset=0, bit_size=32, mode="RO"),
    Row("SecLatch", offset=0x68, bit_offset=0, bit_size=32, mode="RO"),
    Row("EvCntLatch", offset=0x6C, bit_offset=0, bit_size=32, mode="RO"),
    Row("IntEventEn", offset=0xA0, bit_offset=0, bit_size=32, mode="RW"),
    Row("IntEventCount", offset=0xA4, bit_offset=0, bit_size=1, mode="RW"),
    Row("IntEventCode", offset=0xA8, bit_offset=0, bit_size=8, mode="RW"),
    Row("ExtEventEn", offset=0xAC, bit_offset=0, bit_size=1, mode="RW"),
    Row("ExtEventCode", offset=0xB0, bit_offset=0, bit_size=8, mode="RW"),
    Row("Pulse00", offset=0x200, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse01", offset=0x210, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse02", offset=0x220, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse03", offset=0x230, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse04", offset=0x240, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse05", offset=0x250, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse06", offset=0x260, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse07", offset=0x270, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse08", offset=0x280, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse09", offset=0x290, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse10", offset=0x2A0, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("Pulse11", offset=0x2B0, bit_offset=0, bit_size=32, mode="RW", number=4, stride=4),
    Row("OutputMap", offset=0x440, bit_offset=0, bit_size=16, mode="RW", number=12, stride=4),
)

CHILDREN = ()

ARG_SETS = (
    ArgSet("default", {}),
)
