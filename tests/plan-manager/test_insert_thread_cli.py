"""CLI integration tests for insert-thread-before and insert-thread-after commands."""

import json

from click.testing import CliRunner

from i2code.plan.thread_cli import insert_thread_before_cmd, insert_thread_after_cmd


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
Done."""

NEW_TASKS_JSON = json.dumps([
    {
        "title": "New task",
        "task_type": "INFRA",
        "entrypoint": "echo new",
        "observable": "New thing happens",
        "evidence": "echo new-done",
        "steps": ["Do new thing"],
    }
])


class TestInsertThreadBeforeCli:

    def test_inserts_thread_and_renumbers(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(insert_thread_before_cmd, [
            str(plan_file), "--before", "1",
            "--title", "New Thread", "--introduction", "New intro.",
            "--tasks", NEW_TASKS_JSON, "--rationale", "added",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Steel Thread 1: New Thread" in updated
        assert "Steel Thread 2: First Thread" in updated
        assert "Steel Thread 3: Second Thread" in updated

    def test_appends_change_history(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        runner.invoke(insert_thread_before_cmd, [
            str(plan_file), "--before", "2",
            "--title", "New Thread", "--introduction", "New intro.",
            "--tasks", NEW_TASKS_JSON, "--rationale", "needed",
        ])

        updated = plan_file.read_text()
        assert "insert-thread-before" in updated
        assert "needed" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(insert_thread_before_cmd, [
            str(plan_file), "--before", "99",
            "--title", "New", "--introduction", "Intro",
            "--tasks", NEW_TASKS_JSON, "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output


class TestInsertThreadAfterCli:

    def test_inserts_thread_and_renumbers(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(insert_thread_after_cmd, [
            str(plan_file), "--after", "1",
            "--title", "New Thread", "--introduction", "New intro.",
            "--tasks", NEW_TASKS_JSON, "--rationale", "added",
        ])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Steel Thread 1: First Thread" in updated
        assert "Steel Thread 2: New Thread" in updated
        assert "Steel Thread 3: Second Thread" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(insert_thread_after_cmd, [
            str(plan_file), "--after", "99",
            "--title", "New", "--introduction", "Intro",
            "--tasks", NEW_TASKS_JSON, "--rationale", "reason",
        ])

        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output
