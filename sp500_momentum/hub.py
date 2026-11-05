"""Hugging Face datasets (#18): a private snapshot of everything, and a public one of derived data.

    uv run python -m sp500_momentum.hub push --target private   # raw + processed + models
    uv run python -m sp500_momentum.hub push --target public    # derived tables only
    uv run python -m sp500_momentum.hub push --target both --tag final-2026-11
    uv run python -m sp500_momentum.hub pull                    # the private snapshot -> data/, models/

Why two (decisions.md, 5 Nov): Yahoo Finance and Alpha Vantage prices are licensed for personal
use and their terms forbid redistribution. So the full data, raw prices included, is a **private**
dataset, reached with a token by the cloud run, the dashboard and anyone given access. The
**public** dataset carries only what this project computed: features without raw price columns,
model scores, the live picks and the strategies' results, plus a card naming every source.

Settings (from .env, later GitHub Secrets): HF_TOKEN (write access), HF_USER (the account).
"""

import os
from pathlib import Path
import shutil
import tempfile

from loguru import logger
import pandas as pd
import typer

from sp500_momentum.config import (
    FEATURES_TABLE,
    INTERIM_DATA_DIR,
    LIVE_PICKS,
    MODEL_SCORES,
    MODELS_DIR,
    MONTHLY_PANEL,
    PROCESSED_DATA_DIR,
    PROJ_ROOT,
    RAW_DATA_DIR,
    REPORTS_DIR,
)

app = typer.Typer(help="Publish to and pull from the Hugging Face datasets.")

PRIVATE_NAME = "sp500-momentum-data"
PUBLIC_NAME = "sp500-momentum-winners"
# Columns that are, or are built directly from, a vendor's price or volume figures.
PRICE_COLUMNS = ["close_adj", "entry_px", "dollar_vol", "source"]
# What the private snapshot holds (paths relative to the project root).
PRIVATE_FOLDERS = [RAW_DATA_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR]
IGNORE = ["*.gitkeep", "**/.gitkeep", "**/__pycache__/**"]


def repo_ids(user: str | None = None) -> tuple[str, str]:
    """(private, public) dataset ids for an account."""
    user = user or os.getenv("HF_USER")
    if not user:
        raise typer.BadParameter("HF_USER is not set (put your Hugging Face username in .env)")
    return f"{user}/{PRIVATE_NAME}", f"{user}/{PUBLIC_NAME}"


def _token() -> str:
    token = os.getenv("HF_TOKEN")
    if not token:
        raise typer.BadParameter("HF_TOKEN is not set (a write token, in .env)")
    return token


SECRET_KEYS = ["ALPHAVANTAGE_API_KEY", "TELEGRAM_BOT_TOKEN", "HF_TOKEN"]


def files_with_secrets(folders, secrets: list[str] | None = None) -> list[str]:
    """Files under `folders` that contain any secret from .env (by default the keys in
    SECRET_KEYS). Every upload checks this first and refuses if the list isn't empty."""
    if secrets is None:
        secrets = [v for k in SECRET_KEYS if (v := os.getenv(k))]
    needles = [s.encode() for s in secrets if len(s) >= 8]
    hits = []
    for folder in folders:
        for p in Path(folder).rglob("*"):
            if p.is_file() and any(n in p.read_bytes() for n in needles):
                hits.append(p.name)
    return hits


def without_prices(df: pd.DataFrame) -> pd.DataFrame:
    """The table without vendor price and volume columns (returns, ranks and indicators stay:
    they're this project's calculations)."""
    return df.drop(columns=[c for c in PRICE_COLUMNS if c in df.columns])


DATASET_CARD = """---
license: cc-by-sa-4.0
language: en
tags: [finance, stocks, momentum, sp500, backtesting]
pretty_name: S&P 500 momentum winners (derived tables)
---

# S&P 500 momentum winners: derived tables

Derived data from the project [sp500-momentum-winners](https://github.com/siddharthps/sp500-momentum-winners):
every month-end since 2010, the point-in-time S&P 500 members with their features, the models'
out-of-sample scores, the live monthly picks, and the strategies' results.

**Status:** {status}

## Files

| File | What it is |
|---|---|
| `features.parquet` | One row per member per month-end: features known at the close, next-month results (raw price and volume columns removed) |
| `monthly_panel.parquet` | The member table: past and forward returns, membership (raw price columns removed) |
| `model_scores.parquet` | Every model's out-of-sample score, 2014 on (each month scored by a model trained before it) |
| `live_picks.csv` | Every pick made by the monthly run, with when it was made |
| `reports/*.csv` | Result tables: the rule grid, model comparisons, strategies |

## Sources and licences

- **Index membership:** Wikipedia, "List of S&P 500 companies" (CC BY-SA 4.0), hence this
  dataset's licence.
- **Economic series:** FRED (Federal Reserve Bank of St. Louis); the series used are US government
  data (BLS, Federal Reserve, CBO).
- **Prices:** Yahoo Finance and Alpha Vantage. **Raw prices are not included**: their terms forbid
  redistribution. Returns, ranks and indicators computed from them are included. To rebuild prices,
  run the project's download steps with your own access.

Research output, not investment advice.
"""


