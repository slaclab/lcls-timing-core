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
from pathlib import Path

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

from tests.common import pyrogue_ast, register_drift, register_tables, vhdl_registers, yaml_maps  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIR = REPO_ROOT / "python"

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
        name, index = register_drift.split_index(path)
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


def _declared_fields(path, block, base, prefix, depth=0):
    """RegFields for the declarations of the PyRogue file at path, read from source.

    A composite file adds child devices; each child file is read the same way
    at the child's offset and its names carry the child's name.
    """
    if depth > 3:
        raise ValueError(f"{path}: child devices nest deeper than three levels")
    fields = []
    for var in pyrogue_ast.read_remote_variables(path):
        for label, value in (("offset", var.offset), ("bit_offset", var.bit_offset), ("bit_size", var.bit_size)):
            if not isinstance(value, int):
                raise ValueError(f"{path}:{var.line}: {var.name} {label} is not a literal ({value!r})")
        name, index = register_drift.split_index(prefix + var.name)
        fields.append(
            register_drift.RegField(
                block=block,
                name=name,
                index=index,
                byte_offset=base + var.offset,
                bit_offset=var.bit_offset,
                bit_size=var.bit_size,
                mode=var.mode,
                source="python",
                line=var.line,
                readable=var.mode in ("RW", "RO"),
                writable=var.mode in ("RW", "WO"),
            )
        )
    for child in pyrogue_ast.read_child_devices(path):
        if not isinstance(child.offset, int):
            raise ValueError(f"{path}:{child.line}: child {child.name} offset is not a literal")
        fields.extend(
            _declared_fields(
                Path(path).with_name(f"{child.cls}.py"), block, base + child.offset,
                f"{prefix}{child.name}.", depth + 1,
            )
        )
    return fields


def ast_python_fields(class_name, block, python_dir=None):
    """RegFields for a class read from its source file, for a class Rogue rejects.

    The declarations are read with ast and never run, so a class whose tree
    cannot be built is still compared. Array declarations are expanded from
    their literal number and stride; a composite class (TPG) reads each
    child's file at the child's offset.
    """
    root = Path(python_dir) if python_dir is not None else PYTHON_DIR
    return _declared_fields(root / "LclsTimingCore" / f"{class_name}.py", block, 0, "")


def block_result(block, variant, make):
    """Compare one variant of a block across the sources it has.

    make builds a device the way the rogue_build fixture does, so the caller
    owns the lifetime of the Rogue root. The VHDL decode is read with the
    variant's generics, and the YAML map is read only for a variant that
    compares it; a map that is known not to parse becomes one block-level
    finding instead.
    """
    if block.python_source == "ast":
        python = ast_python_fields(block.name, block.name)
    else:
        _, device, _ = make(block.name, **variant.python_args)
        python = python_fields(device, block.name)
    vhdl = None
    skip = frozenset()
    if block.vhdl is not None:
        decode = vhdl_registers.read_decode(block.vhdl, generics=variant.generics)
        vhdl = register_drift.from_vhdl(decode, block.name)
        skip = register_drift.unresolved_words(decode.unresolved)
    yaml = None
    unreadable = False
    if block.yaml is not None and variant.compare_yaml:
        if block.yaml in yaml_maps.KNOWN_YAML_DEFECTS:
            unreadable = True
        else:
            yaml = register_drift.from_yaml(yaml_maps.yaml_fields(block.yaml), block.name)
    return register_drift.compare_block(
        block, variant, python, vhdl, yaml,
        register_drift.NAME_MAPS.get(block.name, {}), yaml_unreadable=unreadable, vhdl_skip=skip,
    )


def variant_result(block, variant):
    """Build one variant under its own root, compare it, and stop the root."""
    with contextlib.ExitStack() as stack:
        return block_result(
            block, variant, lambda cls, **args: stack.enter_context(build_tree(cls, **args))
        )


def _kind(var):
    # RemoteCommand is a RemoteVariable subclass, so it is checked first.
    if isinstance(var, pr.RemoteCommand):
        return "RemoteCommand"
    if isinstance(var, pr.RemoteVariable):
        return "RemoteVariable"
    return "LinkVariable"


def tree_entries(device):
    """Return {path: Expected} for the declared variables of a tree at base 0.

    The attributes read are address, bitOffset, bitSize, mode, enum, and
    overlapEn on RemoteVariables, the Rogue model class name from the private
    _base attribute (UInt, Bool, and so on), and dependencies on
    LinkVariables.
    """
    entries = {}
    for path, var in tree_variables(device).items():
        if isinstance(var, pr.RemoteVariable):
            position = register_tables.abs_bit(var.address, var.bitOffset[0])
            size = var.bitSize[0]
            base = type(var._base).__name__
            depends = ()
        else:
            position, size, base = None, None, None
            depends = tuple(sorted(dep.name for dep in var.dependencies))
        entries[path] = register_tables.Expected(
            path=path,
            abs_bit=position,
            bit_size=size,
            mode=var.mode,
            base=base,
            enum=dict(var.enum) if var.enum else None,
            kind=_kind(var),
            overlap_en=bool(getattr(var, "overlapEn", False)),
            depends=depends,
        )
    return entries


