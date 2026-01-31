"""Tests for Claude Code invocation in implement-with-worktree."""

import os
import sys
import pytest

# Add workflow-scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../workflow-scripts'))


import tempfile
from git import Repo


@pytest.mark.unit
class TestWorktreeIdeaDirectory:
    """Test that Claude is invoked with worktree idea directory, not main repo."""

    def test_get_worktree_idea_directory(self):
        """Should compute the idea directory path within the worktree."""
        from implement_with_worktree import get_worktree_idea_directory

        worktree_path = "/tmp/my-repo-wt-my-feature"
        main_repo_idea_dir = "/home/user/my-repo/docs/ideas/my-feature"
        main_repo_root = "/home/user/my-repo"

        result = get_worktree_idea_directory(
            worktree_path=worktree_path,
            main_repo_idea_dir=main_repo_idea_dir,
            main_repo_root=main_repo_root
        )

        assert result == "/tmp/my-repo-wt-my-feature/docs/ideas/my-feature"

    def test_claude_prompt_uses_worktree_idea_directory(self, mocker):
        """Claude command prompt should reference worktree idea dir, not main repo."""
        from implement_with_worktree import build_claude_command, get_worktree_idea_directory

        # Simulate the paths
        main_repo_root = "/home/user/my-repo"
        main_repo_idea_dir = "/home/user/my-repo/kafka-security-poc"
        worktree_path = "/tmp/my-repo-wt-kafka-security-poc"

        # Get the worktree idea directory (what main() should pass to build_claude_command)
        worktree_idea_dir = get_worktree_idea_directory(
            worktree_path=worktree_path,
            main_repo_idea_dir=main_repo_idea_dir,
            main_repo_root=main_repo_root
        )

        # Build command with worktree idea dir
        cmd = build_claude_command(
            idea_directory=worktree_idea_dir,
            task_description="Task 1.1: Create project"
        )

        # The prompt should reference the worktree path, not main repo
        prompt = cmd[1]
        assert worktree_path in prompt, \
            f"Prompt should use worktree path. Got: {prompt}"
        assert main_repo_root not in prompt, \
            f"Prompt should NOT use main repo path. Got: {prompt}"


