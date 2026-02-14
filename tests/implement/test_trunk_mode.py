"""Tests for --trunk mode of i2code implement."""

import os

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, call

from i2code.implement.cli import implement_cmd
from i2code.implement.implement import ClaudeResult


PLAN_WITH_ONE_TASK = """\
# Plan

- [ ] **Task 1: Set up project**
"""

PLAN_COMPLETED = """\
# Plan

- [x] **Task 1: Set up project**
"""


@pytest.mark.unit
class TestTrunkModeAcceptance:
    """Acceptance test: --trunk with mock-claude executes tasks and prints completion."""

    @patch("i2code.implement.cli.run_trunk_loop")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_trunk_mode_dispatches_to_run_trunk_loop(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
        mock_run_trunk_loop
    ):
        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk"])

        assert result.exit_code == 0
        mock_run_trunk_loop.assert_called_once_with(
            idea_directory="/tmp/fake-idea",
            idea_name="test-feature",
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
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_trunk_with_incompatible_flag_raises_usage_error(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
        flag,
    ):
        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", flag])

        assert result.exit_code != 0
        assert "cannot be combined" in result.output.lower() or "cannot be combined" in (result.exception and str(result.exception) or "").lower()

    @pytest.mark.parametrize("flag,value", [
        ("--ci-fix-retries", "5"),
        ("--ci-timeout", "900"),
    ])
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    def test_trunk_with_non_default_ci_option_raises_usage_error(
        self, mock_validate_dir, mock_validate_files, mock_validate_committed,
        flag, value,
    ):
        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", flag, value])

        assert result.exit_code != 0


@pytest.mark.unit
class TestRunTrunkLoop:
    """Unit tests for run_trunk_loop."""

    @patch("i2code.implement.implement.parse_tasks_from_plan", return_value=[])
    @patch("builtins.open", create=True)
    @patch("i2code.implement.implement.Repo")
    def test_no_tasks_remaining_prints_all_completed(
        self, mock_repo_cls, mock_open, mock_parse,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo_cls.return_value = mock_repo
        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: PLAN_COMPLETED)
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
        )

        captured = capsys.readouterr()
        assert "All tasks completed!" in captured.out

    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.parse_tasks_from_plan")
    @patch("builtins.open", create=True)
    @patch("i2code.implement.implement.Repo")
    def test_invokes_claude_for_first_task(
        self, mock_repo_cls, mock_open, mock_parse,
        mock_build_cmd, mock_run_claude, mock_check,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: "plan")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        # First call: one task; second call (after Claude): no tasks; third call: no tasks
        mock_parse.side_effect = [
            ["**Task 1: Set up project**"],
            [],
            [],
        ]

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        # Make HEAD advance after Claude runs
        mock_repo.head.commit.hexsha = "aaa"

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
        )

        mock_build_cmd.assert_called_once_with(
            "/fake/repo/ideas/test-feature",
            "**Task 1: Set up project**",
            interactive=True,
            extra_prompt=None,
            extra_cli_args=None,
        )
        mock_run_claude.assert_called_once()

    @patch("i2code.implement.implement.check_claude_success", return_value=False)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.parse_tasks_from_plan", return_value=["**Task 1: Set up**"])
    @patch("builtins.open", create=True)
    @patch("i2code.implement.implement.Repo")
    def test_exits_on_claude_failure(
        self, mock_repo_cls, mock_open, mock_parse,
        mock_build_cmd, mock_run_claude, mock_check,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: "plan")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        mock_run_claude.return_value = ClaudeResult(returncode=1, stdout="", stderr="")

        with pytest.raises(SystemExit) as exc_info:
            run_trunk_loop(
                idea_directory="/fake/repo/ideas/test-feature",
                idea_name="test-feature",
            )

        assert exc_info.value.code == 1

    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.parse_tasks_from_plan")
    @patch("builtins.open", create=True)
    @patch("i2code.implement.implement.Repo")
    def test_loops_through_multiple_tasks(
        self, mock_repo_cls, mock_open, mock_parse,
        mock_build_cmd, mock_run_claude, mock_check,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: "plan")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate: 2 tasks → 1 task (after first read) → 1 task → 0 tasks (after second read) → 0 tasks
        mock_parse.side_effect = [
            ["**Task 1**", "**Task 2**"],  # initial read
            ["**Task 2**"],                # post-Claude re-read (task 1 done)
            ["**Task 2**"],                # second loop iteration read
            [],                            # post-Claude re-read (task 2 done)
            [],                            # final loop iteration read
        ]

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
        )

        assert mock_run_claude.call_count == 2
        captured = capsys.readouterr()
        assert "All tasks completed!" in captured.out

    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.parse_tasks_from_plan")
    @patch("builtins.open", create=True)
    @patch("i2code.implement.implement.Repo")
    def test_exits_when_task_not_marked_complete(
        self, mock_repo_cls, mock_open, mock_parse,
        mock_build_cmd, mock_run_claude, mock_check,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: "plan")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        # Task count stays the same after Claude runs
        mock_parse.return_value = ["**Task 1: Set up**"]

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        with pytest.raises(SystemExit) as exc_info:
            run_trunk_loop(
                idea_directory="/fake/repo/ideas/test-feature",
                idea_name="test-feature",
            )

        assert exc_info.value.code == 1

    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command")
    @patch("i2code.implement.implement.parse_tasks_from_plan")
    @patch("builtins.open", create=True)
    @patch("i2code.implement.implement.Repo")
    def test_uses_mock_claude_when_provided(
        self, mock_repo_cls, mock_open, mock_parse,
        mock_build_cmd, mock_run_claude, mock_check,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: "plan")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        mock_parse.side_effect = [
            ["**Task 1: Set up**"],
            [],
            [],
        ]

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            mock_claude="/path/to/mock-script",
        )

        # Should NOT call build_claude_command when mock_claude is provided
        mock_build_cmd.assert_not_called()
        # Should invoke run_claude_interactive with [mock_script, task]
        mock_run_claude.assert_called_once()
        cmd_used = mock_run_claude.call_args[0][0]
        assert cmd_used == ["/path/to/mock-script", "**Task 1: Set up**"]

    @patch("i2code.implement.implement.calculate_claude_permissions", return_value=["Bash(git commit:*)", "Write(/fake/repo/)"])
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_with_output_capture")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "-p", "do task"])
    @patch("i2code.implement.implement.parse_tasks_from_plan")
    @patch("builtins.open", create=True)
    @patch("i2code.implement.implement.Repo")
    def test_non_interactive_passes_allowed_tools(
        self, mock_repo_cls, mock_open, mock_parse,
        mock_build_cmd, mock_run_claude, mock_check,
        mock_calc_perms,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: "plan")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        mock_parse.side_effect = [["**Task 1**"], [], []]
        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            non_interactive=True,
        )

        mock_calc_perms.assert_called_once_with("/fake/repo")
        mock_build_cmd.assert_called_once_with(
            "/fake/repo/ideas/test-feature",
            "**Task 1**",
            interactive=False,
            extra_prompt=None,
            extra_cli_args=["--allowedTools", "Bash(git commit:*),Write(/fake/repo/)"],
        )