def check_table(device, class_name, arg_set):
    """Return the differences between the reviewed table and the built tree."""
    expected = register_tables.expand(register_tables.load_table(class_name), arg_set)
    return register_tables.diff_variables(expected, tree_entries(device))


def round_trip_values(var):
    """Boundary values to write: all ones, one, and the top bit; or the enum ends."""
    if isinstance(var._base, pr.Bool):
        return [True, False]
    if var.enum:
        keys = list(var.enum)
        return [keys[0]] if len(keys) == 1 else [keys[0], keys[-1]]
    size = var.bitSize[0]
    values = [(1 << size) - 1, 1, 1 << (size - 1)]
    if size <= 8:
        values.extend(1 << bit for bit in range(size))
    return list(dict.fromkeys(values))


def _word_span(var):
    start = register_tables.abs_bit(var.address, var.bitOffset[0])
    end = start + var.bitSize[0]
    return start // 32 * 32, (end - 1) // 32 * 32 + 32


def round_trip(device, exempt=frozenset()):
    """Write boundary values to every RW variable and read them back.

    Each variable is written before it is read. The other readable variables
    that share a 32-bit word with it must read the value they held before the
    write, unless the pair is listed in exempt (pairs as find_overlaps returns
    them, matched in either order). Returns sorted failure messages.
    """
    skip = {frozenset(pair) for pair in exempt}
    variables = {
        path: var
        for path, var in tree_variables(device).items()
        if isinstance(var, pr.RemoteVariable) and not isinstance(var, pr.RemoteCommand)
    }
    failures = []
    for path in sorted(variables):
        var = variables[path]
        if var.mode != "RW":
            continue
        low, high = _word_span(var)
        neighbors = [
            other
            for other_path, other in sorted(variables.items())
            if other_path != path
            and other.mode in ("RW", "RO")
            and frozenset((path, other_path)) not in skip
            and register_tables.abs_bit(other.address, other.bitOffset[0]) < high
            and register_tables.abs_bit(other.address, other.bitOffset[0]) + other.bitSize[0] > low
        ]
        for value in round_trip_values(var):
            before = {other.path: other.get(read=True) for other in neighbors}
            var.set(value)
            got = var.get(read=True)
            if got != value:
                failures.append(f"{path}: wrote {value!r}, read {got!r}")
            for other in neighbors:
                after = other.get(read=True)
                if after != before[other.path]:
                    failures.append(
                        f"{path}: writing {value!r} changed {other.path} from {before[other.path]!r} to {after!r}"
                    )
    return sorted(failures)


class RecordingSlave(rim.Slave):
    """In-process memory that logs every transaction it serves.

    log entries are (direction, type, address, size, bytes) with direction "W"
    for rim.Write and rim.Post and "R" for rim.Read and rim.Verify. mem is a
    byte addressed backing store, so a Verify read returns what was written.
    """

    def __init__(self):
        super().__init__(4, 4096)
        self.log = []
        self.mem = {}

    def _doTransaction(self, transaction):
        address, size, kind = transaction.address(), transaction.size(), transaction.type()
        try:
            if kind in (rim.Write, rim.Post):
                data = bytearray(size)
                transaction.getData(data, 0)
                for offset in range(size):
                    self.mem[address + offset] = data[offset]
                self.log.append(("W", kind, address, size, bytes(data)))
            else:
                data = bytearray(self.mem.get(address + offset, 0) for offset in range(size))
                transaction.setData(data, 0)
                self.log.append(("R", kind, address, size, bytes(data)))
        finally:
            transaction.done()

    def writes(self):
        return [entry for entry in self.log if entry[0] == "W"]

    def reads(self):
        return [entry for entry in self.log if entry[0] == "R"]

    def clear(self):
        self.log.clear()

    def preload(self, address, data):
        for offset, value in enumerate(data):
            self.mem[address + offset] = value


def written_bits(log):
    """Return the absolute bits set by the write transactions in log."""
    bits = set()
    for direction, _, address, _, data in log:
        if direction != "W":
            continue
        for offset, value in enumerate(data):
            for bit in range(8):
                if value >> bit & 1:
                    bits.add((address + offset) * 8 + bit)
    return bits
