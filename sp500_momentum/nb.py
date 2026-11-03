"""Guardrails for notebooks, which are committed WITH their outputs.

Every notebook starts with:

    from sp500_momentum import nb
    nb.setup()

Rules (the runner, `run_notebooks.py`, checks them and fails the run if they're broken):
- Show summaries, not raw data: aggregates, rates by year, `.head(n)`. Never a full table.
  Complete results go to files under reports/, and the notebook shows the top rows.
- One table or chart per question, each with a sentence saying what it shows.
- No log lines, progress bars or warnings in the outputs (nothing on stderr).
- No local paths, e-mail addresses or keys in the outputs.
"""

import sys

from loguru import logger
import pandas as pd

from sp500_momentum import plots

MAX_ROWS = 20  # an accidental full-table display shows at most this many rows


def setup():
    """Cap pandas output, silence info logs, and apply the chart style."""
    pd.set_option("display.max_rows", MAX_ROWS)
    pd.set_option("display.min_rows", 10)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", "{:,.4f}".format)
    # Package functions log at INFO; in a notebook only real problems should show (and they'll
    # make the runner fail, which is the point).
    logger.remove()
    logger.add(sys.stderr, level="WARNING", colorize=False, format="{level}: {message}")
    plots.apply_style()
