"""CLI integration tests for mark-step-complete command."""

from click.testing import CliRunner

from i2code.plan.task_cli import mark_step_complete_cmd


PLAN_WITH_INCOMPLETE_STEP = """\
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

---

## Summary
Done.
"""


PLAN_WITH_COMPLETED_STEP = """\
# Implementation Plan: Test Plan

---

## Steel Thread 1: First Thread
Intro.

- [ ] **Task 1.1: A task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [x] Step one
    - [ ] Step two

---

## Summary
Done.
"""


class TestMarkStepCompleteCli:
    """CLI integration: mark-step-complete writes file and outputs confirmation."""

    def test_marks_step_complete_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE_STEP)

        runner = CliRunner()
        result = runner.invoke(mark_step_complete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
            "--step", "1", "--rationale", "done",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "    - [x] Step one\n" in updated
        assert "    - [ ] Step two\n" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE_STEP)

        runner = CliRunner()
        result = runner.invoke(mark_step_complete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
            "--step", "1", "--rationale", "done",
        ])

        assert "Marked step 1 of task 1.1 as complete" in result.output

    def test_error_for_already_complete_step(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_COMPLETED_STEP)

        runner = CliRunner()
        result = runner.invoke(mark_step_complete_cmd, [
            str(plan_file), "--thread", "1", "--task", "1",
            "--step", "1", "--rationale", "done",
        ])

        assert result.exit_code == 1
        assert "already complete" in result.output
