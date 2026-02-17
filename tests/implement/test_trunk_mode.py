"""Tests for --trunk mode of i2code implement."""


import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from i2code.implement.cli import implement_cmd
from i2code.implement.claude_runner import ClaudeResult
from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task

from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository


def make_numbered_task(thread: int, task: int, title: str) -> NumberedTask:
    return NumberedTask(
        number=TaskNumber(thread=thread, task=task),
        task=Task(_lines=[f"- [ ] **Task {thread}.{task}: {title}**"]),
    )


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


@pytest.mark.unit
class TestTrunkModeAcceptance:
    """Acceptance test: --trunk with mock-claude executes tasks and prints completion."""

    @patch("i2code.implement.cli.run_trunk_loop")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.IdeaProject")
    def test_trunk_mode_dispatches_to_run_trunk_loop(
        self, mock_idea_project_cls, mock_validate_committed,
        mock_run_trunk_loop
    ):
        mock_idea_project_cls.return_value = _make_mock_project()
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
    @patch("i2code.implement.cli.IdeaProject")
    def test_trunk_with_incompatible_flag_raises_usage_error(
        self, mock_idea_project_cls, mock_validate_committed,
        flag,
    ):
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
        mock_idea_project_cls.return_value = _make_mock_project()
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--trunk", flag, value])

        assert result.exit_code != 0


