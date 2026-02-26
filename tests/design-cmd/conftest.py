"""Shared fixtures for design-cmd tests."""

import os
import tempfile
from contextlib import contextmanager

from i2code.implement.idea_project import IdeaProject


@contextmanager
def TempIdeaProject(name):
    """Create a temporary IdeaProject with its directory on disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, name)
        os.makedirs(idea_dir)
        yield IdeaProject(idea_dir)
