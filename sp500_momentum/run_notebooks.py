"""Execute the notebooks top to bottom in a fresh kernel, saving their outputs.

    uv run python -m sp500_momentum.run_notebooks run            # every notebook
    uv run python -m sp500_momentum.run_notebooks run 02         # names starting with "02"

Notebooks are committed WITH outputs (readers see results on GitHub without the data), so they
must only ever be run this way: a fresh kernel, top to bottom, so the stored outputs always match
the code. Cell and notebook metadata are cleared to keep diffs small.

After running, every notebook is checked (see `nb.py` for the rules); the run fails if:
- a cell's text output is longer than MAX_OUTPUT_LINES (a table or log was dumped in full),
- anything was written to stderr (log lines, progress bars, warnings),
- an output contains a local path, an e-mail address or the Alpha Vantage key,
- the file is over BUDGET_KB (the pre-commit hook's hard limit is 500 KB).
"""

import os
import re

from loguru import logger
from nbconvert.preprocessors import (
    ClearMetadataPreprocessor,
    CoalesceStreamsPreprocessor,
    ExecutePreprocessor,
)
import nbformat
import typer

from sp500_momentum.config import PROJ_ROOT

NOTEBOOKS_DIR = PROJ_ROOT / "notebooks"
MAX_OUTPUT_LINES = 50
BUDGET_KB = 300
LEAK_PATTERNS = {
    "a local Windows path": re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}", re.IGNORECASE),
    "a local home path": re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/"),
    "an e-mail address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
}

app = typer.Typer(help="Run the notebooks.")


@app.callback()
def _main():
    """Run the notebooks."""


def _texts(output) -> list[tuple[str, str]]:
    """(kind, text) pairs for one output; images are skipped."""
    if output.output_type == "stream":
        return [(f"stream:{output.get('name', 'stdout')}", output.get("text", ""))]
    if output.output_type in ("execute_result", "display_data"):
        data = output.get("data", {})
        return [
            (k, v if isinstance(v, str) else "".join(v))
            for k, v in data.items()
            if k.startswith("text/")
        ]
    if output.output_type == "error":
        return [("error", "\n".join(output.get("traceback", [])))]
    return []


def check_notebook(nb, size_kb: float, secrets: tuple[str, ...] = ()) -> list[str]:
    """Problems with an executed notebook's outputs (an empty list means it passes)."""
    problems = []
    if size_kb > BUDGET_KB:
        problems.append(f"{size_kb:.0f} KB is over the {BUDGET_KB} KB budget")
    for n, cell in enumerate(nb.cells, start=1):
        if cell.cell_type != "code":
            continue
        for output in cell.get("outputs", []):
            for kind, text in _texts(output):
                where = f"cell {n} ({kind})"
                if kind == "stream:stderr" and text.strip():
                    problems.append(f"{where}: wrote to stderr: {text.strip()[:80]!r}")
                if (
                    kind in ("stream:stdout", "text/plain")
                    and text.count("\n") + 1 > MAX_OUTPUT_LINES
                ):
                    problems.append(
                        f"{where}: {text.count(chr(10)) + 1} lines (max {MAX_OUTPUT_LINES})"
                    )
                for what, pattern in LEAK_PATTERNS.items():
                    if pattern.search(text):
                        problems.append(f"{where}: contains {what}")
                for s in secrets:
                    if s and s in text:
                        problems.append(f"{where}: contains a secret from .env")
    return problems


@app.command()
def run(prefix: str = typer.Argument("", help="Only notebooks whose name starts with this")):
    paths = sorted(p for p in NOTEBOOKS_DIR.glob("*.ipynb") if p.name.startswith(prefix))
    if not paths:
        raise typer.BadParameter(f"no notebook in notebooks/ starts with {prefix!r}")
    secrets = tuple(
        v for v in [os.getenv("ALPHAVANTAGE_API_KEY"), os.getenv("TELEGRAM_BOT_TOKEN")] if v
    )
    failed = False
    for path in paths:
        nb = nbformat.read(path, as_version=4)
        ExecutePreprocessor(timeout=1800, kernel_name="python3").preprocess(
            nb, {"metadata": {"path": str(NOTEBOOKS_DIR)}}
        )
        # The kernel may split one print into several stream chunks, differently each run;
        # merging them keeps the stored outputs (and their diffs) identical for identical results.
        CoalesceStreamsPreprocessor().preprocess(nb, {})
        ClearMetadataPreprocessor(
            preserve_nb_metadata_mask={("kernelspec",), ("language_info", "name")}
        ).preprocess(nb, {})
        nbformat.write(nb, path)
        kb = path.stat().st_size / 1024
        problems = check_notebook(nb, kb, secrets)
        if problems:
            failed = True
            logger.error(
                f"{path.name}: {kb:.0f} KB, {len(problems)} problem(s):\n  "
                + "\n  ".join(problems)
            )
        else:
            logger.success(f"{path.name}: executed, {kb:.0f} KB, output checks passed")
    if failed:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
