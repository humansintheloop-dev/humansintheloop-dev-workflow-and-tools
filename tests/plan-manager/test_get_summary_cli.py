"""CLI integration tests for get-summary command."""

from click.testing import CliRunner

from i2code.plan.plan_cli import get_summary_cmd


PLAN_WITH_MIXED_TASKS = """\
# Implementation Plan: Test Project

## Idea Type
**B. Enhancement** - Improving an existing feature

---

## Overview
This plan covers the test project implementation with multiple threads.

---

## Steel Thread 1: First Thread
Introduction.

- [x] **Task 1.1: Done task**
  - TaskType: INFRA
  - Entrypoint: `echo done`
  - Observable: Done
  - Evidence: `echo done`
  - Steps:
    - [x] Already done

- [ ] **Task 1.2: Pending task**
  - TaskType: OUTCOME
  - Entrypoint: `echo pending`
  - Observable: Pending
  - Evidence: `echo pending`
  - Steps:
    - [ ] Not done yet

---

## Steel Thread 2: Second Thread
Intro.

- [x] **Task 2.1: Also done**
  - TaskType: OUTCOME
  - Entrypoint: `echo also-done`
  - Observable: Also done
  - Evidence: `echo also-done`
  - Steps:
    - [x] Done

- [ ] **Task 2.2: Not done**
  - TaskType: OUTCOME
  - Entrypoint: `echo not-done`
  - Observable: Not done
  - Evidence: `echo not-done`
  - Steps:
    - [ ] Pending

---

## Summary
A test summary.
"""


class TestGetSummaryCli:
    """CLI integration: get-summary outputs plan metadata via domain model."""

    def test_outputs_plan_summary(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_MIXED_TASKS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(get_summary_cmd, [str(plan_file)])

        assert result.exit_code == 0
        assert "Plan: Test Project" in result.output
        assert "**B. Enhancement** - Improving an existing feature" in result.output
        assert "test project implementation" in result.output
        assert "Threads: 2" in result.output
        assert "Tasks: 2/4 completed" in result.output
