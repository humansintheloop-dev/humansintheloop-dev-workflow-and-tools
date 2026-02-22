"""Tests for TaskCommitRecovery detection and recovery logic."""

import pytest

from i2code.implement.claude_runner import CapturedOutput, ClaudeResult
from i2code.implement.commit_recovery import TaskCommitRecovery
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

PLAN_WITH_ALL_STEPS_COMPLETE = """\
# Implementation Plan: Test Feature

## Steel Thread 1: Basic Feature

- [ ] **Task 1.1: Implement feature**
  - TaskType: OUTCOME
  - Steps:
    - [x] Step one
    - [x] Step two
"""


@pytest.fixture
def make_recovery(tmp_path):
    """Factory fixture that builds a TaskCommitRecovery with common test scaffolding.

    Returns (recovery, git_repo, runner) so tests can configure
    runner side-effects and inspect git_repo state after the call.
    """
    def _make(*, plan_content, diff_output="", head_content=None):
        plan_dir = tmp_path / "test-feature"
        plan_dir.mkdir()
        (plan_dir / "test-feature-plan.md").write_text(plan_content)

        project = FakeIdeaProject(name="test-feature", directory=str(plan_dir))
        git_repo = FakeGitRepository()
        git_repo.set_diff_output(diff_output)
        if head_content is not None:
            git_repo.set_file_at_head(project.plan_file, head_content)

        runner = FakeClaudeRunner()
        recovery = TaskCommitRecovery(
            git_repo=git_repo, project=project, claude_runner=runner,
        )
        return recovery, git_repo, runner
    return _make


@pytest.mark.unit
class TestTaskCommitRecoveryNeedsRecovery:

    def test_no_diff_returns_false(self, make_recovery):
        recovery, _, _ = make_recovery(plan_content=PLAN_WITH_INCOMPLETE_TASK)
        assert recovery.has_uncommitted_completed_task() is False

    def test_completed_task_returns_true(self, make_recovery):
        recovery, _, _ = make_recovery(
            plan_content=PLAN_WITH_COMPLETED_TASK,
            diff_output="some diff output",
            head_content=PLAN_WITH_INCOMPLETE_TASK,
        )
        assert recovery.has_uncommitted_completed_task() is True

    def test_partial_steps_only_returns_false(self, make_recovery):
        recovery, _, _ = make_recovery(
            plan_content=PLAN_WITH_PARTIAL_STEPS,
            diff_output="some diff output",
            head_content=PLAN_WITH_INCOMPLETE_TASK,
        )
        assert recovery.has_uncommitted_completed_task() is False

    def test_all_steps_complete_but_task_header_incomplete_returns_false(self, make_recovery):
        """When all step checkboxes changed to [x] but task header remains [ ], no recovery."""
        recovery, _, _ = make_recovery(
            plan_content=PLAN_WITH_ALL_STEPS_COMPLETE,
            diff_output="some diff output",
            head_content=PLAN_WITH_INCOMPLETE_TASK,
        )
        assert recovery.has_uncommitted_completed_task() is False

    def test_no_changes_returns_false(self, make_recovery):
        """When plan file has a diff but content is identical in both versions, no recovery."""
        recovery, _, _ = make_recovery(
            plan_content=PLAN_WITH_INCOMPLETE_TASK,
            diff_output="some diff output",
            head_content=PLAN_WITH_INCOMPLETE_TASK,
        )
        assert recovery.has_uncommitted_completed_task() is False


