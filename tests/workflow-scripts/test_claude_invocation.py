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


@pytest.mark.unit
class TestFeedbackTemplate:
    """Test wt-handle-feedback.md prompt template."""

    def test_feedback_template_exists(self):
        """Template file should exist in prompt-templates directory."""
        template_path = os.path.join(
            os.path.dirname(__file__),
            '../../prompt-templates/wt-handle-feedback.md'
        )
        assert os.path.exists(template_path), \
            f"Template not found at {template_path}"

    def test_feedback_template_has_pr_url_placeholder(self):
        """Template should have placeholder for PR URL."""
        template_path = os.path.join(
            os.path.dirname(__file__),
            '../../prompt-templates/wt-handle-feedback.md'
        )
        with open(template_path, 'r') as f:
            content = f.read()
        assert 'PR_URL' in content, \
            "Template should have PR_URL placeholder"

    def test_feedback_template_has_feedback_content_placeholder(self):
        """Template should have placeholder for feedback content."""
        template_path = os.path.join(
            os.path.dirname(__file__),
            '../../prompt-templates/wt-handle-feedback.md'
        )
        with open(template_path, 'r') as f:
            content = f.read()
        assert 'FEEDBACK_CONTENT' in content, \
            "Template should have FEEDBACK_CONTENT placeholder"

    def test_feedback_template_has_feedback_type_placeholder(self):
        """Template should have placeholder for feedback type."""
        template_path = os.path.join(
            os.path.dirname(__file__),
            '../../prompt-templates/wt-handle-feedback.md'
        )
        with open(template_path, 'r') as f:
            content = f.read()
        assert 'FEEDBACK_TYPE' in content, \
            "Template should have FEEDBACK_TYPE placeholder"


@pytest.mark.unit
class TestFeedbackDetection:
    """Test detection of new PR comments and reviews."""

    def test_fetch_pr_comments_returns_list(self, mocker):
        """Should return list of comments from GitHub API."""
        from implement_with_worktree import fetch_pr_comments

        # Mock subprocess.run to return sample comments
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"id": 1, "body": "Fix this"}, {"id": 2, "body": "And this"}]'

        comments = fetch_pr_comments(123)

        assert len(comments) == 2
        assert comments[0]["id"] == 1
        assert comments[1]["id"] == 2

    def test_fetch_pr_reviews_returns_list(self, mocker):
        """Should return list of reviews from GitHub API."""
        from implement_with_worktree import fetch_pr_reviews

        # Mock subprocess.run to return sample reviews
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '[{"id": 100, "state": "CHANGES_REQUESTED"}]'

        reviews = fetch_pr_reviews(123)

        assert len(reviews) == 1
        assert reviews[0]["id"] == 100

    def test_get_new_comments_filters_processed(self):
        """Should return only comments not in processed_comment_ids."""
        from implement_with_worktree import get_new_feedback

        all_comments = [
            {"id": 1, "body": "Already processed"},
            {"id": 2, "body": "New comment"},
            {"id": 3, "body": "Another new one"}
        ]
        processed_ids = [1]

        new_comments = get_new_feedback(all_comments, processed_ids)

        assert len(new_comments) == 2
        assert all(c["id"] not in processed_ids for c in new_comments)

    def test_get_new_comments_returns_empty_if_all_processed(self):
        """Should return empty list if all comments are processed."""
        from implement_with_worktree import get_new_feedback

        all_comments = [
            {"id": 1, "body": "Processed"},
            {"id": 2, "body": "Also processed"}
        ]
        processed_ids = [1, 2]

        new_comments = get_new_feedback(all_comments, processed_ids)

        assert len(new_comments) == 0


@pytest.mark.unit
class TestStatusCheckDetection:
    """Test detection of failed status checks."""

    def test_fetch_failed_checks_returns_failures(self, mocker):
        """Should return list of failed checks."""
        from implement_with_worktree import fetch_failed_checks

        # Mock subprocess.run to return check results with failures
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'build\tfail\t1234\ntest\tpass\t5678\nlint\tfail\t9012'

        failed = fetch_failed_checks(123)

        assert len(failed) == 2
        assert failed[0]["name"] == "build"
        assert failed[1]["name"] == "lint"

    def test_fetch_failed_checks_returns_empty_if_all_pass(self, mocker):
        """Should return empty list if all checks pass."""
        from implement_with_worktree import fetch_failed_checks

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'build\tpass\t1234\ntest\tpass\t5678'

        failed = fetch_failed_checks(123)

        assert len(failed) == 0

    def test_fetch_failed_checks_handles_no_checks(self, mocker):
        """Should return empty list if no checks exist."""
        from implement_with_worktree import fetch_failed_checks

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ''

        failed = fetch_failed_checks(123)

        assert len(failed) == 0


@pytest.mark.unit
class TestFeedbackHandling:
    """Test handling feedback with Claude."""

    def test_build_feedback_command_uses_feedback_template(self):
        """Should use wt-handle-feedback.md template."""
        from implement_with_worktree import build_feedback_command

        cmd = build_feedback_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_type="review_comment",
            feedback_content="Please fix the typo"
        )

        assert "wt-handle-feedback.md" in " ".join(cmd)

    def test_build_feedback_command_includes_pr_url(self):
        """Should include PR URL in command."""
        from implement_with_worktree import build_feedback_command

        cmd = build_feedback_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_type="review_comment",
            feedback_content="Please fix the typo"
        )

        cmd_str = " ".join(cmd)
        assert "https://github.com/owner/repo/pull/123" in cmd_str

    def test_build_feedback_command_includes_feedback_content(self):
        """Should include feedback content in command."""
        from implement_with_worktree import build_feedback_command

        cmd = build_feedback_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_type="review_comment",
            feedback_content="Please fix the typo"
        )

        cmd_str = " ".join(cmd)
        assert "Please fix the typo" in cmd_str
