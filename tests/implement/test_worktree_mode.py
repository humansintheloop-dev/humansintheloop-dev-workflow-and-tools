"""Tests for WorktreeMode class using fakes — zero @patch decorators."""

import os
import tempfile

import pytest

from i2code.implement.claude_runner import CapturedOutput, ClaudeResult
from i2code.implement.commit_recovery import TaskCommitRecovery
from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixer
from i2code.implement.github_actions_monitor import GithubActionsMonitor
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.worktree_mode import LoopSteps, WorktreeMode

from conftest import write_plan_file, mark_task_complete, advance_head, combined
from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState


def _write_ci_workflow(work_dir):
    """Create a minimal CI workflow file so has_ci_workflow_files passes."""
    workflows_dir = os.path.join(work_dir, ".github", "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    with open(os.path.join(workflows_dir, "ci.yml"), "w") as f:
        f.write("name: CI\n")


def _make_worktree_mode(
    plan_path, idea_dir, work_dir,
    fake_repo=None, fake_runner=None, fake_gh=None, fake_state=None,
    opts=None, commit_recovery=None, clock=None,
):  # noqa: PLR0913
    """Create a WorktreeMode with fakes wired up."""
    project = IdeaProject(idea_dir)
    if fake_runner is None:
        fake_runner = FakeClaudeRunner()
    if fake_gh is None:
        fake_gh = FakeGitHubClient()
    if fake_state is None:
        fake_state = FakeWorkflowState()
    if fake_repo is None:
        fake_repo = FakeGitRepository(working_tree_dir=work_dir, gh_client=fake_gh)
    elif fake_repo.gh_client is None:
        fake_repo._gh_client = fake_gh
    if opts is None:
        opts = ImplementOpts(idea_directory=idea_dir)

    ci_monitor = GithubActionsMonitor(
        gh_client=fake_gh,
        skip_ci_wait=opts.skip_ci_wait,
        ci_timeout=opts.ci_timeout,
    )

    build_fixer = GithubActionsBuildFixer(
        opts=opts,
        git_repo=fake_repo,
        claude_runner=fake_runner,
    )

    review_processor = PullRequestReviewProcessor(
        opts=opts,
        git_repo=fake_repo,
        state=fake_state,
        claude_runner=fake_runner,
    )

    if commit_recovery is None:
        noop_repo = FakeGitRepository()
        commit_recovery = TaskCommitRecovery(
            git_repo=noop_repo, project=project, claude_runner=fake_runner,
        )
    loop_steps = LoopSteps(
        claude_runner=fake_runner,
        state=fake_state,
        ci_monitor=ci_monitor,
        build_fixer=build_fixer,
        review_processor=review_processor,
        commit_recovery=commit_recovery,
        clock=clock,
    )
    mode = WorktreeMode(
        opts=opts,
        git_repo=fake_repo,
        work_project=project,
        loop_steps=loop_steps,
    )
    return mode, fake_repo, fake_runner, fake_gh, fake_state


@pytest.mark.unit
class TestWorktreeModeAllComplete:
    """When no tasks remain, WorktreeMode prints completion and PR URL."""

    def test_no_tasks_remaining_prints_all_completed(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Already done", True),
            ])

            mode, fake_repo, fake_runner, fake_gh, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
            )
            mode.execute()

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out
            assert len(fake_runner.calls) == 0

    def test_all_complete_prints_pr_url(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Already done", True),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.pr_number = 42
            fake_gh = FakeGitHubClient()
            fake_gh.set_pr_url(42, "https://github.com/owner/repo/pull/42")

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_gh=fake_gh,
            )
            mode.execute()

            captured = capsys.readouterr()
            assert "https://github.com/owner/repo/pull/42" in captured.out


