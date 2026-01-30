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


@pytest.mark.unit
class TestPushOperations:
    """Test push operations to slice branch."""

    def test_build_push_command(self):
        """Should build correct git push command."""
        from implement_with_worktree import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup")

        assert cmd == ["git", "push", "origin", "idea/my-feature/01-setup"]

    def test_build_push_command_with_force(self):
        """Should include --force-with-lease when requested."""
        from implement_with_worktree import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup", force=True)

        assert "--force-with-lease" in cmd


@pytest.mark.unit
class TestPushToSliceBranch:
    """Test push_to_slice_branch function."""

    def test_push_returns_false_if_pr_not_draft(self, mocker):
        """Should not push and return False if PR is not in Draft state."""
        from implement_with_worktree import push_to_slice_branch

        # Mock is_pr_draft to return False (PR is not draft)
        mocker.patch('implement_with_worktree.is_pr_draft', return_value=False)
        # Mock subprocess.run to track if it was called
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')

        result = push_to_slice_branch(
            slice_branch="idea/my-feature/01-setup",
            pr_number=123
        )

        assert result is False
        mock_run.assert_not_called()

    def test_push_succeeds_when_pr_is_draft(self, mocker):
        """Should push and return True when PR is in Draft state."""
        from implement_with_worktree import push_to_slice_branch

        # Mock is_pr_draft to return True
        mocker.patch('implement_with_worktree.is_pr_draft', return_value=True)
        # Mock subprocess.run to simulate successful push
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0

        result = push_to_slice_branch(
            slice_branch="idea/my-feature/01-setup",
            pr_number=123
        )

        assert result is True
        mock_run.assert_called_once()

    def test_push_returns_false_on_push_failure(self, mocker):
        """Should return False when git push fails."""
        from implement_with_worktree import push_to_slice_branch

        # Mock is_pr_draft to return True
        mocker.patch('implement_with_worktree.is_pr_draft', return_value=True)
        # Mock subprocess.run to simulate failed push
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 1

        result = push_to_slice_branch(
            slice_branch="idea/my-feature/01-setup",
            pr_number=123
        )

        assert result is False
