"""Retry a flaky download a few times, waiting longer each time (#39).

Shared by the plain HTTP sources (Wikipedia, FRED). A scheduled run on a cloud machine meets
more transient failures (timeouts, rate limits) than a PC does, and one failed request
shouldn't cost the month. Errors are reported by type only: a request error's text can carry
a URL, and some URLs carry a key.
"""

from collections.abc import Callable
import time

from loguru import logger


def with_retries[T](
    fn: Callable[[], T],
    label: str,
    attempts: int = 3,
    wait: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call `fn()` up to `attempts` times, waiting `wait`, then 2x, 4x... seconds between tries.

    The last error is raised unchanged, so a source that's really down still fails the run.
    """
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i == attempts - 1:
                raise
            pause = wait * 2**i
            logger.warning(f"{label}: {type(e).__name__}; retrying in {pause:.0f} s")
            sleep(pause)
    raise AssertionError("unreachable")
