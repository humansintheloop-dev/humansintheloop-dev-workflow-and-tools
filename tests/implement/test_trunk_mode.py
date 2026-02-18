"""Tests for TrunkMode class using fakes — zero @patch decorators."""

import os
import tempfile

import pytest

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.implement.trunk_mode import TrunkMode

from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository


def _write_plan_file(plan_dir, idea_name, tasks):
    """Write a plan file with the given tasks.

    Args:
        plan_dir: Directory to write the plan file in.
        idea_name: Name of the idea.
        tasks: List of (thread, task_num, title, completed) tuples.

    Returns:
        Path to the written plan file.
    """
    lines = [f"# Plan for {idea_name}\n\n"]
    current_thread = None
    for thread, task_num, title, completed in tasks:
        if thread != current_thread:
            lines.append(f"## Steel Thread {thread}: Thread {thread}\n\n")
            current_thread = thread
        checkbox = "[x]" if completed else "[ ]"
        lines.append(
            f"- {checkbox} **Task {thread}.{task_num}: {title}**\n"
        )
    plan_path = os.path.join(plan_dir, f"{idea_name}-plan.md")
    with open(plan_path, "w") as f:
        f.writelines(lines)
    return plan_path


def _mark_task_complete(plan_path, thread, task_num, title):
    """Return a callable that marks a task as complete in the plan file."""
    def _mark():
        with open(plan_path, "r") as f:
            content = f.read()
        old = f"- [ ] **Task {thread}.{task_num}: {title}**"
        new = f"- [x] **Task {thread}.{task_num}: {title}**"
        content = content.replace(old, new)
        with open(plan_path, "w") as f:
            f.write(content)
    return _mark


def _advance_head(fake_repo, new_sha):
    """Return a callable that advances the fake repo's HEAD."""
    def _advance():
        fake_repo.set_head_sha(new_sha)
    return _advance


def _combined(*fns):
    """Return a callable that calls all given functions in order."""
    def _run():
        for fn in fns:
            fn()
    return _run


@pytest.mark.unit
class TestTrunkModeExecute:
    """TrunkMode.execute() drives the task loop using injected collaborators."""

    def test_no_tasks_remaining_prints_all_completed(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            _write_plan_file(idea_dir, idea_name, [
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            # Simulate: Claude advances HEAD and marks task complete
            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up project"),
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
            _write_plan_file(idea_dir, idea_name, [
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Task 1", False),
                (1, 2, "Task 2", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effects([
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Task 1"),
                ),
                _combined(
                    _advance_head(fake_repo, "ccc"),
                    _mark_task_complete(plan_path, 1, 2, "Task 2"),
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
            _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            # Advance HEAD (success) but do NOT mark task complete
            fake_runner.set_side_effect(
                _advance_head(fake_repo, "bbb"),
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up"),
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            project = IdeaProject(idea_dir)
            fake_repo = FakeGitRepository()
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up"),
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
