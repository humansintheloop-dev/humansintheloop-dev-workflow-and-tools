"""Shared fixtures and utilities for implement tests."""

import os
import stat
import subprocess
import sys
import tempfile
import time
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
from fake_idea_project import FakeIdeaProject  # noqa: E402, F401

# Command to invoke the implement CLI
SCRIPT_CMD = ["i2code", "implement"]


def create_github_repo(repo_name):
    """Create a new GitHub repository in the test organization.

    Returns:
        repo_full_name (e.g. "org/repo-name")

    Raises:
        RuntimeError: If repository creation fails
    """
    repo_full_name = f"{os.environ.get('GH_TEST_ORG', 'humansintheloop-test-org')}/{repo_name}"
    
    print(f"\n\nCreating {repo_full_name}\n")

    result = subprocess.run(
        ["gh", "repo", "create", repo_full_name, "--private"],
        capture_output=True,
        text=True
    )

    print(f"\n\nCreated {repo_full_name}\n")

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create GitHub repo: {result.stderr}")

    _wait_for_repo_accessible(repo_full_name)

    return repo_full_name


def _wait_for_repo_accessible(repo_full_name, max_attempts=10, delay=2):
    """Poll until the GitHub repo is accessible via the API.

    Newly created repos may not be immediately cloneable due to
    GitHub API propagation delay.
    """
    for attempt in range(max_attempts):
        result = subprocess.run(
            ["gh", "api", f"repos/{repo_full_name}", "--silent"],
            capture_output=True,
        )
        if result.returncode == 0:
            return
        time.sleep(delay)

    raise RuntimeError(
        f"Repo {repo_full_name} not accessible after {max_attempts * delay}s"
    )


def delete_github_repo(repo_full_name):
    """Delete a GitHub repository."""
    subprocess.run(
        ["gh", "repo", "delete", repo_full_name, "--yes"],
        capture_output=True,
        text=True
    )


def run_script(idea_dir, cwd=None, setup_only=False, extra_args=None):
    """Run the i2code implement command.

    Args:
        idea_dir: Path to the idea directory
        cwd: Working directory for the script (optional)
        setup_only: If True, add --setup-only flag (skip task execution)
        extra_args: Additional CLI arguments, e.g. ["--mock-claude", script, "--trunk"] (optional)

    Returns:
        subprocess.CompletedProcess with stdout, stderr, and returncode
    """
    cmd = SCRIPT_CMD + [idea_dir]
    if setup_only:
        cmd.append("--setup-only")
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd
    )


def create_mock_claude_script_that_marks_tasks_complete(tmpdir, idea_name):
    """Create a mock Claude script that marks tasks complete and commits.

    This script simulates what real Claude would do:
    1. Mark the current task as complete in the plan file
    2. Create a commit with the changes
    3. Print the <SUCCESS> tag that --non-interactive requires

    Args:
        tmpdir: Directory to create the script in
        idea_name: Name of the idea (used to find plan file)

    Returns:
        Path to the mock script
    """
    mock_script = os.path.join(tmpdir, "mock-claude-complete.sh")
    with open(mock_script, "w") as f:
        # The script runs in the worktree, so use relative path to find plan file
        # Use awk for portable first-occurrence replacement
        f.write(f"""#!/bin/bash
set -e  # Exit on error

# Mock Claude script that marks tasks complete
# Receives task description as $1
# Runs in the worktree directory

TASK_DESC="$1"
IDEA_NAME="{idea_name}"

# Ensure CI workflow exists (required by the script before pushing)
mkdir -p .github/workflows
if [ ! -f .github/workflows/ci.yml ]; then
    cat > .github/workflows/ci.yml << 'CIEOF'
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "ok"
CIEOF
    git add .github/workflows/ci.yml
fi

# Find the plan file in the worktree (relative path from worktree root)
PLAN_FILE="$IDEA_NAME/$IDEA_NAME-plan.md"

# Mark the first unchecked task as complete using awk
# This replaces only the first occurrence of "- [ ] **Task" with "- [x] **Task"
awk '!done && /- \\[ \\] \\*\\*Task [0-9]+\\.[0-9]+:/ {{sub(/- \\[ \\] \\*\\*Task/, "- [x] **Task"); done=1}} 1' "$PLAN_FILE" > "$PLAN_FILE.tmp"
mv "$PLAN_FILE.tmp" "$PLAN_FILE"

# Stage and commit the change
git add "$PLAN_FILE"
git commit -m "Complete task: $TASK_DESC"

# Report success the way non-interactive Claude does
echo "<SUCCESS>task implemented: $(git rev-parse HEAD)</SUCCESS>"
""")
    # Make executable
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)
    return mock_script


def create_failing_mock_claude_script(tmpdir):
    """Create a mock Claude script that exits 1 without changing any file.

    Args:
        tmpdir: Directory to create the script in

    Returns:
        Path to the mock script
    """
    mock_script = os.path.join(tmpdir, "mock-claude-fail.sh")
    with open(mock_script, "w") as f:
        f.write("""#!/bin/bash
# Mock Claude script that fails without committing
exit 1
""")
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)
    return mock_script


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


def write_plan_file(plan_dir, idea_name, tasks):
    """Write a plan file with the given tasks.

    Args:
        plan_dir: Directory to write the plan file in.
        idea_name: Name of the idea.
        tasks: List of (thread, task_num, title, completed) tuples.

    Returns:
        Path to the written plan file.
    """
    lines = [f"# Plan for {idea_name}\n\n"]
    current_thread = None
    for thread, task_num, title, completed in tasks:
        if thread != current_thread:
            lines.append(f"## Steel Thread {thread}: Thread {thread}\n\n")
            current_thread = thread
        checkbox = "[x]" if completed else "[ ]"
        lines.append(
            f"- {checkbox} **Task {thread}.{task_num}: {title}**\n"
        )
    plan_path = os.path.join(plan_dir, f"{idea_name}-plan.md")
    with open(plan_path, "w") as f:
        f.writelines(lines)
    return plan_path


def mark_task_complete(plan_path, thread, task_num, title):
    """Return a callable that marks a task as complete in the plan file."""
    def _mark():
        with open(plan_path, "r") as f:
            content = f.read()
        old = f"- [ ] **Task {thread}.{task_num}: {title}**"
        new = f"- [x] **Task {thread}.{task_num}: {title}**"
        content = content.replace(old, new)
        with open(plan_path, "w") as f:
            f.write(content)
    return _mark


def advance_head(fake_repo, new_sha):
    """Return a callable that advances the fake repo's HEAD."""
    def _advance():
        fake_repo.set_head_sha(new_sha)
    return _advance


def combined(*fns):
    """Return a callable that calls all given functions in order."""
    def _run():
        for fn in fns:
            fn()
    return _run


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
