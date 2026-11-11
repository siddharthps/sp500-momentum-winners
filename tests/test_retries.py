import pytest

from sp500_momentum.retries import with_retries


def test_returns_at_once_when_it_works():
    waits = []
    assert with_retries(lambda: 42, "x", sleep=waits.append) == 42
    assert waits == []


def test_retries_with_growing_waits_then_succeeds():
    calls, waits = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("temporary")
        return "ok"

    assert with_retries(flaky, "x", attempts=3, wait=5, sleep=waits.append) == "ok"
    assert waits == [5, 10]


def test_raises_the_last_error_when_every_try_fails():
    waits = []

    def down():
        raise TimeoutError("still down")

    with pytest.raises(TimeoutError):
        with_retries(down, "x", attempts=3, wait=1, sleep=waits.append)
    assert waits == [1, 2]  # no wait after the last try
