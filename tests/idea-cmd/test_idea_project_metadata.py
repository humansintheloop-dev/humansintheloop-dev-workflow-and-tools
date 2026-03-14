"""Tests for IdeaProject.metadata_file property."""

import os

import pytest

from i2code.implement.idea_project import IdeaProject


@pytest.mark.unit
def test_metadata_file_returns_correct_path():
    project = IdeaProject("/some/path/my-feature")
    assert project.metadata_file == os.path.join(
        "/some/path/my-feature", "my-feature-metadata.yaml"
    )
