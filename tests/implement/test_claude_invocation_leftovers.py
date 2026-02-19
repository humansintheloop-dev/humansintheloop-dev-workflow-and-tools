"""Tests for Claude Code invocation in implement-with-worktree."""

import pytest


@pytest.mark.unit
class TestWorktreeIdeaDirectory:
    """Test that Claude is invoked with worktree idea directory, not main repo."""

    def test_worktree_idea_project(self):
        """Should return an IdeaProject for the path within the worktree."""
        from i2code.implement.idea_project import IdeaProject

        project = IdeaProject("/home/user/my-repo/docs/ideas/my-feature")

        result = project.worktree_idea_project(
            "/tmp/my-repo-wt-my-feature",
            "/home/user/my-repo",
        )

        assert isinstance(result, IdeaProject)
        assert result.directory == "/tmp/my-repo-wt-my-feature/docs/ideas/my-feature"


@pytest.mark.unit
class TestCalculateClaudePermissions:
    """Test calculation of Claude permissions for --allowedTools."""

    def test_includes_required_permissions(self):
        from i2code.implement.git_setup import calculate_claude_permissions, REQUIRED_PERMISSIONS

        perms = calculate_claude_permissions("/fake/repo")

        for req in REQUIRED_PERMISSIONS:
            assert req in perms

    def test_includes_write_and_edit_for_repo_root(self):
        from i2code.implement.git_setup import calculate_claude_permissions

        perms = calculate_claude_permissions("/fake/repo")

        assert "Write(//fake/repo/)" in perms
        assert "Edit(//fake/repo/)" in perms




@pytest.mark.unit
class TestMainBranchAdvancement:
    """Test detection of main branch advancement."""

    def test_has_main_advanced_returns_false_if_same(self):
        """Should return False when main branch HEAD hasn't changed."""
        from i2code.implement.branch_lifecycle import has_main_advanced

        assert has_main_advanced(
            original_head="abc123",
            current_head="abc123"
        ) is False

    def test_has_main_advanced_returns_true_if_different(self):
        """Should return True when main branch HEAD has changed."""
        from i2code.implement.branch_lifecycle import has_main_advanced

        assert has_main_advanced(
            original_head="abc123",
            current_head="def456"
        ) is True

    def test_get_remote_main_head_returns_sha(self, mocker):
        """Should return the SHA of origin/main."""
        from i2code.implement.branch_lifecycle import get_remote_main_head

        # Mock subprocess.run to simulate git fetch and ls-remote
        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "abc123def456\trefs/heads/main\n"

        sha = get_remote_main_head(branch="main")

        assert sha == "abc123def456"
        # Called twice: once for fetch, once for ls-remote
        assert mock_run.call_count == 2

    def test_get_remote_main_head_fetches_first(self, mocker):
        """Should fetch from origin before getting HEAD."""
        from i2code.implement.branch_lifecycle import get_remote_main_head

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

        mocker.patch('i2code.implement.branch_lifecycle.subprocess.run', side_effect=mock_run)

        get_remote_main_head(branch="main")

        # Verify fetch was called before ls-remote
        assert len(calls) == 2
        assert "fetch" in calls[0]
        assert "ls-remote" in calls[1]

    def test_get_remote_main_head_uses_passed_branch(self, mocker):
        """Should fetch and query the passed branch, not hardcoded 'main'."""
        from i2code.implement.branch_lifecycle import get_remote_main_head

        calls = []
        def mock_run(*args, **kwargs):
            calls.append(args[0])
            result = mocker.MagicMock()
            result.returncode = 0
            if "fetch" in args[0]:
                result.stdout = ""
            else:
                result.stdout = "abc123\trefs/heads/master\n"
            return result

        mocker.patch('i2code.implement.branch_lifecycle.subprocess.run', side_effect=mock_run)

        sha = get_remote_main_head(branch="master")

        assert sha == "abc123"
        # Verify "master" appears in the fetch and ls-remote commands
        fetch_cmd = calls[0]
        assert "master" in fetch_cmd
        ls_remote_cmd = calls[1]
        assert "refs/heads/master" in ls_remote_cmd


