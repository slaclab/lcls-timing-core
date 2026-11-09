Run the regression locally
==========================

The regression has four parts: RTL tests that run cocotb under GHDL (VHDL) or
Icarus Verilog (the LCLS-I Verilog leaves), PyRogue tests that run in a conda
Rogue environment, lint and audit checks, and the strict documentation build.
This page sets up one machine to run every leg that CI runs. Every command
below is checked against the CI workflows and :repo:`tests/README.md` by
:repo:`tests/common/test_docs_examples.py`, so the page cannot drift from CI
silently.

Prerequisites
-------------

- ``ghdl``, ``iverilog``, ``tclsh``, ``make``, and Python 3.12 on ``PATH``.
- Python 3.12 is required: the cocotb version pinned in
  :repo:`pip_requirements.txt` does not work with an older host ``python3``,
  so the commands below use a virtual environment.
- ``micromamba`` or ``conda`` for the Rogue leg.

Set up the environment
----------------------

Clone surf and ruckus ``main`` next to the sources, create the virtual
environment, and import the HDL libraries into ``build/``. Run every command
from the repository root.

.. code-block:: bash

   git clone --depth 1 -b main https://github.com/slaclab/ruckus ruckus
   git clone --depth 1 -b main https://github.com/slaclab/surf surf
   python3.12 -m venv .venv
   .venv/bin/python -m pip install -r pip_requirements.txt
   make MODULES=$PWD import

To use existing checkouts of surf and ruckus instead of fresh clones, point
``MODULES`` at the directory that holds both ``surf/`` and ``ruckus/``; it
defaults to the repository root.

.. warning::

   Never run ``make import`` while pytest is running. It recreates ``build/``,
   which the simulators read.

Run the RTL legs
----------------

There is one leg per directory under ``tests/``. ``common`` holds the
stdlib-only checks (register parsers, the reference generator, the docs tree
and example tests, the workflow tests); the other three hold the cocotb tests
of each source tree.

.. code-block:: bash

   .venv/bin/python -m pytest -q -n 4 tests/common
   .venv/bin/python -m pytest -q -n 4 tests/lcls2_core
   .venv/bin/python -m pytest -q -n 4 tests/lcls2_evr
   .venv/bin/python -m pytest -q -n 4 tests/lcls1_evr

``tests/lcls1_evr`` holds both kinds of simulation: GHDL for the LCLS-I VHDL
entities and Icarus Verilog for the four Verilog leaves. Each case is stopped
after 900 seconds, and simulator build products go to ``tests/sim_build/``,
which is not tracked. To replay the seeded random traffic that a failing log
prints, set ``LCLS_TIMING_SEED=<n>`` in front of the command.

Run the Rogue leg
-----------------

The PyRogue tests need Rogue, which comes from the conda environment described
by :repo:`conda-rogue.yml`. Create it, install the pip requirements into it,
and run the tests with Rogue required, so a missing Rogue fails instead of
skipping. ``PYTHONPATH`` makes the tests exercise the checked-out package
rather than an installed copy.

.. code-block:: bash

   micromamba create -y -p ./rogue-env -f conda-rogue.yml
   micromamba run -p ./rogue-env python -m pip install -r pip_requirements.txt
   LCLS_REQUIRE_ROGUE=1 PYTHONPATH=$PWD/python PYTHONDONTWRITEBYTECODE=1 \
       ./rogue-env/bin/python -m pytest -q -n 4 tests/rogue

With ``conda``, replace the first two commands by
``conda env create -f conda-rogue.yml`` and run the third with the interpreter
of the ``lcls-timing-core-rogue-test`` environment. Keep the environment
directory out of git.

Reproduce the known issues
--------------------------

Some tests state the intended end state of a defect and fail while the defect
exists. They are skipped by default and run only with
``RUN_KNOWN_ISSUE_TESTS=1``. Adding ``--expect-known-issues`` selects only
those tests and expects each to fail:

- ``XFAIL``: the issue still reproduces, and the run exits 0.
- ``XPASS(strict)``: the issue no longer reproduces, and the run fails with the
  issue link from the skip reason. The defect is fixed; prune the skip and its
  allowlist or baseline entry.

