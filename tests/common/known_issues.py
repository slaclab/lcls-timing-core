#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Pytest plugin that inverts the known-issue tests.

A known-issue test is skipped by default, with a skipif reason that ends in
"set RUN_KNOWN_ISSUE_TESTS=1 to reproduce". Running with
``RUN_KNOWN_ISSUE_TESTS=1 pytest --expect-known-issues <path>`` selects only
those tests and expects each one to fail:

* an issue that still reproduces is reported as XFAIL and the run exits 0;
* an issue that no longer reproduces is reported as ``[XPASS(strict)]`` with
  the skip reason, and so the issue link, and the run exits 1.

This is the same two-direction contract as the GHDL analysis baseline: a
known problem may not silently disappear, and a fix has to prune its skip
and its allowlist or baseline entry. Without the option nothing in this
module changes collection or outcomes.

Tests are selected by the mark, never by name: a skipif whose reason contains
the marker text. A name filter such as ``-k known_issue`` also matches
ungated tests.

The module uses only the standard library and pytest. tests/conftest.py
imports its hooks so pytest finds them in the conftest namespace.
"""

import os
import re

import pytest

KNOWN_ISSUE_MARKER = "RUN_KNOWN_ISSUE_TESTS=1"
OPTION = "--expect-known-issues"
ISSUE_URL_RE = re.compile(r"https://github\.com/slaclab/lcls-timing-core/issues/\d+")


def known_issue_reason(item):
    """Return the reason of the first skipif mark that names the marker, else None."""
    for mark in item.iter_markers("skipif"):
        reason = mark.kwargs.get("reason", "")
        if KNOWN_ISSUE_MARKER in reason:
            return reason
    return None


def select_known_issues(items):
    """Split items into (kept, dropped) and mark each kept item as a strict xfail.

    The xfail deliberately names no expected exception type: the gated Rogue
    tests fail with rogue.GeneralError and the cocotb-test runs fail with
    SystemExit, so any single type would turn a reproducing issue into a
    failure.
    """
    kept, dropped = [], []
    for item in items:
        reason = known_issue_reason(item)
        if reason is None:
            dropped.append(item)
            continue
        item.add_marker(pytest.mark.xfail(strict=True, reason=reason))
        kept.append(item)
    return kept, dropped


def pytest_addoption(parser):
    parser.addoption(
        OPTION,
        action="store_true",
        default=False,
        help="run only the RUN_KNOWN_ISSUE_TESTS gated tests and expect each one to fail",
    )


def pytest_configure(config):
    if config.getoption("expect_known_issues", False) and os.environ.get("RUN_KNOWN_ISSUE_TESTS") != "1":
        raise pytest.UsageError("--expect-known-issues needs RUN_KNOWN_ISSUE_TESTS=1")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("expect_known_issues", False):
        return
    kept, dropped = select_known_issues(items)
    config.hook.pytest_deselected(items=dropped)
    items[:] = kept
