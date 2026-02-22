"""Tests for CommitRecovery.needs_recovery() detection logic."""

import pytest

from i2code.implement.commit_recovery import CommitRecovery
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
