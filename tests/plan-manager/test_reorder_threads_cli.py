"""CLI integration tests for reorder-threads command."""

from click.testing import CliRunner

from i2code.plan.thread_cli import reorder_threads_cmd


PLAN_WITH_TWO_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first.

- [ ] **Task 1.1: Alpha task**
  - TaskType: INFRA
  - Entrypoint: `echo alpha`
  - Observable: Alpha happens
  - Evidence: `echo alpha-done`
  - Steps:
    - [ ] Alpha step one

## Steel Thread 2: Second Thread
Introduction to second.

- [ ] **Task 2.1: Beta task**
  - TaskType: OUTCOME
  - Entrypoint: `echo beta`
  - Observable: Beta happens
  - Evidence: `echo beta-done`
  - Steps:
    - [ ] Beta step one

---

## Summary
Done.
"""


class TestReorderThreadsCli:
    """CLI integration: reorder-threads reorders threads via domain model."""

    def test_reorders_threads_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(reorder_threads_cmd, [
            str(plan_file), "--order", "2,1", "--rationale", "swapped",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Steel Thread 1: Second Thread" in updated
        assert "Steel Thread 2: First Thread" in updated

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        runner.invoke(reorder_threads_cmd, [
            str(plan_file), "--order", "2,1", "--rationale", "priority change",
        ])

        updated = plan_file.read_text()
        assert "reorder-threads" in updated
        assert "priority change" in updated

    def test_error_for_invalid_order(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(reorder_threads_cmd, [
            str(plan_file), "--order", "1,3", "--rationale", "bad",
        ])

        assert result.exit_code == 1

    def test_error_for_non_integer_order(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(reorder_threads_cmd, [
            str(plan_file), "--order", "a,b", "--rationale", "bad",
        ])

        assert result.exit_code == 1
