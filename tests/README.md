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

## New VHDL

Lint new VHDL files with the pinned vsg:

```bash
.venv/bin/vsg -f <file> -c vsg-linter.yml
```
