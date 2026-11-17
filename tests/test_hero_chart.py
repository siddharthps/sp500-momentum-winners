"""The README's headline chart: one line per strategy, each ending in its final value, and a
legend so identity never rests on colour alone. Offline, synthetic data."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from sp500_momentum import plots


def _frame():
    idx = pd.period_range("2023-02", "2023-06", freq="M")
    return pd.DataFrame(
        {
            "a": [10_000, 11_000, 12_500, 14_000, 59_209.4],
            "b": [10_000, 10_200, 10_500, 10_800, 19_650],
        },
        index=idx,
    )


def test_hero_chart_labels_each_line_with_its_final_value():
    lines = {"a": ("Simple rule", plots.SLOTS[2]), "b": ("SPY", plots.INK_2)}
    fig = plots.hero_chart(_frame(), lines, "Title", "Subtitle")
    ax = fig.axes[0]
    assert [ln.get_label() for ln in ax.get_lines() if not ln.get_label().startswith("_")] == [
        "Simple rule",
        "SPY",
    ]
    assert {t.get_text() for t in ax.texts} == {"$59,209", "$19,650"}
    assert fig.legends, "a legend backs up the colours"
    assert ax.get_ylim()[0] == 0  # a linear dollar scale from zero
    plt.close(fig)
