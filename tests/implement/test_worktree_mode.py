"""Tests for WorktreeMode class using fakes — zero @patch decorators."""

import os
import tempfile

import pytest

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.worktree_mode import WorktreeMode

from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState


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

    mode = WorktreeMode(
        opts=opts,
        git_repo=fake_repo,
        project=project,
        state=fake_state,
        claude_runner=fake_runner,
        work_plan_file=plan_path,
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up project"),
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
            # CI was waited on
            assert any(c[0] == "wait_for_ci" for c in fake_repo.calls)

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out

    def test_skip_ci_wait_does_not_call_wait_for_ci(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up project"),
                )
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_runner=fake_runner,
                opts=ImplementOpts(idea_directory=idea_dir, skip_ci_wait=True),
            )
            mode.execute()

            # Push was called but wait_for_ci was NOT
            assert ("push",) in fake_repo.calls
            assert not any(c[0] == "wait_for_ci" for c in fake_repo.calls)

    def test_reuses_existing_pr(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up project", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.pr_number = 42  # Pre-existing PR
            fake_runner = FakeClaudeRunner()

            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up project"),
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            fake_gh = FakeGitHubClient()
            fake_gh.set_default_branch("master")

            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up"),
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
            _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            fake_runner = FakeClaudeRunner()
            fake_runner.set_result(ClaudeResult(
                returncode=1, stdout="", stderr="error",
            ))

            mode, _, _, _, _ = _make_worktree_mode(
                _write_plan_file(idea_dir, idea_name, [(1, 1, "Set up", False)]),
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            # Advance HEAD (success) but do NOT mark task complete
            fake_runner.set_side_effect(
                _advance_head(fake_repo, "bbb"),
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])
            # Deliberately do NOT create .github/workflows/

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_runner = FakeClaudeRunner()
            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up"),
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])
            _write_ci_workflow(tmpdir)

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.push = lambda: (fake_repo.calls.append(("push",)) or False)  # push returns False
            fake_runner = FakeClaudeRunner()
            fake_runner.set_side_effect(
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up"),
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
class TestWorktreeModeCIFailure:
    """WorktreeMode detects and fixes CI failures before executing tasks."""

    def test_fixes_ci_failure_on_current_head(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Already done", True),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.set_pushed(True)
            fake_repo.branch = "idea/test/01-setup"
            fake_gh = FakeGitHubClient()
            # CI failing for sha "aaa"; fix_ci_failure advances HEAD to "bbb"
            fake_gh.set_workflow_runs(
                "idea/test/01-setup", "aaa",
                [{"name": "CI", "conclusion": "failure"}],
            )
            def fix_and_advance(**kwargs):
                fake_repo.calls.append(("fix_ci_failure", kwargs.get("worktree_path")))
                fake_repo.set_head_sha("bbb")
                return True

            fake_repo.fix_ci_failure = fix_and_advance

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_gh=fake_gh,
            )
            mode.execute()

            # fix_ci_failure was called
            assert any(c[0] == "fix_ci_failure" for c in fake_repo.calls)
            captured = capsys.readouterr()
            assert "CI build failing" in captured.out

    def test_exits_when_ci_fix_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Set up", False),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.set_pushed(True)
            fake_repo.branch = "idea/test/01-setup"

            def fix_fails(**kwargs):
                fake_repo.calls.append(("fix_ci_failure",))
                return False

            fake_repo.fix_ci_failure = fix_fails
            fake_gh = FakeGitHubClient()
            fake_gh.set_workflow_runs(
                "idea/test/01-setup", "aaa",
                [{"name": "CI", "conclusion": "failure"}],
            )

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_gh=fake_gh,
            )

            with pytest.raises(SystemExit) as exc_info:
                mode.execute()

            assert exc_info.value.code == 1


@pytest.mark.unit
class TestWorktreeModeFeedback:
    """WorktreeMode checks for PR feedback before executing tasks."""

    def test_skips_feedback_when_no_pr(self, capsys):
        """When no PR exists, skip feedback checking entirely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Already done", True),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.set_pushed(True)
            # No pr_number set — feedback should be skipped

            fake_gh = FakeGitHubClient()

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_gh=fake_gh,
            )
            mode.execute()

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out
            # get_pr_url should NOT have been called
            assert not any(c[0] == "get_pr_url" for c in fake_gh.calls)

    def test_skips_feedback_when_not_pushed(self, capsys):
        """When branch has not been pushed, skip feedback checking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = _write_plan_file(idea_dir, idea_name, [
                (1, 1, "Already done", True),
            ])

            fake_repo = FakeGitRepository(working_tree_dir=tmpdir)
            fake_repo.pr_number = 42
            # pushed is False by default

            fake_gh = FakeGitHubClient()

            mode, _, _, _, _ = _make_worktree_mode(
                plan_path, idea_dir, tmpdir,
                fake_repo=fake_repo, fake_gh=fake_gh,
            )
            mode.execute()

            captured = capsys.readouterr()
            assert "All tasks completed!" in captured.out
            # fetch_pr_comments should NOT have been called (feedback skipped)
            assert not any(c[0] == "fetch_pr_comments" for c in fake_gh.calls)


@pytest.mark.unit
class TestWorktreeModeNonInteractive:
    """WorktreeMode in non-interactive mode uses run_with_capture."""

    def test_non_interactive_uses_capture_and_checks_success_tag(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            idea_name = "test-feature"
            idea_dir = os.path.join(tmpdir, idea_name)
            os.makedirs(idea_dir)
            plan_path = _write_plan_file(idea_dir, idea_name, [
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
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up"),
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
            plan_path = _write_plan_file(idea_dir, idea_name, [
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
                _combined(
                    _advance_head(fake_repo, "bbb"),
                    _mark_task_complete(plan_path, 1, 1, "Set up"),
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
