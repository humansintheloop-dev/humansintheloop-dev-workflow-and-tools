"""Tests for worktree project setup: delegates to claude_permissions and runs setup script."""

import pytest
from unittest.mock import patch

from i2code.implement.worktree_setup import setup_project

from fake_git_repository import FakeGitRepository


@pytest.mark.unit
class TestSetupProject:
    """Test setup_project delegates to setup_claude_settings_local_json and runs setup script."""

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_delegates_with_separate_main_repo(self, mock_settings, mock_script):
        """Should pass working_tree_dir and main_repo_dir to setup_claude_settings_local_json."""
        git_repo = FakeGitRepository(
            working_tree_dir="/worktree", main_repo_dir="/main",
        )
        setup_project(git_repo)

        mock_settings.assert_called_once_with("/worktree", "/main")

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_returns_early_when_same_repo(self, mock_settings, mock_script):
        """When main_repo_dir == working_tree_dir, does nothing."""
        git_repo = FakeGitRepository(working_tree_dir="/repo", main_repo_dir="/repo")
        setup_project(git_repo)

        mock_settings.assert_not_called()
        mock_script.assert_not_called()

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_runs_setup_script(self, mock_settings, mock_script):
        """Should run the setup project script in working_tree_dir."""
        git_repo = FakeGitRepository(working_tree_dir="/dest", main_repo_dir="/main")
        setup_project(git_repo)

        mock_script.assert_called_once_with("/dest")
