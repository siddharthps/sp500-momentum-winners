"""Offline tests for the docs-editor subagent's guard hook (#81)."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "docs_guard.py"
if not HOOK.exists():  # the Docker image leaves .claude/ out (.dockerignore); it's dev tooling
    pytest.skip("the docs guard isn't in this checkout", allow_module_level=True)
sys.path.insert(0, str(HOOK.parent))
import docs_guard

ROOT = docs_guard.ROOT


# --- writes -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        str(ROOT / "docs" / "09_results.md"),
        "docs/09_results.md",
        pytest.param(
            "docs\\appendix_a_data_dictionary.md",
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="a separator only on Windows"
            ),
        ),
        str(ROOT / "README.md"),
        "code_issues.local.md",
        "docs/new_page.md",
    ],
)
def test_book_readme_and_notes_are_writable(path):
    assert docs_guard.check_write(path, str(ROOT)) is None


@pytest.mark.parametrize(
    "path",
    [
        "sp500_momentum/config.py",
        str(ROOT / "sp500_momentum" / "backtest.py"),
        "docs/../sp500_momentum/config.py",  # climbing out of docs/
        "docs/../../elsewhere.md",
        "docs",  # the folder itself
        "mkdocs.yml",
        "CLAUDE.md",
        "references/decisions.md",
        ".claude/hooks/docs_guard.py",  # it can't loosen its own guard
        ".claude/agents/docs-editor.md",
        "docs_backup/x.md",  # a sibling whose name starts with "docs"
        "README.md.bak",
        "",
    ],
)
def test_everything_else_is_refused(path):
    assert docs_guard.check_write(path, str(ROOT)) is not None


def test_relative_paths_resolve_against_the_calls_cwd():
    # From inside docs/, "../README.md" is the README; "../tests/x.py" is code.
    cwd = str(ROOT / "docs")
    assert docs_guard.check_write("../README.md", cwd) is None
    assert docs_guard.check_write("../tests/x.py", cwd) is not None


@pytest.mark.skipif(sys.platform != "win32", reason="MSYS paths exist only on Windows")
def test_git_bash_style_paths_are_understood():
    # Git Bash reports the cwd as /c/Users/...; the #81 trial wrongly blocked docs/ because of it.
    msys = "/" + str(ROOT)[0].lower() + str(ROOT)[2:].replace("\\", "/")
    assert docs_guard.check_write("docs/09_results.md", msys) is None
    assert docs_guard.check_write(msys + "/docs/09_results.md") is None
    assert docs_guard.check_write("sp500_momentum/config.py", msys) is not None


# --- shell --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        "git status",
        "git diff --stat",
        "git diff main -- docs/09_results.md",
        "git log --oneline -5",
        "git show HEAD:docs/03_monthly_table.md",
        "git grep -n 499",
        "git ls-files docs",
        "uv run mkdocs build --strict",
        "uv run mkdocs build --strict --quiet",
    ],
)
def test_read_only_commands_run(cmd):
    assert docs_guard.check_bash(cmd) is None


@pytest.mark.parametrize(
    "cmd",
    [
        "git commit -m x",
        "git add docs",
        "git checkout -- sp500_momentum/config.py",
        "git -c core.pager=sh log",
        "git -C .. status",
        "git diff --output=sp500_momentum/config.py",
        "git diff --ext-diff",
        "git grep -Ovim x",
        "git status; rm -rf sp500_momentum",
        "git status && echo hi",
        "git log | tee out.txt",
        "git diff > sp500_momentum/config.py",
        "echo $(rm x)",
        "git log `rm x`",
        "cd docs && git status",
        'uv run python -c \'open("x","w")\'',
        "uv run mkdocs build --site-dir sp500_momentum",
        "uv run mkdocs gh-deploy",
        "python scripts/anything.py",
        "rm README.md",
        "sed -i s/a/b/ sp500_momentum/config.py",
        "",
    ],
)
def test_writes_chains_and_other_programs_are_refused(cmd):
    assert docs_guard.check_bash(cmd) is not None


# --- reads and other tools ----------------------------------------------------------------------


def test_env_files_cant_be_read_but_code_can():
    assert docs_guard.check_read(str(ROOT / ".env")) is not None
    assert docs_guard.check_read(".env.local") is not None
    assert docs_guard.check_read("sp500_momentum/config.py") is None


def test_decide_routes_each_tool():
    def call(tool, **tool_input):
        return docs_guard.decide({"tool_name": tool, "tool_input": tool_input, "cwd": str(ROOT)})

    assert call("Edit", file_path="docs/01_problem.md") is None
    assert call("Write", file_path="sp500_momentum/x.py") is not None
    assert call("NotebookEdit", notebook_path="docs/x.ipynb") is not None
    assert call("PowerShell", command="git status") is not None
    assert call("Bash", command="git status") is None
    assert call("Grep", pattern="x") is None
    assert call("WebSearch", query="momentum anomaly") is None


# --- the script as Claude Code runs it ----------------------------------------------------------


def _run(stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,  # the exit code is what's under test
    )


def test_script_exits_2_with_a_reason_when_blocking():
    out = _run(json.dumps({"tool_name": "Write", "tool_input": {"file_path": "setup.py"}}))
    assert out.returncode == 2
    assert "Blocked by the docs guard" in out.stderr


def test_script_exits_0_when_allowing():
    out = _run(json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}}))
    assert out.returncode == 0


def test_script_fails_closed_on_bad_input():
    assert _run("not json").returncode == 2
