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

from conftest import SCRIPT_CMD, create_github_repo, delete_github_repo


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
""")
    # Make executable
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)
    return mock_script


# Simple plan content for testing sequential execution
SIMPLE_PLAN_CONTENT = """# Simple Test Plan

## Instructions for Coding Agent

- Use TDD

---

## Steel Thread 1: Test Tasks

- [ ] **Task 1.1: First task**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: First thing works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do something first

- [ ] **Task 1.2: Second task**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Second thing works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do something second

- [ ] **Task 1.3: Third task**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Third thing works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do something third
"""


@pytest.mark.integration_gh
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
            SCRIPT_CMD + [idea_dir, "--mock-claude", mock_script],
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
            SCRIPT_CMD + [idea_dir, "--mock-claude", mock_script],
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
            SCRIPT_CMD + [idea_dir, "--mock-claude", mock_script],
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

    repo_full_name, clone_url = create_github_repo(repo_name)

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


@pytest.mark.integration_gh
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
            SCRIPT_CMD + [idea_dir, "--mock-claude", mock_script],
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
            SCRIPT_CMD + [idea_dir, "--mock-claude", mock_script],
            capture_output=True,
            text=True,
            cwd=tmpdir,
            timeout=120
        )

        # Verify tasks were executed in order
        stdout = result.stdout
        task1_pos = stdout.find("Task 1.1")
        task2_pos = stdout.find("Task 1.2")
        task3_pos = stdout.find("Task 1.3")

        assert task1_pos < task2_pos < task3_pos, \
            f"Tasks not in order. Positions: Task1.1={task1_pos}, Task1.2={task2_pos}, Task1.3={task3_pos}"

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
            SCRIPT_CMD + [idea_dir, "--mock-claude", mock_script],
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


# Plan with all tasks already complete for feedback testing
COMPLETED_PLAN_CONTENT = """# Test Plan (All Complete)

## Instructions for Coding Agent

- Use TDD

---

## Steel Thread 1: Test Tasks

- [x] **Task 1.1: Already complete**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: It works
  - Evidence: `pytest`
  - Steps:
    - [x] This is done