@pytest.mark.unit
class TestRunTrunkLoop:
    """Unit tests for run_trunk_loop using FakeGitRepository and FakeClaudeRunner."""

    @patch("i2code.implement.implement.get_next_task", return_value=None)
    def test_no_tasks_remaining_prints_all_completed(
        self, mock_get_next,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        fake_repo = FakeGitRepository()

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            git_repo=fake_repo,
        )

        mock_get_next.assert_called_once()
        captured = capsys.readouterr()
        assert "All tasks completed!" in captured.out

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.command_builder.CommandBuilder.build_task_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    def test_invokes_claude_for_first_task(
        self, mock_get_next,
        mock_build_cmd, mock_check, mock_is_completed,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        fake_repo = FakeGitRepository()
        fake_runner = FakeClaudeRunner()

        task = make_numbered_task(1, 1, "Set up project")
        mock_get_next.side_effect = [task, None]

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            git_repo=fake_repo,
            claude_runner=fake_runner,
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
        assert len(fake_runner.calls) == 1
        method, cmd, cwd = fake_runner.calls[0]
        assert method == "run_interactive"
        assert cmd == ["claude", "do task"]

    @patch("i2code.implement.implement.calculate_claude_permissions", return_value=["Bash(git commit:*)"])
    @patch("i2code.implement.implement.check_claude_success", return_value=False)
    @patch("i2code.implement.command_builder.CommandBuilder.build_task_command", return_value=["claude", "-p", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    def test_exits_on_claude_failure(
        self, mock_get_next,
        mock_build_cmd, mock_check, mock_calc_perms,
    ):
        from i2code.implement.implement import run_trunk_loop

        fake_repo = FakeGitRepository()
        fake_runner = FakeClaudeRunner()
        fake_runner.set_result(ClaudeResult(returncode=1, stdout="<FAILURE>something went wrong</FAILURE>", stderr=""))

        mock_get_next.return_value = make_numbered_task(1, 1, "Set up")

        with pytest.raises(SystemExit) as exc_info:
            run_trunk_loop(
                idea_directory="/fake/repo/ideas/test-feature",
                idea_name="test-feature",
                non_interactive=True,
                git_repo=fake_repo,
                claude_runner=fake_runner,
            )

        assert exc_info.value.code == 1
        mock_get_next.assert_called_once()
        assert len(fake_runner.calls) == 1
        assert fake_runner.calls[0][0] == "run_with_capture"

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.command_builder.CommandBuilder.build_task_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    def test_loops_through_multiple_tasks(
        self, mock_get_next,
        mock_build_cmd, mock_check, mock_is_completed,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        fake_repo = FakeGitRepository()
        fake_runner = FakeClaudeRunner()

        task1 = make_numbered_task(1, 1, "Task 1")
        task2 = make_numbered_task(1, 2, "Task 2")
        mock_get_next.side_effect = [task1, task2, None]

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            git_repo=fake_repo,
            claude_runner=fake_runner,
        )

        assert len(fake_runner.calls) == 2
        assert mock_get_next.call_count == 3
        assert mock_is_completed.call_count == 2
        captured = capsys.readouterr()
        assert "All tasks completed!" in captured.out

    @patch("i2code.implement.implement.is_task_completed", return_value=False)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.command_builder.CommandBuilder.build_task_command", return_value=["claude", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    def test_exits_when_task_not_marked_complete(
        self, mock_get_next,
        mock_build_cmd, mock_check, mock_is_completed,
    ):
        from i2code.implement.implement import run_trunk_loop

        fake_repo = FakeGitRepository()
        fake_runner = FakeClaudeRunner()

        mock_get_next.return_value = make_numbered_task(1, 1, "Set up")

        with pytest.raises(SystemExit) as exc_info:
            run_trunk_loop(
                idea_directory="/fake/repo/ideas/test-feature",
                idea_name="test-feature",
                git_repo=fake_repo,
                claude_runner=fake_runner,
            )

        assert exc_info.value.code == 1
        mock_get_next.assert_called_once()
        mock_is_completed.assert_called_once()

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.command_builder.CommandBuilder.build_task_command")
    @patch("i2code.implement.implement.get_next_task")
    def test_uses_mock_claude_when_provided(
        self, mock_get_next,
        mock_build_cmd, mock_check, mock_is_completed,
        capsys,
    ):
        from i2code.implement.implement import run_trunk_loop

        fake_repo = FakeGitRepository()
        fake_runner = FakeClaudeRunner()

        task = make_numbered_task(1, 1, "Set up")
        mock_get_next.side_effect = [task, None]

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            mock_claude="/path/to/mock-script",
            git_repo=fake_repo,
            claude_runner=fake_runner,
        )

        mock_get_next.assert_called()
        mock_is_completed.assert_called_once()
        mock_build_cmd.assert_not_called()
        assert len(fake_runner.calls) == 1
        method, cmd, cwd = fake_runner.calls[0]
        assert method == "run_interactive"
        assert cmd == ["/path/to/mock-script", task.print()]

    @patch("i2code.implement.implement.is_task_completed", return_value=True)
    @patch("i2code.implement.implement.calculate_claude_permissions", return_value=["Bash(git commit:*)", "Write(/fake/repo/)"])
    @patch("i2code.implement.implement.check_claude_success", return_value=True)
    @patch("i2code.implement.command_builder.CommandBuilder.build_task_command", return_value=["claude", "-p", "do task"])
    @patch("i2code.implement.implement.get_next_task")
    def test_non_interactive_passes_allowed_tools(
        self, mock_get_next,
        mock_build_cmd, mock_check,
        mock_calc_perms, mock_is_completed,
    ):
        from i2code.implement.implement import run_trunk_loop

        fake_repo = FakeGitRepository()
        fake_runner = FakeClaudeRunner()
        fake_runner.set_result(ClaudeResult(returncode=0, stdout="<SUCCESS>task implemented: abc123</SUCCESS>", stderr=""))

        task = make_numbered_task(1, 1, "Task 1")
        mock_get_next.side_effect = [task, None]

        run_trunk_loop(
            idea_directory="/fake/repo/ideas/test-feature",
            idea_name="test-feature",
            non_interactive=True,
            git_repo=fake_repo,
            claude_runner=fake_runner,
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
        assert len(fake_runner.calls) == 1
        assert fake_runner.calls[0][0] == "run_with_capture"
