"""Tests for idea directory validation in implement-with-worktree."""

import os
import sys
import tempfile
import pytest

# Add workflow-scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../workflow-scripts'))


@pytest.mark.unit
class TestIdeaDirectoryValidation:
    """Test validation of idea directory existence."""

    def test_validate_nonexistent_directory_raises_error(self):
        """Script should raise error for non-existent directory."""
        from implement_with_worktree import validate_idea_directory

        with pytest.raises(SystemExit) as exc_info:
            validate_idea_directory("/nonexistent/path/to/idea")

        assert exc_info.value.code != 0

    def test_validate_existing_directory_returns_idea_name(self):
        """Script should return idea name extracted from directory path."""
        from implement_with_worktree import validate_idea_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-test-feature")
            os.makedirs(idea_dir)

            idea_name = validate_idea_directory(idea_dir)

            assert idea_name == "my-test-feature"

    def test_idea_name_extracted_from_last_path_component(self):
        """Idea name should be the last component of the path."""
        from implement_with_worktree import validate_idea_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            idea_dir = os.path.join(tmpdir, "docs", "features", "wt-pr-based-development")
            os.makedirs(idea_dir)

            idea_name = validate_idea_directory(idea_dir)

            assert idea_name == "wt-pr-based-development"
