"""Integration tests for implement CLI.

These tests run the actual i2code implement command and verify its behavior.
"""

import subprocess

import pytest
from unittest.mock import patch, MagicMock

from conftest import SCRIPT_CMD
from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task


def _make_mock_project(name="test-feature", directory="/tmp/fake-idea"):
    """Create a MagicMock that behaves like an IdeaProject instance."""
    mock_project = MagicMock()
    mock_project.name = name
    mock_project.directory = directory
    mock_project.plan_file = f"{directory}/{name}-plan.md"
    mock_project.state_file = f"{directory}/{name}-wt-state.json"
    mock_project.validate.return_value = mock_project
    mock_project.validate_files.return_value = None
    return mock_project


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

    @patch("i2code.implement.cli.get_next_task", return_value=_make_numbered_task("setup"))
    @patch("i2code.implement.cli.WorkflowState.load")
    @patch("i2code.implement.cli.ensure_slice_branch", return_value="idea/test-feature/01-setup")
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_isolated_flag_passes_isolated_true(
        self, mock_repo_cls, mock_idea_project_cls, mock_validate_committed,
        mock_ensure_branch, mock_ensure_slice,
        mock_load_state, mock_first_task
    ):
        """When --isolated is set, ensure_integration_branch is called with isolated=True."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_load_state.return_value = MagicMock(slice_number=1)
        mock_idea_project_cls.return_value = _make_mock_project()
        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--isolated", "--setup-only"])

        mock_ensure_branch.assert_called_once_with(mock_repo, "test-feature", isolated=True)

    @patch("i2code.implement.cli.get_next_task", return_value=_make_numbered_task("setup"))
    @patch("i2code.implement.cli.WorkflowState.load")
    @patch("i2code.implement.cli.ensure_slice_branch", return_value="idea/test-feature/01-setup")
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_non_isolated_passes_isolated_false(
        self, mock_repo_cls, mock_idea_project_cls, mock_validate_committed,
        mock_ensure_branch, mock_ensure_slice,
        mock_load_state, mock_first_task
    ):
        """When --isolated is not set, ensure_integration_branch is called with default isolated=False."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_load_state.return_value = MagicMock(slice_number=1)
        mock_idea_project_cls.return_value = _make_mock_project()
        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--setup-only"])

        mock_ensure_branch.assert_called_once_with(mock_repo, "test-feature", isolated=False)


@pytest.mark.unit
class TestTrunkModeAcceptance:
    """Acceptance test: --trunk dispatches to TrunkMode.execute()."""

    @patch("i2code.implement.trunk_mode.TrunkMode.execute")
    @patch("i2code.implement.cli.GitRepository")
    @patch("i2code.implement.cli.Repo")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    def test_trunk_mode_dispatches_to_trunk_mode_execute(
        self, mock_idea_project_cls, mock_validate_committed,
        mock_repo_cls, mock_git_repo_cls, mock_execute,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_idea_project_cls.return_value = _make_mock_project()
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk"])

        assert result.exit_code == 0
        mock_execute.assert_called_once_with(
            non_interactive=False,
            mock_claude=None,
            extra_prompt=None,
        )


@pytest.mark.unit
class TestTrunkModeIncompatibleFlags:
    """--trunk is incompatible with flags that assume remote/CI/worktree infrastructure."""

    @pytest.mark.parametrize("flag", [
        "--cleanup",
        "--setup-only",
        "--isolate",
        "--isolated",
        "--skip-ci-wait",
    ])
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    def test_trunk_with_incompatible_flag_raises_usage_error(
        self, mock_idea_project_cls, mock_validate_committed,
        flag,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_idea_project_cls.return_value = _make_mock_project()
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", flag])

        assert result.exit_code != 0
        assert "cannot be combined" in result.output.lower() or "cannot be combined" in (result.exception and str(result.exception) or "").lower()

    @pytest.mark.parametrize("flag,value", [
        ("--ci-fix-retries", "5"),
        ("--ci-timeout", "900"),
    ])
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    def test_trunk_with_non_default_ci_option_raises_usage_error(
        self, mock_idea_project_cls, mock_validate_committed,
        flag, value,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_idea_project_cls.return_value = _make_mock_project()
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", flag, value])

        assert result.exit_code != 0


@pytest.mark.unit
class TestIgnoreUncommittedIdeaChanges:
    """--ignore-uncommitted-idea-changes skips validate_idea_files_committed."""

    @patch("i2code.implement.trunk_mode.TrunkMode.execute")
    @patch("i2code.implement.cli.GitRepository")
    @patch("i2code.implement.cli.Repo")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    def test_skips_committed_validation(
        self, mock_idea_project_cls, mock_validate_committed,
        mock_repo_cls, mock_git_repo_cls, mock_execute,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_idea_project_cls.return_value = _make_mock_project()
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, [
            "/tmp/fake-idea", "--trunk", "--ignore-uncommitted-idea-changes",
        ])

        assert result.exit_code == 0
        mock_validate_committed.assert_not_called()

    @patch("i2code.implement.trunk_mode.TrunkMode.execute")
    @patch("i2code.implement.cli.GitRepository")
    @patch("i2code.implement.cli.Repo")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    def test_without_flag_calls_committed_validation(
        self, mock_idea_project_cls, mock_validate_committed,
        mock_repo_cls, mock_git_repo_cls, mock_execute,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_idea_project_cls.return_value = _make_mock_project()
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk"])

        assert result.exit_code == 0
        mock_validate_committed.assert_called_once()


@pytest.mark.unit
class TestWorktreeModeAcceptance:
    """Acceptance test: default path dispatches to WorktreeMode.execute()."""

    @patch("i2code.implement.worktree_mode.WorktreeMode.execute")
    @patch("i2code.implement.cli.GitHubClient")
    @patch("i2code.implement.cli.get_worktree_idea_directory", return_value="/tmp/wt/idea")
    @patch("i2code.implement.cli.ensure_claude_permissions")
    @patch("i2code.implement.cli.ensure_worktree", return_value="/tmp/wt")
    @patch("i2code.implement.cli.ensure_slice_branch", return_value="idea/test/01-setup")
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test/integration")
    @patch("i2code.implement.cli.get_next_task", return_value=_make_numbered_task("setup"))
    @patch("i2code.implement.cli.WorkflowState.load")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_default_path_dispatches_to_worktree_mode_execute(
        self, mock_repo_cls, mock_idea_project_cls,
        mock_validate_committed, mock_load_state,
        mock_first_task, mock_ensure_integration, mock_ensure_slice,
        mock_ensure_worktree, mock_ensure_perms, mock_get_wt_idea,
        mock_gh_client_cls, mock_execute,
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_load_state.return_value = MagicMock(slice_number=1)
        mock_idea_project_cls.return_value = _make_mock_project(name="test", directory="/tmp/fake-idea")
        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        mock_gh = MagicMock()
        mock_gh.find_pr.return_value = None
        mock_gh_client_cls.return_value = mock_gh

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--skip-ci-wait"])

        assert result.exit_code == 0
        mock_execute.assert_called_once_with(
            non_interactive=False,
            mock_claude=None,
            extra_prompt=None,
            skip_ci_wait=True,
            ci_fix_retries=3,
            ci_timeout=600,
        )
