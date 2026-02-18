"""Tests for --dry-run option of i2code implement."""

import pytest
from unittest.mock import MagicMock, patch

from i2code.implement.implement_command import ImplementCommand
from i2code.implement.implement_opts import ImplementOpts


def _make_mock_project():
    """Create a MagicMock that behaves like an IdeaProject instance."""
    mock_project = MagicMock()
    mock_project.name = "test-feature"
    mock_project.directory = "/tmp/fake-idea"
    mock_project.validate.return_value = mock_project
    mock_project.validate_files.return_value = None
    return mock_project


def _make_dry_run_opts(**overrides):
    defaults = dict(idea_directory="/tmp/fake-idea", dry_run=True)
    defaults.update(overrides)
    return ImplementOpts(**defaults)


def _make_command(**opt_overrides):
    opts = _make_dry_run_opts(**opt_overrides)
    project = _make_mock_project()
    return ImplementCommand(opts, project, MagicMock(), MagicMock(), MagicMock(), MagicMock())


@pytest.mark.unit
class TestDryRun:
    """--dry-run prints what mode would be used and exits."""

    def test_dry_run_trunk_mode(self, capsys):
        cmd = _make_command(trunk=True)
        cmd.execute()

        assert "trunk" in capsys.readouterr().out.lower()

    def test_dry_run_isolate_mode(self, capsys):
        cmd = _make_command(isolate=True)
        cmd.execute()

        assert "isolate" in capsys.readouterr().out.lower()

    def test_dry_run_worktree_mode(self, capsys):
        cmd = _make_command()
        cmd.execute()

        assert "worktree" in capsys.readouterr().out.lower()

    def test_dry_run_does_not_execute(self):
        cmd = _make_command(trunk=True)
        with patch.object(cmd, '_trunk_mode') as mock_trunk:
            cmd.execute()
            mock_trunk.assert_not_called()
