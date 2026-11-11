"""FRED macro series, from FRED's public CSV endpoint (no API key).

The class used pandas_datareader, which is unmaintained. The CSV endpoint returns the same
data. Note: it stalls (read timeout) on our custom User-Agent header but answers at once with
the default one, so this module doesn't send HTTP_HEADERS (checked Nov 2026).
"""

import io

import pandas as pd
import requests

from sp500_momentum.retries import with_retries

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def parse_csv(text: str, series_id: str) -> pd.DataFrame:
    """FRED CSV -> date, value. Missing values ('.' in older files, blank in newer) are dropped."""
    df = pd.read_csv(io.StringIO(text))
    df = df.rename(columns={df.columns[0]: "date", series_id: "value"})
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"])[["date", "value"]].reset_index(drop=True)


def fetch_series(series_id: str, start: str) -> pd.DataFrame:
    """One FRED series from `start` on."""

    def fetch() -> str:
        r = requests.get(URL, params={"id": series_id, "cosd": start}, timeout=60)
        r.raise_for_status()
        if not r.text.startswith("observation_date"):
            raise RuntimeError(f"Unexpected FRED reply for {series_id}: {r.text[:200]}")
        return r.text

    return parse_csv(with_retries(fetch, f"FRED {series_id}"), series_id)
