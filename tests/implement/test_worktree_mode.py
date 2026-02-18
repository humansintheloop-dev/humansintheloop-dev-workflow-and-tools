"""Tests for WorktreeMode class using fakes — zero @patch decorators."""

import os
import tempfile

import pytest

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixer
from i2code.implement.github_actions_monitor import GithubActionsMonitor
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.worktree_mode import WorktreeMode

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
    opts=None,
):
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

    mode = WorktreeMode(
        opts=opts,
        git_repo=fake_repo,
        state=fake_state,
        claude_runner=fake_runner,
        work_project=project,
        ci_monitor=ci_monitor,
        build_fixer=build_fixer,
        review_processor=review_processor,
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
                returncode=1, stdout="", stderr="error",
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
                stdout="<SUCCESS>task implemented: bbb</SUCCESS>",
                stderr="",
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
                stdout="some output without success tag",
                stderr="",
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
