"""Shared fixtures and utilities for implement tests."""

import os
import subprocess
import tempfile

import pytest
from git import Repo


# Command to invoke the implement CLI
SCRIPT_CMD = ["i2code", "implement"]


def run_script(idea_dir, cwd=None, setup_only=False, mock_claude=None):
    """Run the i2code implement command.

    Args:
        idea_dir: Path to the idea directory
        cwd: Working directory for the script (optional)
        setup_only: If True, add --setup-only flag (skip task execution)
        mock_claude: Path to mock Claude script (optional)

    Returns:
        subprocess.CompletedProcess with stdout, stderr, and returncode
    """
    cmd = SCRIPT_CMD + [idea_dir]
    if setup_only:
        cmd.append("--setup-only")
    if mock_claude:
        cmd.extend(["--mock-claude", mock_claude])
    return subprocess.run(
        cmd,
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
