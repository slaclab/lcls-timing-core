#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Structural tests of .github/workflows/timing_ci.yml.

Test methodology:
    Sweep: the parsed workflow: its triggers, job ids and display names, the
        test matrix, the release gate, per-job permissions and timeouts,
        action pins, the scripts of the production guard, Rogue, lint, and
        documentation jobs, and the tool version step of every job.
    Stimulus: yaml.safe_load of the workflow file; the repository tree for
        the matrix legs.
    Checks: renaming a job or matrix leg, dropping a release prerequisite,
        adding a job-level condition to the production guard job, unpinned
        actions, event expressions inside shell scripts, a missing Rogue
        check, packaging steps, and surf or ruckus clones in the
        documentation job each fail one named test, as does a job that drops
        surf or ruckus from its tool version step or runs it too late.
    Timing: static. No workflow is run and nothing is simulated.
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "timing_ci.yml"

REUSABLE_RELEASE = "slaclab/ruckus/.github/workflows/gen_release.yml@main"
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")
PR_TYPES = {"opened", "synchronize", "reopened", "labeled", "unlabeled"}

JOB_NAMES = {
    "lint": "Linting",
    "test": "RTL test: ${{ matrix.module }}",
    "rogue_test": "Rogue Regression Tests",
    "production_guard": "Production Guard",
    "test_and_document": "Test And Generate Documentation",
}
MATRIX_LEGS = ["common", "lcls1_evr", "lcls2_core", "lcls2_evr"]
RELEASE_NEEDS = {"lint", "test", "rogue_test", "production_guard",
                 "test_and_document"}
TOOL_ITEMS = {
    "lint": ["surf", "ruckus", "ghdl", "python", "flake8", "vsg"],
    "test": ["surf", "ruckus", "ghdl", "iverilog", "python", "cocotb",
             "cocotb-test"],
    "rogue_test": ["surf", "ruckus", "python", "rogue", "cocotb",
                   "cocotb-test"],
    "production_guard": ["surf", "ruckus", "python", "git"],
    "test_and_document": ["surf", "ruckus", "python", "doxygen"],
}
FIRST_WORK_STEP = (r"^(make|python -m pytest|doxygen|"
                   r'python3 "\$\{RUNNER_TEMP\}/production_guard\.py")')


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def jobs(workflow):
    return workflow["jobs"]


def step_runs(job):
    """Return (index, step, run text) for every step that has a run script."""
    return [(i, step, step["run"])
            for i, step in enumerate(job.get("steps", []))
            if "run" in step]


def first_index(job, pattern):
    """Index of the first step whose run script matches the regex."""
    for i, _, run in step_runs(job):
        if re.search(pattern, run):
            return i
    return None


def test_triggers_are_push_and_pull_request_with_label_types(workflow):
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"push", "pull_request"}
    assert set(triggers["pull_request"]["types"]) == PR_TYPES


def test_pull_request_target_is_never_used(workflow):
    triggers = workflow.get("on", workflow.get(True))
    assert "pull_request_target" not in triggers
    code_lines = [line for line in WORKFLOW_FILE.read_text().splitlines()
                  if not line.lstrip().startswith("#")]
    assert not any("pull_request_target" in line for line in code_lines)


def test_job_ids_and_display_names(jobs):
    assert set(jobs) == set(JOB_NAMES) | {"gen_release"}
    for job_id, name in JOB_NAMES.items():
        assert jobs[job_id]["name"] == name, job_id


def test_matrix_legs_each_have_a_test_file(jobs):
    matrix = jobs["test"]["strategy"]["matrix"]
    assert matrix["module"] == MATRIX_LEGS
    assert jobs["test"]["strategy"]["fail-fast"] is False
    for leg in MATRIX_LEGS:
        assert list((REPO_ROOT / "tests" / leg).glob("test_*.py")), leg


def test_release_needs_every_job(jobs):
    release = jobs["gen_release"]
    assert set(release["needs"]) == RELEASE_NEEDS
    assert release["uses"] == REUSABLE_RELEASE
    assert "if" not in release


def test_production_guard_has_no_job_level_condition(jobs):
    assert "if" not in jobs["production_guard"]


def test_jobs_have_read_permissions_and_a_timeout(jobs):
    for job_id, job in jobs.items():
        if job_id == "gen_release":
            continue
        assert job["permissions"] == {"contents": "read"}, job_id
        assert isinstance(job["timeout-minutes"], int), job_id


def test_third_party_actions_are_pinned_to_a_commit(jobs):
    seen = 0
    for job_id, job in jobs.items():
        for step in job.get("steps", []):
            if "uses" in step:
                seen += 1
                assert PINNED_ACTION.match(step["uses"]), (job_id,
                                                           step["uses"])
    assert seen > 0


def test_no_shell_script_reads_an_event_expression(jobs):
    for job_id, job in jobs.items():
        for _, step, run in step_runs(job):
            assert "github.event" not in run, (job_id, step.get("name"))


