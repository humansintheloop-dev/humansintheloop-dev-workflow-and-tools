"""CLI integration tests for insert-task-after command."""

from click.testing import CliRunner

from i2code.plan.task_cli import insert_task_after_cmd


PLAN_WITH_TWO_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [ ] **Task 1.1: Existing task A**
  - TaskType: INFRA
  - Entrypoint: `echo a`
  - Observable: A works
  - Evidence: `echo a-done`
  - Steps:
    - [ ] Do A

- [ ] **Task 1.2: Existing task B**
  - TaskType: OUTCOME
  - Entrypoint: `echo b`
  - Observable: B works
  - Evidence: `echo b-done`
  - Steps:
    - [ ] Do B

---

## Summary
Done.
"""


class TestInsertTaskAfterCli:
    """CLI integration: insert-task-after inserts task into file via domain model."""

    def test_inserts_after_first_task_and_renumbers(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_after_cmd, [
            str(plan_file), "--thread", "1", "--after", "1",
            "--title", "New task", "--task-type", "INFRA",
            "--entrypoint", "echo new", "--observable", "New works",
            "--evidence", "echo new-done", "--steps", '["Step new"]',
            "--rationale", "Adding new task",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Task 1.1: Existing task A" in updated
        assert "Task 1.2: New task" in updated
        assert "Task 1.3: Existing task B" in updated

    def test_inserts_after_last_task(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_after_cmd, [
            str(plan_file), "--thread", "1", "--after", "2",
            "--title", "New task", "--task-type", "OUTCOME",
            "--entrypoint", "echo new", "--observable", "New works",
            "--evidence", "echo new-done", "--steps", '["Step new"]',
            "--rationale", "Adding new task",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Task 1.1: Existing task A" in updated
        assert "Task 1.2: Existing task B" in updated
        assert "Task 1.3: New task" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_after_cmd, [
            str(plan_file), "--thread", "1", "--after", "1",
            "--title", "New task", "--task-type", "INFRA",
            "--entrypoint", "echo new", "--observable", "New works",
            "--evidence", "echo new-done", "--steps", '["Step new"]',
            "--rationale", "Adding",
        ])

        assert "Inserted task" in result.output

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_after_cmd, [
            str(plan_file), "--thread", "1", "--after", "1",
            "--title", "New task", "--task-type", "INFRA",
            "--entrypoint", "echo new", "--observable", "New works",
            "--evidence", "echo new-done", "--steps", '["Step new"]',
            "--rationale", "Need a new task",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "insert-task-after" in updated
        assert "Need a new task" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_after_cmd, [
            str(plan_file), "--thread", "99", "--after", "1",
            "--title", "New", "--task-type", "INFRA",
            "--entrypoint", "echo", "--observable", "obs",
            "--evidence", "ev", "--steps", '["step"]',
            "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output

    def test_error_for_nonexistent_task(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_after_cmd, [
            str(plan_file), "--thread", "1", "--after", "99",
            "--title", "New", "--task-type", "INFRA",
            "--entrypoint", "echo", "--observable", "obs",
            "--evidence", "ev", "--steps", '["step"]',
            "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "does not exist" in result.output