def stage_public(folder: Path, status: str) -> list[str]:
    """Write the public files into `folder`; returns their names."""
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for src in [FEATURES_TABLE, MONTHLY_PANEL]:
        without_prices(pd.read_parquet(src)).to_parquet(folder / src.name, index=False)
        written.append(src.name)
    shutil.copy(MODEL_SCORES, folder / MODEL_SCORES.name)
    written.append(MODEL_SCORES.name)
    if LIVE_PICKS.exists():
        shutil.copy(LIVE_PICKS, folder / LIVE_PICKS.name)
        written.append(LIVE_PICKS.name)
    (folder / "reports").mkdir(exist_ok=True)
    for csv in sorted(REPORTS_DIR.glob("*.csv")):
        shutil.copy(csv, folder / "reports" / csv.name)
        written.append(f"reports/{csv.name}")
    (folder / "README.md").write_text(DATASET_CARD.format(status=status), encoding="utf-8")
    written.append("README.md")
    return written


@app.command()
def push(
    target: str = typer.Option("private", help="private, public or both"),
    tag: str = typer.Option("", help="Also tag this version (e.g. final-2026-11)"),
    status: str = typer.Option(
        "preview: the download of delisted companies is still running", help="For the card"
    ),
):
    """Upload the snapshot(s). Each upload is one commit in the dataset's history."""
    from huggingface_hub import HfApi

    if target not in {"private", "public", "both"}:
        raise typer.BadParameter("target must be private, public or both")
    api = HfApi(token=_token())
    private_id, public_id = repo_ids()
    stamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    if target in {"private", "both"}:
        leaked = files_with_secrets(PRIVATE_FOLDERS)
        if leaked:  # names only: never print a secret
            logger.error(f"Refusing to upload: a secret from .env is in {leaked[:10]}")
            raise typer.Exit(code=1)
        api.create_repo(private_id, repo_type="dataset", private=True, exist_ok=True)
        for folder in PRIVATE_FOLDERS:
            rel = folder.relative_to(PROJ_ROOT).as_posix()
            api.upload_folder(
                repo_id=private_id,
                repo_type="dataset",
                folder_path=folder,
                path_in_repo=rel,
                ignore_patterns=IGNORE,
                commit_message=f"{rel} snapshot {stamp}",
            )
        if tag:
            api.create_tag(private_id, tag=tag, repo_type="dataset", exist_ok=True)
        logger.success(f"Private snapshot pushed to {private_id}")
    if target in {"public", "both"}:
        api.create_repo(public_id, repo_type="dataset", private=False, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            files = stage_public(Path(tmp), status)
            leaked = files_with_secrets([tmp])
            if leaked:
                logger.error(f"Refusing to upload: a secret from .env is in {leaked[:10]}")
                raise typer.Exit(code=1)
            api.upload_folder(
                repo_id=public_id,
                repo_type="dataset",
                folder_path=tmp,
                commit_message=f"Derived tables {stamp} ({status})",
            )
        if tag:
            api.create_tag(public_id, tag=tag, repo_type="dataset", exist_ok=True)
        logger.success(f"Public dataset pushed to {public_id}: {len(files)} files")


def pull_snapshot(revision: str | None = None) -> None:
    """Download the private snapshot into data/ and models/ (overwriting local copies)."""
    from huggingface_hub import snapshot_download

    private_id, _ = repo_ids()
    snapshot_download(
        repo_id=private_id,
        repo_type="dataset",
        revision=revision,
        local_dir=PROJ_ROOT,
        token=_token(),
        allow_patterns=[f"{f.relative_to(PROJ_ROOT).as_posix()}/**" for f in PRIVATE_FOLDERS],
    )


@app.command()
def pull(revision: str = typer.Option("", help="A tag or commit (default: the latest)")):
    """Download the private snapshot: every later step then runs without the sources."""
    pull_snapshot(revision or None)
    logger.success("Snapshot downloaded into data/ and models/")


if __name__ == "__main__":
    app()