@pytest.mark.unit
class TestClaudeCommandConstruction:
    """Test construction of Claude command (without executing)."""

    def test_build_claude_command_basic(self):
        """Command should be ['claude', prompt] for interactive mode."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file"
        )

        assert cmd[0] == "claude"
        assert len(cmd) == 2

    def test_build_claude_command_includes_idea_directory(self):
        """Command should reference the idea directory."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file"
        )

        # The command should include a way to pass the idea directory
        cmd_str = " ".join(cmd)
        assert "docs/features/my-feature" in cmd_str

    def test_build_claude_command_includes_task(self):
        """Command should include the current task description."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file"
        )

        cmd_str = " ".join(cmd)
        assert "Task 1.1" in cmd_str or "Create config file" in cmd_str

    def test_build_claude_command_returns_list(self):
        """Command should be returned as a list for subprocess."""
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file"
        )

        assert isinstance(cmd, list)
        assert len(cmd) > 0
        assert cmd[0] == "claude"

    def test_build_claude_command_is_interactive(self):
        """Command should invoke Claude in interactive mode, not print mode.

        The -p/--print flag makes Claude non-interactive (print and exit).
        For interactive use, the prompt should be a positional argument.
        """
        from implement_with_worktree import build_claude_command

        cmd = build_claude_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file"
        )

        # Should NOT use -p or --print flags (those make it non-interactive)
        assert "-p" not in cmd, "Command should not use -p flag for interactive mode"
        assert "--print" not in cmd, "Command should not use --print flag for interactive mode"

        # Command should be: ["claude", prompt]
        # where prompt is the second element (positional argument)
        assert len(cmd) == 2, f"Expected ['claude', prompt], got {cmd}"
        assert cmd[0] == "claude"
        assert "Task 1.1" in cmd[1], "Prompt should contain the task description"


@pytest.mark.unit
class TestRunClaudeWithOutputCapture:
    """Test running Claude with output capture and real-time display."""

    def test_run_claude_captures_stdout(self, mocker):
        """Should capture stdout from Claude process."""
        from implement_with_worktree import run_claude_with_output_capture

        # Mock Popen with pipe-like objects
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        # read1() returns data then empty bytes (EOF) to stop the reader thread
        mock_stdout.read1.side_effect = [b"line1\n", b"line2\n", b""]
        mock_stderr.read1.side_effect = [b""]  # No stderr

        mock_process = mocker.MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.returncode = 0
        mocker.patch('implement_with_worktree.subprocess.Popen', return_value=mock_process)

        result = run_claude_with_output_capture(["claude", "test"], cwd="/tmp")

        assert "line1" in result.stdout
        assert "line2" in result.stdout
        assert result.returncode == 0

    def test_run_claude_captures_stderr(self, mocker):
        """Should capture stderr from Claude process."""
        from implement_with_worktree import run_claude_with_output_capture

        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        # read1() returns data then empty bytes (EOF)
        mock_stdout.read1.side_effect = [b""]  # No stdout
        mock_stderr.read1.side_effect = [b"error1\n", b""]

        mock_process = mocker.MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.returncode = 1
        mocker.patch('implement_with_worktree.subprocess.Popen', return_value=mock_process)

        result = run_claude_with_output_capture(["claude", "test"], cwd="/tmp")

        assert "error1" in result.stderr
        assert result.returncode == 1


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


@pytest.mark.unit
class TestMainBranchAdvancement:
    """Test detection of main branch advancement."""

    def test_has_main_advanced_returns_false_if_same(self):
        """Should return False when main branch HEAD hasn't changed."""
        from implement_with_worktree import has_main_advanced

        assert has_main_advanced(
            original_head="abc123",
            current_head="abc123"
        ) is False

    def test_has_main_advanced_returns_true_if_different(self):
        """Should return True when main branch HEAD has changed."""
        from implement_with_worktree import has_main_advanced

        assert has_main_advanced(
            original_head="abc123",
            current_head="def456"
        ) is True

    def test_get_remote_main_head_returns_sha(self, mocker):
        """Should return the SHA of origin/main."""
        from implement_with_worktree import get_remote_main_head

        # Mock subprocess.run to simulate git fetch and ls-remote
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "abc123def456\trefs/heads/main\n"

        sha = get_remote_main_head()

        assert sha == "abc123def456"
        # Called twice: once for fetch, once for ls-remote
        assert mock_run.call_count == 2

    def test_get_remote_main_head_fetches_first(self, mocker):
        """Should fetch from origin before getting HEAD."""
        from implement_with_worktree import get_remote_main_head

        # Track all subprocess calls
        calls = []
        def mock_run(*args, **kwargs):
            calls.append(args[0])
            result = mocker.MagicMock()
            result.returncode = 0
            if "fetch" in args[0]:
                result.stdout = ""
            else:
                result.stdout = "abc123\trefs/heads/main\n"
            return result

        mocker.patch('implement_with_worktree.subprocess.run', side_effect=mock_run)

        get_remote_main_head()

        # Verify fetch was called before ls-remote
        assert len(calls) == 2
        assert "fetch" in calls[0]
        assert "ls-remote" in calls[1]


