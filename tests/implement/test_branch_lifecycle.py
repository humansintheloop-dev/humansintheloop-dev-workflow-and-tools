"""Tests for branch lifecycle operations in implement-with-worktree."""

import pytest

from i2code.implement.branch_lifecycle import (
    delete_local_branch,
    get_remote_main_head,
    has_main_advanced,
    remove_worktree,
)

_SUBPROCESS_PATH = "i2code.implement.branch_lifecycle.subprocess.run"


def _mock_subprocess(mocker, returncode=0, stdout=""):
    """Patch subprocess.run and return the mock."""
    mock_run = mocker.patch(_SUBPROCESS_PATH)
    mock_run.return_value.returncode = returncode
    mock_run.return_value.stdout = stdout
    return mock_run


def _mock_fetch_and_ls_remote(mocker, ls_remote_stdout):
    """Patch subprocess.run to record calls and simulate fetch + ls-remote.

    Returns the list that captures each call's args.
    """
    calls = []

    def side_effect(*args, **kwargs):
        calls.append(args[0])
        result = mocker.MagicMock()
        result.returncode = 0
        result.stdout = "" if "fetch" in args[0] else ls_remote_stdout
        return result

    mocker.patch(_SUBPROCESS_PATH, side_effect=side_effect)
    return calls


@pytest.mark.unit
class TestMainBranchAdvancement:
    """Test detection of main branch advancement."""

    def test_has_main_advanced_returns_false_if_same(self):
        assert has_main_advanced(original_head="abc123", current_head="abc123") is False

    def test_has_main_advanced_returns_true_if_different(self):
        assert has_main_advanced(original_head="abc123", current_head="def456") is True

    def test_get_remote_main_head_returns_sha(self, mocker):
        mock_run = _mock_subprocess(mocker, stdout="abc123def456\trefs/heads/main\n")
        sha = get_remote_main_head(branch="main")
        assert sha == "abc123def456"
        assert mock_run.call_count == 2

    def test_get_remote_main_head_fetches_first(self, mocker):
        calls = _mock_fetch_and_ls_remote(mocker, "abc123\trefs/heads/main\n")
        get_remote_main_head(branch="main")

        assert len(calls) == 2
        assert "fetch" in calls[0]
        assert "ls-remote" in calls[1]

    def test_get_remote_main_head_uses_passed_branch(self, mocker):
        calls = _mock_fetch_and_ls_remote(mocker, "abc123\trefs/heads/master\n")
        sha = get_remote_main_head(branch="master")

        assert sha == "abc123"
        assert "master" in calls[0]
        assert "refs/heads/master" in calls[1]


@pytest.mark.unit
class TestCleanupOperations:
    """Test cleanup operations (worktree and branch removal)."""

    def test_remove_worktree_calls_git_worktree_remove(self, mocker):
        mock_run = _mock_subprocess(mocker)
        result = remove_worktree("/path/to/worktree")
        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "worktree" in call_args
        assert "remove" in call_args
        assert "/path/to/worktree" in call_args

    def test_remove_worktree_returns_false_on_failure(self, mocker):
        _mock_subprocess(mocker, returncode=1)
        assert remove_worktree("/path/to/worktree") is False

    def test_delete_local_branch_calls_git_branch_d(self, mocker):
        mock_run = _mock_subprocess(mocker)
        result = delete_local_branch("idea/my-feature/integration")
        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "branch" in call_args
        assert "-D" in call_args
        assert "idea/my-feature/integration" in call_args

    def test_delete_local_branch_returns_false_on_failure(self, mocker):
        _mock_subprocess(mocker, returncode=1)
        assert delete_local_branch("idea/my-feature/integration") is False
