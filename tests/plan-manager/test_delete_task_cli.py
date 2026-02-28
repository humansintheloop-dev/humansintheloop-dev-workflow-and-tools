"""CLI integration tests for delete-task command."""

from click.testing import CliRunner

from i2code.plan.task_cli import delete_task_cmd


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

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

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


def _invoke_delete_task(plan_file, thread="1", task="1", rationale="not needed"):
    """Write plan, invoke delete-task, return (result, updated_text)."""
    plan_file.write_text(PLAN_WITH_THREE_TASKS)
    args = [str(plan_file), "--thread", thread, "--task", task, "--rationale", rationale]
    result = CliRunner(catch_exceptions=False).invoke(delete_task_cmd, args)
    return result, plan_file.read_text()


class TestDeleteTaskCli:
    """CLI integration: delete-task removes task from file and outputs confirmation."""

    def test_deletes_task_and_writes_file(self, tmp_path):
        result, updated = _invoke_delete_task(tmp_path / "plan.md", task="2")
        assert result.exit_code == 0
        assert "Second task" not in updated

    def test_renumbers_remaining_tasks(self, tmp_path):
        result, updated = _invoke_delete_task(tmp_path / "plan.md")
        assert result.exit_code == 0
        assert "Task 1.1: Second task" in updated
        assert "Task 1.2: Third task" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        result, _ = _invoke_delete_task(tmp_path / "plan.md")
        assert "Deleted task 1.1" in result.output

    def test_appends_change_history(self, tmp_path):
        result, updated = _invoke_delete_task(tmp_path / "plan.md", rationale="covered elsewhere")
        assert result.exit_code == 0
        assert "delete-task" in updated
        assert "covered elsewhere" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        result, _ = _invoke_delete_task(tmp_path / "plan.md", thread="99", rationale="reason")
        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output

    def test_error_for_nonexistent_task(self, tmp_path):
        result, _ = _invoke_delete_task(tmp_path / "plan.md", task="99", rationale="reason")
        assert result.exit_code == 1
        assert "does not exist" in result.output
