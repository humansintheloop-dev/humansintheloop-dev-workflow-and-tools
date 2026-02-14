"""Unit tests for Thread.introduction property."""

from i2code.plan_domain.thread import Thread


class TestThreadIntroduction:

    def test_returns_introduction_from_header_lines(self):
        thread = Thread(_header_lines=[
            '## Steel Thread 1: Setup',
            'Introduction to this thread.',
            '',
            'Second paragraph of introduction.',
            '',
        ])
        assert thread.introduction == 'Introduction to this thread.\n\nSecond paragraph of introduction.'
