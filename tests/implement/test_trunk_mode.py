"""Tests for TrunkMode class using fakes — zero @patch decorators."""

import os
import tempfile
from contextlib import contextmanager

import pytest

from i2code.implement.claude_runner import CapturedOutput, ClaudeResult
from i2code.implement.commit_recovery import TaskCommitRecovery
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.trunk_mode import TrunkMode
from i2code.implement.workspace import Workspace

from conftest import write_plan_file, mark_task_complete, advance_head, combined
from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository


def _opts(**kwargs):
    """Build ImplementOpts with defaults suitable for TrunkMode tests."""
    kwargs.setdefault("idea_directory", "/tmp/fake-idea")
    return ImplementOpts(**kwargs)


def _noop_commit_recovery(project, fake_runner):
    """Create a TaskCommitRecovery that finds nothing to recover."""
    return TaskCommitRecovery(git_repo=FakeGitRepository(), project=project, claude_runner=fake_runner)


def _make_trunk_mode(task_specs, opts_overrides=None):
    """Create a TrunkMode test environment.

    Returns (mode, project, fake_repo, fake_runner, plan_path).
    """
    tmpdir = tempfile.mkdtemp()
    idea_name = "test-feature"
    idea_dir = os.path.join(tmpdir, idea_name)
    os.makedirs(idea_dir)
    plan_path = write_plan_file(idea_dir, idea_name, task_specs)

    project = IdeaProject(idea_dir)
    fake_repo = FakeGitRepository()
    fake_runner = FakeClaudeRunner()

    mode = TrunkMode(
        opts=_opts(**(opts_overrides or {})),
        workspace=Workspace(fake_repo, project),
        claude_runner=fake_runner,
        commit_recovery=_noop_commit_recovery(project, fake_runner),
    )
    return mode, project, fake_repo, fake_runner, plan_path


@contextmanager
def _trunk_mode_setup(tasks):
    """Create common test infrastructure: tmpdir, project, fakes, and plan file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_name = "test-feature"
        idea_dir = os.path.join(tmpdir, idea_name)
        os.makedirs(idea_dir)
        plan_path = write_plan_file(idea_dir, idea_name, tasks)
        project = IdeaProject(idea_dir)
        fake_repo = FakeGitRepository()
        fake_runner = FakeClaudeRunner()
        yield project, fake_repo, fake_runner, plan_path


def _build_trunk_mode(project, fake_repo, fake_runner, **opts_kwargs):
    """Build a TrunkMode with noop commit recovery."""
    return TrunkMode(
        opts=_opts(**opts_kwargs),
        workspace=Workspace(fake_repo, project),
        claude_runner=fake_runner,
        commit_recovery=_noop_commit_recovery(project, fake_runner),
    )


@pytest.mark.unit
class TestTrunkModeExecute:
    """TrunkMode.execute() drives the task loop using injected collaborators."""

    def test_no_tasks_remaining_prints_all_completed(self, capsys):
        mode, _, _, fake_runner, _ = _make_trunk_mode([(1, 1, "Already done", True)])
        mode.execute()

        captured = capsys.readouterr()
        assert "All tasks completed!" in captured.out
        assert len(fake_runner.calls) == 0

    def test_invokes_claude_for_first_task(self, capsys):
        mode, _, fake_repo, fake_runner, plan_path = _make_trunk_mode([(1, 1, "Set up project", False)])

        fake_runner.set_side_effect(combined(
            advance_head(fake_repo, "bbb"),
            mark_task_complete(plan_path, 1, 1, "Set up project"),
        ))
        mode.execute()

        assert len(fake_runner.calls) == 1
        assert fake_runner.calls[0][0] == "run"
        assert "All tasks completed!" in capsys.readouterr().out

    def test_exits_on_claude_failure(self):
        mode, _, _, fake_runner, _ = _make_trunk_mode([(1, 1, "Set up", False)])
        fake_runner.set_result(ClaudeResult(returncode=1, output=CapturedOutput(stderr="error")))

        with pytest.raises(SystemExit) as exc_info:
            mode.execute()
        assert exc_info.value.code == 1
        assert len(fake_runner.calls) == 3

    def test_loops_through_multiple_tasks(self, capsys):
        mode, _, fake_repo, fake_runner, plan_path = _make_trunk_mode([
            (1, 1, "Task 1", False), (1, 2, "Task 2", False),
        ])
        fake_runner.set_side_effects([
            combined(advance_head(fake_repo, "bbb"), mark_task_complete(plan_path, 1, 1, "Task 1")),
            combined(advance_head(fake_repo, "ccc"), mark_task_complete(plan_path, 1, 2, "Task 2")),
        ])
        mode.execute()

        assert len(fake_runner.calls) == 2
        assert "All tasks completed!" in capsys.readouterr().out

    def test_exits_when_task_not_marked_complete(self):
        mode, _, fake_repo, fake_runner, _ = _make_trunk_mode([(1, 1, "Set up", False)])
        fake_runner.set_side_effect(advance_head(fake_repo, "bbb"))

        with pytest.raises(SystemExit) as exc_info:
            mode.execute()
        assert exc_info.value.code == 1

    def test_non_interactive_uses_run(self, capsys):
        mode, _, fake_repo, fake_runner, plan_path = _make_trunk_mode(
            [(1, 1, "Set up", False)], opts_overrides=dict(non_interactive=True, mock_claude="/mock"),
        )
        fake_runner.set_side_effect(combined(
            advance_head(fake_repo, "bbb"), mark_task_complete(plan_path, 1, 1, "Set up"),
        ))
        fake_runner.set_result(ClaudeResult(
            returncode=0, output=CapturedOutput("<SUCCESS>task implemented: bbb</SUCCESS>"),
        ))
        mode.execute()

        assert len(fake_runner.calls) == 1
        method, cmd, _ = fake_runner.calls[0]
        assert method == "run"
        assert cmd[0] == "/mock"

    def test_mock_claude_bypasses_command_builder(self, capsys):
        mode, _, fake_repo, fake_runner, plan_path = _make_trunk_mode(
            [(1, 1, "Set up", False)], opts_overrides=dict(mock_claude="/path/to/mock-script"),
        )
        fake_runner.set_side_effect(combined(
            advance_head(fake_repo, "bbb"), mark_task_complete(plan_path, 1, 1, "Set up"),
        ))
        mode.execute()

        assert len(fake_runner.calls) == 1
        assert fake_runner.calls[0][1][0] == "/path/to/mock-script"


PLAN_WITH_INCOMPLETE_TASK = """\
# Implementation Plan: Test Feature