def test_production_guard_reads_event_values_through_env(jobs):
    env = jobs["production_guard"]["env"]
    assert env["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert env["HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    assert env["BYPASS"] == ("${{ contains(github.event.pull_request."
                             "labels.*.name, 'production-change') }}")


def test_production_guard_runs_the_base_commit_copy(jobs):
    job = jobs["production_guard"]
    checkout = job["steps"][0]
    assert checkout["with"]["fetch-depth"] == 0
    by_name = {step.get("name"): step for step in job["steps"]}
    note = by_name["Not a pull request"]
    assert note["if"] == "github.event_name != 'pull_request'"
    check = by_name["Check production bytes"]
    assert check["if"] == "github.event_name == 'pull_request'"
    run = check["run"]
    assert 'git show "${BASE_SHA}:tests/common/production_guard.py"' in run
    assert 'python3 "${RUNNER_TEMP}/production_guard.py"' in run
    assert '--base "$BASE_SHA" --head "$HEAD_SHA"' in run
    shown = run.index("git show")
    launched = run.index('python3 "${RUNNER_TEMP}')
    assert shown < launched


def test_production_guard_bypasses_only_a_failure_with_the_label(jobs):
    run = {step.get("name"): step
           for step in jobs["production_guard"]["steps"]}[
        "Check production bytes"]["run"]
    assert re.search(r'\[ "\$rc" -eq 1 \] && \[ "\$BYPASS" = "true" \]', run)
    assert 'exit "$rc"' in run


def test_rogue_job_verifies_rogue_before_any_pytest_step(jobs):
    job = jobs["rogue_test"]
    verify = first_index(job, r"import rogue, pyrogue")
    pytest_step = first_index(job, r"-m pytest")
    assert verify is not None and pytest_step is not None
    assert verify < pytest_step
    assert job["defaults"]["run"]["shell"] == "bash -el {0}"


def test_rogue_job_builds_the_conda_environment_and_requires_rogue(jobs):
    job = jobs["rogue_test"]
    conda = [s for s in job["steps"] if "setup-miniconda" in s.get("uses", "")]
    assert len(conda) == 1
    inputs = conda[0]["with"]
    assert inputs["environment-file"] == "conda-rogue.yml"
    assert inputs["activate-environment"] == "lcls-timing-core-rogue-test"
    assert inputs["miniforge-variant"] == "Miniforge3"
    run = [s for s in job["steps"] if "-m pytest" in s.get("run", "")][0]
    assert run["env"]["LCLS_REQUIRE_ROGUE"] == "1"
    assert 'PYTHONPATH="$PWD/python"' in run["run"]
    assert "tests/rogue" in run["run"]
    assert first_index(job, r"pip install -r pip_requirements\.txt")


def test_lint_job_runs_every_check_in_ci_order(jobs):
    job = jobs["lint"]
    patterns = [
        r"make MODULES=\$PWD import",
        r"tests/common/lint_checks\.py text",
        r"compileall .*python/ tests/",
        r"flake8 --count python/ tests/",
        r"tests/common/lint_checks\.py vsg",
        r"tests/common/compliance_audit\.py audit tests",
    ]
    indices = [first_index(job, pattern) for pattern in patterns]
    assert None not in indices, indices
    assert indices == sorted(indices)
    audit = [s for s in job["steps"] if "compliance_audit" in s.get("run", "")]
    assert "$GITHUB_STEP_SUMMARY" in audit[0]["run"]
    assert "continue-on-error" not in audit[0]
    clones = [r for _, _, r in step_runs(job) if "git clone" in r]
    assert any("slaclab/surf" in c and "slaclab/ruckus" in c for c in clones)


def test_rtl_leg_installs_both_simulators_and_runs_its_own_tests(jobs):
    job = jobs["test"]
    install = [r for _, _, r in step_runs(job) if "apt-get install" in r][0]
    assert "ghdl" in install and "iverilog" in install
    assert first_index(job, r"-m pytest .*tests/\$\{\{ matrix\.module \}\}")


def test_documentation_job_builds_doxygen_without_the_dependencies(jobs):
    job = jobs["test_and_document"]
    runs = "\n".join(run for _, _, run in step_runs(job))
    assert "doxygen Doxyfile" in runs
    assert not re.search(r"git clone|make |flake8", runs)
    deploy = [s for s in job["steps"] if "gh-pages" in s.get("uses", "")][0]
    assert deploy["if"] == "startsWith(github.ref, 'refs/tags/')"


def test_no_step_packages_the_repository(jobs):
    banned = re.compile(r"setup\.py|pip install (-e )?\.(\s|$)|conda build"
                        r"|python -m build|PYTHONPATH=.*pip install")
    for job_id, job in jobs.items():
        for _, step, run in step_runs(job):
            assert not banned.search(run), (job_id, step.get("name"))


def tool_version_steps(job):
    return [(i, run) for i, _, run in step_runs(job)
            if "tests/common/tool_versions.py" in run]


@pytest.mark.parametrize("job_id", sorted(TOOL_ITEMS))
def test_every_job_logs_the_expected_tool_versions(jobs, job_id):
    found = tool_version_steps(jobs[job_id])
    assert len(found) == 1, job_id
    words = found[0][1].split()
    items = [w for w in words[2:] if not w.startswith("--")]
    assert items == TOOL_ITEMS[job_id]
    assert {"surf", "ruckus"} <= set(items)


@pytest.mark.parametrize("job_id", sorted(TOOL_ITEMS))
def test_remote_deps_exactly_when_the_job_clones_nothing(jobs, job_id):
    job = jobs[job_id]
    clones = any("git clone" in run for _, _, run in step_runs(job))
    _, run = tool_version_steps(job)[0]
    assert ("--remote-deps" in run.split()) is (not clones), job_id


@pytest.mark.parametrize("job_id", sorted(TOOL_ITEMS))
def test_tool_versions_come_before_any_make_pytest_guard_or_doxygen(
        jobs, job_id):
    job = jobs[job_id]
    logged, _ = tool_version_steps(job)[0]
    for i, _, run in step_runs(job):
        if re.search(FIRST_WORK_STEP, run.strip(), re.MULTILINE):
            assert logged < i, (job_id, job["steps"][i].get("name"))


def test_the_release_job_declares_no_steps(jobs):
    assert "steps" not in jobs["gen_release"]


def test_workflow_is_ascii():
    WORKFLOW_FILE.read_bytes().decode("ascii")
