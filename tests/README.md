# Regression tests

RTL leaf tests run cocotb under GHDL (VHDL) or Icarus Verilog (LCLS-I Verilog).
The PyRogue tests (models, round trips, and register-map drift) run in a conda
Rogue environment. Everything is driven from the repository root.

## Prerequisites

- `ghdl`, `iverilog`, `tclsh`, `make`, and Python 3.12 on `PATH`.
- The host `python3` (3.10) does not work: the cocotb version pinned in
  `pip_requirements.txt` needs Python 3.12. Use the venv below.

## Bootstrap

Clone the two ruckus-style dependencies next to the sources, from the
repository root:

```bash
git clone --depth 1 -b main https://github.com/slaclab/ruckus ruckus
git clone --depth 1 -b main https://github.com/slaclab/surf surf
```

To use existing local checkouts of surf and ruckus instead, point `MODULES` at
the directory that holds both `surf/` and `ruckus/`. It defaults to the
repository root, which is where the clones above land:

```bash
make MODULES=/path/to/dir-with-surf-and-ruckus import
```

Create the Python environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r pip_requirements.txt
```

Import the HDL libraries into `build/`:

```bash
make MODULES=$PWD import
```

Do not run `make import` while pytest is running: it recreates `build/`, which
the simulators read.

## Run

```bash
.venv/bin/python -m pytest -n auto tests/lcls2_core
.venv/bin/python -m pytest -n auto tests/lcls2_evr
.venv/bin/python -m pytest -n auto tests/lcls1_evr
```

`tests/lcls2_evr` covers the LCLS-II EVR blocks under GHDL. `tests/lcls1_evr`
holds both kinds of test: GHDL tests for the LCLS-I VHDL entities and Icarus
Verilog tests for the four Verilog leaves.

Running `.venv/bin/python -m pytest` from the repository root collects only
`tests/`. Each case is stopped after 900 seconds. Simulator build products go
to `tests/sim_build/`, which is not tracked.

Two knobs help when a result needs a closer look. This reproduces every known
defect (those tests fail until the RTL is fixed), and this replays the seeded
random traffic printed in a failing log:

```bash
RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -n auto tests/lcls2_core -k known_issue
RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -n auto tests/lcls2_evr -k known_issue
RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -n auto tests/lcls1_evr -k known_issue
RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -n auto tests/common -k known_issue
RUN_KNOWN_ISSUE_TESTS=1 LCLS_REQUIRE_ROGUE=1 PYTHONPATH=$PWD/python \
    micromamba run -p ./rogue-env python -m pytest -n auto tests/rogue -k known_issue
LCLS_TIMING_SEED=<n> .venv/bin/python -m pytest -n auto tests/lcls2_core
LCLS_TIMING_SEED=<n> .venv/bin/python -m pytest -n auto tests/lcls2_evr
LCLS_TIMING_SEED=<n> .venv/bin/python -m pytest -n auto tests/lcls1_evr
```

## Run what CI runs

Each block mirrors one CI job in `.github/workflows/timing_ci.yml`. Run them
from the repository root after the bootstrap above.

Linting (job `Linting`):

```bash
.venv/bin/python tests/common/lint_checks.py --include-untracked text
.venv/bin/python -m compileall -f -q python/ tests/
.venv/bin/flake8 --count python/ tests/
.venv/bin/python tests/common/lint_checks.py --include-untracked vsg
.venv/bin/python tests/common/compliance_audit.py audit tests
```

The audit only reports; it never changes the exit status. CI scans tracked
files, so `--include-untracked` is for local use before `git add`.

RTL legs (job `RTL test: <leg>`), one per directory under `tests/`:

```bash
make MODULES=$PWD import
.venv/bin/python -m pytest -n auto tests/common
.venv/bin/python -m pytest -n auto tests/lcls2_core
.venv/bin/python -m pytest -n auto tests/lcls1_evr
.venv/bin/python -m pytest -n auto tests/lcls2_evr
```

The probe behind the GHDL analysis gate prints one line per imported unit:

```bash
.venv/bin/python -m tests.common.ghdl_analysis --report
```

Rogue (job `Rogue Regression Tests`). Build the environment from
`conda-rogue.yml` with conda or micromamba, install `pip_requirements.txt`
into it, then run the tests with Rogue required, so a missing Rogue fails
instead of skipping:

```bash
micromamba create -y -p ./rogue-env -f conda-rogue.yml
micromamba run -p ./rogue-env python -m pip install -r pip_requirements.txt
LCLS_REQUIRE_ROGUE=1 PYTHONPATH=$PWD/python \
    micromamba run -p ./rogue-env python -m pytest tests/rogue
