"""CLI integration tests for mark-task-complete command."""

from click.testing import CliRunner

from i2code.plan.task_cli import mark_task_complete_cmd


PLAN_WITH_INCOMPLETE = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first thread.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one
    - [ ] Step two

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


PLAN_WITH_COMPLETED = """\
# Implementation Plan: Test Plan

---

## Steel Thread 1: First Thread
Intro.

- [x] **Task 1.1: Already done**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [x] Step one

---

## Summary
Done.
"""


class TestMarkTaskCompleteCli:
    """CLI integration: mark-task-complete writes file and outputs confirmation."""

    def test_marks_task_complete_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(mark_task_complete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "- [x] **Task 1.1: First task**" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(mark_task_complete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
        ])

        assert "Marked task 1.1 as complete" in result.output

    def test_error_for_already_complete_task(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_COMPLETED)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(mark_task_complete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
        ])

        assert result.exit_code == 1
        assert "already complete" in result.output

