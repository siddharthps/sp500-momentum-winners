"""#85: potential GDP read point-in-time from its published versions, the FRED API key kept out of
errors, and market-condition correlations limited to market-wide columns. All offline."""

import numpy as np
import pandas as pd
import pytest
import requests

from sp500_momentum import eda
from sp500_momentum.features import gdppot_point_in_time
from sp500_momentum.sources import fred as fred_src


def _vintages():
    """Two published versions of a quarterly series: the first in force until 2015-02-09, the
    second (revised up) from 2015-02-10 on."""
    quarters = pd.date_range("2013-01-01", "2015-01-01", freq="QS")
    v1 = pd.DataFrame(
        {
            "date": quarters,
            "value": [100.0 * 1.01**i for i in range(len(quarters))],
            "realtime_start": pd.Timestamp("2000-01-01"),
            "realtime_end": pd.Timestamp("2015-02-09"),
        }
    )
    v2 = v1.assign(
        value=[100.0 * 1.02**i for i in range(len(quarters))],
        realtime_start=pd.Timestamp("2015-02-10"),
        realtime_end=pd.Timestamp("2262-01-01"),
    )
    return pd.concat([v1, v2], ignore_index=True)


def test_gdppot_uses_the_version_in_force_the_day_before_each_decision():
    dates = pd.Series(pd.to_datetime(["2015-01-30", "2015-02-10", "2015-02-27"]))
    out = gdppot_point_in_time(_vintages(), dates)
    # Jan: old version. 10 Feb: published that day, so not yet usable. 27 Feb: new version.
    assert out["gdppot_qoq"].round(6).tolist() == [0.01, 0.01, 0.02]
    assert out["gdppot_yoy"].iloc[2] == pytest.approx(1.02**4 - 1)
    assert out.index.astype(str).tolist() == ["2015-01", "2015-02", "2015-02"]


def test_gdppot_refuses_a_series_without_its_published_versions():
    plain = _vintages()[["date", "value"]]
    with pytest.raises(ValueError, match="published versions"):
        gdppot_point_in_time(plain, pd.Series(pd.to_datetime(["2015-01-30"])))


def test_gdppot_before_any_version_is_missing():
    out = gdppot_point_in_time(_vintages(), pd.Series(pd.to_datetime(["1999-06-30"])))
    assert np.isnan(out["gdppot_qoq"].iloc[0])


def test_parse_vintages_keeps_real_time_periods_and_caps_the_open_end():
    payload = {
        "observations": [
            {
                "date": "2015-01-01",
                "value": "100.5",
                "realtime_start": "2015-02-10",
                "realtime_end": "9999-12-31",
            },
            {
                "date": "2015-04-01",
                "value": ".",
                "realtime_start": "2015-02-10",
                "realtime_end": "9999-12-31",
            },
        ]
    }
    out = fred_src.parse_vintages(payload)
    assert len(out) == 1  # "." dropped
    assert out["realtime_end"].iloc[0] == pd.Timestamp("2262-01-01")
    assert out["value"].iloc[0] == 100.5


def test_fetch_vintages_needs_a_key():
    with pytest.raises(RuntimeError, match="FRED_API_KEY is not set"):
        fred_src.fetch_vintages("GDPPOT", "2005-01-01", "")


def test_fetch_vintages_errors_never_carry_the_key(monkeypatch):
    key = "k" * 32

    class Reply:
        status_code = 400

        def raise_for_status(self):
            e = requests.HTTPError(f"400 Client Error for url: {fred_src.API_URL}?api_key={key}")
            e.response = self
            raise e

    monkeypatch.setattr(fred_src.requests, "get", lambda *a, **k: Reply())
    monkeypatch.setattr("sp500_momentum.retries.time.sleep", lambda s: None)
    with pytest.raises(RuntimeError) as info:
        fred_src.fetch_vintages("GDPPOT", "2005-01-01", key)
    assert key not in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__
    assert "HTTPError (HTTP 400)" in str(info.value)


def _regime_frame():
    dates = pd.to_datetime(["2015-01-30"] * 2 + ["2015-02-27"] * 2 + ["2015-03-31"] * 2)
    return pd.DataFrame(
        {
            "date": dates,
            "mkt_spy_ret_1m": [0.01, 0.01, -0.02, -0.02, 0.03, 0.03],  # one value per date
            "sector_etf_ret_1m": [0.05, -0.04, 0.02, 0.01, -0.03, 0.06],  # differs by stock
        }
    )


def test_market_wide_keeps_only_columns_with_one_value_per_date():
    df = _regime_frame()
    assert eda.market_wide(df, ["mkt_spy_ret_1m", "sector_etf_ret_1m"]) == ["mkt_spy_ret_1m"]


def test_regime_correlations_refuses_a_per_stock_column():
    df = _regime_frame()
    spread = pd.Series(
        [0.1, -0.2, 0.3], index=pd.to_datetime(["2015-01-30", "2015-02-27", "2015-03-31"])
    )
    with pytest.raises(ValueError, match="sector_etf_ret_1m"):
        eda.regime_correlations(df, spread, ["mkt_spy_ret_1m", "sector_etf_ret_1m"])
    out = eda.regime_correlations(df, spread, ["mkt_spy_ret_1m"])
    assert out.index.tolist() == ["mkt_spy_ret_1m"]
