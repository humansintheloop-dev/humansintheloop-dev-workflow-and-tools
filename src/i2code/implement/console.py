"""Timestamped console output for implement progress messages."""

import time


def print_message(message="", now=time.localtime, **print_kwargs):
    """Print a progress message prefixed with the current wall-clock time."""
    separator, text = _split_leading_blank_lines(str(message))
    print(f"{separator}[{time.strftime('%H:%M:%S', now())}] {text}", **print_kwargs)


def _split_leading_blank_lines(message):
    """Split off leading newlines so they stay ahead of the timestamp."""
    text = message.lstrip("\n")
    return message[: len(message) - len(text)], text
