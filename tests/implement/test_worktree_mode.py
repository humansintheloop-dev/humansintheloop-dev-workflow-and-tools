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
from fake_loop_collaborators import (
    SequentialReviewProcessor,
    SequentialBuildFixer,
    NoOpBuildFixer,
    NoOpCommitRecovery,
)
from fake_workflow_state import FakeWorkflowState


def _write_ci_workflow(work_dir):
    """Create a minimal CI workflow file so has_ci_workflow_files passes."""
    workflows_dir = os.path.join(work_dir, ".github", "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    with open(os.path.join(workflows_dir, "ci.yml"), "w") as f:
        f.write("name: CI\n")


def _setup_idea(tmpdir, tasks, *, ci_workflow=False):
    """Create idea directory and plan file, returning (plan_path, idea_dir)."""
    idea_name = "test-feature"
    idea_dir = os.path.join(tmpdir, idea_name)
    os.makedirs(idea_dir)
    plan_path = write_plan_file(idea_dir, idea_name, tasks)
    if ci_workflow:
        _write_ci_workflow(tmpdir)
    return plan_path, idea_dir


def _setup_task_with_success(tmpdir, task_name="Set up"):
    """Create a single pending task with side effects that succeed."""
    plan_path, idea_dir = _setup_idea(tmpdir, [(1, 1, task_name, False)], ci_workflow=True)
    fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
    fake_runner = FakeClaudeRunner()
    fake_runner.set_side_effect(
        combined(
            advance_head(fake_repo, "bbb"),
            mark_task_complete(plan_path, 1, 1, task_name),
        )
    )
    return plan_path, idea_dir, fake_repo, fake_runner


def _make_success_mode(tmpdir, task_name="Set up", **mode_kwargs):
    """Set up a mode with a successful task, ready to execute."""
    plan_path, idea_dir, fake_repo, fake_runner = _setup_task_with_success(tmpdir, task_name)
    mode_kwargs.setdefault('fake_repo', fake_repo)
    mode_kwargs.setdefault('fake_runner', fake_runner)
    mode_kwargs.setdefault('opts', ImplementOpts(idea_directory=idea_dir, skip_ci_wait=True))
    return _make_worktree_mode(plan_path, idea_dir, tmpdir, **mode_kwargs)


def _make_worktree_mode(plan_path, idea_dir, work_dir, **kwargs):
    """Create a WorktreeMode with fakes wired up."""
    project = IdeaProject(idea_dir)
    fake_runner = kwargs.get('fake_runner') or FakeClaudeRunner()
    fake_gh = kwargs.get('fake_gh') or FakeGitHubClient()
    fake_state = kwargs.get('fake_state') or FakeWorkflowState()
    fake_repo = kwargs.get('fake_repo')
    opts = kwargs.get('opts') or ImplementOpts(idea_directory=idea_dir)

    if fake_repo is None:
        fake_repo = FakeGitRepository(working_tree_dir=work_dir, gh_client=fake_gh)
    elif fake_repo.gh_client is None:
        fake_repo._gh_client = fake_gh

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

    commit_recovery = kwargs.get('commit_recovery')
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
        clock=kwargs.get('clock'),
    )
    mode = WorktreeMode(
        opts=opts,
        git_repo=fake_repo,
        work_project=project,
        loop_steps=loop_steps,
    )
    return mode, fake_repo, fake_runner, fake_gh, fake_state


def _make_all_complete_mode(tmpdir, *, pr_number=None, pr_url=None):
    """Create a mode where all tasks are complete, optionally with a PR."""
    plan_path, idea_dir = _setup_idea(tmpdir, [(1, 1, "Already done", True)])
    fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
    fake_repo.set_pushed(True)
    fake_gh = FakeGitHubClient()
    if pr_number is not None:
        fake_repo.pr_number = pr_number
        if pr_url:
            fake_gh.set_pr_url(pr_number, pr_url)
    mode, _, _, _, _ = _make_worktree_mode(
        plan_path, idea_dir, tmpdir,
        fake_repo=fake_repo, fake_gh=fake_gh,
    )
    return mode, fake_repo, fake_gh


