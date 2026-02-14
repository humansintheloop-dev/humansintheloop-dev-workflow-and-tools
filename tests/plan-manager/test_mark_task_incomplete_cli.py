"""CLI integration tests for mark-task-incomplete command."""

from click.testing import CliRunner

from i2code.plan.task_cli import mark_task_incomplete_cmd


PLAN_WITH_COMPLETED = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first thread.

- [x] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [x] Step one
    - [x] Step two

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else happens
  - Evidence: `echo done2`
  - Steps:
    - [ ] Step one

---

## Summary
Done.
"""


PLAN_WITH_INCOMPLETE = """\
# Implementation Plan: Test Plan

---

## Steel Thread 1: First Thread
Intro.

- [ ] **Task 1.1: Already incomplete**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one

---

## Summary
Done.
"""


class TestMarkTaskIncompleteCli:
    """CLI integration: mark-task-incomplete writes file and outputs confirmation."""

    def test_marks_task_incomplete_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_COMPLETED)

        runner = CliRunner()
        result = runner.invoke(mark_task_incomplete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "- [ ] **Task 1.1: First task**" in updated

    def test_marks_all_steps_incomplete(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_COMPLETED)

        runner = CliRunner()
        result = runner.invoke(mark_task_incomplete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "    - [ ] Step one\n    - [ ] Step two" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_COMPLETED)

        runner = CliRunner()
        result = runner.invoke(mark_task_incomplete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
        ])

        assert "Marked task 1.1 as incomplete" in result.output

    def test_error_for_already_incomplete_task(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE)

        runner = CliRunner()
        result = runner.invoke(mark_task_incomplete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
        ])

        assert result.exit_code == 1
        assert "already incomplete" in result.output
