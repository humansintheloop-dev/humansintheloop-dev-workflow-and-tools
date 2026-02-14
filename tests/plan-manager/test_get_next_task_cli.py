"""CLI integration tests for get-next-task command."""

from click.testing import CliRunner

from i2code.plan.plan_cli import get_next_task_cmd


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

---

## Summary
Done.
"""


ALL_COMPLETE = """\
# Implementation Plan: Test Plan

---

## Steel Thread 1: First Thread
Intro.

- [x] **Task 1.1: Done task**
  - TaskType: INFRA
  - Entrypoint: `echo done`
  - Observable: Done
  - Evidence: `echo done`
  - Steps:
    - [x] All done

---

## Summary
All done.
"""


class TestGetNextTaskCli:
    """CLI integration: get-next-task outputs formatted task info."""

    def test_outputs_formatted_task_info(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE)

        runner = CliRunner()
        result = runner.invoke(get_next_task_cmd, [str(plan_file)])

        assert result.exit_code == 0
        assert "Thread 1, Task 1.1: First task" in result.output
        assert "TaskType: INFRA" in result.output
        assert "Entrypoint: echo hello" in result.output
        assert "Observable: Something happens" in result.output
        assert "Evidence: echo done" in result.output
        assert "1. [ ] Step one" in result.output
        assert "2. [ ] Step two" in result.output

    def test_outputs_all_complete_message(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(ALL_COMPLETE)

        runner = CliRunner()
        result = runner.invoke(get_next_task_cmd, [str(plan_file)])

        assert result.exit_code == 0
        assert "All tasks are complete." in result.output