@pytest.mark.unit
class TestRebaseOperations:
    """Test rebase operations for main branch advancement."""

    def test_rebase_integration_branch_success(self, mocker):
        """Should return True when rebase succeeds."""
        from implement_with_worktree import rebase_integration_branch

        # Mock subprocess.run to simulate successful rebase
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0

        result = rebase_integration_branch("idea/my-feature/integration")

        assert result is True

    def test_rebase_integration_branch_returns_false_on_conflict(self, mocker):
        """Should return False when rebase has conflicts."""
        from implement_with_worktree import rebase_integration_branch

        # Mock subprocess.run to simulate rebase conflict
        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 1

        result = rebase_integration_branch("idea/my-feature/integration")

        assert result is False

    def test_rebase_integration_branch_aborts_on_conflict(self, mocker):
        """Should abort rebase when conflicts occur."""
        from implement_with_worktree import rebase_integration_branch

        calls = []
        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            result = mocker.MagicMock()
            # First call (rebase) fails, second call (abort) succeeds
            if "rebase" in cmd and "--abort" not in cmd:
                result.returncode = 1
            else:
                result.returncode = 0
            return result

        mocker.patch('implement_with_worktree.subprocess.run', side_effect=mock_run)

        rebase_integration_branch("idea/my-feature/integration")

        # Verify abort was called after failed rebase
        abort_calls = [c for c in calls if "--abort" in c]
        assert len(abort_calls) == 1

    def test_update_slice_after_rebase_force_pushes(self, mocker):
        """Should force push slice branch after rebase."""
        from implement_with_worktree import update_slice_after_rebase

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0

        update_slice_after_rebase("idea/my-feature/01-setup")

        # Verify force-with-lease was used
        call_args = mock_run.call_args[0][0]
        assert "--force-with-lease" in call_args


@pytest.mark.unit
class TestRebaseConflictHandling:
    """Test handling of rebase conflicts."""

    def test_handle_rebase_conflict_returns_message(self):
        """Should return a message explaining the conflict."""
        from implement_with_worktree import get_rebase_conflict_message

        message = get_rebase_conflict_message("idea/my-feature/integration")

        assert "conflict" in message.lower()
        assert "idea/my-feature/integration" in message

    def test_handle_rebase_conflict_includes_instructions(self):
        """Should include instructions for manual resolution."""
        from implement_with_worktree import get_rebase_conflict_message

        message = get_rebase_conflict_message("idea/my-feature/integration")

        # Should tell user what to do
        assert "manual" in message.lower() or "resolve" in message.lower()


@pytest.mark.unit
class TestPRReadyForReview:
    """Test marking PR as ready for review."""

    def test_mark_pr_ready_calls_gh_pr_ready(self, mocker):
        """Should call gh pr ready with PR number."""
        from implement_with_worktree import mark_pr_ready

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0

        result = mark_pr_ready(123)

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "pr" in call_args
        assert "ready" in call_args
        assert "123" in call_args

    def test_mark_pr_ready_returns_false_on_failure(self, mocker):
        """Should return False when gh pr ready fails."""
        from implement_with_worktree import mark_pr_ready

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 1

        result = mark_pr_ready(123)

        assert result is False


@pytest.mark.unit
class TestPRPolling:
    """Test PR polling for feedback."""

    def test_get_pr_state_returns_open(self, mocker):
        """Should return PR state from GitHub."""
        from implement_with_worktree import get_pr_state

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "OPEN"}'

        state = get_pr_state(123)

        assert state == "OPEN"

    def test_get_pr_state_returns_merged(self, mocker):
        """Should return MERGED state when PR is merged."""
        from implement_with_worktree import get_pr_state

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "MERGED"}'

        state = get_pr_state(123)

        assert state == "MERGED"

    def test_get_pr_state_returns_closed(self, mocker):
        """Should return CLOSED state when PR is closed."""
        from implement_with_worktree import get_pr_state

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "CLOSED"}'

        state = get_pr_state(123)

        assert state == "CLOSED"

    def test_is_pr_complete_true_when_merged(self):
        """Should return True when PR is merged."""
        from implement_with_worktree import is_pr_complete

        assert is_pr_complete("MERGED") is True

    def test_is_pr_complete_true_when_closed(self):
        """Should return True when PR is closed."""
        from implement_with_worktree import is_pr_complete

        assert is_pr_complete("CLOSED") is True

    def test_is_pr_complete_false_when_open(self):
        """Should return False when PR is still open."""
        from implement_with_worktree import is_pr_complete

        assert is_pr_complete("OPEN") is False


