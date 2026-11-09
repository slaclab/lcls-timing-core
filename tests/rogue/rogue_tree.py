#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Helpers that build and inspect LclsTimingCore device trees under Rogue.

Unlike the readers in tests/common, this module imports pyrogue and rogue, so
it is only importable where Rogue is installed. Importing it is also the Rogue
gate for every test in this directory: without Rogue the importing module
skips, and with LCLS_REQUIRE_ROGUE=1 a missing Rogue is an error.

``build_tree`` is the one place a root is created. It builds a
``pr.Root(pollEn=False)`` on a ``rim.Emulate`` memory, starts it, and always
stops it, including when ``start()`` itself raises (Rogue reports register
overlaps there).

Rogue normalizes ``offset`` and ``bitOffset`` to word alignment, so a variable
declared at offset 0x25 bit 5 reports address 0x24 bit 13. Everything here
therefore compares the absolute bit position, byte address * 8 + bit offset,
never the two numbers separately.
"""

import contextlib
import importlib
import os
import re

import pytest

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
import rogue.interfaces.memory as rim  # noqa: E402

from tests.common import register_drift  # noqa: E402

# Device nodes Rogue adds to every device; they are not register declarations.
VARIABLE_TYPES = (pr.RemoteVariable, pr.LinkVariable)

INDEX_RE = re.compile(r"^(?P<base>.*)\[(?P<index>\d+)\]$")


def rogue_class(name):
    """Return the device class called name.

    The package star imports rebind each submodule name to its class, so
    getattr on the package yields the class.
    """
    return getattr(importlib.import_module("LclsTimingCore"), name)


@contextlib.contextmanager
def build_tree(cls_or_name, memory=None, base=0, **args):
    """Build, start, yield (root, device, memory), and always stop the root."""
    cls = rogue_class(cls_or_name) if isinstance(cls_or_name, str) else cls_or_name
    root = pr.Root(name="root", pollEn=False)
    try:
        if memory is None:
            memory = rim.Emulate(4, 0x100000)
        root.addInterface(memory)
        device = cls(memBase=memory, offset=base, **args)
        root.add(device)
        root.start()
        yield root, device, memory
    finally:
        root.stop()


def tree_variables(device):
    """Return {path relative to device: variable} for the declared variables."""
    prefix = device.path + "."
    found = {}
    for var in device.variableList:
        if isinstance(var, VARIABLE_TYPES):
            found[var.path[len(prefix):] if var.path.startswith(prefix) else var.name] = var
    return found


def _split_index(path):
    match = INDEX_RE.match(path)
    if match:
        return match.group("base"), int(match.group("index"))
    return path, None


def python_fields(device, block):
    """Return one RegField per RemoteVariable of device, built at base 0."""
    fields = []
    for path, var in sorted(tree_variables(device).items()):
        if not isinstance(var, pr.RemoteVariable):
            continue
        name, index = _split_index(path)
        mode = var.mode
        fields.append(
            register_drift.RegField(
                block=block,
                name=name,
                index=index,
                byte_offset=var.address,
                bit_offset=var.bitOffset[0],
                bit_size=var.bitSize[0],
                mode=mode,
                source="python",
                line=0,
                readable=mode in ("RW", "RO"),
                writable=mode in ("RW", "WO"),
            )
        )
    return fields