@pytest.mark.unit
class TestTaskCommitRecoveryRecover:

    def test_recover_success_returns_true(self, make_recovery, capsys):
        """When Claude succeeds (exit 0, HEAD advances, <SUCCESS> tag), returns True."""
        recovery, git_repo, runner = make_recovery(
            plan_content=PLAN_WITH_COMPLETED_TASK,
            diff_output="some diff output",
        )
        runner.set_result(ClaudeResult(
            returncode=0,
            output=CapturedOutput("<SUCCESS>recovery commit: bbb</SUCCESS>"),
        ))
        runner.set_side_effect(advance_head(git_repo, "bbb"))

        result = recovery.commit_uncommitted_changes()

        assert result is True
        assert len(runner.calls) == 1
        method, cmd, cwd = runner.calls[0]
        assert method == "run_with_capture"
        captured = capsys.readouterr()
        assert "Detected uncommitted changes" in captured.out

    @pytest.mark.parametrize("returncode,advance_head_to", [
        pytest.param(0, "bbb", id="HEAD advances but no SUCCESS tag"),
        pytest.param(1, None, id="Claude fails with non-zero exit"),
    ])
    def test_recover_returns_false_on_failure(self, make_recovery, returncode, advance_head_to):
        """commit_uncommitted_changes() returns False when recovery fails."""
        recovery, git_repo, runner = make_recovery(
            plan_content=PLAN_WITH_COMPLETED_TASK,
            diff_output="some diff output",
        )
        runner.set_result(ClaudeResult(returncode=returncode))
        if advance_head_to:
            runner.set_side_effect(advance_head(git_repo, advance_head_to))

        result = recovery.commit_uncommitted_changes()

        assert result is False
        assert len(runner.calls) == 1


@pytest.mark.unit
class TestTaskCommitRecoveryCheckAndRecover:

    def test_commit_if_needed_when_no_recovery_needed(self, make_recovery):
        """When has_uncommitted_completed_task() is False, does not call recover()."""
        recovery, _, runner = make_recovery(
            plan_content=PLAN_WITH_INCOMPLETE_TASK,
        )

        result = recovery.commit_if_needed()

        assert result is False
        assert len(runner.calls) == 0

    def test_first_attempt_succeeds_no_retry(self, make_recovery, capsys):
        """When first recovery attempt succeeds, no retry and prints success."""
        recovery, git_repo, runner = make_recovery(
            plan_content=PLAN_WITH_COMPLETED_TASK,
            diff_output="some diff output",
            head_content=PLAN_WITH_INCOMPLETE_TASK,
        )
        runner.set_result(ClaudeResult(
            returncode=0,
            output=CapturedOutput("<SUCCESS>recovery commit: bbb</SUCCESS>"),
        ))
        runner.set_side_effect(advance_head(git_repo, "bbb"))

        recovery.commit_if_needed()

        assert len(runner.calls) == 1
        captured = capsys.readouterr()
        assert "Recovery commit successful." in captured.out

    def test_first_attempt_fails_second_succeeds(self, make_recovery, capsys):
        """When first attempt fails and second succeeds, prints retry then success."""
        recovery, git_repo, runner = make_recovery(
            plan_content=PLAN_WITH_COMPLETED_TASK,
            diff_output="some diff output",
            head_content=PLAN_WITH_INCOMPLETE_TASK,
        )
        runner.set_results([
            ClaudeResult(returncode=1),
            ClaudeResult(returncode=0, output=CapturedOutput("<SUCCESS>recovery commit: ccc</SUCCESS>")),
        ])
        runner.set_side_effects([
            lambda: None,  # first call: no HEAD advance (failure)
            advance_head(git_repo, "ccc"),  # second call: HEAD advances (success)
        ])

        recovery.commit_if_needed()

        assert len(runner.calls) == 2
        captured = capsys.readouterr()
        assert "Recovery attempt 1 failed, retrying..." in captured.out
        assert "Recovery commit successful." in captured.out

    def test_both_attempts_fail_exits_with_error(self, make_recovery, capsys):
        """When both attempts fail, prints error and calls sys.exit(1)."""
        recovery, _, runner = make_recovery(
            plan_content=PLAN_WITH_COMPLETED_TASK,
            diff_output="some diff output",
            head_content=PLAN_WITH_INCOMPLETE_TASK,
        )
        runner.set_results([
            ClaudeResult(returncode=1),
            ClaudeResult(returncode=1),
        ])

        with pytest.raises(SystemExit) as exc_info:
            recovery.commit_if_needed()

        assert exc_info.value.code == 1
        assert len(runner.calls) == 2
        captured = capsys.readouterr()
        assert "Recovery attempt 1 failed, retrying..." in captured.out
        assert "Error: Could not commit recovered changes after 2 attempts. Please commit manually and rerun." in captured.out
