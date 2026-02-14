"""CLI integration tests for insert-task-before command."""

from click.testing import CliRunner

from i2code.plan.task_cli import insert_task_before_cmd


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


class TestInsertTaskBeforeCli:
    """CLI integration: insert-task-before inserts task into file via domain model."""

    def test_inserts_before_first_task_and_renumbers(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_before_cmd, [
            str(plan_file), "--thread", "1", "--before", "1",
            "--title", "New task", "--task-type", "INFRA",
            "--entrypoint", "echo new", "--observable", "New works",
            "--evidence", "echo new-done", "--steps", '["Step new"]',
            "--rationale", "Adding new task",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Task 1.1: New task" in updated
        assert "Task 1.2: Existing task A" in updated
        assert "Task 1.3: Existing task B" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_before_cmd, [
            str(plan_file), "--thread", "1", "--before", "1",
            "--title", "New task", "--task-type", "INFRA",
            "--entrypoint", "echo new", "--observable", "New works",
            "--evidence", "echo new-done", "--steps", '["Step new"]',
            "--rationale", "Adding new task",
        ])

        assert "Inserted task" in result.output

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_before_cmd, [
            str(plan_file), "--thread", "1", "--before", "1",
            "--title", "New task", "--task-type", "INFRA",
            "--entrypoint", "echo new", "--observable", "New works",
            "--evidence", "echo new-done", "--steps", '["Step new"]',
            "--rationale", "Need a new task",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "insert-task-before" in updated
        assert "Need a new task" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_before_cmd, [
            str(plan_file), "--thread", "99", "--before", "1",
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
        result = runner.invoke(insert_task_before_cmd, [
            str(plan_file), "--thread", "1", "--before", "99",
            "--title", "New", "--task-type", "INFRA",
            "--entrypoint", "echo", "--observable", "obs",
            "--evidence", "ev", "--steps", '["step"]',
            "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_error_for_invalid_json_steps(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)

        runner = CliRunner()
        result = runner.invoke(insert_task_before_cmd, [
            str(plan_file), "--thread", "1", "--before", "1",
            "--title", "New", "--task-type", "INFRA",
            "--entrypoint", "echo", "--observable", "obs",
            "--evidence", "ev", "--steps", "not-json",
            "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "not valid JSON" in result.output
