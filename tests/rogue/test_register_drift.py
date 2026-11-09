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
        keep every pairing of the earlier register tests. The seeded cases
        run the command line in a subprocess on a copy of the package: the
        unmodified copy passes, a one bit change to a variable that the RTL
        decodes fails as an unlisted drift, and fixing a listed drift fails
        as a stale entry.
    Timing: no simulator and no polling; each Rogue root runs on an
        in-process memory and is stopped before the next one is built; each
        subprocess has a 300 s timeout.
    Propagation sampling: not applicable, a register map has no propagation
        delay.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.common import ast_constants, register_drift, register_tables, vhdl_registers, yaml_maps
from tests.rogue import rogue_tree

CASES = [
    pytest.param(block, variant, id=f"{name}-{variant.id}")
    for name, block in sorted(register_drift.BLOCKS.items())
    for variant in block.variants
]

REPO_ROOT = Path(__file__).resolve().parents[2]

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


def test_source_reader_places_children_and_arrays(tmp_path):
    package = tmp_path / "LclsTimingCore"
    package.mkdir()
    (package / "Child.py").write_text(
        "import pyrogue as pr\n\n\n"
        "class Child(pr.Device):\n"
        "    def __init__(self, **kwargs):\n"
        "        super().__init__(**kwargs)\n"
        "        self.add(pr.RemoteVariable(name='A', offset=0x04, bitSize=8, bitOffset=2, mode='RO'))\n"
        "        self.addRemoteVariables(name='Arr', offset=0x10, bitSize=8, bitOffset=0,\n"
        "                                mode='RW', number=2, stride=4)\n",
        encoding="utf-8",
    )
    (package / "Parent.py").write_text(
        "import pyrogue as pr\nimport LclsTimingCore as lclsTiming\n\n\n"
        "class Parent(pr.Device):\n"
        "    def __init__(self, **kwargs):\n"
        "        super().__init__(**kwargs)\n"
        "        self.add(lclsTiming.Child(offset=0x100))\n",
        encoding="utf-8",
    )
    fields = rogue_tree.ast_python_fields("Parent", "Parent", python_dir=tmp_path)
    placed = sorted((f.name, f.index, f.byte_offset, f.bit_offset, f.bit_size, f.mode) for f in fields)
    assert placed == [
        ("Child.A", None, 0x104, 2, 8, "RO"),
        ("Child.Arr", 0, 0x110, 0, 8, "RW"),
        ("Child.Arr", 1, 0x114, 0, 8, "RW"),
    ]


def test_source_reader_rejects_a_non_literal_declaration(tmp_path):
    package = tmp_path / "LclsTimingCore"
    package.mkdir()
    (package / "Loop.py").write_text(
        "import pyrogue as pr\n\n\n"
        "class Loop(pr.Device):\n"
        "    def __init__(self, **kwargs):\n"
        "        super().__init__(**kwargs)\n"
        "        for i in range(2):\n"
        "            self.add(pr.RemoteVariable(name='X', offset=4 * i, bitSize=8, mode='RW'))\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not a literal"):
        rogue_tree.ast_python_fields("Loop", "Loop", python_dir=tmp_path)


def test_shared_helpers_serve_the_per_class_copies(rogue_build):
    """find_overlaps can ignore the declared flag, and all_ones picks the top value."""
    _, device, _ = rogue_build("TPGMiniCore")
    entries = rogue_tree.tree_entries(device)
    assert register_tables.find_overlaps(entries) == []
    pairs = register_tables.find_overlaps(
        entries, ignore_flag=True, honored={"BsaCompleteWr", "BsaCompleteRd"}
    )
    assert pairs == [
        ("BsaAvgToWr[1]", "BsaDestMode[1]"),
        ("BsaAvgToWr[1]", "BsaSequenceBitSelect[1]"),
        ("BsaAvgToWr[1]", "BsaSequenceSelect[1]"),
    ]
    assert rogue_tree.all_ones(entries["FixedRateDiv[0]"]) == 0xFFFFFFFF
    assert rogue_tree.all_ones(entries["BsaFixedRate[0]"]) == 6
    assert rogue_tree.all_ones(entries["TxPolarity"]) == 1
    boolean = register_tables.Expected("B", 0, 1, "RW", "Bool", None, "RemoteVariable", False, ())
    assert rogue_tree.all_ones(boolean) is True


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


@pytest.fixture
def python_copy(tmp_path):
    """A copy of python/ under tmp_path; seeded edits never touch the checkout."""
    target = tmp_path / "python"
    shutil.copytree(REPO_ROOT / "python", target, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def _edit_declaration(path, variable, old, new):
    """Replace old by new in the declaration of variable, after checking it is there."""
    text = path.read_text(encoding="utf-8")
    start = text.index(f'name        = "{variable}"')
    end = text.find("self.add(", start)
    end = len(text) if end < 0 else end
    block = text[start:end]
    assert old in block, f"{old!r} not found in the {variable} declaration"
    path.write_text(text[:start] + block.replace(old, new, 1) + text[end:], encoding="utf-8")


def _run_drift_cli(python_dir, *blocks):
    environment = dict(os.environ, LCLS_REQUIRE_ROGUE="1", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-m", "tests.rogue.rogue_tree", "drift", "--python-dir", str(python_dir), *blocks],
        cwd=REPO_ROOT, env=environment, capture_output=True, text=True, timeout=300,
    )


SEEDED = {
    "unmodified": (None, 0, None),
    # Polarity moves from bit 16 to bit 17 while the RTL decodes bit 16.
    "polarity_bit_offset": (
        ("Polarity", "bitOffset   = 16,", "bitOffset   = 17,"),
        1,
        "unlisted drift: ('EvrV2TriggerReg', 'Polarity', 'bitOffset')",
    ),
    # ComplEn moves to bit 28, where the RTL and the YAML map put it.
    "compl_en_fixed": (
        ("ComplEn", "bitOffset   = 29,", "bitOffset   = 28,"),
        1,
        "no longer drifts; remove the entry: ('EvrV2TriggerReg', 'ComplEn', 'bitOffset')",
    ),
}


@pytest.mark.parametrize("case", sorted(SEEDED))
def test_seeded_drift_is_reported(python_copy, case):
    edit, exit_code, reason = SEEDED[case]
    if edit is not None:
        _edit_declaration(python_copy / "LclsTimingCore" / "EvrV2TriggerReg.py", *edit)
    result = _run_drift_cli(python_copy, "EvrV2TriggerReg")
    assert result.returncode == exit_code, result.stdout + result.stderr
    if reason is None:
        # Rogue prints its version banner on stdout; no reason line may follow it.
        assert "unlisted drift" not in result.stdout and "no longer drifts" not in result.stdout
    else:
        assert reason in result.stdout, result.stdout + result.stderr


def test_seeded_cli_refuses_a_package_outside_python_dir(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    environment = dict(os.environ, LCLS_REQUIRE_ROGUE="1", PYTHONDONTWRITEBYTECODE="1")
    environment["PYTHONPATH"] = str(REPO_ROOT / "python")
    result = subprocess.run(
        [sys.executable, "-m", "tests.rogue.rogue_tree", "drift", "--python-dir", str(empty), "EvrV2TriggerReg"],
        cwd=REPO_ROOT, env=environment, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 2
    assert "outside" in result.stderr


def test_seeded_cli_rejects_an_unknown_block(python_copy):
    result = _run_drift_cli(python_copy, "NoSuchBlock")
    assert result.returncode == 2
    assert "unknown block" in result.stderr
