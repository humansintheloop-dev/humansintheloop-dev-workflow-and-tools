"""Shared fixtures for go-cmd tests."""

import io
import os
import sys
import tempfile
from contextlib import contextmanager
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(__file__))

from i2code.go_cmd.menu import MenuConfig
from i2code.implement.idea_project import IdeaProject


@contextmanager
def TempIdeaProject(name):
    """Create a temporary IdeaProject with its directory on disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, name)
        os.makedirs(idea_dir)
        yield IdeaProject(idea_dir)


def menu_config_by_label(choices):
    """Create a MenuConfig that resolves menu option labels to numbers."""
    output = io.StringIO()
    it = iter(choices)

    def resolve_choice(_prompt):
        label = next(it)
        for line in reversed(output.getvalue().splitlines()):
            stripped = line.strip()
            if label in stripped and stripped[0].isdigit():
                return stripped.split(")")[0]
        raise ValueError(f"Menu option '{label}' not found in displayed menu")

    return MenuConfig(input_fn=resolve_choice, output=output)


def make_mock_fn_returning(*results):
    """Create a MagicMock that returns each result in sequence."""
    it = iter(results)
    return MagicMock(side_effect=lambda _: next(it))
