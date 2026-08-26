"""Tests for timestamped console output."""

import io

import pytest

from i2code.implement.console import print_message


@pytest.mark.unit
class TestPrintMessage:
    """print_message(text) prefixes stdout messages with the wall-clock time."""

    def test_prefixes_message_with_current_time(self, capsys):
        print_message("Pushing changes...", now=lambda: (2026, 8, 26, 14, 31, 12, 0, 0, 0))

        assert capsys.readouterr().out == "[14:31:12] Pushing changes...\n"

    def test_keeps_leading_blank_lines_ahead_of_the_timestamp(self, capsys):
        print_message("\nFixing: flaky test", now=lambda: (2026, 8, 26, 14, 31, 12, 0, 0, 0))

        assert capsys.readouterr().out == "\n[14:31:12] Fixing: flaky test\n"

    def test_passes_print_keyword_arguments_through(self):
        stream = RecordingStream()

        print_message(
            "Task 5 of 33 completed successfully in 7 minutes.",
            now=lambda: (2026, 8, 26, 14, 38, 4, 0, 0, 0),
            file=stream,
            flush=True,
        )

        assert stream.flushed
        assert stream.getvalue() == "[14:38:04] Task 5 of 33 completed successfully in 7 minutes.\n"


class RecordingStream(io.StringIO):
    """StringIO that records whether it was flushed."""

    flushed = False

    def flush(self):
        self.flushed = True
