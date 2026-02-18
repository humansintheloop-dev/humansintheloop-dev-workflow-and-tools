"""Tests for TrunkMode class using fakes — zero @patch decorators."""

import os
import tempfile

import pytest

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.implement.trunk_mode import TrunkMode

from conftest import write_plan_file, mark_task_complete, advance_head, combined
from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository


@pytest.mark.unit
class TestTrunkModeExecute:
    """TrunkMode.execute() drives the task loop using injected collaborators."""

    def test_no_tasks_remaining_prints_all_completed(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            write_plan_file(idea_dir, idea_name, [
                (1, 1, "Already done", True),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            mode = TrunkMode(
                git_repo=fake_repo,
                project=project,
                claude_runner=fake_runner,
            )
            mode.execute()

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out
            assert len(fake_runner.calls) == 0

    def test_invokes_claude_for_first_task(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            # Simulate: Claude advances HEAD and marks task complete
            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up project"),
                )
            )

            mode = TrunkMode(
                git_repo=fake_repo,
                project=project,
                claude_runner=fake_runner,
            )
            mode.execute()

            assert len(fake_runner.calls) == 1
            method, cmd, cwd = fake_runner.calls[0]
            assert method == "run_interactive"
            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out

    def test_exits_on_claude_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()
            fake_runner.set_result(ClaudeResult(
                returncode=1, stdout="", stderr="error",
            ))

            mode = TrunkMode(
                git_repo=fake_repo,
                project=project,
                claude_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1
            assert len(fake_runner.calls) == 1

    def test_loops_through_multiple_tasks(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Task 1", False),
                (1, 2, "Task 2", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effects([
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Task 1"),
                ),
                combined(
                    advance_head(fake_repo, "ccc"),
                    mark_task_complete(plan_path, 1, 2, "Task 2"),
                ),
            ])

            mode = TrunkMode(
                git_repo=fake_repo,
                project=project,
                claude_runner=fake_runner,
            )
            mode.execute()

            assert len(fake_runner.calls) == 2
            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out

    def test_exits_when_task_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            # Advance HEAD (success) but do NOT mark task complete
            fake_runner.set_side_effect(
                advance_head(fake_repo, "bbb"),
            )

            mode = TrunkMode(
                git_repo=fake_repo,
                project=project,
                claude_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1

    def test_non_interactive_uses_run_with_capture(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up"),
                )
            )
            fake_runner.set_result(ClaudeResult(
                returncode=0,
                stdout="<SUCCESS>task implemented: bbb</SUCCESS>",
                stderr="",
            ))

            mode = TrunkMode(
                git_repo=fake_repo,
                project=project,
                claude_runner=fake_runner,
            )
            mode.execute(non_interactive=True, mock_claude="/mock")

            assert len(fake_runner.calls) == 1
            method, cmd, cwd = fake_runner.calls[0]
            assert method == "run_with_capture"
            assert cmd[0] == "/mock"

    def test_mock_claude_bypasses_command_builder(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up"),
                )
            )

            mode = TrunkMode(
                git_repo=fake_repo,
                project=project,
                claude_runner=fake_runner,
            )
            mode.execute(mock_claude="/path/to/mock-script")

            assert len(fake_runner.calls) == 1
            method, cmd, cwd = fake_runner.calls[0]
            assert cmd[0] == "/path/to/mock-script"
