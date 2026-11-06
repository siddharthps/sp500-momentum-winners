"""MkDocs build hooks (#26): let the book's chapters keep the paths that work on GitHub.

The chapters embed charts as `../reports/figures/<name>.png` and link a few files outside `docs/`
(the README, `references/`). GitHub resolves those inside the repository; an MkDocs site only
serves `docs/`. At build time, without touching the Markdown sources:
- every chart in reports/figures/ is added to the site as `figures/<name>.png`;
- the chart paths are rewritten to `figures/<name>.png`;
- links to other files outside docs/ become links to the file on GitHub.

`mkdocs build --strict` (in CI) then fails on any chart or link that doesn't resolve.
"""

from pathlib import Path
import re

from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "reports" / "figures"
GITHUB = "https://github.com/siddharthps/sp500-momentum-winners/blob/main/"

CHART = re.compile(r"\]\(\.\./reports/figures/([^)\s]+)\)")
OUTSIDE = re.compile(r"\]\(\.\./(?!reports/figures/)([^)\s]+)\)")


def rewrite(markdown: str) -> str:
    """Chart paths -> the site's figures/; other ../ links -> the file on GitHub."""
    markdown = CHART.sub(r"](figures/\1)", markdown)
    return OUTSIDE.sub(lambda m: f"]({GITHUB}{m.group(1)})", markdown)


def on_files(files, config):
    """Add every chart to the site, so --strict can check the image links."""
    for png in sorted(FIGURES.glob("*.png")):
        files.append(
            File(
                f"figures/{png.name}",
                src_dir=str(FIGURES.parent),
                dest_dir=config["site_dir"],
                use_directory_urls=config["use_directory_urls"],
            )
        )
    return files


def on_page_markdown(markdown, page, config, files):
    return rewrite(markdown)
