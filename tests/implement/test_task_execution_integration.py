"""Integration tests for task execution in implement-with-worktree.

These tests use real git/GitHub but mock Claude invocation.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import uuid
from dataclasses import dataclass

import pytest
from git import Repo

from conftest import SCRIPT_CMD, create_github_repo, delete_github_repo
from i2code.plan_domain.parser import parse as parse_plan
from i2code.plan_domain.task import Task


@dataclass
class GitHubTestRepo:
    tmpdir: str
    repo_full_name: str
    idea_dir: str
    idea_name: str
    plan_path: str
    worktree_path: str
    worktree_plan_path: str
    repo: Repo


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
    """Test that script detects and executes tasks with mock Claude."""

    def test_mock_claude_detects_and_completes_tasks(self, github_test_repo_with_simple_plan):
        """End-to-end: setup, execute tasks, verify PR, add task, verify PR reuse."""
        self.repo = github_test_repo_with_simple_plan
        self.mock_script = create_mock_claude_script_that_marks_tasks_complete(
            self.repo.tmpdir, self.repo.idea_name
        )

        self._assert_setup_only_creates_no_pr()

        result = self._run_implement()

        self._assert_tasks_committed_in_order(["Task 1.1", "Task 1.2", "Task 1.3"])
        self._assert_all_tasks_completed(expected_count=3)
        assert "All tasks completed!" in result.stdout

        pr = self._assert_draft_pr_created()
        self._assert_pr_is_open_and_not_complete(pr["number"])

        self._add_task_to_plan(after_task=3)

        result2 = self._run_implement()
        self._assert_all_tasks_completed(expected_count=4)
        assert "All tasks completed!" in result2.stdout

        self._assert_pr_reused(pr["number"])

        head_before = self._get_head_sha()
        result3 = self._run_implement()
        assert "All tasks completed!" in result3.stdout
        assert self._get_head_sha() == head_before, \
            "Expected no new commits when all tasks complete"

        self._add_pr_comments(pr["number"])
        self._assert_fetch_pr_comments(pr["number"])
        self._assert_new_feedback_filtering(pr["number"])
        self._assert_state_tracks_processed_comments(pr["number"])

    def _get_head_sha(self):
        return Repo(self.repo.worktree_path).head.commit.hexsha

    def _assert_setup_only_creates_no_pr(self):
        subprocess.run(
            SCRIPT_CMD + [self.repo.idea_dir, "--setup-only"],
            capture_output=True, text=True, cwd=self.repo.tmpdir, timeout=120
        )
        assert len(self._get_open_prs()) == 0, \
            "setup-only should not create a PR"

    def _run_implement(self):
        result = subprocess.run(
            SCRIPT_CMD + [self.repo.idea_dir, "--mock-claude", self.mock_script,
                          "--skip-ci-wait"],
            capture_output=True, text=True, cwd=self.repo.tmpdir, timeout=120
        )
        assert result.returncode == 0, \
            f"Script failed with code {result.returncode}. stderr: {result.stderr}"
        return result

    def _assert_tasks_committed_in_order(self, expected_tasks):
        worktree_repo = Repo(self.repo.worktree_path)
        commits = list(worktree_repo.iter_commits())
        task_commits = [c for c in commits if c.message.startswith("Complete task:")]
        assert len(task_commits) == len(expected_tasks), \
            f"Expected {len(expected_tasks)} task commits, got {len(task_commits)}: " \
            f"{[c.message.strip() for c in task_commits]}"
        task_commits.reverse()  # newest-first -> chronological
        for commit, expected in zip(task_commits, expected_tasks):
            assert expected in commit.message

    def _assert_all_tasks_completed(self, expected_count):
        with open(self.repo.worktree_plan_path, 'r') as f:
            plan = parse_plan(f.read())
        assert plan.get_next_task() is None, "Expected all tasks completed"
        for task_num in range(1, expected_count + 1):
            assert plan.is_task_completed(thread=1, task=task_num), \
                f"Task 1.{task_num} should be completed"

    def _assert_draft_pr_created(self):
        pr_list = self._get_open_prs()
        assert len(pr_list) == 1, f"Expected 1 PR, got {len(pr_list)}"
        pr = pr_list[0]
        assert pr["isDraft"] is True
        assert self.repo.idea_name in pr["title"]
        return pr

    def _assert_pr_is_open_and_not_complete(self, pr_number):
        from i2code.implement.implement import get_pr_state, is_pr_complete
        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo.tmpdir)
            state = get_pr_state(pr_number)
        finally:
            os.chdir(original_cwd)
        assert state == "OPEN", f"Expected OPEN state, got {state}"
        assert is_pr_complete(state) is False

    def _assert_pr_reused(self, original_pr_number):
        pr_list = self._get_open_prs()
        assert len(pr_list) == 1, f"Expected PR reuse, got {len(pr_list)} PRs"
        assert pr_list[0]["number"] == original_pr_number

    def _add_task_to_plan(self, after_task):
        with open(self.repo.worktree_plan_path, 'r') as f:
            plan = parse_plan(f.read())
        plan.insert_task_after(thread=1, after_task=after_task, task=Task.create(
            title="Fourth task",
            task_type="code",
            entrypoint="src/main.py",
            observable="Fourth thing works",
            evidence="pytest",
            steps=["Do something fourth"],
        ))
        with open(self.repo.worktree_plan_path, 'w') as f:
            f.write(plan.to_text())

    def _add_pr_comments(self, pr_number):
        worktree_repo = Repo(self.repo.worktree_path)
        head_sha = worktree_repo.head.commit.hexsha

        # The PR diff contains the plan file — use that path for the review comment
        plan_rel_path = f"{self.repo.idea_name}/{self.repo.idea_name}-plan.md"

        # Add a file-level review comment (no line resolution needed)
        result = subprocess.run(
            ["gh", "api",
             f"repos/{self.repo.repo_full_name}/pulls/{pr_number}/comments",
             "-X", "POST",
             "-f", "body=Please fix this typo",
             "-f", f"commit_id={head_sha}",
             "-f", f"path={plan_rel_path}",
             "-f", "subject_type=file"],
            capture_output=True, text=True, cwd=self.repo.tmpdir
        )
        assert result.returncode == 0, \
            f"Failed to add review comment: {result.stderr}"

    def _assert_fetch_pr_comments(self, pr_number):
        from i2code.implement.implement import fetch_pr_comments

        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo.tmpdir)
            comments = fetch_pr_comments(pr_number)
        finally:
            os.chdir(original_cwd)

        assert len(comments) >= 1, \
            f"Expected at least 1 comment, got {len(comments)}"

    def _assert_new_feedback_filtering(self, pr_number):
        from i2code.implement.implement import fetch_pr_comments, get_new_feedback

        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo.tmpdir)
            comments = fetch_pr_comments(pr_number)
        finally:
            os.chdir(original_cwd)

        assert comments, "Expected comments on PR but found none"

        processed_ids = [c["id"] for c in comments]
        new_feedback = get_new_feedback(comments, processed_ids)

        assert len(new_feedback) == 0, \
            f"Expected 0 new feedback after marking all processed, got {len(new_feedback)}"

    def _assert_state_tracks_processed_comments(self, pr_number):
        from i2code.implement.implement import (
            init_or_load_state, save_state, fetch_pr_comments, get_new_feedback
        )

        state = init_or_load_state(self.repo.idea_dir, self.repo.idea_name)
        assert state["processed_comment_ids"] == [], \
            "New state should have empty processed_comment_ids"

        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo.tmpdir)
            comments = fetch_pr_comments(pr_number)
        finally:
            os.chdir(original_cwd)

        assert comments, "Expected comments on PR but found none"

        new_feedback = get_new_feedback(comments, state["processed_comment_ids"])
        assert len(new_feedback) == len(comments), \
            "All comments should be new initially"

        for comment in new_feedback:
            state["processed_comment_ids"].append(comment["id"])

        save_state(self.repo.idea_dir, self.repo.idea_name, state)

        reloaded_state = init_or_load_state(self.repo.idea_dir, self.repo.idea_name)
        assert len(reloaded_state["processed_comment_ids"]) == len(comments), \
            "Processed comment IDs should be persisted"

        new_feedback_after = get_new_feedback(
            comments, reloaded_state["processed_comment_ids"]
        )
        assert len(new_feedback_after) == 0, \
            "No new feedback should exist after marking all as processed"

    def _get_open_prs(self):
        import json
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", self.repo.repo_full_name,
             "--json", "number,title,isDraft", "--state", "open"],
            capture_output=True, text=True
        )
        return json.loads(result.stdout) if result.returncode == 0 else []


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

        tmpdir_name = os.path.basename(tmpdir)
        worktree_path = os.path.join(
            os.path.dirname(tmpdir), f"{tmpdir_name}-wt-{idea_name}"
        )
        yield GitHubTestRepo(
            tmpdir=tmpdir,
            repo_full_name=repo_full_name,
            idea_dir=idea_dir,
            idea_name=idea_name,
            plan_path=plan_path,
            worktree_path=worktree_path,
            worktree_plan_path=os.path.join(
                worktree_path, idea_name, f"{idea_name}-plan.md"
            ),
            repo=repo,
        )

    finally:
        delete_github_repo(repo_full_name)
        if 'tmpdir' in locals():
            shutil.rmtree(tmpdir, ignore_errors=True)

