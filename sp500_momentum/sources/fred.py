"""FRED macro series, from FRED's public CSV endpoint (no API key), plus the past versions
(vintages) of revised series from FRED's API (needs FRED_API_KEY; #85).

The class used pandas_datareader, which is unmaintained. The CSV endpoint returns the same
data. Note: it stalls (read timeout) on our custom User-Agent header but answers at once with
the default one, so this module doesn't send HTTP_HEADERS (checked Nov 2026).

The API key travels in the request URL, so errors from the vintage request are re-raised by
type and HTTP status only, never with their message (which would carry the URL).
"""

import io

import pandas as pd
import requests

from sp500_momentum.retries import with_retries

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
API_URL = "https://api.stlouisfed.org/fred/series/observations"
# The real-time window to ask for: every version in force from REALTIME_START to the latest.
REALTIME_START = "2000-01-01"
REALTIME_END = "9999-12-31"  # FRED's "latest available"


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


def parse_vintages(payload: dict) -> pd.DataFrame:
    """FRED API observations by real-time period (output_type 1) -> date, value, realtime_start,
    realtime_end: each value with the dates it was the published figure. Missing ('.') dropped."""
    obs = pd.DataFrame(payload.get("observations", []))
    if obs.empty:
        raise RuntimeError("FRED API reply has no observations")
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(obs["date"]),
            "value": pd.to_numeric(obs["value"], errors="coerce"),
            "realtime_start": pd.to_datetime(obs["realtime_start"]),
            # "9999-12-31" (still current) is beyond pandas' date range: cap it
            "realtime_end": pd.to_datetime(
                obs["realtime_end"].replace(REALTIME_END, "2262-01-01")
            ),
        }
    )
    return out.dropna(subset=["value"]).reset_index(drop=True)


def fetch_vintages(series_id: str, start: str, api_key: str) -> pd.DataFrame:
    """Every published version of a series' observations from `start` on, in one request."""
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY is not set: it's needed for the past versions of revised series"
        )
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
        "realtime_start": REALTIME_START,
        "realtime_end": REALTIME_END,
        "output_type": 1,
    }

    def fetch() -> dict:
        try:
            r = requests.get(API_URL, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            status = getattr(e.response, "status_code", None)
            raise RuntimeError(
                f"FRED API {series_id}: {type(e).__name__} (HTTP {status})"
            ) from None

    return parse_vintages(with_retries(fetch, f"FRED API {series_id}"))
