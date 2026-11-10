#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Import smoke of every LclsTimingCore module in a Rogue environment.

Test methodology:
    Sweep: every module found by pkgutil.iter_modules over
        python/LclsTimingCore, in sorted order so the parametrized ids are
        identical across runs and xdist workers.
    Stimulus: importlib.import_module for each module, with the repository
        python/ directory at the front of sys.path. The repository is never
        installed as a package, so nothing appends to the tracked
        __init__.py.
    Checks: the module object is read from sys.modules, because the package
        star imports shadow each submodule with its same-named class. The
        module defines its same-named attribute, and its __file__ resolves
        under the repository tree so an installed copy cannot stand in for
        the tree under test. Rogue itself must report a non-empty version.
    Timing: no hardware, no clocks, no polling. Importing a module builds no
        device tree.

Without Rogue the whole file skips with a reason naming LCLS_REQUIRE_ROGUE.
With LCLS_REQUIRE_ROGUE=1 a missing Rogue is a collection error instead.
"""

import importlib
import os
import pkgutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_DIR = REPO_ROOT / "python" / "LclsTimingCore"

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

MODULES = sorted(m.name for m in pkgutil.iter_modules([str(PKG_DIR)]))


def test_module_list_is_not_empty():
    assert MODULES, f"no modules found under {PKG_DIR}"


def test_rogue_importable():
    rogue = importlib.import_module("rogue")
    importlib.import_module("pyrogue")

    version = rogue.Version.current()
    assert isinstance(version, str) and version


@pytest.mark.parametrize("name", MODULES)
def test_import(name):
    importlib.import_module(f"LclsTimingCore.{name}")
    module = sys.modules[f"LclsTimingCore.{name}"]

    assert hasattr(module, name)
    assert Path(module.__file__).resolve().is_relative_to(PKG_DIR.resolve())
