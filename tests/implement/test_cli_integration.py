"""Integration tests for implement CLI.

These tests run the actual i2code implement command and verify its behavior.
"""

import os
import subprocess
import tempfile

import pytest
from unittest.mock import patch, MagicMock

from conftest import SCRIPT_CMD
from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task


@pytest.mark.integration
class TestCLINoArguments:
    """Test CLI behavior when run with no arguments."""

    def test_no_arguments_shows_usage_error(self):
        """Running script with no arguments should show usage error and exit non-zero."""
        result = subprocess.run(
            SCRIPT_CMD,
            capture_output=True,
            text=True
        )

        # Should exit with non-zero code
        assert result.returncode != 0

        # Click shows "Usage:" and mentions the required argument
        assert "usage:" in result.stderr.lower() or "error:" in result.stderr.lower()
        assert "idea-directory" in result.stderr.lower() or "idea_directory" in result.stderr.lower()


@pytest.mark.integration
class TestCLIHelpFlag:
    """Test CLI --help flag behavior."""

    def test_help_flag_shows_help_text(self):
        """Running script with --help should show help text and exit zero."""
        result = subprocess.run(
            SCRIPT_CMD + ['--help'],
            capture_output=True,
            text=True
        )

        # Should exit with zero code
        assert result.returncode == 0

        # Should show help information in stdout
        assert "idea-directory" in result.stdout.lower() or "idea_directory" in result.stdout.lower()
        assert "--cleanup" in result.stdout
        # Should include description
        assert "worktree" in result.stdout.lower() or "draft pr" in result.stdout.lower()


def _make_numbered_task(title: str) -> NumberedTask:
    return NumberedTask(
        number=TaskNumber(thread=1, task=1),
        task=Task(_lines=[f"- [ ] **Task 1.1: {title}**"]),
    )


@pytest.mark.unit
class TestIsolatedFlagPassthrough:
    """Test that --isolated flag is forwarded to ensure_integration_branch()."""

    CLI_PATCHES = [
        "i2code.implement.cli.ensure_integration_branch",
        "i2code.implement.cli.ensure_slice_branch",
        "i2code.implement.cli.validate_idea_directory",
        "i2code.implement.cli.validate_idea_files",
        "i2code.implement.cli.validate_idea_files_committed",
        "i2code.implement.cli.init_or_load_state",
        "i2code.implement.cli.get_next_task",
        "i2code.implement.cli.Repo",
    ]

    @patch("i2code.implement.cli.get_next_task", return_value=_make_numbered_task("setup"))
    @patch("i2code.implement.cli.init_or_load_state", return_value={"slice_number": 1})
    @patch("i2code.implement.cli.ensure_slice_branch", return_value="idea/test-feature/01-setup")
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    @patch("i2code.implement.cli.Repo")
    def test_isolated_flag_passes_isolated_true(
        self, mock_repo_cls, mock_validate_dir, mock_validate_committed,
        mock_validate_files, mock_ensure_branch, mock_ensure_slice,
        mock_init_state, mock_first_task
    ):
        """When --isolated is set, ensure_integration_branch is called with isolated=True."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--isolated", "--setup-only"])

        mock_ensure_branch.assert_called_once_with(mock_repo, "test-feature", isolated=True)

    @patch("i2code.implement.cli.get_next_task", return_value=_make_numbered_task("setup"))
    @patch("i2code.implement.cli.init_or_load_state", return_value={"slice_number": 1})
    @patch("i2code.implement.cli.ensure_slice_branch", return_value="idea/test-feature/01-setup")
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    @patch("i2code.implement.cli.Repo")
    def test_non_isolated_passes_isolated_false(
        self, mock_repo_cls, mock_validate_dir, mock_validate_committed,
        mock_validate_files, mock_ensure_branch, mock_ensure_slice,
        mock_init_state, mock_first_task
    ):
        """When --isolated is not set, ensure_integration_branch is called with default isolated=False."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--setup-only"])

        mock_ensure_branch.assert_called_once_with(mock_repo, "test-feature", isolated=False)


@pytest.mark.unit
class TestIgnoreUncommittedIdeaChanges:
    """--ignore-uncommitted-idea-changes skips validate_idea_files_committed."""

    @patch("i2code.implement.cli.run_trunk_loop")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_skips_committed_validation(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
        mock_run_trunk_loop,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        runner = CliRunner()
        result = runner.invoke(implement_cmd, [
            "/tmp/fake-idea", "--trunk", "--ignore-uncommitted-idea-changes",
        ])

        assert result.exit_code == 0
        mock_validate_committed.assert_not_called()

    @patch("i2code.implement.cli.run_trunk_loop")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_without_flag_calls_committed_validation(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
        mock_run_trunk_loop,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk"])

        assert result.exit_code == 0
        mock_validate_committed.assert_called_once()
