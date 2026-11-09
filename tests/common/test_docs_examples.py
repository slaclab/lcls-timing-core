#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Check that the examples on the how-to pages match what they describe.

Test methodology:
    Sweep: every code block of every page under docs/how-to/. Shell commands
        of the run-the-regression page are compared with the commands of the
        two workflow files and the fenced blocks of tests/README.md.
    Stimulus: the RST read as text, the workflow files read with
        yaml.safe_load, tests/README.md read as text, and the shell lines
        tokenized with shlex. Nothing is executed.
    Checks: a shell command on the run-the-regression page that equals no CI
        or README command after normalization (environment prefixes, the
        interpreter path, and the pytest parallelism and reporting options
        are normalized away on both sides), a documented-only command whose
        CI enforcement is gone, a normalizer that stops splitting or
        stripping as specified, and a code block that pipes a download into a
        shell, runs setup.py, installs the working tree with pip, or embeds a
        token each fail one named test.
    Timing: not applicable, no clock and no simulated time.
    Propagation sampling: not applicable, there is no propagation delay.
"""

import ast
import re
import shlex
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
HOW_TO = REPO_ROOT / "docs" / "how-to"
RUN_REGRESSION = HOW_TO / "run_regression.rst"
README_TESTS = REPO_ROOT / "tests" / "README.md"
WORKFLOWS = (
    REPO_ROOT / ".github" / "workflows" / "timing_ci.yml",
    REPO_ROOT / ".github" / "workflows" / "docs.yml",
)
GEN_DOCS_TEST = REPO_ROOT / "tests" / "common" / "test_gen_docs.py"
FRESHNESS_TEST = "test_committed_reference_matches_a_fresh_generation"

# CI enforces the freshness of the generated reference through the common-leg
# test above instead of a run step, so these two commands have no CI line to
# equal.
DOCUMENTED_ONLY = {
    ("python", "-m", "tests.common.gen_docs"),
    ("python", "-m", "tests.common.gen_docs", "--check"),
}

CODE_BLOCK_RE = re.compile(r"^(\s*)\.\. code-block::\s*(\S+)\s*$")
FENCE_RE = re.compile(r"^```\w*\n(.*?)^```", re.MULTILINE | re.DOTALL)
ENV_ASSIGNMENT_RE = re.compile(r"^[A-Z_][A-Z0-9_]*=")
PYTEST_REPORT_RE = re.compile(r"^-r[A-Za-z]+$")
MATRIX_EXPRESSION = "${{ matrix.module }}"
SEPARATORS = ("&&", "||", "|", ";")
PYTHON_NAMES = ("python", "python3", "python3.12")
CHECKED_PROGRAMS = ("make", "sphinx-build", "flake8")
CHECKED_MODULES = ("pytest", "compileall", "tests.common.gen_docs")
CHECKED_SCRIPTS = ("tests/common/lint_checks.py", "tests/common/compliance_audit.py")

UNSAFE_PATTERNS = (
    (re.compile(r"\b(?:curl|wget)\b[^\n]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b"), "a download piped into a shell"),
    (re.compile(r"\bsetup\.py\b"), "setup.py"),
    (re.compile(r"\bpip3?\s+install\b(?:\s+-\S+)*\s+\.(?:\s|$)"), "pip install of the working tree"),
    (re.compile(r"GH_TOKEN\s*=|ghp_"), "a token"),
)


def how_to_pages():
    """Every .rst page under docs/how-to/."""
    return sorted(HOW_TO.glob("*.rst"))


def _blocks(page, language):
    """Return one list of (line number, dedented text) per code-block directive of ``language``.

    ``language`` None selects every language. Option lines of the directive
    are dropped.
    """
    lines = Path(page).read_text(encoding="utf-8").splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        match = CODE_BLOCK_RE.match(lines[index])
        if not match or (language is not None and match.group(2) != language):
            index += 1
            continue
        indent = len(match.group(1))
        cursor = index + 1
        body = []
        while cursor < len(lines):
            line = lines[cursor]
            if line.strip() and len(line) - len(line.lstrip()) <= indent:
                break
            body.append((cursor + 1, line))
            cursor += 1
        while body and (not body[0][1].strip() or body[0][1].strip().startswith(":")):
            body.pop(0)
        while body and not body[-1][1].strip():
            body.pop()
        widths = [len(text) - len(text.lstrip()) for _, text in body if text.strip()]
        cut = min(widths) if widths else 0
        blocks.append([(number, text[cut:]) for number, text in body])
        index = cursor
    return blocks


def code_blocks(page, language):
    """Return the dedented body of each ``.. code-block:: <language>`` directive of ``page``."""
    return ["\n".join(text for _, text in block) for block in _blocks(page, language)]


def logical_lines(pairs):
    """Join backslash continuations; drop prompts, blank lines, and comment lines.

    ``pairs`` is a list of (line number, text); each result carries the number
    of the first physical line.
    """
    joined = []
    pending = None
    for number, text in pairs:
        stripped = text.strip()
        if pending is not None:
            first, partial = pending
            text_so_far = partial + " " + stripped
            pending = None
        else:
            first, text_so_far = number, stripped
        if text_so_far.endswith("\\"):
            pending = (first, text_so_far[:-1].rstrip())
            continue
        joined.append((first, text_so_far))
    if pending is not None:
        joined.append(pending)
    lines = []
    for number, text in joined:
        if text.startswith("$ "):
            text = text[2:]
        if not text or text.startswith("#"):
            continue
        lines.append((number, text))
    return lines


def split_commands(line):
    """Split one logical line into token lists at ``&&``, ``||``, ``|``, and ``;``.

    Shell quotes are removed by the tokenizer, so ``"$PWD/python"`` and
    ``$PWD/python`` compare equal. Shell variables stay literal text.
    """
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    commands = [[]]
    for token in lexer:
        if token in SEPARATORS:
            commands.append([])
        else:
            commands[-1].append(token)
    return commands


def _program(token):
    base = token.rsplit("/", 1)[-1]
    if base in PYTHON_NAMES:
        return "python"
    if token.endswith("/bin/sphinx-build"):
        return "sphinx-build"
    if token.endswith("/bin/flake8"):
        return "flake8"
    return token


def _strip_pytest_options(command):
    """Drop the options that change only the parallelism or the reporting of a pytest run."""
    kept = list(command[:3])
    rest = list(command[3:])
    index = 0
    while index < len(rest):
        token = rest[index]
        if token in ("-v", "-q"):
            index += 1
        elif token in ("-n", "--dist"):
            index += 2
        elif token.startswith("--dist=") or (token.startswith("-n") and not token.startswith("--")):
            index += 1
        elif PYTEST_REPORT_RE.match(token):
            index += 1
        else:
            kept.append(token)
            index += 1
    return kept


def normalize_line(line, matrix=None):
    """Return the normalized commands (tuples of tokens) of one logical line.

    ``matrix`` is the list of values of the job's matrix.module, or None. A
    line that holds the matrix expression is expanded into one line per value;
    any other workflow expression stays literal text.
    """
    if matrix is not None and MATRIX_EXPRESSION in line:
        lines = [line.replace(MATRIX_EXPRESSION, str(value)) for value in matrix]
    else:
        lines = [line]
    result = []
    for text in lines:
        for command in split_commands(text):
            tokens = list(command)
            while tokens and ENV_ASSIGNMENT_RE.match(tokens[0]):
                tokens.pop(0)
            if not tokens:
                continue
            tokens[0] = _program(tokens[0])
            if tokens[:3] == ["python", "-m", "pytest"]:
                tokens = _strip_pytest_options(tokens)
            result.append(tuple(tokens))
    return result


def normalize(text, matrix=None, lenient=False):
    """Return the normalized commands of every logical line of ``text``.

    A line the tokenizer cannot parse raises ValueError, or is skipped when
    ``lenient`` is true (a workflow script holds quoted multi-line text).
    """
    commands = []
    for _, line in logical_lines(list(enumerate(text.splitlines(), 1))):
        try:
            commands.extend(normalize_line(line, matrix))
        except ValueError:
            if not lenient:
                raise
    return commands


def is_checked(command):
    """True for the commands the page test compares: make, sphinx-build, flake8, and the python entry points."""
    program = command[0]
    if program in CHECKED_PROGRAMS:
        return True
    if program != "python" or len(command) < 2:
        return False
    if command[1] == "-m":
        return len(command) > 2 and command[2] in CHECKED_MODULES
    return command[1] in CHECKED_SCRIPTS


def candidate_commands():
    """Return the normalized commands of every workflow run script and every fenced README block."""
    candidates = set()
    for path in WORKFLOWS:
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job in (workflow.get("jobs") or {}).values():
            matrix = ((job.get("strategy") or {}).get("matrix") or {}).get("module")
            for step in job.get("steps") or []:
                script = step.get("run")
                if script:
                    candidates.update(normalize(script, matrix, lenient=True))
    readme = README_TESTS.read_text(encoding="utf-8")
    for body in FENCE_RE.findall(readme):
        candidates.update(normalize(body, lenient=True))
    return candidates


def test_regression_commands_match_ci():
    candidates = candidate_commands()
    checked = 0
    failures = []
    for block in _blocks(RUN_REGRESSION, "bash"):
        for number, line in logical_lines(block):
            for command in normalize_line(line):
                if not is_checked(command):
                    continue
                checked += 1
                if command not in candidates and command not in DOCUMENTED_ONLY:
                    failures.append(f"{RUN_REGRESSION.name}:{number}: {' '.join(command)} matches no CI or README command")
    assert checked > 0, "no checked command found on the run-the-regression page"
    assert not failures, "\n".join(failures)


def test_documented_only_commands_are_enforced_in_ci():
    tree = ast.parse(GEN_DOCS_TEST.read_text(encoding="utf-8"))
    names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert FRESHNESS_TEST in names, (
        f"{GEN_DOCS_TEST.name} no longer defines {FRESHNESS_TEST}, the only CI enforcement of the "
        f"documented-only commands {sorted(' '.join(c) for c in DOCUMENTED_ONLY)}"
    )


def test_normalize_examples():
    local = normalize("RUN_KNOWN_ISSUE_TESTS=1 .venv/bin/python -m pytest -q -n 4 --expect-known-issues -rxX tests/common")
    ci = normalize(
        "python -m pytest -v -n auto --dist=worksteal --expect-known-issues -rxX tests/${{ matrix.module }}",
        matrix=["common"],
    )
    expected = [("python", "-m", "pytest", "--expect-known-issues", "tests/common")]
    assert local == expected
    assert ci == expected

    rogue_ci = normalize('PYTHONPATH="$PWD/python" python -m pytest -v -n auto tests/rogue')
    rogue_local = normalize("PYTHONPATH=$PWD/python /tmp/lcls-timing-rogue/env/bin/python -m pytest -q -n 4 tests/rogue")
    assert rogue_ci == rogue_local == [("python", "-m", "pytest", "tests/rogue")]

    line = 'python tests/common/compliance_audit.py audit tests --fail-on-findings --output "$RUNNER_TEMP/audit.txt" || rc=$?'
    assert len(split_commands(line)) == 2
    commands = normalize(line)
    assert commands[0][:2] == ("python", "tests/common/compliance_audit.py")
    assert commands[0][-2:] == ("--output", "$RUNNER_TEMP/audit.txt")

    assert normalize("make MODULES=$PWD import \\\n   && echo done") == [
        ("make", "MODULES=$PWD", "import"),
        ("echo", "done"),
    ]
    assert normalize("$ .venv/bin/flake8 --count python/ tests/") == [("flake8", "--count", "python/", "tests/")]
    assert normalize("# a comment\n\n") == []
    # Another matrix expression stays literal, so it can match nothing.
    assert normalize("echo ${{ github.sha }}", matrix=["common"])[0][1:] == ("${{", "github.sha", "}}")


@pytest.mark.parametrize("page", how_to_pages(), ids=lambda page: page.name)
def test_no_unsafe_commands(page):
    findings = []
    for block in _blocks(page, None):
        for number, text in block:
            for pattern, what in UNSAFE_PATTERNS:
                if pattern.search(text):
                    findings.append(f"{page.name}:{number}: {what}: {text.strip()}")
    assert not findings, "\n".join(findings)
