"""Shared fixtures and utilities for workflow-scripts tests."""

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


def run_script(idea_dir, cwd=None):
    """Run the implement-with-worktree.sh script.

    Args:
        idea_dir: Path to the idea directory
        cwd: Working directory for the script (optional)

    Returns:
        subprocess.CompletedProcess with stdout, stderr, and returncode
    """
    return subprocess.run(
        [SCRIPT_PATH, idea_dir],
        capture_output=True,
        text=True,
        cwd=cwd
    )


@pytest.fixture
def test_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()
        yield tmpdir, repo


@pytest.fixture
def test_git_repo_with_commit():
    """Create a temporary git repository with an initial commit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Repo.init(tmpdir)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()

        # Need an initial commit before we can create branches
        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write("# Test Repo")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        yield tmpdir, repo