@pytest.mark.unit
class TestWorktreeModeTaskExecution:
    """WorktreeMode executes tasks, pushes, creates PR, and waits for CI."""

    def test_executes_single_task_push_pr_ci(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up project"),
                )
            )

            mode, _, _, fake_gh, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
            )
            mode.execute()

            # Claude was invoked
            assert len(fake_runner.calls) == 1
            # Push was called
            assert ("push",) in fake_repo.calls
            # PR was created
            assert any(c[0] == "ensure_pr" for c in fake_repo.calls)
            # CI was waited on (via GithubActionsMonitor → gh_client)
            assert any(c[0] == "wait_for_workflow_completion" for c in fake_gh.calls)

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out

    def test_reuses_existing_pr(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.pr_number = 42  # Pre-existing PR
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up project"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
                opts=ImplementOpts(idea_directory=idea_dir, skip_ci_wait=True),
            )
            mode.execute()

            # ensure_pr should NOT have been called since PR already exists
            assert not any(c[0] == "ensure_pr" for c in fake_repo.calls)

    def test_uses_detected_default_branch_for_pr(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            fake_gh = FakeGitHubClient()
            fake_gh.set_default_branch("master")

            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner, fake_gh=fake_gh,
                opts=ImplementOpts(idea_directory=idea_dir, skip_ci_wait=True),
            )
            mode.execute()

            # ensure_pr was called
            ensure_pr_calls = [c for c in fake_repo.calls if c[0] == "ensure_pr"]
            assert len(ensure_pr_calls) == 1


def _run_with_fake_clock(capsys, start, end):
    """Run a single task with a fake clock and return captured stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_name = "test-feature"
        idea_dir = os.path.join(tmpdir, idea_name)
        os.makedirs(idea_dir)
        plan_path = write_plan_file(idea_dir, idea_name, [
            (1, 1, "Set up project", False),
        ])
        _write_ci_workflow(tmpdir)

        fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
        fake_runner = FakeClaudeRunner()

        fake_runner.set_side_effect(
            combined(
                advance_head(fake_repo, "bbb"),
                mark_task_complete(plan_path, 1, 1, "Set up project"),
            )
        )

        clock_values = iter([start, end])
        mode, _, _, _, _ = _make_worktree_mode(
            plan_path, idea_dir, tmpdir,
            fake_repo=fake_repo, fake_runner=fake_runner,
            opts=ImplementOpts(idea_directory=idea_dir, skip_ci_wait=True),
            clock=lambda: next(clock_values),
        )
        mode.execute()

        return capsys.readouterr().out


@pytest.mark.unit
@pytest.mark.parametrize("start,end,expected_duration", [
    (100.0, 145.0, "45 seconds"),
    (100.0, 101.0, "1 second"),
    (100.0, 280.0, "3 minutes"),
    (100.0, 160.0, "1 minute"),
])
def test_prints_task_duration(capsys, start, end, expected_duration):
    output = _run_with_fake_clock(capsys, start, end)
    assert f"Task completed successfully in {expected_duration}." in output


@pytest.mark.unit
class TestWorktreeModeFailures:
    """WorktreeMode exits on various failure conditions."""

    def test_exits_on_claude_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            fake_runner = FakeClaudeRunner()
            fake_runner.set_result(ClaudeResult(
                returncode=1, output=CapturedOutput(stderr="error"),
            ))

            mode, _, _, _, _ = _make_worktree_mode(
                write_plan_file(idea_dir, idea_name, [(1, 1, "Set up", False)]),
                idea_dir, tmpdir, fake_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1

    def test_exits_when_task_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            # Advance HEAD (success) but do NOT mark task complete
            fake_runner.set_side_effect(
                advance_head(fake_repo, "bbb"),
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1

    def test_exits_when_no_ci_workflow_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])
            # Deliberately do NOT create .github/workflows/

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1

    def test_exits_when_push_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.push = lambda: (fake_repo.calls.append(("push",)) or False)  # push returns False
            fake_runner = FakeClaudeRunner()
            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1


@pytest.mark.unit
class TestWorktreeModeNonInteractive:
    """WorktreeMode in non-interactive mode uses run_with_capture."""

    def test_non_interactive_uses_capture_and_checks_success_tag(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            fake_runner.set_result(ClaudeResult(
                returncode=0,
                output=CapturedOutput("<SUCCESS>task implemented: bbb</SUCCESS>"),
            ))
            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
                opts=ImplementOpts(idea_directory=idea_dir, non_interactive=True, mock_claude="/mock", skip_ci_wait=True),
            )
            mode.execute()

            assert len(fake_runner.calls) == 1
            method, cmd, cwd = fake_runner.calls[0]
            assert method == "run_with_capture"

    def test_non_interactive_exits_without_success_tag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            fake_runner.set_result(ClaudeResult(
                returncode=0,
                output=CapturedOutput("some output without success tag"),
            ))
            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
                opts=ImplementOpts(idea_directory=idea_dir, non_interactive=True, mock_claude="/mock"),
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1


PLAN_WITH_INCOMPLETE_TASK = """\
# Implementation Plan: Test Feature

