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
        argument variant (for example EvrV2TriggerReg with the default
        arguments and useTap, TimingFrameRx with each clock select mode,
        TPGMiniCore with 1, 2, and 4 BSA arrays), so the parametrized ids are
        identical across xdist workers.
    Stimulus: the device class is built at base address 0 under a Rogue root
        with the variant's arguments; the VHDL decode file is parsed with the
        variant's generics; the YAML map is flattened only for the variant
        whose arguments enable every optional register, because the map has
        no conditional fields. A block with no RTL in the repository is
        compared between Python and YAML alone, and a YAML map that does not
        parse is one block-level finding.
    Checks: register_drift.compare_block reports byte offset, bit offset, bit
        size, access mode, and presence per field, and verdict fails on any
        drift that is not in ALLOWLIST. A second test fails on any ALLOWLIST
        entry that no longer drifts and writes the drift report when
        LCLS_DRIFT_REPORT names a path; a third validates the entries; two
        more check that every block has its sources and that the name maps
        keep every pairing of the earlier register tests.
    Timing: no simulator and no polling; each Rogue root runs on an
        in-process memory and is stopped before the next one is built.
    Propagation sampling: not applicable, a register map has no propagation
        delay.
"""

import os
from pathlib import Path

import pytest

from tests.common import ast_constants, register_drift, vhdl_registers, yaml_maps
from tests.rogue import rogue_tree

CASES = [
    pytest.param(block, variant, id=f"{name}-{variant.id}")
    for name, block in sorted(register_drift.BLOCKS.items())
    for variant in block.variants
]

# The name maps of the earlier register testbenches, as (file, constant, block).
EARLIER_MAPS = (
    ("tests/lcls2_evr/test_EvrV2Axi.py", "NAME_MAP", "EvrV2Core"),
    ("tests/lcls2_evr/test_EvrV2ChannelReg.py", "NAME_MAP", "EvrV2ChannelReg"),
    ("tests/lcls2_evr/test_EvrV2TrigReg.py", "NAME_MAP", "EvrV2TriggerReg"),
)

# Earlier RTL names that the decode reports under another spelling: the
# interrupt request is the local register sReg, and the global event count is
# the thirteenth entry of the event count mux.
EARLIER_ALIASES = {
    ("EvrV2Core", "irqReq"): "sReg",
    ("EvrV2Core", "globalCount"): "eventCount[12]",
}


def _all_results():
    return [
        rogue_tree.variant_result(block, variant)
        for _, block in sorted(register_drift.BLOCKS.items())
        for variant in block.variants
    ]


@pytest.mark.parametrize("block, variant", CASES)
def test_block_has_no_unlisted_drift(block, variant):
    result = rogue_tree.variant_result(block, variant)
    reasons = register_drift.verdict(result.drifts, register_drift.ALLOWLIST, blocks=set())
    unlisted = [r for r in reasons if r.startswith("unlisted drift")]
    assert unlisted == [], "\n".join(unlisted)


def test_allowlist_entries_still_drift():
    results = _all_results()
    drifts = [drift for result in results for drift in result.drifts]
    reasons = register_drift.verdict(
        drifts, register_drift.ALLOWLIST, blocks=set(register_drift.BLOCKS)
    )
    report = os.environ.get("LCLS_DRIFT_REPORT")
    if report:
        register_drift.write_report(report, register_drift.format_report(results, register_drift.ALLOWLIST))
    stale = [r for r in reasons if r.startswith("listed in ALLOWLIST")]
    assert stale == [], "\n".join(stale)


# Classes with no conditional declarations, so the source reader and the built
# tree describe the same variables.
UNCONDITIONAL = ("EvrV1Isr", "EvrV2Core", "GthRxAlignCheck", "LclsTriggerPulse", "TPGControl")


@pytest.mark.parametrize("name", UNCONDITIONAL)
def test_source_reader_matches_built_tree(name, rogue_build):
    """The reader used for the rejected classes agrees with Rogue where both work."""
    _, device, _ = rogue_build(name)

    def key(field):
        return (field.name, field.index, field.abs_bit, field.bit_size, field.mode)

    built = sorted(map(key, rogue_tree.python_fields(device, name)), key=repr)
    read = sorted(map(key, rogue_tree.ast_python_fields(name, name)), key=repr)
    assert read == built


def test_allowlist_is_well_formed():
    register_drift.validate_allowlist(register_drift.ALLOWLIST)


def test_name_maps_cover_earlier_maps():
    """Every Python to RTL pair of the earlier testbenches is in NAME_MAPS."""
    missing = []
    for path, constant, block in EARLIER_MAPS:
        earlier = ast_constants.read_constants(path, [constant])[constant]
        assert earlier, f"{path} {constant} is empty"
        ours = register_drift.NAME_MAPS[block]
        for python_name, rtl_name in sorted(earlier.items()):
            rtl_name = EARLIER_ALIASES.get((block, rtl_name), rtl_name)
            if python_name == rtl_name:
                continue
            if ours.get(python_name, {}).get("vhdl", python_name) != rtl_name:
                missing.append((block, python_name, rtl_name))
    assert missing == []


def test_every_block_has_sources():
    for name, block in register_drift.BLOCKS.items():
        assert block.name == name
        if block.vhdl is not None:
            assert block.vhdl in vhdl_registers.DECODE_FILES, (name, block.vhdl)
            assert vhdl_registers.DECODE_FILES[block.vhdl] == name, (name, block.vhdl)
        assert block.yaml in yaml_maps.YAML_CLASSIFICATION, (name, block.yaml)
        assert yaml_maps.YAML_CLASSIFICATION[block.yaml] == "drift", (name, block.yaml)
        assert sum(variant.compare_yaml for variant in block.variants) == 1, name
        assert (Path(__file__).resolve().parents[2] / "python" / "LclsTimingCore" / f"{name}.py").is_file()
