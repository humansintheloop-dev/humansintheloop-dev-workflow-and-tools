"""Shared fixtures and utilities for implement tests."""

import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager

import pytest
from git import Repo

from i2code.implement.idea_project import IdeaProject

# Ensure tests/implement/ is on sys.path so test files can import
# fake_github_client unambiguously (avoids conftest module name collisions).
sys.path.insert(0, os.path.dirname(__file__))

from fake_claude_runner import FakeClaudeRunner  # noqa: E402, F401
from fake_github_client import FakeGitHubClient  # noqa: E402, F401
from fake_git_repository import FakeGitRepository  # noqa: E402, F401

# Command to invoke the implement CLI
SCRIPT_CMD = ["i2code", "implement"]


def create_github_repo(repo_name):
    """Create a new GitHub repository in the test organization.

    Returns:
        repo_full_name (e.g. "org/repo-name")

    Raises:
        RuntimeError: If repository creation fails
    """
    repo_full_name = f"{os.environ['GH_TEST_ORG']}/{repo_name}"
    result = subprocess.run(
        ["gh", "repo", "create", repo_full_name, "--private"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create GitHub repo: {result.stderr}")

    return repo_full_name


def delete_github_repo(repo_full_name):
    """Delete a GitHub repository."""
    subprocess.run(
        ["gh", "repo", "delete", repo_full_name, "--yes"],
        capture_output=True,
        text=True
    )


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


@contextmanager
def TempIdeaProject(name):
    """Create a temporary IdeaProject with its directory on disk.

    Usage:
        with TempIdeaProject("my-feature") as project:
            assert project.name == "my-feature"
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, name)
        os.makedirs(idea_dir)
        yield IdeaProject(idea_dir)


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
