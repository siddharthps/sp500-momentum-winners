"""PreToolUse guard for the docs-editor subagent (#81).

The agent may write only the book (`docs/`), the README and its local code-issue notes, may run only
read-only git and the book build, and may not read `.env` files. Claude Code passes the tool call as
JSON on stdin; exit code 2 blocks it and sends stderr back to the agent as the reason.

It fails closed: any error while checking blocks the call (a crash would otherwise exit 1, which
Claude Code treats as non-blocking and lets the call through). Standard library only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import sys

# The repo root, from this file's own location (.claude/hooks/docs_guard.py), never from anything
# the agent can influence.
ROOT = Path(__file__).resolve().parents[2]

WRITE_DIRS = ("docs",)
WRITE_FILES = ("README.md", "code_issues.local.md")

WRITE_TOOLS = {"Edit", "Write", "MultiEdit"}
SHELL_TOOLS = {"Bash"}
BLOCKED_TOOLS = {"NotebookEdit", "PowerShell"}  # no reason to touch notebooks; one shell is enough
READ_TOOLS = {"Read"}

GIT_SUBCOMMANDS = {"status", "diff", "log", "show", "grep", "blame", "ls-files"}
# Options that make a read-only git command write a file or run another program.
GIT_BAD_OPTIONS = ("--output", "-O", "--open-files-in-pager", "--ext-diff", "--textconv", "--exec")
MKDOCS_EXTRA = {"--strict", "-s", "--quiet", "-q"}
SHELL_METACHARS = (";", "&", "|", ">", "<", "`", "$", "\n", "\r", "(", ")")


def _same_or_inside(path: Path, base: Path) -> bool:
    p, b = os.path.normcase(str(path)), os.path.normcase(str(base))
    return p == b or p.startswith(b.rstrip("\\/") + os.sep)


def _native(p: str) -> str:
    """Git Bash (MSYS) paths like /c/Users/x -> C:/Users/x on Windows; anything else unchanged.

    Without this, Python on Windows reads /c/Users/x as C:\\c\\Users\\x (found in the #81 trial).
    """
    if os.name == "nt" and re.match(r"^/[a-zA-Z](/|$)", p):
        return f"{p[1]}:/{p[3:]}"
    return p


def _resolve(file_path: str, cwd: str | None) -> Path:
    path = Path(_native(file_path))
    if not path.is_absolute():
        path = Path(_native(cwd) if cwd else ROOT) / path
    return path.resolve()


def check_write(file_path: str, cwd: str | None = None, root: Path = ROOT) -> str | None:
    """The reason a write is refused, or None when it is allowed."""
    if not file_path:
        return "no file path given"
    path = _resolve(file_path, cwd)
    root = root.resolve()
    allowed = [root / d for d in WRITE_DIRS]
    if any(_same_or_inside(path, d) and path != d for d in allowed):
        return None
    if any(os.path.normcase(str(path)) == os.path.normcase(str(root / f)) for f in WRITE_FILES):
        return None
    return (
        f"writes are limited to docs/, README.md and code_issues.local.md; refused: {file_path}. "
        "Record code problems in code_issues.local.md instead."
    )


def check_read(file_path: str) -> str | None:
    name = Path(file_path or "").name.lower()
    if name == ".env" or name.startswith(".env."):
        return "secrets files (.env) are off limits"
    return None


def check_bash(command: str) -> str | None:
    """Allow only read-only git subcommands and `uv run mkdocs build --strict`."""
    command = (command or "").strip()
    if not command:
        return "empty command"
    if any(c in command for c in SHELL_METACHARS):
        return (
            "one plain command only: no chaining, pipes, redirection, subshells or variables "
            "(and no leading `cd`; the shell already starts in the repo)"
        )
    try:
        args = shlex.split(command)
    except ValueError:
        return "the command couldn't be parsed"

    if args[0] == "git":
        if len(args) < 2 or args[1] not in GIT_SUBCOMMANDS:
            return f"git is limited to: {', '.join(sorted(GIT_SUBCOMMANDS))} (no global options)"
        for a in args[2:]:
            if any(
                a == o or a.startswith(o + "=") or (o == "-O" and a.startswith("-O"))
                for o in GIT_BAD_OPTIONS
            ):
                return f"git option not allowed (it writes files or runs programs): {a}"
        return None

    if args[:4] == ["uv", "run", "mkdocs", "build"] and set(args[4:]) <= MKDOCS_EXTRA:
        return None

    return (
        "the shell is limited to read-only git (status, diff, log, show, grep, blame, ls-files) "
        "and `uv run mkdocs build --strict`"
    )


def decide(payload: dict, root: Path = ROOT) -> str | None:
    """The reason to block this tool call, or None to let it through."""
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool in BLOCKED_TOOLS:
        return f"{tool} isn't available to the docs agent"
    if tool in WRITE_TOOLS:
        return check_write(tool_input.get("file_path", ""), payload.get("cwd"), root)
    if tool in SHELL_TOOLS:
        return check_bash(tool_input.get("command", ""))
    if tool in READ_TOOLS:
        return check_read(tool_input.get("file_path", ""))
    return None


def main() -> int:
    try:
        reason = decide(json.loads(sys.stdin.read() or "{}"))
    except Exception as exc:  # noqa: BLE001 - on purpose: any failure must block (fail closed)
        reason = f"the docs guard couldn't check this call ({type(exc).__name__}), so it's blocked"
    if reason:
        print(f"Blocked by the docs guard: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
