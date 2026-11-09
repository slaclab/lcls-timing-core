#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Register map drift between the RTL decode, the PyRogue tree, and the YAML map.

Test methodology:
    Sweep: every block in register_drift.BLOCKS, in sorted order, once per
        argument variant (for EvrV2TriggerReg the default arguments and
        useTap), so the parametrized ids are identical across xdist workers.
    Stimulus: the device class is built at base address 0 under a Rogue root
        with the variant's arguments; the VHDL decode file is parsed with the
        variant's generics; the YAML map is flattened only for a variant
        whose arguments enable every optional register, because the map has
        no conditional fields.
    Checks: register_drift.compare reports byte offset, bit offset, bit
        size, access mode, and presence per field, and verdict fails on any
        drift that is not in ALLOWLIST. A second test fails on any ALLOWLIST
        entry that no longer drifts, and a third validates the entries.
    Timing: no simulator and no polling; the Rogue root runs on an in-process
        memory and every root is stopped when its test ends.
    Propagation sampling: not applicable, a register map has no propagation
        delay.
"""

import pytest

from tests.common import register_drift, vhdl_registers, yaml_maps
from tests.rogue import rogue_tree


def _drifts(block, variant, make):
    _, device, _ = make(block.name, **variant.python_args)
    python = rogue_tree.python_fields(device, block.name)
    vhdl = None
    if block.vhdl is not None:
        decode = vhdl_registers.read_decode(block.vhdl, generics=variant.generics)
        vhdl = register_drift.from_vhdl(decode, block.name)
    yaml = None
    if block.yaml is not None and variant.compare_yaml:
        yaml = register_drift.from_yaml(yaml_maps.yaml_fields(block.yaml), block.name)
    return register_drift.compare(
        block.name, python, vhdl, yaml, register_drift.NAME_MAPS.get(block.name, {})
    )


CASES = [
    pytest.param(block, variant, id=f"{name}-{variant.id}")
    for name, block in sorted(register_drift.BLOCKS.items())
    for variant in block.variants
]


@pytest.mark.parametrize("block, variant", CASES)
def test_block_has_no_unlisted_drift(rogue_build, block, variant):
    drifts = _drifts(block, variant, rogue_build)
    reasons = register_drift.verdict(drifts, register_drift.ALLOWLIST, blocks=set())
    unlisted = [r for r in reasons if r.startswith("unlisted drift")]
    assert unlisted == [], "\n".join(unlisted)


def test_allowlist_entries_still_drift(rogue_build):
    drifts = []
    for _, block in sorted(register_drift.BLOCKS.items()):
        for variant in block.variants:
            drifts.extend(_drifts(block, variant, rogue_build))
    reasons = register_drift.verdict(
        drifts, register_drift.ALLOWLIST, blocks=set(register_drift.BLOCKS)
    )
    stale = [r for r in reasons if r.startswith("listed in ALLOWLIST")]
    assert stale == [], "\n".join(stale)


def test_allowlist_is_well_formed():
    register_drift.validate_allowlist(register_drift.ALLOWLIST)
