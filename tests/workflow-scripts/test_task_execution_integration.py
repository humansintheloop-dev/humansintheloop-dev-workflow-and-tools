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


def create_mock_claude_script_that_marks_tasks_complete(tmpdir, idea_name):
    """Create a mock Claude script that marks tasks complete and commits.

    This script simulates what real Claude would do:
    1. Mark the current task as complete in the plan file
    2. Create a commit with the changes

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

# Find the plan file in the worktree (relative path from worktree root)
PLAN_FILE="$IDEA_NAME/$IDEA_NAME-plan.md"

# Mark the first unchecked task as complete using awk
# This replaces only the first occurrence of "- [ ] **Task" with "- [x] **Task"
awk '!done && /- \\[ \\] \\*\\*Task/ {{sub(/- \\[ \\] \\*\\*Task/, "- [x] **Task"); done=1}} 1' "$PLAN_FILE" > "$PLAN_FILE.tmp"
mv "$PLAN_FILE.tmp" "$PLAN_FILE"

# Stage and commit the change
git add "$PLAN_FILE"
git commit -m "Complete task: $TASK_DESC"
""")
    # Make executable
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)
    return mock_script


# Simple plan content for testing sequential execution
SIMPLE_PLAN_CONTENT = """# Simple Test Plan

## Instructions for Coding Agent

- Use TDD

---

## Steel Thread 1 – Test Tasks

- [ ] **Task 1: First task**
  - [ ] Do something first

- [ ] **Task 2: Second task**
  - [ ] Do something second

- [ ] **Task 3: Third task**
  - [ ] Do something third
"""


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


@pytest.mark.integration
class TestTaskDetectionAndExecution:
    """Test that script detects and executes tasks from plan file."""

    def test_script_outputs_first_task(self, github_test_repo_with_simple_plan):
        """Script should output the first uncompleted task it will execute."""
        tmpdir = github_test_repo_with_simple_plan["tmpdir"]
        idea_dir = github_test_repo_with_simple_plan["idea_dir"]
        idea_name = github_test_repo_with_simple_plan["idea_name"]

        # Create mock Claude script that marks tasks complete
        mock_script = create_mock_claude_script_that_marks_tasks_complete(tmpdir, idea_name)

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=120
        )

        # The script should output information about the task it's about to execute
        assert "Executing task:" in result.stdout, \
            f"Script didn't output task info. stdout: {result.stdout}, stderr: {result.stderr}"

    def test_script_uses_mock_claude(self, github_test_repo_with_simple_plan):
        """Script should use mock Claude when --mock-claude is provided."""
        tmpdir = github_test_repo_with_simple_plan["tmpdir"]
        idea_dir = github_test_repo_with_simple_plan["idea_dir"]
        idea_name = github_test_repo_with_simple_plan["idea_name"]

        # Create mock Claude script that marks tasks complete
        mock_script = create_mock_claude_script_that_marks_tasks_complete(tmpdir, idea_name)

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=120
        )

        # The script should indicate it's using mock Claude
        assert "Using mock Claude" in result.stdout, \
            f"Script didn't use mock Claude. stdout: {result.stdout}, stderr: {result.stderr}"

    def test_mock_claude_creates_commit(self, github_test_repo_with_simple_plan):
        """Mock Claude should create a commit that gets pushed."""
        tmpdir = github_test_repo_with_simple_plan["tmpdir"]
        idea_dir = github_test_repo_with_simple_plan["idea_dir"]
        idea_name = github_test_repo_with_simple_plan["idea_name"]

        # Create mock Claude script that marks tasks complete
        mock_script = create_mock_claude_script_that_marks_tasks_complete(tmpdir, idea_name)

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=120
        )

        # The script should report task completed successfully
        assert "Task completed successfully" in result.stdout, \
            f"Task didn't complete. stdout: {result.stdout}, stderr: {result.stderr}"


