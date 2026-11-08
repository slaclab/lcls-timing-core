#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Placeholder so the tests can import the module and fail on behavior."""

BYPASS_LABEL = "production-change"


def is_protected(path):
    return False


def changed_paths(base, head):
    return []


def escape_workflow_data(text):
    return text


def main(argv=None):
    return 0