@pytest.mark.unit
class TestCleanupOperations:
    """Test cleanup operations (worktree and branch removal)."""

    def test_remove_worktree_calls_git_worktree_remove(self, mocker):
        """Should call git worktree remove with correct path."""
        from implement_with_worktree import remove_worktree

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0

        result = remove_worktree("/path/to/worktree")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "worktree" in call_args
        assert "remove" in call_args
        assert "/path/to/worktree" in call_args

    def test_remove_worktree_returns_false_on_failure(self, mocker):
        """Should return False when worktree removal fails."""
        from implement_with_worktree import remove_worktree

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 1

        result = remove_worktree("/path/to/worktree")

        assert result is False

    def test_delete_local_branch_calls_git_branch_d(self, mocker):
        """Should call git branch -D to delete local branch."""
        from implement_with_worktree import delete_local_branch

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 0

        result = delete_local_branch("idea/my-feature/integration")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "branch" in call_args
        assert "-D" in call_args
        assert "idea/my-feature/integration" in call_args

    def test_delete_local_branch_returns_false_on_failure(self, mocker):
        """Should return False when branch deletion fails."""
        from implement_with_worktree import delete_local_branch

        mock_run = mocker.patch('implement_with_worktree.subprocess.run')
        mock_run.return_value.returncode = 1

        result = delete_local_branch("idea/my-feature/integration")

        assert result is False


@pytest.mark.unit
class TestSliceRollover:
    """Test slice rollover when PR exits Draft state unexpectedly."""

    def test_should_rollover_true_when_not_draft_with_local_commits(self, mocker):
        """Should return True when PR is not draft and has unpushed commits."""
        from implement_with_worktree import should_rollover

        # Mock is_pr_draft to return False (PR is ready, not draft)
        mocker.patch('implement_with_worktree.is_pr_draft', return_value=False)

        result = should_rollover(pr_number=123, has_unpushed_commits=True)

        assert result is True

    def test_should_rollover_false_when_draft(self, mocker):
        """Should return False when PR is still in draft state."""
        from implement_with_worktree import should_rollover

        mocker.patch('implement_with_worktree.is_pr_draft', return_value=True)

        result = should_rollover(pr_number=123, has_unpushed_commits=True)

        assert result is False

    def test_should_rollover_false_when_no_unpushed_commits(self, mocker):
        """Should return False when there are no unpushed commits."""
        from implement_with_worktree import should_rollover

        mocker.patch('implement_with_worktree.is_pr_draft', return_value=False)

        result = should_rollover(pr_number=123, has_unpushed_commits=False)

        assert result is False

    def test_generate_next_slice_branch_increments_number(self):
        """Should generate next slice branch with incremented number."""
        from implement_with_worktree import generate_next_slice_branch

        next_branch = generate_next_slice_branch(
            idea_name="my-feature",
            current_slice_number=1,
            slice_name="continuation"
        )

        assert next_branch == "idea/my-feature/02-continuation"

    def test_generate_next_slice_branch_zero_pads(self):
        """Should zero-pad the slice number."""
        from implement_with_worktree import generate_next_slice_branch

        next_branch = generate_next_slice_branch(
            idea_name="my-feature",
            current_slice_number=9,
            slice_name="next"
        )

        assert next_branch == "idea/my-feature/10-next"


@pytest.mark.unit
class TestInterruptHandling:
    """Test interrupt handling and graceful shutdown."""

    def test_register_signal_handlers_sets_up_sigint(self, mocker):
        """Should register handler for SIGINT (Ctrl+C)."""
        import signal
        from implement_with_worktree import register_signal_handlers

        mock_signal = mocker.patch('implement_with_worktree.signal.signal')

        register_signal_handlers()

        # Verify SIGINT handler was registered
        calls = [c for c in mock_signal.call_args_list if c[0][0] == signal.SIGINT]
        assert len(calls) == 1

    def test_cleanup_on_interrupt_saves_state(self, mocker):
        """Should save state when interrupted."""
        from implement_with_worktree import cleanup_on_interrupt, save_state

        # Mock save_state
        mock_save = mocker.patch('implement_with_worktree.save_state')

        # Call cleanup with state info
        cleanup_on_interrupt(
            idea_directory="/path/to/idea",
            idea_name="my-feature",
            state={"slice_number": 1}
        )

        mock_save.assert_called_once()
