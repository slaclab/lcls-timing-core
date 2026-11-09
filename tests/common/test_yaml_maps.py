#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Every YAML register map in yaml/ loads, and its defects are pinned exactly.

Test methodology:
    Sweep: all 20 files of yaml/, each loaded with its includes spliced in;
        the parse failures, the unresolved includes, and (in later cases) the
        register shape of every map that parses.
    Stimulus: the repository files themselves, read with PyYAML safe_load
        only; no Rogue and no simulator.
    Checks: every file is classified once; the set of files that fail to parse
        equals the recorded baseline with the exact error class, line, and
        message; the only unresolved include is TPGSeqMem.yaml. A new failure
        fails, and a recorded failure that disappears fails until the entry is
        removed. Two gated tests state the intended end state (the include
        resolves, every map parses) and fail while the maps are defective.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import os
from pathlib import Path

import pytest

from tests.common import yaml_maps as ym

KNOWN_ISSUE_SKIP = os.getenv("RUN_KNOWN_ISSUE_TESTS") != "1"

REPO_YAML = Path(__file__).resolve().parents[2] / "yaml"


@pytest.fixture(scope="module")
def loaded():
    return ym.load_all()


def test_every_yaml_file_is_classified():
    on_disk = {path.name for path in REPO_YAML.glob("*.yaml")}
    classified = set(ym.YAML_CLASSIFICATION)
    assert on_disk - classified == set(), f"yaml/ files with no classification: {sorted(on_disk - classified)}"
    assert classified - on_disk == set(), f"classified files missing from yaml/: {sorted(classified - on_disk)}"
    assert set(ym.YAML_CLASSIFICATION.values()) == {"drift", "shape"}
    shape = sorted(name for name, kind in ym.YAML_CLASSIFICATION.items() if kind == "shape")
    assert shape == [
        "AmcCarrierDRAM.yaml",
        "BldAxiStream.yaml",
        "EvrV2Module.yaml",
        "EvrV2PulsegenRegs.yaml",
        "EvrV2TriggerPulse.yaml",
    ]


def test_parse_results_match_baseline(loaded):
    assert list(loaded) == sorted(loaded)
    assert ym.defect_verdict(loaded) == []
    assert sorted(name for name, result in loaded.items() if result.error is not None) == sorted(
        ym.KNOWN_YAML_DEFECTS
    )


def test_only_unresolved_include_is_tpgseqmem(loaded):
    unresolved = {name: tuple(result.missing_includes) for name, result in loaded.items() if result.missing_includes}
    assert unresolved == ym.KNOWN_MISSING_INCLUDES


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPG.yaml includes TPGSeqMem.yaml, which does not exist in yaml/; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_yaml_known_issue_tpgseqmem_include(loaded):
    missing = loaded["TPG.yaml"].missing_includes
    assert not missing, f"TPG.yaml includes {missing}, which does not exist in yaml/"


@pytest.mark.skipif(
    KNOWN_ISSUE_SKIP,
    reason=(
        "known issue: TPG.yaml, TPGControl.yaml, and TPGSeqState.yaml do not parse; "
        "set RUN_KNOWN_ISSUE_TESTS=1 to reproduce"
    ),
)
def test_yaml_known_issue_every_file_parses(loaded):
    failing = sorted(name for name, result in loaded.items() if result.error is not None)
    assert not failing, f"these maps do not parse: {failing}"