## Steel Thread 1: Basic Feature

- [ ] **Task 1.1: Implement feature**
  - TaskType: OUTCOME
  - Steps:
    - [ ] Step one
    - [ ] Step two
"""

PLAN_WITH_COMPLETED_TASK_1 = """\
# Implementation Plan: Test Feature

## Steel Thread 1: Basic Feature

- [x] **Task 1.1: Implement feature**
  - TaskType: OUTCOME
  - Steps:
    - [x] Step one
    - [x] Step two
"""


def _make_trunk_mode_with_recovery(task_specs, diff_output="", file_at_head=None):
    """Create a TrunkMode with real TaskCommitRecovery.

    Returns (mode, project, fake_repo, fake_runner, plan_path).
    """
    tmpdir = tempfile.mkdtemp()
    idea_name = "test-feature"
    idea_dir = os.path.join(tmpdir, idea_name)
    os.makedirs(idea_dir)
    plan_path = write_plan_file(idea_dir, idea_name, task_specs)

    project = IdeaProject(idea_dir)
    fake_repo = FakeGitRepository()
    fake_runner = FakeClaudeRunner()

    fake_repo.set_diff_output(diff_output)
    if file_at_head is not None:
        fake_repo.set_file_at_head(project.plan_file, file_at_head)

    commit_recovery = TaskCommitRecovery(git_repo=fake_repo, project=project, claude_runner=fake_runner)

    mode = TrunkMode(
        opts=_opts(),
        workspace=Workspace(fake_repo, project),
        claude_runner=fake_runner,
        commit_recovery=commit_recovery,
    )
    return mode, project, fake_repo, fake_runner, plan_path


@pytest.mark.unit
class TestTrunkModeWithRecovery:
    """TrunkMode.execute() runs recovery before the task loop when needed."""

    def test_recovery_needed_and_succeeds_then_main_loop_continues(self, capsys):
        """When recovery is needed and succeeds, the main loop continues with next task."""
        mode, _, fake_repo, fake_runner, plan_path = _make_trunk_mode_with_recovery(
            [(1, 1, "Already recovered", True), (1, 2, "Next task", False)],
            diff_output="some diff output",
            file_at_head=PLAN_WITH_INCOMPLETE_TASK,
        )

        fake_runner.set_results([
            ClaudeResult(returncode=0, output=CapturedOutput("<SUCCESS>recovery commit: bbb</SUCCESS>")),
            ClaudeResult(returncode=0),
        ])
        fake_runner.set_side_effects([
            advance_head(fake_repo, "bbb"),
            combined(advance_head(fake_repo, "ccc"), mark_task_complete(plan_path, 1, 2, "Next task")),
        ])
        mode.execute()

        assert len(fake_runner.calls) == 2
        assert fake_runner.calls[0][0] == "run_batch"
        assert fake_runner.calls[1][0] == "run"
        captured = capsys.readouterr()
        assert "Detected uncommitted changes" in captured.out
        assert "All tasks completed!" in captured.out

    def test_no_recovery_needed_main_loop_starts_normally(self, capsys):
        """When no recovery is needed, the main loop starts normally."""
        mode, _, fake_repo, fake_runner, plan_path = _make_trunk_mode_with_recovery(
            [(1, 1, "Set up project", False)],
        )

        fake_runner.set_side_effect(combined(
            advance_head(fake_repo, "bbb"), mark_task_complete(plan_path, 1, 1, "Set up project"),
        ))
        mode.execute()

        assert len(fake_runner.calls) == 1
        assert fake_runner.calls[0][0] == "run"
        captured = capsys.readouterr()
        assert "Detected uncommitted changes" not in captured.out
        assert "All tasks completed!" in captured.out
