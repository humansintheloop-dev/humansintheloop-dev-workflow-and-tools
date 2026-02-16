"""CLI integration tests for get-thread command."""

from click.testing import CliRunner

from i2code.plan.plan_cli import get_thread_cmd


PLAN_WITH_TWO_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to the first thread.

This has multiple paragraphs of introduction.

- [x] **Task 1.1: Completed task**
  - TaskType: INFRA
  - Entrypoint: `echo setup`
  - Observable: Setup is done
  - Evidence: `echo verified`
  - Steps:
    - [x] Create the file
    - [x] Verify the file

- [ ] **Task 1.2: Pending task**
  - TaskType: OUTCOME
  - Entrypoint: `echo run`
  - Observable: Feature works
  - Evidence: `pytest tests/`
  - Steps:
    - [ ] Write the test
    - [x] Implement the code
    - [ ] Verify it works

---

## Steel Thread 2: Second Thread
Introduction to second thread.

- [ ] **Task 2.1: Another task**
  - TaskType: OUTCOME
  - Entrypoint: `echo another`
  - Observable: Another thing happens
  - Evidence: `echo another-done`
  - Steps:
    - [ ] Do another thing

---

## Summary
Done.
"""


class TestGetThreadCli:
    """CLI integration: get-thread outputs thread content via domain model."""

    def test_outputs_thread_with_tasks(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(get_thread_cmd, [str(plan_file), "--thread", "1"])

        assert result.exit_code == 0
        assert "Thread 1: First Thread" in result.output
        assert "Introduction to the first thread." in result.output
        assert "multiple paragraphs" in result.output
        assert "- [x] Task 1.1: Completed task" in result.output
        assert "TaskType: INFRA" in result.output
        assert "- [ ] Task 1.2: Pending task" in result.output
        assert "1. [x] Create the file" in result.output
        assert "2. [x] Verify the file" in result.output

    def test_error_on_nonexistent_thread(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(get_thread_cmd, [str(plan_file), "--thread", "99"])

        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output