@pytest.mark.unit
class TestRebaseOperations:
    """Test rebase operations for main branch advancement."""

    def test_rebase_integration_branch_success(self, mocker):
        """Should return True when rebase succeeds."""
        from i2code.implement.branch_lifecycle import rebase_integration_branch

        # Mock subprocess.run to simulate successful rebase
        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
        mock_run.return_value.returncode = 0

        result = rebase_integration_branch("idea/my-feature/integration", base_branch="main")

        assert result is True

    def test_rebase_integration_branch_returns_false_on_conflict(self, mocker):
        """Should return False when rebase has conflicts."""
        from i2code.implement.branch_lifecycle import rebase_integration_branch

        # Mock subprocess.run to simulate rebase conflict
        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
        mock_run.return_value.returncode = 1

        result = rebase_integration_branch("idea/my-feature/integration", base_branch="main")

        assert result is False

    def test_rebase_integration_branch_aborts_on_conflict(self, mocker):
        """Should abort rebase when conflicts occur."""
        from i2code.implement.branch_lifecycle import rebase_integration_branch

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

        mocker.patch('i2code.implement.branch_lifecycle.subprocess.run', side_effect=mock_run)

        rebase_integration_branch("idea/my-feature/integration", base_branch="main")

        # Verify abort was called after failed rebase
        abort_calls = [c for c in calls if "--abort" in c]
        assert len(abort_calls) == 1

    def test_rebase_integration_branch_uses_passed_base_branch(self, mocker):
        """Should rebase onto the passed base_branch, not hardcoded 'main'."""
        from i2code.implement.branch_lifecycle import rebase_integration_branch

        calls = []
        def mock_run(cmd, **kwargs):
            calls.append(cmd)
            result = mocker.MagicMock()
            result.returncode = 0
            return result

        mocker.patch('i2code.implement.branch_lifecycle.subprocess.run', side_effect=mock_run)

        rebase_integration_branch("idea/my-feature/integration", base_branch="master")

        rebase_cmd = [c for c in calls if "rebase" in c and "--abort" not in c]
        assert len(rebase_cmd) == 1
        assert "origin/master" in rebase_cmd[0]

    def test_update_slice_after_rebase_force_pushes(self, mocker):
        """Should force push slice branch after rebase."""
        from i2code.implement.branch_lifecycle import update_slice_after_rebase

        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
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
        from i2code.implement.branch_lifecycle import get_rebase_conflict_message

        message = get_rebase_conflict_message("idea/my-feature/integration", base_branch="main")

        assert "conflict" in message.lower()
        assert "idea/my-feature/integration" in message

    def test_handle_rebase_conflict_includes_instructions(self):
        """Should include instructions for manual resolution."""
        from i2code.implement.branch_lifecycle import get_rebase_conflict_message

        message = get_rebase_conflict_message("idea/my-feature/integration", base_branch="main")

        # Should tell user what to do
        assert "manual" in message.lower() or "resolve" in message.lower()

    def test_rebase_conflict_message_uses_passed_base_branch(self):
        """Should use the passed base_branch, not hardcoded 'main'."""
        from i2code.implement.branch_lifecycle import get_rebase_conflict_message

        message = get_rebase_conflict_message("idea/my-feature/integration", base_branch="master")

        assert "origin/master" in message
        assert "origin/main" not in message


@pytest.mark.unit
class TestCleanupOperations:
    """Test cleanup operations (worktree and branch removal)."""

    def test_remove_worktree_calls_git_worktree_remove(self, mocker):
        """Should call git worktree remove with correct path."""
        from i2code.implement.branch_lifecycle import remove_worktree

        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
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
        from i2code.implement.branch_lifecycle import remove_worktree

        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
        mock_run.return_value.returncode = 1

        result = remove_worktree("/path/to/worktree")

        assert result is False

    def test_delete_local_branch_calls_git_branch_d(self, mocker):
        """Should call git branch -D to delete local branch."""
        from i2code.implement.branch_lifecycle import delete_local_branch

        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
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
        from i2code.implement.branch_lifecycle import delete_local_branch

        mock_run = mocker.patch('i2code.implement.branch_lifecycle.subprocess.run')
        mock_run.return_value.returncode = 1

        result = delete_local_branch("idea/my-feature/integration")

        assert result is False


@pytest.mark.unit
class TestInterruptHandling:
    """Test interrupt handling and graceful shutdown."""

    def test_register_signal_handlers_sets_up_sigint(self, mocker):
        """Should register handler for SIGINT (Ctrl+C)."""
        import signal
        from i2code.implement.branch_lifecycle import register_signal_handlers

        mock_signal = mocker.patch('i2code.implement.branch_lifecycle.signal.signal')

        register_signal_handlers()

        # Verify SIGINT handler was registered
        calls = [c for c in mock_signal.call_args_list if c[0][0] == signal.SIGINT]
        assert len(calls) == 1

    def test_cleanup_on_interrupt_saves_state(self, mocker):
        """Should save state when interrupted."""
        from unittest.mock import MagicMock
        from i2code.implement.branch_lifecycle import cleanup_on_interrupt

        mock_state = MagicMock()

        cleanup_on_interrupt(
            state_file="/path/to/idea/my-feature-wt-state.json",
            state=mock_state
        )

        mock_state.save.assert_called_once()
