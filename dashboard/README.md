# S&P 500 momentum winners: live dashboard

A Streamlit app, hosted free on [Streamlit Community Cloud](https://streamlit.io/cloud) from this
repository's `main` branch (entry point `dashboard/app.py`, Python 3.12). Each month-end, the
point-in-time S&P 500 members are ranked two ways, a model and the plain 6-month rule, and the
top 10 are bought at the next open. The page shows:
- the latest picks;
- the live record as results come in;
- the backtest;
- whether the model still sees the kind of market it was trained on (input drift).

**Data:** it reads only the public dataset
[siddharthps/sp500-momentum-winners](https://huggingface.co/datasets/siddharthps/sp500-momentum-winners),
which the project's monthly run updates. It holds no token, so it can show only public data.

**Updates:** new code arrives with each merge to `main`, and new data with each monthly push, after
the page's 6-hour cache. An idle app sleeps; the next visitor wakes it in about 30 seconds.

**Run locally:**

```bash
uv run streamlit run dashboard/app.py                      # reads the public dataset
DASHBOARD_DATA_DIR=path/to/files uv run streamlit run dashboard/app.py   # or local files
```

`logic.py` holds the calculations (plain pandas, tested in `tests/test_dashboard.py`, including
a full offline run of the app). `requirements.txt` is what Community Cloud installs: only these
light packages, not the project's model stack.

Research output, not investment advice.