@pytest.mark.unit
class TestWorktreeModeAllComplete:
    """When no tasks remain, WorktreeMode prints completion and PR URL."""

    def test_no_tasks_remaining_prints_all_completed(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, _ = _make_all_complete_mode(tmpdir)
            mode.execute()

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out

    def test_all_complete_prints_pr_url(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, _ = _make_all_complete_mode(
                tmpdir, pr_number=42, pr_url="https://github.com/owner/repo/pull/42",
            )
            mode.execute()

            captured = capsys.readouterr()
            assert "https://github.com/owner/repo/pull/42" in captured.out

    def test_all_complete_marks_pr_ready_when_pr_exists(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, fake_gh = _make_all_complete_mode(
                tmpdir, pr_number=42, pr_url="https://github.com/owner/repo/pull/42",
            )
            mode.execute()

            mark_ready_calls = [c for c in fake_gh.calls if c[0] == "mark_pr_ready"]
            assert len(mark_ready_calls) == 1
            assert mark_ready_calls[0] == ("mark_pr_ready", 42)

            captured = capsys.readouterr()
            assert "ready for review" in captured.out

    def test_all_complete_does_not_mark_ready_when_no_pr(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, fake_gh = _make_all_complete_mode(tmpdir)
            mode.execute()

            mark_ready_calls = [c for c in fake_gh.calls if c[0] == "mark_pr_ready"]
            assert len(mark_ready_calls) == 0

            captured = capsys.readouterr()
            assert "ready for review" not in captured.out


@pytest.mark.unit
class TestWorktreeModeTaskExecution:
    """WorktreeMode executes tasks, pushes, creates PR, and waits for CI."""

    def test_executes_single_task_push_pr_ci(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path, idea_dir, fake_repo, fake_runner = _setup_task_with_success(tmpdir)

            mode, _, _, fake_gh, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
            )
            mode.execute()

            assert len(fake_runner.calls) == 1
            assert ("push",) in fake_repo.calls
            assert any(c[0] == "ensure_pr" for c in fake_repo.calls)
            assert any(c[0] == "wait_for_workflow_completion" for c in fake_gh.calls)

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out

    def test_reuses_existing_pr(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, fake_repo, _, _, _ = _make_success_mode(tmpdir, "Set up project")
            fake_repo.pr_number = 42
            mode.execute()

            assert not any(c[0] == "ensure_pr" for c in fake_repo.calls)

    def test_uses_detected_default_branch_for_pr(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_gh = FakeGitHubClient()
            fake_gh.set_default_branch("master")
            mode, fake_repo, _, _, _ = _make_success_mode(tmpdir, fake_gh=fake_gh)
            mode.execute()

            ensure_pr_calls = [c for c in fake_repo.calls if c[0] == "ensure_pr"]
            assert len(ensure_pr_calls) == 1


def _run_with_fake_clock(capsys, start, end):
    """Run a single task with a fake clock and return captured stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        clock_values = iter([start, end])
        mode, _, _, _, _ = _make_success_mode(
            tmpdir, "Set up project", clock=lambda: next(clock_values),
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


def _setup_failure_task(tmpdir, task_name="Set up", *, ci_workflow=True):
    """Create a single pending task for failure testing."""
    plan_path, idea_dir = _setup_idea(
        tmpdir, [(1, 1, task_name, False)], ci_workflow=ci_workflow,
    )
    fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
    fake_runner = FakeClaudeRunner()
    return plan_path, idea_dir, fake_repo, fake_runner


def _make_completed_task_failure_mode(tmpdir, *, ci_workflow=True, customize_repo=None):
    """Make a mode where the task completes but a subsequent step fails."""
    plan_path, idea_dir, fake_repo, fake_runner = _setup_failure_task(
        tmpdir, ci_workflow=ci_workflow,
    )
    if customize_repo:
        customize_repo(fake_repo)
    fake_runner.set_side_effect(
        combined(
            advance_head(fake_repo, "bbb"),
            mark_task_complete(plan_path, 1, 1, "Set up"),
        )
    )
    return _make_worktree_mode(
        plan_path, idea_dir, tmpdir,
        fake_repo=fake_repo, fake_runner=fake_runner,
    )


@pytest.mark.unit
class TestWorktreeModeFailures:
    """WorktreeMode exits on various failure conditions."""

    def test_exits_on_claude_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path, idea_dir, _, fake_runner = _setup_failure_task(tmpdir)
            fake_runner.set_result(ClaudeResult(
                returncode=1, output=CapturedOutput(stderr="error"),
            ))

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir, fake_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1

    def test_exits_when_task_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path, idea_dir, fake_repo, fake_runner = _setup_failure_task(tmpdir)
            fake_runner.set_side_effect(advance_head(fake_repo, "bbb"))

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1

    def test_exits_when_no_ci_workflow_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, _, _, _ = _make_completed_task_failure_mode(tmpdir, ci_workflow=False)

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1

    def test_exits_when_push_fails(self):
        def break_push(repo):
            repo.push = lambda: (repo.calls.append(("push",)) or False)

        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, _, _, _ = _make_completed_task_failure_mode(
                tmpdir, customize_repo=break_push,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1


def _make_non_interactive_mode(tmpdir, result_output, *, skip_ci_wait=False):
    """Make a non-interactive mode with a specific ClaudeResult output."""
    plan_path, idea_dir, fake_repo, fake_runner = _setup_failure_task(tmpdir)
    fake_runner.set_side_effect(
        combined(
            advance_head(fake_repo, "bbb"),
            mark_task_complete(plan_path, 1, 1, "Set up"),
        )
    )
    fake_runner.set_result(ClaudeResult(
        returncode=0, output=CapturedOutput(result_output),
    ))
    opts = ImplementOpts(
        idea_directory=idea_dir, non_interactive=True,
        mock_claude="/mock", skip_ci_wait=skip_ci_wait,
    )
    return _make_worktree_mode(
        plan_path, idea_dir, tmpdir,
        fake_repo=fake_repo, fake_runner=fake_runner, opts=opts,
    )


@pytest.mark.unit
class TestWorktreeModeNonInteractive:
    """WorktreeMode in non-interactive mode uses run."""

    def test_non_interactive_uses_capture_and_checks_success_tag(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, fake_runner, _, _ = _make_non_interactive_mode(
                tmpdir, "<SUCCESS>task implemented: bbb</SUCCESS>", skip_ci_wait=True,
            )
            mode.execute()

            assert len(fake_runner.calls) == 1
            method, cmd, cwd = fake_runner.calls[0]
            assert method == "run"

    def test_non_interactive_exits_without_success_tag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mode, _, _, _, _ = _make_non_interactive_mode(
                tmpdir, "some output without success tag",
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
            plan_path, idea_dir = _setup_idea(tmpdir, [
                (1, 1, "Already recovered", True),
                (1, 2, "Next task", False),
            ], ci_workflow=True)

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
            assert fake_runner.calls[0][0] == "run_batch"  # recovery (commit_recovery uses run_batch directly)
            assert fake_runner.calls[1][0] == "run"  # task execution

            captured = capsys.readouterr()
            assert "Detected uncommitted changes" in captured.out
            assert "All tasks completed!" in captured.out

    def test_no_recovery_needed_main_loop_starts_normally(self, capsys):
        """When no recovery is needed, the main loop starts without recovery call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path, idea_dir, fake_repo, fake_runner = _setup_task_with_success(
                tmpdir, "Set up project",
            )

            project = IdeaProject(idea_dir)

            # No diff = no recovery needed
            fake_repo.set_diff_output("")

            commit_recovery = TaskCommitRecovery(
                git_repo=fake_repo, project=project, claude_runner=fake_runner,
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
            assert method == "run"

            captured = capsys.readouterr()
            assert "Detected uncommitted changes" not in captured.out
            assert "All tasks completed!" in captured.out


# --- Review poll loop helpers ---


def _make_review_poll_mode(tmpdir, *, feedback_sequence, pr_state,
                           pr_number=42):
    """Create a WorktreeMode for review poll loop testing.

    Args:
        feedback_sequence: list of bool results for process_feedback() calls.
            Includes the main-loop call (typically False) followed by poll-loop calls.
        pr_state: PR state string returned by get_pr_state (e.g. "MERGED").
        pr_number: PR number to configure.
    """
    plan_path, idea_dir = _setup_idea(tmpdir, [(1, 1, "Done", True)])
    project = IdeaProject(idea_dir)

    fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
    fake_repo.set_pushed(True)
    fake_repo.pr_number = pr_number
    fake_gh = FakeGitHubClient()
    fake_gh.set_pr_state(pr_number, pr_state)
    fake_repo._gh_client = fake_gh

    review_processor = SequentialReviewProcessor(feedback_sequence)
    sleep_calls = []

    loop_steps = LoopSteps(
        claude_runner=FakeClaudeRunner(),
        state=FakeWorkflowState(),
        ci_monitor=None,
        build_fixer=NoOpBuildFixer(),
        review_processor=review_processor,
        commit_recovery=NoOpCommitRecovery(),
        sleep=lambda secs: sleep_calls.append(secs),
    )

    opts = ImplementOpts(
        idea_directory=idea_dir,
        address_review_comments=True,
    )

    mode = WorktreeMode(
        opts=opts,
        git_repo=fake_repo,
        work_project=project,
        loop_steps=loop_steps,
    )
    return mode, review_processor, fake_gh, sleep_calls


@pytest.mark.unit
class TestReviewPollLoop:
    """When address_review_comments is True and all tasks are complete,
    WorktreeMode enters a review poll loop."""

    def test_processes_feedback_then_exits_on_merge(self, capsys):
        """Feedback on first poll call, PR merged on second → exits gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Main loop: process_feedback → False
            # Poll iteration 1: process_feedback → True (feedback!), continue
            # Poll iteration 2: process_feedback → False, get_pr_state → MERGED
            mode, review_proc, fake_gh, _ = _make_review_poll_mode(
                tmpdir,
                feedback_sequence=[False, True, False],
                pr_state="MERGED",
            )

            mode.execute()

            assert review_proc.call_count == 3
            get_state_calls = [c for c in fake_gh.calls if c[0] == "get_pr_state"]
            assert len(get_state_calls) == 1
            captured = capsys.readouterr()
            assert "merged" in captured.out.lower()

    def test_exits_gracefully_when_pr_closed(self, capsys):
        """PR is CLOSED (not merged) → loop exits with appropriate message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Main loop: process_feedback → False
            # Poll: process_feedback → False, get_pr_state → CLOSED
            mode, _, fake_gh, _ = _make_review_poll_mode(
                tmpdir,
                feedback_sequence=[False, False],
                pr_state="CLOSED",
            )

            mode.execute()

            captured = capsys.readouterr()
            assert "closed" in captured.out.lower()

    def test_sleeps_and_continues_when_no_feedback_and_pr_open(self, capsys):
        """No feedback, PR still open → sleeps then polls again."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Main loop: process_feedback → False
            # Poll 1: process_feedback → False, get_pr_state → OPEN → sleep
            # (sleep callback changes state to MERGED)
            # Poll 2: process_feedback → False, get_pr_state → MERGED → exit
            mode, _, fake_gh, sleep_calls = _make_review_poll_mode(
                tmpdir,
                feedback_sequence=[False, False, False],
                pr_state="OPEN",
            )

            def merge_on_sleep(secs):
                sleep_calls.append(secs)
                fake_gh.set_pr_state(42, "MERGED")

            mode._sleep = merge_on_sleep
            mode.execute()

            assert sleep_calls == [30]
            captured = capsys.readouterr()
            assert "merged" in captured.out.lower()


def _make_review_poll_mode_with_ci(tmpdir, *, ci_results, feedback_sequence,
                                    pr_state):
    """Create a WorktreeMode for testing CI fix integration in the review poll loop.

    Args:
        ci_results: list of bool results for check_and_fix_ci() calls.
            Includes the main-loop call (typically False) followed by poll-loop calls.
        feedback_sequence: list of bool results for process_feedback() calls.
        pr_state: PR state string returned by get_pr_state (e.g. "MERGED").

    Returns:
        (mode, build_fixer, review_processor, fake_gh, call_log)
    """
    plan_path, idea_dir = _setup_idea(tmpdir, [(1, 1, "Done", True)])
    project = IdeaProject(idea_dir)

    pr_number = 42
    fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
    fake_repo.set_pushed(True)
    fake_repo.pr_number = pr_number
    fake_gh = FakeGitHubClient()
    fake_gh.set_pr_state(pr_number, pr_state)
    fake_repo._gh_client = fake_gh

    call_log = []
    build_fixer = SequentialBuildFixer(ci_results, call_log=call_log)
    review_processor = SequentialReviewProcessor(feedback_sequence, call_log=call_log)

    loop_steps = LoopSteps(
        claude_runner=FakeClaudeRunner(),
        state=FakeWorkflowState(),
        ci_monitor=None,
        build_fixer=build_fixer,
        review_processor=review_processor,
        commit_recovery=NoOpCommitRecovery(),
    )

    opts = ImplementOpts(
        idea_directory=idea_dir,
        address_review_comments=True,
    )

    mode = WorktreeMode(
        opts=opts,
        git_repo=fake_repo,
        work_project=project,
        loop_steps=loop_steps,
    )
    return mode, build_fixer, review_processor, fake_gh, call_log


@pytest.mark.unit
class TestReviewPollLoopCiFix:
    """Review poll loop calls build_fixer.check_and_fix_ci() before
    processing feedback, and skips feedback when a CI fix is applied."""

    def test_ci_fix_applied_then_feedback_processed_on_next_iteration(self, capsys):
        """CI failure on first poll iteration -> fix applied -> next iteration
        processes feedback normally -> PR merged -> exit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Main loop: check_and_fix_ci → False, process_feedback → False
            # Poll iter 1: check_and_fix_ci → True (fix applied) → continue
            # Poll iter 2: check_and_fix_ci → False, process_feedback → False
            #              → get_pr_state → MERGED → exit
            mode, build_fixer, review_proc, fake_gh, call_log = (
                _make_review_poll_mode_with_ci(
                    tmpdir,
                    ci_results=[False, True, False],
                    feedback_sequence=[False, False],
                    pr_state="MERGED",
                )
            )

            mode.execute()

            assert build_fixer.call_count == 3
            assert review_proc.call_count == 2

            # Verify ordering: in poll loop, check_and_fix_ci is always
            # called before process_feedback
            poll_log = call_log[2:]  # skip main-loop calls
            assert poll_log == [
                "check_and_fix_ci",   # poll iter 1: fix applied → skip feedback
                "check_and_fix_ci",   # poll iter 2: no fix
                "process_feedback",   # poll iter 2: feedback checked
            ]

            captured = capsys.readouterr()
            assert "merged" in captured.out.lower()

    def test_repeated_ci_failures_fixed_before_feedback(self, capsys):
        """CI failure fixed but fix itself breaks CI -> second fix ->
        eventually passes -> feedback processed -> PR merged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Main loop: check_and_fix_ci → False, process_feedback → False
            # Poll iter 1: check_and_fix_ci → True (fix applied) → continue
            # Poll iter 2: check_and_fix_ci → True (fix again) → continue
            # Poll iter 3: check_and_fix_ci → False, process_feedback → False
            #              → get_pr_state → MERGED → exit
            mode, build_fixer, review_proc, fake_gh, call_log = (
                _make_review_poll_mode_with_ci(
                    tmpdir,
                    ci_results=[False, True, True, False],
                    feedback_sequence=[False, False],
                    pr_state="MERGED",
                )
            )

            mode.execute()

            assert build_fixer.call_count == 4
            assert review_proc.call_count == 2

            poll_log = call_log[2:]  # skip main-loop calls
            assert poll_log == [
                "check_and_fix_ci",   # poll iter 1: fix applied
                "check_and_fix_ci",   # poll iter 2: fix applied again
                "check_and_fix_ci",   # poll iter 3: no fix needed
                "process_feedback",   # poll iter 3: feedback checked
            ]

            captured = capsys.readouterr()
            assert "merged" in captured.out.lower()
