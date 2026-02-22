"""Tests for CommitRecovery detection and recovery logic."""

import pytest

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.commit_recovery import CommitRecovery
from conftest import advance_head
from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_idea_project import FakeIdeaProject


PLAN_WITH_INCOMPLETE_TASK = """\
# Implementation Plan: Test Feature

## Steel Thread 1: Basic Feature

- [ ] **Task 1.1: Implement feature**
  - TaskType: OUTCOME
  - Steps:
    - [ ] Step one
    - [ ] Step two
"""

PLAN_WITH_COMPLETED_TASK = """\
# Implementation Plan: Test Feature

## Steel Thread 1: Basic Feature

- [x] **Task 1.1: Implement feature**
  - TaskType: OUTCOME
  - Steps:
    - [x] Step one
    - [x] Step two
"""

PLAN_WITH_PARTIAL_STEPS = """\
# Implementation Plan: Test Feature

## Steel Thread 1: Basic Feature

- [ ] **Task 1.1: Implement feature**
  - TaskType: OUTCOME
  - Steps:
    - [x] Step one
    - [ ] Step two
"""


@pytest.mark.unit
class TestCommitRecoveryNeedsRecovery:

    def test_no_diff_returns_false(self, tmp_path):
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(PLAN_WITH_INCOMPLETE_TASK)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output("")

        recovery = CommitRecovery(git_repo=git_repo, project=project, claude_runner=None)
        assert recovery.needs_recovery() is False

    def test_completed_task_returns_true(self, tmp_path):
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(PLAN_WITH_COMPLETED_TASK)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output("some diff output")
        git_repo.set_file_at_head(project.plan_file, PLAN_WITH_INCOMPLETE_TASK)

        recovery = CommitRecovery(git_repo=git_repo, project=project, claude_runner=None)
        assert recovery.needs_recovery() is True

    def test_partial_steps_only_returns_false(self, tmp_path):
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(PLAN_WITH_PARTIAL_STEPS)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output("some diff output")
        git_repo.set_file_at_head(project.plan_file, PLAN_WITH_INCOMPLETE_TASK)

        recovery = CommitRecovery(git_repo=git_repo, project=project, claude_runner=None)
        assert recovery.needs_recovery() is False


@pytest.mark.unit
class TestCommitRecoveryRecover:

    def test_recover_success_returns_true(self, tmp_path, capsys):
        """When Claude succeeds (exit 0, HEAD advances), recover() returns True."""
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(PLAN_WITH_COMPLETED_TASK)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output("some diff output")
        fake_runner = FakeClaudeRunner()

        # Simulate: Claude advances HEAD (successful commit)
        fake_runner.set_side_effect(advance_head(git_repo, "bbb"))

        recovery = CommitRecovery(
            git_repo=git_repo, project=project, claude_runner=fake_runner,
        )
        result = recovery.recover()

        assert result is True
        assert len(fake_runner.calls) == 1
        method, cmd, cwd = fake_runner.calls[0]
        assert method == "run_interactive"
        captured = capsys.readouterr()
        assert "Detected uncommitted changes" in captured.out

    def test_recover_failure_returns_false(self, tmp_path, capsys):
        """When Claude fails (non-zero exit), recover() returns False."""
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(PLAN_WITH_COMPLETED_TASK)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output("some diff output")
        fake_runner = FakeClaudeRunner()

        # Claude fails: non-zero return, HEAD does not advance
        fake_runner.set_result(ClaudeResult(returncode=1))

        recovery = CommitRecovery(
            git_repo=git_repo, project=project, claude_runner=fake_runner,
        )
        result = recovery.recover()

        assert result is False
        assert len(fake_runner.calls) == 1


@pytest.mark.unit
class TestCommitRecoveryCheckAndRecover:

    def test_check_and_recover_when_recovery_needed(self, tmp_path, capsys):
        """When needs_recovery() is True, calls recover() and returns its result."""
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(PLAN_WITH_COMPLETED_TASK)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output("some diff output")
        git_repo.set_file_at_head(project.plan_file, PLAN_WITH_INCOMPLETE_TASK)
        fake_runner = FakeClaudeRunner()
        fake_runner.set_side_effect(advance_head(git_repo, "bbb"))

        recovery = CommitRecovery(
            git_repo=git_repo, project=project, claude_runner=fake_runner,
        )
        result = recovery.check_and_recover()

        assert result is True
        assert len(fake_runner.calls) == 1

    def test_check_and_recover_when_no_recovery_needed(self, tmp_path):
        """When needs_recovery() is False, does not call recover()."""
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(PLAN_WITH_INCOMPLETE_TASK)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output("")  # No diff = no recovery needed
        fake_runner = FakeClaudeRunner()

        recovery = CommitRecovery(
            git_repo=git_repo, project=project, claude_runner=fake_runner,
        )
        result = recovery.check_and_recover()

        assert result is False
        assert len(fake_runner.calls) == 0
