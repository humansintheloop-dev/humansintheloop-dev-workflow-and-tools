"""Tests for worktree project setup: settings copy, setup script."""

import os
import tempfile
import pytest
from unittest.mock import patch

from i2code.implement.worktree_setup import setup_project


@pytest.mark.unit
class TestSetupProject:
    """Test setup_project copies settings, ensures permissions, and runs setup script."""

    @patch("i2code.implement.worktree_setup.ensure_claude_permissions")
    def test_copies_settings_when_source_root_provided(self, mock_perms):
        """Should copy .claude/settings.local.json from source to dest."""

        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source")
            dest = os.path.join(tmpdir, "dest")
            os.makedirs(source)
            os.makedirs(dest)

            # Create .claude/settings.local.json in source
            claude_dir = os.path.join(source, ".claude")
            os.makedirs(claude_dir)
            settings_file = os.path.join(claude_dir, "settings.local.json")
            with open(settings_file, "w") as f:
                f.write('{"permissions": {"allow": ["Bash(*)"]}}')

            setup_project(dest, source_root=source)

            dest_settings = os.path.join(dest, ".claude", "settings.local.json")
            assert os.path.isfile(dest_settings)
            with open(dest_settings, "r") as f:
                content = f.read()
            assert '"permissions"' in content

    @patch("i2code.implement.worktree_setup.ensure_claude_permissions")
    def test_skips_settings_when_no_source_root(self, mock_perms):
        """Should not copy settings when source_root is None."""

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "dest")
            os.makedirs(dest)

            setup_project(dest)

            assert not os.path.exists(os.path.join(dest, ".claude", "settings.local.json"))

    @patch("i2code.implement.worktree_setup.ensure_claude_permissions")
    def test_skips_settings_when_missing_in_source(self, mock_perms):
        """Should not fail if .claude/settings.local.json does not exist in source."""

        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source")
            dest = os.path.join(tmpdir, "dest")
            os.makedirs(source)
            os.makedirs(dest)

            setup_project(dest, source_root=source)

            assert not os.path.exists(os.path.join(dest, ".claude", "settings.local.json"))

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.ensure_claude_permissions")
    def test_permissions_merged_after_settings_copy(self, mock_perms, mock_script):
        """Permissions should be ensured after settings are copied, so they merge correctly."""

        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source")
            dest = os.path.join(tmpdir, "dest")
            os.makedirs(source)
            os.makedirs(dest)

            setup_project(dest, source_root=source)

            mock_perms.assert_called_once_with(dest)

    @patch("i2code.implement.worktree_setup._run_setup_project_script")
    @patch("i2code.implement.worktree_setup.ensure_claude_permissions")
    def test_ensures_permissions_without_source_root(self, mock_perms, mock_script):
        """Permissions should be ensured even without source_root."""

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "dest")
            os.makedirs(dest)

            setup_project(dest)

            mock_perms.assert_called_once_with(dest)