@pytest.fixture(scope="function")
def github_test_repo_with_simple_plan():
    """Create a GitHub repository with a simple 3-task plan for testing sequential execution."""
    repo_name = f"test-tmp-seq-exec-{uuid.uuid4().hex[:8]}"

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

        # Create simple idea directory with minimal files
        idea_name = "simple-test"
        idea_dir = os.path.join(tmpdir, idea_name)
        os.makedirs(idea_dir)

        # Create required idea files
        with open(os.path.join(idea_dir, f"{idea_name}-idea.md"), "w") as f:
            f.write("# Simple Test Idea\n\nA simple test idea.")

        with open(os.path.join(idea_dir, f"{idea_name}-discussion.md"), "w") as f:
            f.write("# Discussion\n\nNo discussion needed.")

        with open(os.path.join(idea_dir, f"{idea_name}-spec.md"), "w") as f:
            f.write("# Specification\n\nSimple spec.")

        plan_path = os.path.join(idea_dir, f"{idea_name}-plan.md")
        with open(plan_path, "w") as f:
            f.write(SIMPLE_PLAN_CONTENT)

        # Add and commit idea files
        for filename in os.listdir(idea_dir):
            filepath = os.path.join(idea_dir, filename)
            rel_path = os.path.relpath(filepath, tmpdir)
            repo.index.add([rel_path])
        repo.index.commit("Add simple test idea files")

        # Push to GitHub
        repo.remote("origin").push("HEAD:main")

        yield {
            "tmpdir": tmpdir,
            "repo_full_name": repo_full_name,
            "idea_dir": idea_dir,
            "idea_name": idea_name,
            "plan_path": plan_path,
            "repo": repo
        }

    finally:
        delete_github_repo(repo_full_name)
        if 'tmpdir' in locals():
            shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.integration
class TestSequentialTaskExecution:
    """Test that script executes all tasks sequentially until complete."""

    def test_executes_all_tasks_until_complete(self, github_test_repo_with_simple_plan):
        """Script should execute tasks one by one until all are complete."""
        tmpdir = github_test_repo_with_simple_plan["tmpdir"]
        idea_dir = github_test_repo_with_simple_plan["idea_dir"]
        idea_name = github_test_repo_with_simple_plan["idea_name"]

        # Create mock Claude script that marks tasks complete
        mock_script = create_mock_claude_script_that_marks_tasks_complete(
            tmpdir, idea_name
        )

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=120  # 2 minute timeout
        )

        # Verify all 3 tasks were executed
        assert "Executing task:" in result.stdout, \
            f"No tasks executed. stdout: {result.stdout}, stderr: {result.stderr}"

        # Count how many tasks were executed
        task_count = result.stdout.count("Executing task:")
        assert task_count == 3, \
            f"Expected 3 tasks executed, got {task_count}. stdout: {result.stdout}, stderr: {result.stderr}"

        # Verify script completed successfully
        assert result.returncode == 0, \
            f"Script failed with code {result.returncode}. stderr: {result.stderr}"

    def test_tasks_executed_in_order(self, github_test_repo_with_simple_plan):
        """Script should execute tasks in order (Task 1, Task 2, Task 3)."""
        tmpdir = github_test_repo_with_simple_plan["tmpdir"]
        idea_dir = github_test_repo_with_simple_plan["idea_dir"]
        idea_name = github_test_repo_with_simple_plan["idea_name"]

        # Create mock Claude script that marks tasks complete
        mock_script = create_mock_claude_script_that_marks_tasks_complete(
            tmpdir, idea_name
        )

        # Run the script with mock Claude
        result = subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=120
        )

        # Verify tasks were executed in order
        stdout = result.stdout
        task1_pos = stdout.find("Task 1")
        task2_pos = stdout.find("Task 2")
        task3_pos = stdout.find("Task 3")

        assert task1_pos < task2_pos < task3_pos, \
            f"Tasks not in order. Positions: Task1={task1_pos}, Task2={task2_pos}, Task3={task3_pos}"

    def test_plan_file_updated_after_completion(self, github_test_repo_with_simple_plan):
        """Plan file in worktree should have all tasks marked complete after script finishes."""
        tmpdir = github_test_repo_with_simple_plan["tmpdir"]
        idea_dir = github_test_repo_with_simple_plan["idea_dir"]
        idea_name = github_test_repo_with_simple_plan["idea_name"]

        # Create mock Claude script that marks tasks complete
        mock_script = create_mock_claude_script_that_marks_tasks_complete(
            tmpdir, idea_name
        )

        # Run the script with mock Claude
        subprocess.run(
            [SCRIPT_PATH, idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=120
        )

        # Read the plan file from the worktree and verify all tasks are marked complete
        # The worktree is at ../<repo-name>-wt-<idea-name>
        repo_name = os.path.basename(tmpdir)
        worktree_path = os.path.join(os.path.dirname(tmpdir), f"{repo_name}-wt-{idea_name}")
        worktree_plan_path = os.path.join(worktree_path, idea_name, f"{idea_name}-plan.md")

        with open(worktree_plan_path, 'r') as f:
            plan_content = f.read()

        # Count uncompleted vs completed tasks
        uncompleted = plan_content.count("- [ ] **Task")
        completed = plan_content.count("- [x] **Task")

        assert uncompleted == 0, \
            f"Expected 0 uncompleted tasks, found {uncompleted}"
        assert completed == 3, \
            f"Expected 3 completed tasks, found {completed}"
