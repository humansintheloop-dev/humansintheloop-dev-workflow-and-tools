"""Tests for worktree project setup: delegates to claude_permissions and setup script."""

import pytest
from unittest.mock import patch

from i2code.implement.worktree_setup import setup_project


@pytest.mark.unit
class TestSetupProject:
    """Test setup_project delegates to setup_claude_settings_local_json and runs setup script."""

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_delegates_to_claude_settings_with_source_root(self, mock_settings, mock_script):
        """Should pass dest_root and source_root to setup_claude_settings_local_json."""
        setup_project("/dest", source_root="/source")

        mock_settings.assert_called_once_with("/dest", "/source")

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_delegates_to_claude_settings_without_source_root(self, mock_settings, mock_script):
        """Should pass dest_root and None to setup_claude_settings_local_json."""
        setup_project("/dest")

        mock_settings.assert_called_once_with("/dest", None)

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.setup_claude_settings_local_json")
    def test_runs_setup_script(self, mock_settings, mock_script):
        """Should run the setup project script."""
        setup_project("/dest")

        mock_script.assert_called_once_with("/dest")
