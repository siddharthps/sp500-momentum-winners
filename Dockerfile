# The pipeline in a container (#48): the exact environment CI tests, from uv's lock file.
#
#   docker build -t sp500-momentum .
#   docker run --rm sp500-momentum                                   # the rebuild's steps (dry run)
#   docker run --rm --env-file .env -v "$PWD/data:/app/data" -v "$PWD/models:/app/models" \
#       sp500-momentum sp500_momentum.modeling.predict run --no-publish   # any project command
#
# No data, models or secrets are baked in (see .dockerignore): data and models are mounted, or
# pulled from the private Hugging Face snapshot with `--from-file` and a token passed at run time.
# Published from main to ghcr.io/siddharthps/sp500-momentum-winners.

FROM python:3.12-slim AS base

# The base image's Debian packages, brought up to date with their security fixes
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# The base image's pip is never used (uv manages everything) and vendors pkg_resources from
# setuptools 70.3.0 (CVE-2025-47273, flagged by the CI scan, 6 Nov): remove it.
RUN python -m pip uninstall -y pip

# uv, pinned to the version the lock file was made with
COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Dependencies only (cached until the lock file changes). TA-Lib comes as a prebuilt
#    manylinux wheel, so nothing is compiled.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project --no-dev

# 2. The project itself
COPY . .
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
RUN useradd -m -u 1000 app && chown -R app /app
USER app

# `docker run <image> <module> [args]` runs `python -m <module> [args]`
ENTRYPOINT ["python", "-m"]
CMD ["sp500_momentum.pipeline", "rebuild-all", "--dry-run"]


# The same image plus the dev tools, used by CI to run the tests inside the container.
FROM base AS test
USER root
RUN uv sync --locked
USER app
CMD ["pytest", "-q"]