"""


@pytest.fixture(scope="function")
def github_test_repo_with_pr_and_comments():
    """Create a GitHub repository with a PR that has review comments."""
    repo_name = f"test-tmp-feedback-{uuid.uuid4().hex[:8]}"

    repo_full_name, clone_url = create_github_repo(repo_name)
    tmpdir = None

    try:
        tmpdir = tempfile.mkdtemp()

        # Clone
        subprocess.run(["git", "clone", clone_url, tmpdir], capture_output=True)

        repo = Repo(tmpdir)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()

        # Initial commit on main
        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write(f"# {repo_name}\n\nInitial content.")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Push main
        repo.remote("origin").push("HEAD:main")

        # Create idea directory with completed plan
        idea_name = "feedback-test"
        idea_dir = os.path.join(tmpdir, idea_name)
        os.makedirs(idea_dir)

        with open(os.path.join(idea_dir, f"{idea_name}-idea.md"), "w") as f:
            f.write("# Feedback Test Idea\n\nTesting feedback handling.")

        with open(os.path.join(idea_dir, f"{idea_name}-discussion.md"), "w") as f:
            f.write("# Discussion\n\nNo discussion needed.")

        with open(os.path.join(idea_dir, f"{idea_name}-spec.md"), "w") as f:
            f.write("# Specification\n\nSimple spec.")

        plan_path = os.path.join(idea_dir, f"{idea_name}-plan.md")
        with open(plan_path, "w") as f:
            f.write(COMPLETED_PLAN_CONTENT)

        # Add and commit idea files
        for filename in os.listdir(idea_dir):
            filepath = os.path.join(idea_dir, filename)
            rel_path = os.path.relpath(filepath, tmpdir)
            repo.index.add([rel_path])
        repo.index.commit("Add feedback test idea files")

        # Create feature branch with a change
        feature_branch = "feature/test-change"
        repo.create_head(feature_branch)
        repo.heads[feature_branch].checkout()

        # Make a change on the feature branch
        with open(readme, "w") as f:
            f.write(f"# {repo_name}\n\nModified content for PR.")
        repo.index.add(["README.md"])
        repo.index.commit("Update README")

        # Push feature branch
        repo.remote("origin").push(f"{feature_branch}:{feature_branch}")

        # Create a PR using gh CLI
        pr_result = subprocess.run(
            ["gh", "pr", "create",
             "--title", "Test PR for feedback",
             "--body", "This PR is for testing feedback detection.",
             "--head", feature_branch,
             "--base", "main",
             "--repo", repo_full_name],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        if pr_result.returncode != 0:
            raise RuntimeError(f"Could not create PR: {pr_result.stderr}")

        # Parse PR number from URL
        pr_url = pr_result.stdout.strip()
        pr_number = int(pr_url.split("/")[-1])

        # Add a review comment to the PR using gh api
        comment_result = subprocess.run(
            ["gh", "api",
             f"repos/{repo_full_name}/pulls/{pr_number}/comments",
             "-X", "POST",
             "-f", "body=Please fix this typo",
             "-f", "commit_id=" + repo.head.commit.hexsha,
             "-f", "path=README.md",
             "-F", "line=2"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        # Also add a regular issue comment (simpler)
        issue_comment_result = subprocess.run(
            ["gh", "pr", "comment", str(pr_number),
             "--body", "This needs more work",
             "--repo", repo_full_name],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )

        yield {
            "tmpdir": tmpdir,
            "repo_full_name": repo_full_name,
            "idea_dir": idea_dir,
            "idea_name": idea_name,
            "plan_path": plan_path,
            "repo": repo,
            "pr_number": pr_number,
            "pr_url": pr_url,
            "feature_branch": feature_branch
        }

    finally:
        delete_github_repo(repo_full_name)
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.integration_gh
class TestFeedbackDetectionIntegration:
    """Test feedback detection with real GitHub PRs."""

    def test_fetch_pr_comments_returns_comments(self, github_test_repo_with_pr_and_comments):
        """Should fetch review comments from a real PR."""
        from i2code.implement.implement import fetch_pr_comments

        pr_number = github_test_repo_with_pr_and_comments["pr_number"]
        tmpdir = github_test_repo_with_pr_and_comments["tmpdir"]

        # Change to repo directory so gh uses correct context
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            comments = fetch_pr_comments(pr_number)
        finally:
            os.chdir(original_cwd)

        # Should have at least one review comment
        assert len(comments) >= 1, \
            f"Expected at least 1 comment, got {len(comments)}"

    def test_get_new_feedback_filters_processed(self, github_test_repo_with_pr_and_comments):
        """Should filter out already-processed feedback."""
        from i2code.implement.implement import fetch_pr_comments, get_new_feedback

        pr_number = github_test_repo_with_pr_and_comments["pr_number"]
        tmpdir = github_test_repo_with_pr_and_comments["tmpdir"]

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            comments = fetch_pr_comments(pr_number)
        finally:
            os.chdir(original_cwd)

        assert comments, "Expected comments on PR but found none"

        # Mark all comments as processed
        processed_ids = [c["id"] for c in comments]

        # Get new feedback (should be empty)
        new_feedback = get_new_feedback(comments, processed_ids)

        assert len(new_feedback) == 0, \
            f"Expected 0 new feedback after marking all processed, got {len(new_feedback)}"

    def test_state_file_tracks_processed_comments(self, github_test_repo_with_pr_and_comments):
        """State file should be able to track processed comment IDs."""
        from i2code.implement.implement import (
            init_or_load_state, save_state, fetch_pr_comments, get_new_feedback
        )

        idea_dir = github_test_repo_with_pr_and_comments["idea_dir"]
        idea_name = github_test_repo_with_pr_and_comments["idea_name"]
        pr_number = github_test_repo_with_pr_and_comments["pr_number"]
        tmpdir = github_test_repo_with_pr_and_comments["tmpdir"]

        # Initialize state
        state = init_or_load_state(idea_dir, idea_name)
        assert state["processed_comment_ids"] == [], \
            "New state should have empty processed_comment_ids"

        # Fetch comments
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            comments = fetch_pr_comments(pr_number)
        finally:
            os.chdir(original_cwd)

        assert comments, "Expected comments on PR but found none"

        # Get new feedback (all should be new)
        new_feedback = get_new_feedback(comments, state["processed_comment_ids"])
        assert len(new_feedback) == len(comments), \
            "All comments should be new initially"

        # Process feedback by adding IDs to state
        for comment in new_feedback:
            state["processed_comment_ids"].append(comment["id"])

        # Save state
        save_state(idea_dir, idea_name, state)

        # Reload state
        reloaded_state = init_or_load_state(idea_dir, idea_name)

        # Verify processed IDs were persisted
        assert len(reloaded_state["processed_comment_ids"]) == len(comments), \
            "Processed comment IDs should be persisted"

        # Get new feedback again (should be empty now)
        new_feedback_after = get_new_feedback(comments, reloaded_state["processed_comment_ids"])
        assert len(new_feedback_after) == 0, \
            "No new feedback should exist after marking all as processed"


@pytest.mark.integration_gh
class TestPRCompletionIntegration:
    """Test PR completion detection with real GitHub PRs."""

    def test_get_pr_state_returns_valid_state(self, github_test_repo_with_pr_and_comments):
        """Should return valid state for a real PR."""
        from i2code.implement.implement import get_pr_state

        pr_number = github_test_repo_with_pr_and_comments["pr_number"]
        tmpdir = github_test_repo_with_pr_and_comments["tmpdir"]

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            state = get_pr_state(pr_number)
        finally:
            os.chdir(original_cwd)

        assert state == "OPEN", f"Expected OPEN state, got {state}"

    def test_is_pr_complete_returns_false_for_open_pr(self, github_test_repo_with_pr_and_comments):
        """Should return False for an open PR."""
        from i2code.implement.implement import get_pr_state, is_pr_complete

        pr_number = github_test_repo_with_pr_and_comments["pr_number"]
        tmpdir = github_test_repo_with_pr_and_comments["tmpdir"]

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            state = get_pr_state(pr_number)
        finally:
            os.chdir(original_cwd)

        assert is_pr_complete(state) is False
