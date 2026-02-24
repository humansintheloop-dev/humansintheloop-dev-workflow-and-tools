"""Integration tests for idea validation in implement-with-worktree.

These tests run the actual shell script against real test repositories.
"""

import json
import os

import pytest

from conftest import run_script


@pytest.mark.integration
class TestNonExistentDirectory:
    """Test script behavior with non-existent directory."""

    def test_nonexistent_directory_returns_error(self):
        """Running script with non-existent directory should return error."""
        result = run_script('/nonexistent/path/to/idea')

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "directory" in result.stderr.lower()


@pytest.mark.integration
class TestIncompleteIdeaDirectory:
    """Test script behavior with incomplete idea directory (missing files)."""

    def test_missing_files_returns_error_listing_missing(self, test_git_repo):
        """Running script with incomplete idea directory should list missing files."""
        tmpdir, repo = test_git_repo

        # Create idea directory with only one file
        idea_dir = os.path.join(tmpdir, "test-feature")
        os.makedirs(idea_dir)

        # Create only the idea file
        idea_file = os.path.join(idea_dir, "test-feature-idea.md")
        with open(idea_file, "w") as f:
            f.write("# Test Feature Idea")

        # Commit the file
        repo.index.add([os.path.relpath(idea_file, tmpdir)])
        repo.index.commit("Add idea file")

        result = run_script(idea_dir)

        assert result.returncode != 0
        # Should mention missing files
        assert "missing" in result.stderr.lower()
        # Should list specific missing files
        assert "discussion" not in result.stderr.lower()
        assert "spec" in result.stderr.lower()
        assert "plan" in result.stderr.lower()


@pytest.mark.integration
class TestUncommittedIdeaFiles:
    """Test script behavior with uncommitted idea files."""

    def test_uncommitted_files_returns_error(self, test_git_repo):
        """Running script with uncommitted idea files should return error."""
        tmpdir, repo = test_git_repo

        # Create idea directory with all required files
        idea_dir = os.path.join(tmpdir, "test-feature")
        os.makedirs(idea_dir)

        # Create all required files
        for suffix in ["idea.md", "spec.md", "plan.md"]:
            filepath = os.path.join(idea_dir, f"test-feature-{suffix}")
            with open(filepath, "w") as f:
                f.write(f"# {suffix}")

        # Don't commit - files are untracked

        result = run_script(idea_dir)

        assert result.returncode != 0
        assert "uncommitted" in result.stderr.lower() or "untracked" in result.stderr.lower()


@pytest.mark.integration
class TestValidIdeaDirectory:
    """Test script behavior with valid committed idea directory."""

    def test_valid_directory_creates_state_file(self, test_git_repo):
        """Running script with valid idea directory should create state file."""
        tmpdir, repo = test_git_repo

        # Create idea directory with all required files
        idea_dir = os.path.join(tmpdir, "test-feature")
        os.makedirs(idea_dir)

        # Create all required files
        for suffix in ["idea.md", "spec.md", "plan.md"]:
            filepath = os.path.join(idea_dir, f"test-feature-{suffix}")
            with open(filepath, "w") as f:
                f.write(f"# {suffix}")

        # Commit all files
        for suffix in ["idea.md", "spec.md", "plan.md"]:
            rel_path = os.path.join("test-feature", f"test-feature-{suffix}")
            repo.index.add([rel_path])
        repo.index.commit("Add idea files")

        result = run_script(idea_dir, setup_only=True)

        # Script should succeed (exit 0) or at least create state file before failing
        # on later steps (like GitHub operations)
        state_file = os.path.join(idea_dir, "test-feature-wt-state.json")

        # Check state file was created
        assert os.path.isfile(state_file), f"State file not created. stderr: {result.stderr}"

        # Verify state file content
        with open(state_file, "r") as f:
            state = json.load(f)

        assert "slice_number" not in state
        assert "processed_comment_ids" in state
        assert "processed_review_ids" in state
