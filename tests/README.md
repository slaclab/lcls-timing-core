# Regression tests

RTL leaf tests run cocotb under GHDL (VHDL) or Icarus Verilog (LCLS-I Verilog).
PyRogue import tests run in a conda Rogue environment. Everything is driven
from the repository root.

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
.venv/bin/python -m pytest -n auto tests/lcls1_evr
```

Running `.venv/bin/python -m pytest` from the repository root collects only
`tests/`. Each case is stopped after 900 seconds. Simulator build products go
to `tests/sim_build/`, which is not tracked.

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
