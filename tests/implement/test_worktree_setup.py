"""Tests for ProjectSetup: delegates to claude_permissions and runs setup script."""

import pytest
from unittest.mock import patch

from i2code.implement.worktree_setup import ProjectSetup

from fake_git_repository import FakeGitRepository


@pytest.mark.unit
class TestSetupWorktree:
    """ProjectSetup.setup_worktree delegates when is_worktree, skips otherwise."""

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_delegates_with_separate_main_repo(self, mock_settings, mock_script):
        git_repo = FakeGitRepository(
            working_tree_dir="/worktree", main_repo_dir="/main",
        )
        ProjectSetup().setup_worktree(git_repo)

        mock_settings.assert_called_once_with("/worktree", "/main")

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_returns_early_when_same_repo(self, mock_settings, mock_script):
        git_repo = FakeGitRepository(working_tree_dir="/repo", main_repo_dir="/repo")
        ProjectSetup().setup_worktree(git_repo)

        mock_settings.assert_not_called()
        mock_script.assert_not_called()

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_runs_setup_script(self, mock_settings, mock_script):
        git_repo = FakeGitRepository(working_tree_dir="/dest", main_repo_dir="/main")
        ProjectSetup().setup_worktree(git_repo)

        mock_script.assert_called_once_with("/dest")


@pytest.mark.unit
class TestSetupClone:
    """ProjectSetup.setup_clone always delegates, even when not a worktree."""

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_runs_even_when_not_worktree(self, mock_settings, mock_script):
        git_repo = FakeGitRepository(working_tree_dir="/clone", main_repo_dir="/clone")
        ProjectSetup().setup_clone(git_repo)

        mock_settings.assert_called_once_with("/clone", "/clone")
        mock_script.assert_called_once_with("/clone")
