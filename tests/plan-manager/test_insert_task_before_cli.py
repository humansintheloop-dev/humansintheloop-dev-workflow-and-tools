"""CLI integration tests for insert-task-before command."""

import json

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


TASK_FILE_JSON = json.dumps({
    "title": "File-based task",
    "task_type": "OUTCOME",
    "entrypoint": "echo file-task",
    "observable": "File task works",
    "evidence": "echo file-task-done",
    "steps": ["File step 1", "File step 2"],
})


def _invoke_insert_before_with_task_file(plan_file, task_json=TASK_FILE_JSON, extra_args=None):
    """Write plan and task JSON file, invoke insert-task-before with --task-file."""
    plan_file.write_text(PLAN_WITH_TWO_TASKS)
    task_file = plan_file.parent / "task.json"
    task_file.write_text(task_json)
    args = [
        str(plan_file), "--thread", "1", "--before", "1",
        "--task-file", str(task_file),
        "--rationale", "Adding task from file",
    ]
    if extra_args:
        args += extra_args
    result = CliRunner(catch_exceptions=False).invoke(insert_task_before_cmd, args)
    return result, plan_file.read_text()


class TestInsertTaskBeforeCliWithTaskFile:
    """CLI integration: insert-task-before supports --task-file JSON input."""

    def test_inserts_using_task_file(self, tmp_path):
        result, updated = _invoke_insert_before_with_task_file(tmp_path / "plan.md")
        assert result.exit_code == 0
        assert "Task 1.1: File-based task" in updated
        assert "File step 1" in updated
        assert "File step 2" in updated

    def test_error_when_task_file_combined_with_individual_option(self, tmp_path):
        result, _ = _invoke_insert_before_with_task_file(
            tmp_path / "plan.md", extra_args=["--title", "Override"],
        )
        assert result.exit_code == 1
        assert "insert-task-before: --task-file and individual task options are mutually exclusive" in result.output

    def test_error_when_no_options_provided(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_TASKS)
        args = [
            str(plan_file), "--thread", "1", "--before", "1",
            "--rationale", "Adding task",
        ]
        result = CliRunner(catch_exceptions=False).invoke(insert_task_before_cmd, args)
        assert result.exit_code == 1
        assert "insert-task-before: either --task-file or all individual task options are required" in result.output

    def test_error_when_task_file_missing_required_field(self, tmp_path):
        incomplete_json = json.dumps({
            "title": "Incomplete",
            "task_type": "OUTCOME",
            "entrypoint": "echo x",
            "observable": "x works",
            "steps": ["Step 1"],
        })
        result, _ = _invoke_insert_before_with_task_file(
            tmp_path / "plan.md", task_json=incomplete_json,
        )
        assert result.exit_code == 1
        assert "insert-task-before: --task-file JSON is missing required field: evidence" in result.output

    def test_error_when_task_file_invalid_json(self, tmp_path):
        result, _ = _invoke_insert_before_with_task_file(
            tmp_path / "plan.md", task_json="not-json",
        )
        assert result.exit_code == 1
        assert "insert-task-before: --task-file is not valid JSON:" in result.output
