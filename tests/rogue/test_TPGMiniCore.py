#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""TPGMiniCore device tree build and BsaActive register placement.

Test methodology:
    Sweep: NARRAYSBSA over 1, 2, 4, 5 and 32. TPGMiniReg asserts
        NARRAYS_BSA < 33, so 32 is the largest firmware build and 5 is the
        first value that used to collide with the BSA definition words.
    Stimulus: a pyrogue Root holding one TPGMiniCore on a MemEmulate slave,
        started with polling and the initial read disabled. One test writes
        single BsaActive elements and inspects the bytes MemEmulate stored.
    Checks: Root.start() accepts the register map (Rogue rejects overlapping
        bit masks there). Every BsaActive element sits in the BSACTRL word at
        0x01FC with bit offset equal to its index, which is how TPGMiniReg
        decodes it (bsadefv(i).init := regWrData(i)). Writing one element
        sets exactly that bit of the word and leaves the first BSA definition
        word at 0x0200 untouched.
    Timing: no hardware, no clocks, no polling.

Without Rogue the whole file skips with a reason naming LCLS_REQUIRE_ROGUE.
With LCLS_REQUIRE_ROGUE=1 a missing Rogue is a collection error instead.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python"))

REQUIRE_ROGUE = os.environ.get("LCLS_REQUIRE_ROGUE") == "1"

if REQUIRE_ROGUE:
    importlib.import_module("rogue")
    importlib.import_module("pyrogue")
else:
    pytest.importorskip(
        "pyrogue",
        reason=(
            "Rogue is not installed; run in the conda-rogue.yml env and set "
            "LCLS_REQUIRE_ROGUE=1 to make this a hard failure"
        ),
    )

import pyrogue as pr  # noqa: E402
import pyrogue.interfaces.simulation  # noqa: E402

from LclsTimingCore.TPGMiniCore import TPGMiniCore  # noqa: E402

BSACTRL_OFFSET = 0x01FC
BSADEF_OFFSET  = 0x0200
NARRAYS_CASES  = [1, 2, 4, 5, 32]


@pytest.fixture
def tpg_root(request):
    mem = pr.interfaces.simulation.MemEmulate()
    root = pr.Root(name="root", pollEn=False, initRead=False)
    root.add(TPGMiniCore(name="TPGMiniCore", NARRAYSBSA=request.param, memBase=mem))
    root.start()
    try:
        yield root, mem, request.param
    finally:
        root.stop()


@pytest.mark.parametrize("tpg_root", NARRAYS_CASES, indirect=True)
def test_bsaactive_one_bit_per_array(tpg_root):
    root, _mem, narrays = tpg_root
    bsa_active = root.TPGMiniCore.BsaActive

    assert sorted(bsa_active) == list(range(narrays))
    for i in range(narrays):
        var = bsa_active[i]
        assert var.offset == BSACTRL_OFFSET, f"BsaActive[{i}] at {var.offset:#x}"
        assert var.bitSize == [1]
        assert var.bitOffset == [i]


@pytest.mark.parametrize("tpg_root", [32], indirect=True)
def test_bsaactive_write_lands_in_bsactrl_word(tpg_root):
    root, mem, narrays = tpg_root
    base = root.TPGMiniCore.offset + BSACTRL_OFFSET
    bsadef = root.TPGMiniCore.offset + BSADEF_OFFSET

    def word(addr):
        return int.from_bytes(bytes(mem._data.get(addr + k, 0) for k in range(4)), "little")

    for i in (0, 1, 3, 4, 31):
        root.TPGMiniCore.BsaActive[i].set(1, write=True)
        assert word(base) == 1 << i, f"BsaActive[{i}] wrote {word(base):#010x}"
        assert word(bsadef) == 0, f"BsaActive[{i}] touched {BSADEF_OFFSET:#x}"
        root.TPGMiniCore.BsaActive[i].set(0, write=True)
        assert word(base) == 0
