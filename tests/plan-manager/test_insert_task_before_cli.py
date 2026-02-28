"""CLI integration tests for insert-task-before command."""

from click.testing import CliRunner

from i2code.plan.task_cli import insert_task_before_cmd


PLAN_WITH_TWO_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [ ] **Task 1.1: Existing task A**
  - TaskType: INFRA
  - Entrypoint: `echo a`
  - Observable: A works
  - Evidence: `echo a-done`
  - Steps:
    - [ ] Do A

- [ ] **Task 1.2: Existing task B**
  - TaskType: OUTCOME
  - Entrypoint: `echo b`
  - Observable: B works
  - Evidence: `echo b-done`
  - Steps:
    - [ ] Do B

---

## Summary
Done.
"""

_INSERT_DEFAULTS = dict(
    thread="1", before="1", title="New task", task_type="INFRA",
    entrypoint="echo new", observable="New works",
    evidence="echo new-done", steps='["Step new"]', rationale="Adding new task",
)


def _invoke_insert_before(plan_file, **overrides):
    """Write plan, invoke insert-task-before with defaults + overrides, return (result, updated_text)."""
    plan_file.write_text(PLAN_WITH_TWO_TASKS)
    d = {**_INSERT_DEFAULTS, **overrides}
    args = [
        str(plan_file), "--thread", d["thread"], "--before", d["before"],
        "--title", d["title"], "--task-type", d["task_type"],
        "--entrypoint", d["entrypoint"], "--observable", d["observable"],
        "--evidence", d["evidence"], "--steps", d["steps"],
        "--rationale", d["rationale"],
    ]
    result = CliRunner(catch_exceptions=False).invoke(insert_task_before_cmd, args)
    return result, plan_file.read_text()


class TestInsertTaskBeforeCli:
    """CLI integration: insert-task-before inserts task into file via domain model."""

    def test_inserts_before_first_task_and_renumbers(self, tmp_path):
        result, updated = _invoke_insert_before(tmp_path / "plan.md")
        assert result.exit_code == 0
        assert "Task 1.1: New task" in updated
        assert "Task 1.2: Existing task A" in updated
        assert "Task 1.3: Existing task B" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        result, _ = _invoke_insert_before(tmp_path / "plan.md")
        assert "Inserted task" in result.output

    def test_appends_change_history(self, tmp_path):
        result, updated = _invoke_insert_before(tmp_path / "plan.md", rationale="Need a new task")
        assert result.exit_code == 0
        assert "insert-task-before" in updated
        assert "Need a new task" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        result, _ = _invoke_insert_before(tmp_path / "plan.md", thread="99")
        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output

    def test_error_for_nonexistent_task(self, tmp_path):
        result, _ = _invoke_insert_before(tmp_path / "plan.md", before="99")
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_error_for_invalid_json_steps(self, tmp_path):
        result, _ = _invoke_insert_before(tmp_path / "plan.md", steps="not-json")
        assert result.exit_code == 1
        assert "not valid JSON" in result.output
