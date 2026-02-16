"""CLI integration tests for replace-thread command."""

import json

from click.testing import CliRunner

from i2code.plan.thread_cli import replace_thread_cmd


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

---

## Summary
Done.
"""

NEW_TASKS_JSON = json.dumps([
    {
        "title": "New task A",
        "task_type": "INFRA",
        "entrypoint": "echo new-a",
        "observable": "New A works",
        "evidence": "echo new-a-done",
        "steps": ["Step A1", "Step A2"],
    },
    {
        "title": "New task B",
        "task_type": "OUTCOME",
        "entrypoint": "echo new-b",
        "observable": "New B works",
        "evidence": "echo new-b-done",
        "steps": ["Step B1"],
    },
])


class TestReplaceThreadCli:
    """CLI integration: replace-thread replaces thread content via domain model."""

    def test_replaces_thread_and_writes_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(replace_thread_cmd, [
            str(plan_file), "--thread", "1",
            "--title", "Replaced Thread", "--introduction", "New intro.",
            "--tasks", NEW_TASKS_JSON, "--rationale", "replaced",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Steel Thread 1: Replaced Thread" in updated
        assert "New intro." in updated
        assert "Task 1.1: New task A" in updated
        assert "Task 1.2: New task B" in updated

    def test_other_threads_unchanged(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        runner.invoke(replace_thread_cmd, [
            str(plan_file), "--thread", "1",
            "--title", "Replaced", "--introduction", "New.",
            "--tasks", NEW_TASKS_JSON, "--rationale", "replaced",
        ])

        updated = plan_file.read_text()
        assert "Steel Thread 2: Second Thread" in updated
        assert "Task 2.1: Second task" in updated

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        runner.invoke(replace_thread_cmd, [
            str(plan_file), "--thread", "1",
            "--title", "Replaced", "--introduction", "New.",
            "--tasks", NEW_TASKS_JSON, "--rationale", "restructured",
        ])

        updated = plan_file.read_text()
        assert "replace-thread" in updated
        assert "restructured" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(replace_thread_cmd, [
            str(plan_file), "--thread", "99",
            "--title", "T", "--introduction", "I",
            "--tasks", NEW_TASKS_JSON, "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output
