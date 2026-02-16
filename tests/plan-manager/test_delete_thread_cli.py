"""CLI integration tests for delete-thread command."""

from click.testing import CliRunner

from i2code.plan.thread_cli import delete_thread_cmd


PLAN_WITH_THREE_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

## Steel Thread 2: Second Thread
Introduction to second.

- [ ] **Task 2.1: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

## Steel Thread 3: Third Thread
Introduction to third.

- [ ] **Task 3.1: Third task**
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


class TestDeleteThreadCli:
    """CLI integration: delete-thread removes thread from file and outputs confirmation."""

    def test_deletes_thread_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(delete_thread_cmd, [
            str(plan_file), "--thread", "2", "--rationale", "not needed",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Second Thread" not in updated

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(delete_thread_cmd, [
            str(plan_file), "--thread", "1", "--rationale", "covered elsewhere",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "delete-thread" in updated
        assert "covered elsewhere" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(delete_thread_cmd, [
            str(plan_file), "--thread", "99", "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output
