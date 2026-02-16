"""Tests for --dry-run option of i2code implement."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from i2code.implement.cli import implement_cmd


@pytest.mark.unit
class TestDryRun:
    """--dry-run prints what mode would be used and exits."""

    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_dry_run_trunk_mode(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
    ):
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", "--dry-run"])

        assert result.exit_code == 0
        assert "trunk" in result.output.lower()

    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_dry_run_isolate_mode(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
    ):
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--isolate", "--dry-run"])

        assert result.exit_code == 0
        assert "isolate" in result.output.lower()

    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_dry_run_worktree_mode(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
    ):
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--dry-run"])

        assert result.exit_code == 0
        assert "worktree" in result.output.lower()

    @patch("i2code.implement.cli.run_trunk_loop")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_dry_run_does_not_execute(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
        mock_run_trunk_loop,
    ):
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", "--dry-run"])

        assert result.exit_code == 0
        mock_run_trunk_loop.assert_not_called()
