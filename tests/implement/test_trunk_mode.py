"""Tests for --trunk mode of i2code implement."""


import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from i2code.implement.cli import implement_cmd
from i2code.implement.implement import ClaudeResult
from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task


def make_numbered_task(thread: int, task: int, title: str) -> NumberedTask:
    return NumberedTask(
        number=TaskNumber(thread=thread, task=task),
        task=Task(_lines=[f"- [ ] **Task {thread}.{task}: {title}**"]),
    )


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
        runner = CliRunner(catch_exceptions=False)
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
        runner = CliRunner(catch_exceptions=False)
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
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", flag, value])

        assert result.exit_code != 0


@pytest.mark.unit
class TestRunTrunkLoop:
    """Unit tests for run_trunk_loop."""

    @patch("i2code.implement.implement.get_next_task", return_value=None)
    @patch("i2code.implement.implement.Repo")
    def test_no_tasks_remaining_prints_all_completed(
        self, mock_repo_cls, mock_get_next,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo_cls.return_value = mock_repo

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
        )

        mock_get_next.assert_called_once()
        captured = capsys.readouterr()
        assert "All tasks completed!" in captured.out

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    @patch("i2code.implement.implement.Repo")
    def test_invokes_claude_for_first_task(
        self, mock_repo_cls, mock_get_next,
        mock_build_cmd, mock_run_claude, mock_check, mock_is_completed,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        task = make_numbered_task(1, 1, "Set up project")
        # First call: task found; second call (after completion): no tasks
        mock_get_next.side_effect = [task, None]

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
        )

        mock_get_next.assert_called()
        mock_is_completed.assert_called_once()
        mock_build_cmd.assert_called_once_with(
            "/fake/repo/ideas/test-feature",
            task.print(),
            interactive=True,
            extra_prompt=None,
            extra_cli_args=None,
        )
        mock_run_claude.assert_called_once()

    @patch("i2code.implement.implement.calculate_claude_permissions", return_value=["Bash(git commit:*)"])
    @patch("i2code.implement.implement.run_claude_with_output_capture")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "-p", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    @patch("i2code.implement.implement.Repo")
    def test_exits_on_claude_failure(
        self, mock_repo_cls, mock_get_next,
        mock_build_cmd, mock_run_claude, mock_calc_perms,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_get_next.return_value = make_numbered_task(1, 1, "Set up")

        mock_run_claude.return_value = ClaudeResult(returncode=1, stdout="<FAILURE>something went wrong</FAILURE>", stderr="")

        with pytest.raises(SystemExit) as exc_info:
            run_trunk_loop(
                idea_directory="/fake/repo/ideas/test-feature",
                idea_name="test-feature",
                non_interactive=True,
            )

        assert exc_info.value.code == 1
        mock_get_next.assert_called_once()

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    @patch("i2code.implement.implement.Repo")
    def test_loops_through_multiple_tasks(
        self, mock_repo_cls, mock_get_next,
        mock_build_cmd, mock_run_claude, mock_check, mock_is_completed,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        task1 = make_numbered_task(1, 1, "Task 1")
        task2 = make_numbered_task(1, 2, "Task 2")
        # Simulate: task1 → completed → task2 → completed → None
        mock_get_next.side_effect = [task1, task2, None]

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
        )

        assert mock_run_claude.call_count == 2
        assert mock_get_next.call_count == 3
        assert mock_is_completed.call_count == 2
        captured = capsys.readouterr()
        assert "All tasks completed!" in captured.out

    @patch("i2code.implement.implement.is_task_completed", return_value=False)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    @patch("i2code.implement.implement.Repo")
    def test_exits_when_task_not_marked_complete(
        self, mock_repo_cls, mock_get_next,
        mock_build_cmd, mock_run_claude, mock_check, mock_is_completed,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        mock_get_next.return_value = make_numbered_task(1, 1, "Set up")

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        with pytest.raises(SystemExit) as exc_info:
            run_trunk_loop(
                idea_directory="/fake/repo/ideas/test-feature",
                idea_name="test-feature",
            )

        assert exc_info.value.code == 1
        mock_get_next.assert_called_once()
        mock_is_completed.assert_called_once()

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_claude_command")
    @patch("i2code.implement.implement.get_next_task")
    @patch("i2code.implement.implement.Repo")
    def test_uses_mock_claude_when_provided(
        self, mock_repo_cls, mock_get_next,
        mock_build_cmd, mock_run_claude, mock_check, mock_is_completed,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        task = make_numbered_task(1, 1, "Set up")
        mock_get_next.side_effect = [task, None]

        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            mock_claude="/path/to/mock-script",
        )

        mock_get_next.assert_called()
        mock_is_completed.assert_called_once()
        # Should NOT call build_claude_command when mock_claude is provided
        mock_build_cmd.assert_not_called()
        # Should invoke run_claude_interactive with [mock_script, task_description]
        mock_run_claude.assert_called_once()
        cmd_used = mock_run_claude.call_args[0][0]
        assert cmd_used == ["/path/to/mock-script", task.print()]

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.calculate_claude_permissions", return_value=["Bash(git commit:*)", "Write(/fake/repo/)"])
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.implement.run_claude_with_output_capture")
    @patch("i2code.implement.implement.build_claude_command", return_value=["claude", "-p", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    @patch("i2code.implement.implement.Repo")
    def test_non_interactive_passes_allowed_tools(
        self, mock_repo_cls, mock_get_next,
        mock_build_cmd, mock_run_claude, mock_check,
        mock_calc_perms, mock_is_completed,
    ):
        from i2code.implement.implement import run_trunk_loop

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/fake/repo"
        mock_repo.head.commit.hexsha = "aaa"
        mock_repo_cls.return_value = mock_repo

        task = make_numbered_task(1, 1, "Task 1")
        mock_get_next.side_effect = [task, None]
        mock_run_claude.return_value = ClaudeResult(returncode=0, stdout="<SUCCESS>task implemented: abc123</SUCCESS>", stderr="")

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            non_interactive=True,
        )

        mock_get_next.assert_called()
        mock_is_completed.assert_called_once()
        mock_calc_perms.assert_called_once_with("/fake/repo")
        mock_build_cmd.assert_called_once_with(
            "/fake/repo/ideas/test-feature",
            task.print(),
            interactive=False,
            extra_prompt=None,
            extra_cli_args=["--allowedTools", "Bash(git commit:*),Write(/fake/repo/)"],
        )
