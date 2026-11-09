#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Shared setup for every Rogue test in this directory.

The repository ``python/`` directory is put at the front of ``sys.path`` so
the package under test is the checkout, never an installed copy.

Rogue itself is gated in ``rogue_tree``, which every test module imports:
without Rogue the module skips with a reason naming ``LCLS_REQUIRE_ROGUE``, and
with ``LCLS_REQUIRE_ROGUE=1`` a missing Rogue is a collection error instead.
The gate cannot live in this file, because a skip raised while pytest imports a
conftest is a collection error rather than a skip. ``rogue_tree`` is therefore
imported inside the fixtures, never at module level here.

Fixtures:
    rogue_build         function scoped factory that builds a device tree
    rogue_build_module  module scoped factory, for trees that tests only read
    recording_slave     a fresh RecordingSlave that logs every transaction

Every root built through the factories is stopped at teardown, even when the
build itself raised, so no test can leave a Rogue root running.
"""

import contextlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT / "python") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "python"))


def _factory(stack):
    from tests.rogue import rogue_tree

    def make(cls_name, *, memory=None, base=0, **args):
        return stack.enter_context(
            rogue_tree.build_tree(cls_name, memory=memory, base=base, **args)
        )

    return make


@pytest.fixture
def rogue_build():
    with contextlib.ExitStack() as stack:
        yield _factory(stack)


@pytest.fixture(scope="module")
def rogue_build_module():
    with contextlib.ExitStack() as stack:
        yield _factory(stack)


@pytest.fixture
def recording_slave():
    from tests.rogue import rogue_tree

    return rogue_tree.RecordingSlave()