The option needs ``RUN_KNOWN_ISSUE_TESTS=1`` and exits with a usage error
without it. CI runs the same commands in the manual ``Known issues`` jobs
(Actions, Run workflow).

.. code-block:: bash

   RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -q -n 4 --expect-known-issues -rxX tests/common
   RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -q -n 4 --expect-known-issues -rxX tests/lcls2_core
   RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -q -n 4 --expect-known-issues -rxX tests/lcls2_evr
   RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -q -n 4 --expect-known-issues -rxX tests/lcls1_evr
   RUN_KNOWN_ISSUE_TESTS=1 LCLS_REQUIRE_ROGUE=1 PYTHONPATH=$PWD/python \
       ./rogue-env/bin/python -m pytest -q -n 4 --expect-known-issues -rxX tests/rogue

When ``GITHUB_STEP_SUMMARY`` is set, a run with the option also appends a table
with one row per selected test: whether it still reproduces, and the issue link
from its skip reason.

Run the lint and audit checks
-----------------------------

These are the commands of the ``Linting`` job. CI scans tracked files, so
``--include-untracked`` is for local use before ``git add``. The compliance
audit fails the job on any finding.

.. code-block:: bash

   .venv/bin/python tests/common/lint_checks.py --include-untracked text
   .venv/bin/python -m compileall -f -q python/ tests/
   .venv/bin/flake8 --count python/ tests/
   .venv/bin/python tests/common/lint_checks.py --include-untracked vsg
   .venv/bin/python tests/common/compliance_audit.py audit tests --fail-on-findings

Regenerate and check the reference
----------------------------------

The entity reference pages under ``docs/reference/`` are generated from the
VHDL declarations, the PyRogue classes, and the YAML maps. Regenerate them
after changing a source or a test that moves a verification status, and check
that the committed pages are fresh. CI enforces the same freshness through
``test_committed_reference_matches_a_fresh_generation`` in the ``common`` leg,
not through a separate step.

.. code-block:: bash

   .venv/bin/python -m tests.common.gen_docs
   .venv/bin/python -m tests.common.gen_docs --check

Build the documentation
-----------------------

The ``Documentation`` job builds the site with warnings as errors, so a broken
reference, an orphan page, or a malformed table fails it.

.. code-block:: bash

   .venv/bin/python -m pip install -r docs/requirements.txt
   .venv/bin/sphinx-build -W --keep-going docs/ docs/_build/html

Open ``docs/_build/html/index.html`` to read the result.

Production guard
----------------

The ``Production Guard`` job fails a pull request that changes RTL,
``python/LclsTimingCore/``, ``yaml/``, ``coregen/``, or a child ``ruckus.tcl``.
Run it locally with
``python3 tests/common/production_guard.py --base <base sha> --head <head sha>``.
A maintainer can let an intended production change through with the
``production-change`` label on the pull request.

CI job names and their local commands
-------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 28 24 48

   * - CI job
     - Workflow
     - Local command
   * - ``Linting``
     - ``timing_ci.yml``
     - The lint and audit commands above.
   * - ``RTL test: <leg>``
     - ``timing_ci.yml``
     - ``make MODULES=$PWD import``, then the leg command of "Run the RTL
       legs".
   * - ``Rogue Regression Tests``
     - ``timing_ci.yml``
     - The Rogue command of "Run the Rogue leg".
   * - ``Known issues: <leg>``
     - ``timing_ci.yml`` (manual)
     - The ``--expect-known-issues`` command of the leg.
   * - ``Known issues: rogue``
     - ``timing_ci.yml`` (manual)
     - The ``--expect-known-issues`` Rogue command.
   * - ``Production Guard``
     - ``timing_ci.yml``
     - ``tests/common/production_guard.py`` as above.
   * - ``Documentation``
     - ``timing_ci.yml`` and ``docs.yml``
     - The strict ``sphinx-build`` command.

See also
--------

- :doc:`/reference/known_issues`
