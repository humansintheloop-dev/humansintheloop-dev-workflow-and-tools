"""CLI integration tests for reorder-tasks command."""

from click.testing import CliRunner

from i2code.plan.task_cli import reorder_tasks_cmd


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


class TestReorderTasksCli:
    """CLI integration: reorder-tasks reorders tasks in file via domain model."""

    def test_reorders_tasks_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(reorder_tasks_cmd, [
            str(plan_file), "--thread", "1", "--order", "3,2,1", "--rationale", "reversed",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Task 1.1: Third task" in updated
        assert "Task 1.2: Second task" in updated
        assert "Task 1.3: First task" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(reorder_tasks_cmd, [
            str(plan_file), "--thread", "1", "--order", "3,2,1", "--rationale", "reversed",
        ])

        assert "Reordered tasks in thread 1" in result.output

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(reorder_tasks_cmd, [
            str(plan_file), "--thread", "1", "--order", "3,2,1", "--rationale", "reversed for priority",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "reorder-tasks" in updated
        assert "reversed for priority" in updated

    def test_error_for_non_integer_order(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(reorder_tasks_cmd, [
            str(plan_file), "--thread", "1", "--order", "a,b,c", "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "comma-separated integers" in result.output
