"""Integration test: implement exits with error when all tasks are complete.

Runs the real i2code implement command against a test git repo where all
plan tasks are marked [x] complete. Verifies that the command exits with
a non-zero status, stderr contains "all tasks", and no branches,
worktrees, or Claude invocations occur.
"""

import os
import stat

import pytest
from git import Repo

from conftest import run_script, write_plan_file


@pytest.mark.integration
class TestAllTasksCompleteExitsWithError:
    """i2code implement should exit with error when all plan tasks are complete."""

    def test_exits_with_error_and_no_side_effects(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        idea_name = "test-feature"
        idea_dir = os.path.join(tmpdir, idea_name)
        os.makedirs(idea_dir)

        # Create required idea files
        with open(os.path.join(idea_dir, f"{idea_name}-idea.md"), "w") as f:
            f.write("# Test Feature Idea\n\nA test idea.")

        with open(os.path.join(idea_dir, f"{idea_name}-spec.md"), "w") as f:
            f.write("# Specification\n\nTest spec.")

        # Create plan file with ALL tasks marked complete
        write_plan_file(idea_dir, idea_name, [
            (1, 1, "First task", True),
            (1, 2, "Second task", True),
        ])

        # Commit all idea files
        for filename in os.listdir(idea_dir):
            rel_path = os.path.join(idea_name, filename)
            repo.index.add([rel_path])
        repo.index.commit("Add idea files with all tasks complete")

        # Create a mock Claude script that writes a sentinel file when invoked
        sentinel_path = os.path.join(tmpdir, "claude-was-invoked.sentinel")
        mock_claude_script = os.path.join(tmpdir, "mock-claude.sh")
        with open(mock_claude_script, "w") as f:
            f.write(f"""#!/bin/bash
touch "{sentinel_path}"
""")
        os.chmod(mock_claude_script,
                 os.stat(mock_claude_script).st_mode | stat.S_IEXEC)

        # Run i2code implement
        result = run_script(idea_dir, cwd=tmpdir, mock_claude=mock_claude_script)

        # (a) Non-zero returncode
        assert result.returncode != 0, (
            f"Expected non-zero exit code, got {result.returncode}. "
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # (b) stderr contains "all tasks"
        assert "all tasks" in result.stderr.lower(), (
            f"Expected stderr to contain 'all tasks', got: {result.stderr}"
        )

        # (c) No idea/* branches created beyond master
        repo = Repo(tmpdir)
        branch_names = [b.name for b in repo.branches]
        idea_branches = [b for b in branch_names if b.startswith("idea/")]
        assert len(idea_branches) == 0, (
            f"Expected no idea/* branches, found: {idea_branches}"
        )

        # (d) No worktree directory created
        repo_name = os.path.basename(tmpdir)
        parent_dir = os.path.dirname(tmpdir)
        expected_worktree = os.path.join(
            parent_dir, f"{repo_name}-wt-{idea_name}"
        )
        assert not os.path.isdir(expected_worktree), (
            f"Worktree directory should not exist: {expected_worktree}"
        )

        # (e) Mock Claude script was never invoked (sentinel file absent)
        assert not os.path.exists(sentinel_path), (
            "Sentinel file exists — mock Claude was invoked when it should not have been"
        )
