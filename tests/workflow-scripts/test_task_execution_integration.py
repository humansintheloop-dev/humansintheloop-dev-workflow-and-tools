"""Integration tests for task execution in implement-with-worktree.

These tests use real git/GitHub but mock Claude invocation.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import uuid

import pytest
from git import Repo

from conftest import SCRIPT_PATH


def create_mock_claude_script(tmpdir):
    """Create a mock Claude script that creates a commit.

    Args:
        tmpdir: Directory to create the script in

    Returns:
        Path to the mock script
    """
    mock_script = os.path.join(tmpdir, "mock-claude.sh")
    with open(mock_script, "w") as f:
        f.write("""#!/bin/bash
# Mock Claude script for testing
# Creates an empty commit to simulate Claude's work

git commit --allow-empty -m "Mock Claude commit for task: $1"
exit 0
""")
    # Make executable
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)
    return mock_script


# Test idea directory source
TEST_IDEA_SOURCE = os.path.join(
    os.path.dirname(__file__),
    '../kafka-security-poc'
)


def create_github_repo(repo_name):
    """Create a new GitHub repository."""
    result = subprocess.run(
        ["gh", "repo", "create", repo_name, "--private"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return None

    # Get username
    user_result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True
    )
    if user_result.returncode != 0:
        return None

    username = user_result.stdout.strip()
    repo_full_name = f"{username}/{repo_name}"
    clone_url = f"git@github.com:{repo_full_name}.git"
    return repo_full_name, clone_url


def delete_github_repo(repo_full_name):
    """Delete a GitHub repository."""
    subprocess.run(
        ["gh", "repo", "delete", repo_full_name, "--yes"],
        capture_output=True,
        text=True
    )


@pytest.fixture(scope="module")
def github_test_repo_with_plan():
    """Create a GitHub repository with a plan file containing uncompleted tasks."""
    repo_name = f"test-task-exec-{uuid.uuid4().hex[:8]}"

    result = create_github_repo(repo_name)
    if result is None:
        pytest.skip("Could not create GitHub repository")

    repo_full_name, clone_url = result

    try:
        tmpdir = tempfile.mkdtemp()

        # Clone
        subprocess.run(["git", "clone", clone_url, tmpdir], capture_output=True)

        repo = Repo(tmpdir)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()

        # Initial commit
        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write(f"# {repo_name}")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Copy test idea directory
        idea_dest = os.path.join(tmpdir, "kafka-security-poc")
        shutil.copytree(TEST_IDEA_SOURCE, idea_dest)

        # Add and commit idea files
        for root, dirs, files in os.walk(idea_dest):
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, tmpdir)
                repo.index.add([rel_path])
        repo.index.commit("Add test idea files")

        # Push to GitHub
        repo.remote("origin").push("HEAD:main")

        yield {
            "tmpdir": tmpdir,
            "repo_full_name": repo_full_name,
            "idea_dir": idea_dest,
            "repo": repo
        }

    finally:
        delete_github_repo(repo_full_name)
        if 'tmpdir' in locals():
            shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.integration
class TestTaskDetectionAndExecution:
    """Test that script detects and executes tasks from plan file."""

    def test_script_outputs_first_task(self, github_test_repo_with_plan):
        """Script should output the first uncompleted task it will execute."""
        tmpdir = github_test_repo_with_plan["tmpdir"]
        idea_dir = github_test_repo_with_plan["idea_dir"]

        # Create mock Claude script
        mock_script = create_mock_claude_script(tmpdir)

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        # The script should output information about the task it's about to execute
        assert "Executing task:" in result.stdout, \
            f"Script didn't output task info. stdout: {result.stdout}, stderr: {result.stderr}"

    def test_script_uses_mock_claude(self, github_test_repo_with_plan):
        """Script should use mock Claude when --mock-claude is provided."""
        tmpdir = github_test_repo_with_plan["tmpdir"]
        idea_dir = github_test_repo_with_plan["idea_dir"]

        # Create mock Claude script
        mock_script = create_mock_claude_script(tmpdir)

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        # The script should indicate it's using mock Claude
        assert "Using mock Claude" in result.stdout, \
            f"Script didn't use mock Claude. stdout: {result.stdout}, stderr: {result.stderr}"

    def test_mock_claude_creates_commit(self, github_test_repo_with_plan):
        """Mock Claude should create a commit that gets pushed."""
        tmpdir = github_test_repo_with_plan["tmpdir"]
        idea_dir = github_test_repo_with_plan["idea_dir"]
        repo_full_name = github_test_repo_with_plan["repo_full_name"]

        # Create mock Claude script
        mock_script = create_mock_claude_script(tmpdir)

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        # The script should report task completed successfully
        assert "Task completed successfully" in result.stdout, \
            f"Task didn't complete. stdout: {result.stdout}, stderr: {result.stderr}"