```

With `conda`, replace `micromamba create -p` and `micromamba run -p` by
`conda env create -f conda-rogue.yml` and `conda run -n
lcls-timing-core-rogue-test`. Keep the environment directory out of git.

Production guard (job `Production Guard`). It fails when a pull request
changes RTL, `python/LclsTimingCore/`, `yaml/`, `coregen/`, or a child
`ruckus.tcl`:

```bash
python3 tests/common/production_guard.py --base <base sha> --head <head sha>
```

In CI the job runs the guard script from the pull request base commit when
the base has one, so a pull request cannot change the check that judges it.
A maintainer can let an intended production change through by adding the
`production-change` label to the pull request; the job then reports the
bypass in its summary instead of failing. A usage or git error is never
bypassed.

Every job also writes the surf and ruckus commit SHAs and its tool versions
to the job summary. The same table is available locally:

```bash
.venv/bin/python tests/common/tool_versions.py surf ruckus ghdl iverilog python
```

## Coverage gate and units that are not simulated

`tests/common/test_core_inventory.py` fails when a unit that a `ruckus.tcl`
loads (LCLS-II/core, LCLS-II/evr, and LCLS-I) has no test of its own. A VHDL
entity counts as tested only when a test passes it, or its own wrapper, as the
`toplevel` of `run_lcls_vhdl_test`; a Verilog module only when a test passes it
to `run_icarus_verilog_test`. Being instantiated inside another unit's wrapper
does not count. The only units allowed without such a test are the keys of
`KNOWN_GHDL_UNANALYZABLE` and `NOT_SIMULATED` in `tests/common/ghdl_analysis.py`.

### Not simulated

EvrV1EventReceiver and EvrV1Core analyze cleanly under GHDL but cannot be
simulated. EvrV1EventReceiver instantiates EvrV1EventReceiverChannel,
EvrV1TimeofDayReceiver, EvrV1TimeStampGenerator, and EvrV1DbusDecode, which
are Verilog modules declared as VHDL components. GHDL cannot bind Verilog and
Icarus cannot elaborate VHDL, so the mixed-language top has no simulator.
EvrV1Core inherits the limit because it instantiates EvrV1EventReceiver. The
four Verilog leaves and the VHDL children (EvrV1Reg, EvrV1TimeStampFIFO,
EvrV1EventRAM256x32, EvrV1HeartBeat) are tested on their own. The reasons are kept in `NOT_SIMULATED`, and the gate fails if a listed
unit gains a test, so the entry gets removed with it.

### EvrV1DbusDecode and the Databuff model

Icarus rejects an unsized constant in a concatenation of EvrV1DbusDecode.v. The
regular test therefore compiles a patched copy, generated at test time under
`tests/sim_build/lcls1_evr/_patched/` and never tracked. The production file is
only read, and it is compiled as is by the known-issue test. EvrV1DbusDecode
instantiates a VHDL RAM that Icarus cannot elaborate, so its tests use a
behavioral Databuff model in `tests/lcls1_evr/models/`; a shared vector set
checks that the model and the production RAM agree.

## PyRogue models and register-map drift

The register maps of this repository exist three times: the VHDL decode, the
PyRogue classes in `python/LclsTimingCore/`, and the YAML maps in `yaml/`. The
suite checks each class on its own and compares the three sources.

Run the Rogue leg the way CI does (job `Rogue Regression Tests`), from the
repository root, in the environment built from `conda-rogue.yml`:

```bash
LCLS_REQUIRE_ROGUE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/python \
    micromamba run -p ./rogue-env python -m pytest -v -n auto tests/rogue
```

With another interpreter that has Rogue, call that interpreter's `python -m
pytest` with the same three variables. `LCLS_REQUIRE_ROGUE=1` turns a missing
Rogue into an error instead of a skip, and `PYTHONPATH` makes the tests use the
checked-out package rather than an installed copy. The files of the common leg
need no Rogue and run in the venv with `.venv/bin/python -m pytest -n auto
tests/common`.

What each family of files checks:

- `tests/rogue/tables/<Class>.py` is the reviewed expectation of one class: one
  row per declaration in the Python source (offset, bit offset, width, mode,
  array count and stride), written as the source reads.
- `tests/rogue/test_<Class>.py` builds the class under a Rogue root and
  compares the built variables with the table (path, absolute bit position,
  width, mode, base type, enum map), writes boundary values to every read-write
  variable and reads them back, and replays the traffic through a recording
  slave that logs each bus transaction. Classes that Rogue rejects at start
  (bit overlaps) are pinned with the exact Rogue message and have a gated
  `known_issue` test that expects the build to succeed.
- `tests/rogue/test_import_smoke.py` imports every module of the package.
- `tests/common/test_register_tables.py` and `tests/common/test_yaml_maps.py`
  cover the table engine and the YAML loader. The YAML test also pins each map
  that does not parse and each include that does not resolve.
- `tests/common/test_vhdl_registers.py` pins the VHDL decode parser to the
  layouts measured on the simulated RTL, so a parser change that loses a field
  fails.
- `tests/rogue/test_register_drift.py` compares the Python tree, the RTL decode,
  and the YAML map field by field (byte offset, bit offset, width, access mode,
  presence). Each difference must appear in `ALLOWLIST` in
  `tests/common/register_drift.py` with the issue that tracks it, or the test
  fails. `tests/common/test_register_drift.py` covers the comparison engine on
  synthetic fields.
- `tests/common/test_register_inventory.py` is the coverage gate. It fails when
  a class in `python/LclsTimingCore/` has no `tests/rogue/test_<Class>.py` or
  no `tests/rogue/tables/<Class>.py` (whose `CLASS` must equal the module
  name), when a test or table names no class, when a file in `yaml/` is not in
  `YAML_CLASSIFICATION` (or a classified file is gone), when a class is in
  neither `BLOCKS` nor `COVERED_BY_LEAVES`, and when a VHDL file under
  `LCLS-I` or `LCLS-II` that calls `axiSlaveWaitTxn`, `axiSlaveWaitWriteTxn`,
  or `axiSlaveWaitReadTxn` is not one of the keys of `DECODE_FILES`.

### Known defects

Some tests state the intended end state and fail while the defect exists. They
are skipped by default and run with `RUN_KNOWN_ISSUE_TESTS=1`:

```bash
RUN_KNOWN_ISSUE_TESTS=1 LCLS_REQUIRE_ROGUE=1 PYTHONPATH=$PWD/python \
    micromamba run -p ./rogue-env python -m pytest -n 0 tests/rogue -k known_issue
RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -n 0 tests/common -k known_issue
```

Seven tests of `tests/rogue` fail (five bit overlaps that Rogue rejects, and
two in `TPGMiniCore`) and two of `tests/common` fail (the YAML maps that do
not parse, and the include of `TPGSeqMem.yaml` that does not exist). When one
of them passes, the defect is fixed; prune the matching entries as described
under "Pruning after a fix".

### Drift report

`LCLS_DRIFT_REPORT=<path>` makes the drift test write every difference, one
line per field plus one line per block, to `<path>` (a temporary file renamed
into place, so a failed run leaves no partial report). Two runs on the same
tree give identical files:

```bash
LCLS_DRIFT_REPORT=/tmp/drift.txt LCLS_REQUIRE_ROGUE=1 PYTHONPATH=$PWD/python \
    micromamba run -p ./rogue-env python -m pytest -n 0 tests/rogue/test_register_drift.py
```

The same comparison runs on a copy of the package with
`python -m tests.rogue.rogue_tree drift --python-dir <copy> <Block>...`; the
seeded-drift tests use it so the checkout is never edited.

### Adding a class

1. Write `tests/rogue/tables/<Class>.py` once, from the built tree
   (`tests.rogue.rogue_tree.build_tree`), with `CLASS`, `ROWS`, `CHILDREN`, and
   `ARG_SETS` (the first argument set is `default`, with no arguments).
2. Review every row against the Python source. A table is a reviewed
   expectation: never regenerate it to make a test pass.
3. Write `tests/rogue/test_<Class>.py` (copy the nearest class of the same
   shape).
4. Add the class to `BLOCKS` in `tests/common/register_drift.py` (or to
   `COVERED_BY_LEAVES` when its children are compared directly), and add its
   YAML map, if any, to `YAML_CLASSIFICATION` in `tests/common/yaml_maps.py`.
5. Run `tests/common/test_register_inventory.py`; it names whatever is missing.

A new register decode file is the same step: add it to `DECODE_FILES` in
`tests/common/vhdl_registers.py`, paired with its block.

### Pruning after a fix

Every list of known differences fails in both directions: a difference that is
not listed fails the test, and a listed difference that no longer exists fails
the test until the entry is removed. When a fix lands, delete the entries it
makes stale:

- `ALLOWLIST` (`tests/common/register_drift.py`): the `(block, field, kind)`
  entries of the fixed registers. A difference that is only a spelling goes to
  `NAME_MAPS` in the same file instead, never to `ALLOWLIST`.
- `KNOWN_YAML_DEFECTS`, `KNOWN_MISSING_INCLUDES`, `UNKNOWN_KEYS`, and
  `SHAPE_FINDINGS` (`tests/common/yaml_maps.py`): the maps that do not parse,
  the includes that do not resolve, the key spellings CPSW does not define, and
  the arrays that declare no stride.
- `OBSERVED_OVERLAPS` (`tests/rogue/test_TPGMiniCore.py`): the bit overlaps the
  class is known to build with.

If a fix also changes a table row, review the row against the new source before
editing it.

## Tests that need a wrapper

When a block cannot be driven directly (for example a record port), put a thin
VHDL wrapper in a `wrappers/` directory beside the RTL it wraps, and pass it
to `run_lcls_vhdl_test` through `extra_vhdl_sources`. Wrappers are never listed
in a `ruckus.tcl`, so Vivado builds do not see them, and the production guard
allows `.vhd` files in a `wrappers/` directory below the repository root.

## New VHDL

Lint new VHDL files with the pinned vsg:

```bash
.venv/bin/vsg -f <file> -c vsg-linter.yml
```
