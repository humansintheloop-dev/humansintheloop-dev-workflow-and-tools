"""CLI integration tests for move-task-after command."""

from click.testing import CliRunner

from i2code.plan.task_cli import move_task_after_cmd


PLAN_WITH_THREE_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [x] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [x] Do first

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

- [ ] **Task 1.3: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo third`
  - Observable: Third
  - Evidence: `echo third-done`
  - Steps:
    - [ ] Do third

---

## Summary
Done.
"""


class TestMoveTaskAfterCli:
    """CLI integration: move-task-after moves tasks in file via domain model."""

    def test_moves_task_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(move_task_after_cmd, [
            str(plan_file), "--thread", "1", "--task", "1", "--after", "3", "--rationale", "deferred",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Task 1.1: Second task" in updated
        assert "Task 1.2: Third task" in updated
        assert "Task 1.3: First task" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(move_task_after_cmd, [
            str(plan_file), "--thread", "1", "--task", "1", "--after", "3", "--rationale", "deferred",
        ])

        assert "Moved task 1.1 after task 1.3" in result.output

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(move_task_after_cmd, [
            str(plan_file), "--thread", "1", "--task", "1", "--after", "3", "--rationale", "task deferred",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "move-task-after" in updated
        assert "task deferred" in updated
