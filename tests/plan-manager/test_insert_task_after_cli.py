"""CLI integration tests for insert-task-after command."""

from click.testing import CliRunner

from i2code.plan.task_cli import insert_task_after_cmd


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
    thread="1", after="1", title="New task", task_type="INFRA",
    entrypoint="echo new", observable="New works",
    evidence="echo new-done", steps='["Step new"]', rationale="Adding new task",
)


def _invoke_insert_after(plan_file, **overrides):
    """Write plan, invoke insert-task-after with defaults + overrides, return (result, updated_text)."""
    plan_file.write_text(PLAN_WITH_TWO_TASKS)
    d = {**_INSERT_DEFAULTS, **overrides}
    args = [
        str(plan_file), "--thread", d["thread"], "--after", d["after"],
        "--title", d["title"], "--task-type", d["task_type"],
        "--entrypoint", d["entrypoint"], "--observable", d["observable"],
        "--evidence", d["evidence"], "--steps", d["steps"],
        "--rationale", d["rationale"],
    ]
    result = CliRunner(catch_exceptions=False).invoke(insert_task_after_cmd, args)
    return result, plan_file.read_text()


class TestInsertTaskAfterCli:
    """CLI integration: insert-task-after inserts task into file via domain model."""

    def test_inserts_after_first_task_and_renumbers(self, tmp_path):
        result, updated = _invoke_insert_after(tmp_path / "plan.md")
        assert result.exit_code == 0
        assert "Task 1.1: Existing task A" in updated
        assert "Task 1.2: New task" in updated
        assert "Task 1.3: Existing task B" in updated

    def test_inserts_after_last_task(self, tmp_path):
        result, updated = _invoke_insert_after(tmp_path / "plan.md", after="2", task_type="OUTCOME")
        assert result.exit_code == 0
        assert "Task 1.1: Existing task A" in updated
        assert "Task 1.2: Existing task B" in updated
        assert "Task 1.3: New task" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        result, _ = _invoke_insert_after(tmp_path / "plan.md", rationale="Adding")
        assert "Inserted task" in result.output

    def test_appends_change_history(self, tmp_path):
        result, updated = _invoke_insert_after(tmp_path / "plan.md", rationale="Need a new task")
        assert result.exit_code == 0
        assert "insert-task-after" in updated
        assert "Need a new task" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        result, _ = _invoke_insert_after(tmp_path / "plan.md", thread="99")
        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output

    def test_error_for_nonexistent_task(self, tmp_path):
        result, _ = _invoke_insert_after(tmp_path / "plan.md", after="99")
        assert result.exit_code == 1
        assert "does not exist" in result.output
