"""Unit tests for Thread.title property."""

from i2code.plan_domain.thread import Thread


class TestThreadTitle:

    def test_returns_title_from_header(self):
        thread = Thread(_header_lines=['## Steel Thread 1: Setup Infrastructure', ''])
        assert thread.title == 'Setup Infrastructure'
