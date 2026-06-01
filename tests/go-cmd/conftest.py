"""Shared fixtures for go-cmd tests."""

import io
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(__file__))

from i2code.go_cmd.menu import MenuConfig
from i2code.implement.idea_project import IdeaProject


@contextmanager
def TempIdeaProject(name):
    """Create a temporary IdeaProject with its directory on disk.

    The directory is laid out as `<tmpdir>/docs/ideas/active/<name>` so that
    `_git_root_from_path` resolves the enclosing git root deterministically.
    The git root is attached as `project_root` on the yielded IdeaProject
    so tests can build sibling worktree/clone paths.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Resolve the tmpdir so that _git_root_from_path (which calls
        # Path.resolve) produces the same prefix as project.directory —
        # otherwise relpath produces a broken path on macOS where
        # /var/folders is a symlink to /private/var/folders.
        resolved_root = str(Path(tmpdir).resolve())
        idea_dir = os.path.join(resolved_root, "docs", "ideas", "active", name)
        os.makedirs(idea_dir)
        project = IdeaProject(idea_dir)
        project.project_root = resolved_root  # type: ignore[attr-defined]
        yield project


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
