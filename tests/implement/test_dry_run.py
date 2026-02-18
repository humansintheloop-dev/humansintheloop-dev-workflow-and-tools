"""Tests for --dry-run option of i2code implement."""

import pytest
from unittest.mock import MagicMock, patch

from i2code.implement.cli import implement
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


def _mock_deps():
    return MagicMock(), MagicMock(), MagicMock(), MagicMock()


@pytest.mark.unit
class TestDryRun:
    """--dry-run prints what mode would be used and exits."""

    def test_dry_run_trunk_mode(self, capsys):
        opts = _make_dry_run_opts(trunk=True)
        implement(opts, _make_mock_project(), *_mock_deps())

        assert "trunk" in capsys.readouterr().out.lower()

    def test_dry_run_isolate_mode(self, capsys):
        opts = _make_dry_run_opts(isolate=True)
        implement(opts, _make_mock_project(), *_mock_deps())

        assert "isolate" in capsys.readouterr().out.lower()

    def test_dry_run_worktree_mode(self, capsys):
        opts = _make_dry_run_opts()
        implement(opts, _make_mock_project(), *_mock_deps())

        assert "worktree" in capsys.readouterr().out.lower()

    @patch("i2code.implement.cli.implement_trunk_mode")
    def test_dry_run_does_not_execute(self, mock_trunk_mode):
        opts = _make_dry_run_opts(trunk=True)
        implement(opts, _make_mock_project(), *_mock_deps())

        mock_trunk_mode.assert_not_called()
