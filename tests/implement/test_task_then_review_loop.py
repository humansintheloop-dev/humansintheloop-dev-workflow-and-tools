"""Tests for the transition from task execution to review poll loop.

When address_review_comments is True and tasks remain, tasks execute normally
first; after the last task completes, the review poll loop activates.
"""

import os
import tempfile

import pytest

from i2code.implement.github_actions_monitor import GithubActionsMonitor
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.worktree_mode import LoopSteps, WorktreeMode

from conftest import write_plan_file, mark_task_complete, advance_head, combined
from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_loop_collaborators import (
    SequentialReviewProcessor,
    NoOpBuildFixer,
    NoOpCommitRecovery,
)
from fake_workflow_state import FakeWorkflowState


def _setup_idea(tmpdir, tasks):
    """Create idea directory, plan file, and CI workflow."""
    idea_name = "test-feature"
    idea_dir = os.path.join(tmpdir, idea_name)
    os.makedirs(idea_dir)
    plan_path = write_plan_file(idea_dir, idea_name, tasks)
    workflows_dir = os.path.join(tmpdir, ".github", "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    with open(os.path.join(workflows_dir, "ci.yml"), "w") as f:
        f.write("name: CI\n")
    return plan_path, idea_dir


def _make_mode(tmpdir, *, tasks, feedback_count):
    """Create a WorktreeMode that executes tasks then enters review poll loop.

    Args:
        tmpdir: Temporary directory for the test.
        tasks: List of (thread, task_num, title, completed) tuples.
        feedback_count: Number of process_feedback() calls (all return False).

    Returns:
        (mode, fake_runner, review_processor, plan_path, fake_repo)
    """
    plan_path, idea_dir = _setup_idea(tmpdir, tasks)
    project = IdeaProject(idea_dir)

    fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
    fake_gh = FakeGitHubClient()
    fake_gh.set_pr_state(42, "MERGED")
    fake_repo._gh_client = fake_gh
    fake_repo.pr_number = 42
    fake_repo.set_pushed(True)

    fake_runner = FakeClaudeRunner()
    review_processor = SequentialReviewProcessor([False] * feedback_count)

    ci_monitor = GithubActionsMonitor(
        gh_client=fake_gh, skip_ci_wait=True, ci_timeout=600,
    )

    loop_steps = LoopSteps(
        claude_runner=fake_runner,
        state=FakeWorkflowState(),
        ci_monitor=ci_monitor,
        build_fixer=NoOpBuildFixer(),
        review_processor=review_processor,
        commit_recovery=NoOpCommitRecovery(),
    )

    opts = ImplementOpts(
        idea_directory=idea_dir,
        skip_ci_wait=True,
        address_review_comments=True,
    )

    mode = WorktreeMode(
        opts=opts,
        git_repo=fake_repo,
        work_project=project,
        loop_steps=loop_steps,
    )
    return mode, fake_runner, review_processor, plan_path, fake_repo


@pytest.mark.unit
class TestTaskExecutionThenReviewPollLoop:
    """When address_review_comments is True and tasks remain, tasks execute
    normally first; after the last task, the review poll loop activates."""

    def test_one_task_executes_then_review_loop_activates(self, capsys):
        """One incomplete task executes via ClaudeRunner, then the review poll
        loop activates and exits when PR is merged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # feedback_count = 3:
            #   main loop iter 1: False (task found, executed)
            #   main loop iter 2: False (no task -> poll loop)
            #   poll loop iter 1: False -> check PR -> MERGED -> exit
            mode, fake_runner, review_proc, plan_path, fake_repo = _make_mode(
                tmpdir,
                tasks=[(1, 1, "Set up project", False)],
                feedback_count=3,
            )

            fake_runner.set_side_effects([
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up project"),
                ),
            ])

            mode.execute()

            assert len(fake_runner.calls) == 1
            assert fake_runner.calls[0][0] == "run"
            assert review_proc.call_count == 3

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out
            assert "merged" in captured.out.lower()

    def test_multiple_tasks_execute_then_review_loop_activates(self, capsys):
        """All incomplete tasks execute in order; review poll loop activates
        only after the last task completes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # feedback_count = 4:
            #   main loop iter 1: False (task 1.1 found, executed)
            #   main loop iter 2: False (task 1.2 found, executed)
            #   main loop iter 3: False (no task -> poll loop)
            #   poll loop iter 1: False -> check PR -> MERGED -> exit
            mode, fake_runner, review_proc, plan_path, fake_repo = _make_mode(
                tmpdir,
                tasks=[
                    (1, 1, "Set up project", False),
                    (1, 2, "Add feature", False),
                ],
                feedback_count=4,
            )

            fake_runner.set_side_effects([
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up project"),
                ),
                combined(
                    advance_head(fake_repo, "ccc"),
                    mark_task_complete(plan_path, 1, 2, "Add feature"),
                ),
            ])

            mode.execute()

            assert len(fake_runner.calls) == 2
            assert fake_runner.calls[0][0] == "run"
            assert fake_runner.calls[1][0] == "run"
            assert review_proc.call_count == 4

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out
            assert "merged" in captured.out.lower()
