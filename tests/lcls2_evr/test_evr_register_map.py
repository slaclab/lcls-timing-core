#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Unit tests of the PyRogue source reader used by the EVR register walks.

Test methodology:
    Sweep: the three shipped PyRogue files EvrV2TriggerReg.py,
        EvrV2ChannelReg.py and EvrV2Core.py, plus small synthetic sources.
    Stimulus: tests.common.pyrogue_ast reads each file as text.
    Checks: declaration counts (9, 11 and 21 calls), the expansion of
        addRemoteVariables into 12 entries per array, the bit positions
        ComplEn 29 and ComplAnd 30 exactly as written, equal absolute bits
        for an offset plus bit offset written two ways, the captured useTap
        and dmaEnable conditions, a non-literal bitSize, a missing mode read
        as RW, two reads being equal, and neither pyrogue nor rogue being
        imported.
    Timing: none, no simulator.
    Propagation sampling: none, no simulator.
"""

import subprocess
import sys
import textwrap

import pytest

from tests.common import pyrogue_ast
from tests.common.regression_utils import REPO_ROOT

PYTHON_DIR = REPO_ROOT / "python" / "LclsTimingCore"
TRIGGER_REG = PYTHON_DIR / "EvrV2TriggerReg.py"
CHANNEL_REG = PYTHON_DIR / "EvrV2ChannelReg.py"
CORE = PYTHON_DIR / "EvrV2Core.py"


def by_name(variables):
    return {var.name: var for var in variables}


def declaration_count(variables):
    """Return the number of calls the variables came from (one source line per call)."""
    return len({var.line for var in variables})


@pytest.mark.parametrize(
    ("path", "calls"),
    [(TRIGGER_REG, 9), (CHANNEL_REG, 11), (CORE, 21)],
    ids=["trigger_reg", "channel_reg", "core"],
)
def test_declaration_counts(path, calls):
    variables = pyrogue_ast.read_remote_variables(path)
    assert declaration_count(variables) == calls


def test_trigger_reg_has_one_entry_per_call():
    assert len(pyrogue_ast.read_remote_variables(TRIGGER_REG)) == 9


def test_array_calls_expand_to_twelve_entries():
    variables = pyrogue_ast.read_remote_variables(CORE)
    names = [var.name for var in variables]
    assert len(variables) == 9 + 12 * 12
    for stem in ("ChannelBsaEnable", "ChannelDestSel", "ChannelEventCnt", "TriggerChannel", "TriggerFineDelay"):
        assert [name for name in names if name.startswith(stem + "[")] == [f"{stem}[{i}]" for i in range(12)]
    named = by_name(variables)
    assert named["ChannelDestSel[0]"].offset == 0x25
    assert named["ChannelDestSel[11]"].offset == 0x25 + 11 * 32
    assert named["TriggerDelay[3]"].offset == 0x208 + 3 * 16


def test_source_order_is_kept():
    names = [var.name for var in pyrogue_ast.read_remote_variables(TRIGGER_REG)]
    assert names == [
        "EnableTrig",
        "Source",
        "Polarity",
        "ComplEn",
        "ComplAnd",
        "Delay",
        "Width",
        "DelayTap",
        "DelayTapReadback",
    ]


def test_compl_bits_read_as_written():
    named = by_name(pyrogue_ast.read_remote_variables(TRIGGER_REG))
    assert named["ComplEn"].bit_offset == 29
    assert named["ComplAnd"].bit_offset == 30
    assert named["EnableTrig"].bit_offset == 31
    assert named["Polarity"].bit_offset == 16


def test_offset_and_bit_offset_give_the_same_absolute_bits():
    named = by_name(pyrogue_ast.read_remote_variables(CORE))
    assert pyrogue_ast.absolute_bits(named["ChannelDestSel[0]"]).start == 0x24 * 8 + 13
    assert pyrogue_ast.absolute_bits(named["ChannelDestSel[0]"]).start == 0x25 * 8 + 5
    assert len(pyrogue_ast.absolute_bits(named["ChannelDestSel[0]"])) == 18


def test_conditions_are_captured():
    tap = by_name(pyrogue_ast.read_remote_variables(TRIGGER_REG))
    assert tap["DelayTap"].condition == "useTap"
    assert tap["DelayTapReadback"].condition == "useTap"
    assert tap["Delay"].condition is None
    chan = by_name(pyrogue_ast.read_remote_variables(CHANNEL_REG))
    for name in ("BsaEnabled", "dmaEnabled", "BsaWindowDelay", "BsaWindowSetup", "BsaWindowWidth"):
        assert chan[name].condition == "dmaEnable", name
    for name in ("EnableReg", "RateSel", "DestSel", "Count"):
        assert chan[name].condition is None, name


def test_modes():
    named = by_name(pyrogue_ast.read_remote_variables(TRIGGER_REG))
    assert named["DelayTapReadback"].mode == "RO"
    assert named["Delay"].mode == "RW"
    core = by_name(pyrogue_ast.read_remote_variables(CORE))
    assert core["ChannelEventCnt[0]"].mode == "RW"
    assert core["IrqStatus"].mode == "RO"
    chan = by_name(pyrogue_ast.read_remote_variables(CHANNEL_REG))
    assert chan["RateType"].mode == "RW", "a declaration without mode reads as RW"


def test_two_reads_are_equal():
    for path in (TRIGGER_REG, CHANNEL_REG, CORE):
        assert pyrogue_ast.read_remote_variables(path) == pyrogue_ast.read_remote_variables(path)


def test_non_literal_values_are_marked_not_raised():
    source = textwrap.dedent(
        """
        class Dev(pr.Device):
            def __init__(self, width=3):
                self.add(pr.RemoteVariable(name="Wide", offset=0x10, bitSize=width, bitOffset=2))
        """
    )
    (var,) = pyrogue_ast.parse_remote_variables(source)
    assert var.bit_size == pyrogue_ast.NON_LITERAL
    assert var.mode == "RW"
    with pytest.raises(ValueError, match="bit_size"):
        pyrogue_ast.absolute_bits(var)


def test_else_branch_carries_the_negated_condition():
    source = textwrap.dedent(
        """
        if flag:
            self.add(pr.RemoteVariable(name="A", offset=0, bitSize=1))
        else:
            self.add(pr.RemoteVariable(name="B", offset=4, bitSize=1))
        self.add(pr.RemoteVariable(name="C", offset=8, bitSize=1))
        """
    )
    conditions = {var.name: var.condition for var in pyrogue_ast.parse_remote_variables(source)}
    assert conditions == {"A": "flag", "B": "not (flag)", "C": None}


def test_reader_does_not_import_rogue():
    """A fresh interpreter that reads every file ends with neither package imported."""
    code = (
        "import sys\n"
        "from tests.common import pyrogue_ast\n"
        f"for p in {[str(TRIGGER_REG), str(CHANNEL_REG), str(CORE)]!r}:\n"
        "    pyrogue_ast.read_remote_variables(p)\n"
        "assert 'pyrogue' not in sys.modules and 'rogue' not in sys.modules\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_reader_source_never_executes_code():
    import ast

    tree = ast.parse((REPO_ROOT / "tests/common/pyrogue_ast.py").read_text(encoding="utf-8"))
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called & {"eval", "exec", "compile", "__import__"}
