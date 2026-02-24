"""Tests for branch lifecycle operations in implement-with-worktree."""

import pytest


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
