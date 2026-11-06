"""Offline tests for the book's build hooks (#26)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mkdocs_hooks


def test_chart_paths_point_at_the_sites_figures():
    md = "Before ![A chart](../reports/figures/risk_paths.png) after"
    assert mkdocs_hooks.rewrite(md) == "Before ![A chart](figures/risk_paths.png) after"


def test_other_outside_links_go_to_github():
    md = "See [the log](../references/decisions.md) and [the README](../README.md)."
    out = mkdocs_hooks.rewrite(md)
    assert (
        "](https://github.com/siddharthps/sp500-momentum-winners/blob/main/references/decisions.md)"
        in out
    )
    assert "](https://github.com/siddharthps/sp500-momentum-winners/blob/main/README.md)" in out


def test_links_inside_docs_are_left_alone():
    md = "[Chapter 7](07_simulation.md) and [a site](https://example.com/x)"
    assert mkdocs_hooks.rewrite(md) == md
