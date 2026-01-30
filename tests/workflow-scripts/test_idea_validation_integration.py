"""Integration tests for idea validation in implement-with-worktree.

These tests run the actual shell script against real test repositories.
"""

import json
import os
import subprocess
import tempfile

import pytest
from git import Repo


# Path to the shell script
SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__),
    '../../workflow-scripts/implement-with-worktree.sh'
)


@pytest.fixture
def test_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()
        yield tmpdir, repo


@pytest.mark.integration
class TestNonExistentDirectory:
    """Test script behavior with non-existent directory."""

    def test_nonexistent_directory_returns_error(self):
        """Running script with non-existent directory should return error."""
        result = subprocess.run(
            [SCRIPT_PATH, '/nonexistent/path/to/idea'],
            capture_output=True,
            text=True
        )

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

        result = subprocess.run(
            [SCRIPT_PATH, idea_dir],
            capture_output=True,
            text=True
        )

        assert result.returncode != 0
        # Should mention missing files
        assert "missing" in result.stderr.lower()
        # Should list specific missing files
        assert "discussion" in result.stderr.lower()
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
        for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
            filepath = os.path.join(idea_dir, f"test-feature-{suffix}")
            with open(filepath, "w") as f:
                f.write(f"# {suffix}")

        # Don't commit - files are untracked

        result = subprocess.run(
            [SCRIPT_PATH, idea_dir],
            capture_output=True,
            text=True
        )

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
        for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
            filepath = os.path.join(idea_dir, f"test-feature-{suffix}")
            with open(filepath, "w") as f:
                f.write(f"# {suffix}")

        # Commit all files
        for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
            rel_path = os.path.join("test-feature", f"test-feature-{suffix}")
            repo.index.add([rel_path])
        repo.index.commit("Add idea files")

        result = subprocess.run(
            [SCRIPT_PATH, idea_dir],
            capture_output=True,
            text=True
        )

        # Script should succeed (exit 0) or at least create state file before failing
        # on later steps (like GitHub operations)
        state_file = os.path.join(idea_dir, "test-feature-wt-state.json")

        # Check state file was created
        assert os.path.isfile(state_file), f"State file not created. stderr: {result.stderr}"

        # Verify state file content
        with open(state_file, "r") as f:
            state = json.load(f)

        assert state.get("slice_number") == 1
        assert "processed_comment_ids" in state
        assert "processed_review_ids" in state
