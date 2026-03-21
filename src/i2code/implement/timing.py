"""Timing utilities for measuring operation durations."""

import time
from contextlib import contextmanager


class Timer:
    """Measures elapsed time from creation to print.

    Usage:
        Timer.enabled = True
        t = Timer.start()
        do_something()
        t.print("do_something")
    """

    enabled = False

    def __init__(self):
        self._start = time.monotonic()

    @classmethod
    def start(cls):
        return cls()

    def print(self, label):
        if not Timer.enabled:
            return
        elapsed = time.monotonic() - self._start
        print(f"  [timing] {label}: {elapsed:.1f}s")


@contextmanager
def timed(label):
    """Context manager that prints elapsed time on exit.

    Usage:
        with timed("push"):
            git_repo.push()
    """
    t = Timer.start()
    yield
    t.print(label)
