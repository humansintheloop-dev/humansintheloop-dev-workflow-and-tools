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

_THREAD_DEFAULTS = dict(
    title="New Thread", introduction="New intro.",
    tasks=NEW_TASKS_JSON, rationale="added",
)


def _invoke_thread_cmd(cmd, plan_file, position_arg, **overrides):
    """Write plan, invoke thread command with defaults + overrides, return (result, updated_text).

    position_arg: e.g. ("--before", "1") or ("--after", "2")
    """
    plan_file.write_text(PLAN_WITH_TWO_THREADS)
    d = {**_THREAD_DEFAULTS, **overrides}
    args = [
        str(plan_file), *position_arg,
        "--title", d["title"], "--introduction", d["introduction"],
        "--tasks", d["tasks"], "--rationale", d["rationale"],
    ]
    result = CliRunner(catch_exceptions=False).invoke(cmd, args)
    return result, plan_file.read_text()


class TestInsertThreadBeforeCli:

    def test_inserts_thread_and_renumbers(self, tmp_path):
        result, updated = _invoke_thread_cmd(insert_thread_before_cmd, tmp_path / "plan.md", ("--before", "1"))
        assert result.exit_code == 0
        assert "Steel Thread 1: New Thread" in updated
        assert "Steel Thread 2: First Thread" in updated
        assert "Steel Thread 3: Second Thread" in updated

    def test_appends_change_history(self, tmp_path):
        _, updated = _invoke_thread_cmd(
            insert_thread_before_cmd, tmp_path / "plan.md", ("--before", "2"), rationale="needed",
        )
        assert "insert-thread-before" in updated
        assert "needed" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        result, _ = _invoke_thread_cmd(
            insert_thread_before_cmd, tmp_path / "plan.md", ("--before", "99"), rationale="reason",
        )
        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output


class TestInsertThreadAfterCli:

    def test_inserts_thread_and_renumbers(self, tmp_path):
        result, updated = _invoke_thread_cmd(insert_thread_after_cmd, tmp_path / "plan.md", ("--after", "1"))
        assert result.exit_code == 0
        assert "Steel Thread 1: First Thread" in updated
        assert "Steel Thread 2: New Thread" in updated
        assert "Steel Thread 3: Second Thread" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        result, _ = _invoke_thread_cmd(
            insert_thread_after_cmd, tmp_path / "plan.md", ("--after", "99"), rationale="reason",
        )
        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output
