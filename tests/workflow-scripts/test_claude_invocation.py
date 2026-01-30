"""Tests for Claude Code invocation in implement-with-worktree."""

import os
import sys
import pytest

# Add workflow-scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../workflow-scripts'))


@pytest.mark.unit
class TestClaudeCommandConstruction:
    """Test construction of Claude command (without executing)."""

    def test_build_claude_command_includes_prompt_file(self):
        """Command should include the prompt template file."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            prompt_template="implement-plan.md"
        )

        assert "implement-plan.md" in " ".join(cmd)

    def test_build_claude_command_includes_idea_directory(self):
        """Command should reference the idea directory."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            prompt_template="implement-plan.md"
        )

        # The command should include a way to pass the idea directory
        cmd_str = " ".join(cmd)
        assert "docs/features/my-feature" in cmd_str

    def test_build_claude_command_includes_task(self):
        """Command should include the current task description."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            prompt_template="implement-plan.md"
        )

        cmd_str = " ".join(cmd)
        assert "Task 1.1" in cmd_str or "Create config file" in cmd_str

    def test_build_claude_command_returns_list(self):
        """Command should be returned as a list for subprocess."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            prompt_template="implement-plan.md"
        )

        assert isinstance(cmd, list)
        assert len(cmd) > 0
        assert cmd[0] == "claude"


@pytest.mark.unit
class TestClaudeInvocationResult:
    """Test handling of Claude invocation results."""

    def test_check_claude_success_with_zero_exit(self):
        """Should return True for exit code 0."""
        from implement_with_worktree import check_claude_success

        assert check_claude_success(exit_code=0, head_before="abc123", head_after="def456") is True

    def test_check_claude_success_fails_with_nonzero_exit(self):
        """Should return False for non-zero exit code."""
        from implement_with_worktree import check_claude_success

        assert check_claude_success(exit_code=1, head_before="abc123", head_after="def456") is False

    def test_check_claude_success_fails_if_head_unchanged(self):
        """Should return False if HEAD didn't advance (no commit made)."""
        from implement_with_worktree import check_claude_success

        assert check_claude_success(exit_code=0, head_before="abc123", head_after="abc123") is False

    def test_check_claude_success_requires_both_conditions(self):
        """Success requires exit code 0 AND HEAD advancement."""
        from implement_with_worktree import check_claude_success

        # Exit 0 but no commit
        assert check_claude_success(exit_code=0, head_before="abc", head_after="abc") is False
        # Commit made but exit failed
        assert check_claude_success(exit_code=1, head_before="abc", head_after="def") is False
        # Both conditions met
        assert check_claude_success(exit_code=0, head_before="abc", head_after="def") is True