## Steel Thread 1: Basic Feature

- [ ] **Task 1.1: Implement feature**
  - TaskType: OUTCOME
  - Steps:
    - [ ] Step one
    - [ ] Step two
"""


@pytest.mark.unit
class TestWorktreeModeWithRecovery:
    """WorktreeMode.execute() runs recovery before the task loop when needed."""

    def test_recovery_needed_and_succeeds_then_main_loop_continues(self, capsys):
        """When recovery is needed and succeeds, recovery call happens before task-loop call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)

            # Task 1.1 already completed (recovered), task 1.2 pending
            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Already recovered", True),
                (1, 2, "Next task", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()

            project = IdeaProject(idea_dir)

            # Set up TaskCommitRecovery to detect recovery is needed
            fake_repo.set_diff_output("some diff output")
            fake_repo.set_file_at_head(
                project.plan_file,
                PLAN_WITH_INCOMPLETE_TASK,
            )

            commit_recovery = TaskCommitRecovery(
                git_repo=fake_repo, project=project, claude_runner=fake_runner,
            )

            # Two Claude calls: (1) recovery commit (non-interactive), (2) execute task 1.2
            fake_runner.set_results([
                ClaudeResult(returncode=0, output=CapturedOutput("<SUCCESS>recovery commit: bbb</SUCCESS>")),
                ClaudeResult(returncode=0),
            ])
            fake_runner.set_side_effects([
                advance_head(fake_repo, "bbb"),  # recovery advances HEAD
                combined(
                    advance_head(fake_repo, "ccc"),
                    mark_task_complete(plan_path, 1, 2, "Next task"),
                ),
            ])

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
                commit_recovery=commit_recovery,
                opts=ImplementOpts(idea_directory=idea_dir, skip_ci_wait=True),
            )
            mode.execute()

            # Recovery Claude call (non-interactive) happens before task-loop call
            assert len(fake_runner.calls) == 2
            assert fake_runner.calls[0][0] == "run_with_capture"  # recovery
            assert fake_runner.calls[1][0] == "run_interactive"  # task execution

            captured = capsys.readouterr()
            assert "Detected uncommitted changes" in captured.out
            assert "All tasks completed!" in captured.out

    def test_no_recovery_needed_main_loop_starts_normally(self, capsys):
        """When no recovery is needed, the main loop starts without recovery call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)

            plan_path = write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()

            project = IdeaProject(idea_dir)

            # No diff = no recovery needed
            fake_repo.set_diff_output("")

            commit_recovery = TaskCommitRecovery(
                git_repo=fake_repo, project=project, claude_runner=fake_runner,
            )

            fake_runner.set_side_effect(
                combined(
                    advance_head(fake_repo, "bbb"),
                    mark_task_complete(plan_path, 1, 1, "Set up project"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
                commit_recovery=commit_recovery,
                opts=ImplementOpts(idea_directory=idea_dir, skip_ci_wait=True),
            )
            mode.execute()

            # Only one Claude call for task execution, no recovery
            assert len(fake_runner.calls) == 1
            method, cmd, cwd = fake_runner.calls[0]
            assert method == "run_interactive"

            captured = capsys.readouterr()
            assert "Detected uncommitted changes" not in captured.out
            assert "All tasks completed!" in captured.out
