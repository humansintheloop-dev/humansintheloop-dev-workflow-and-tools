"""CLI integration tests for replace-task command."""

import json

from click.testing import CliRunner

from i2code.plan.task_cli import replace_task_cmd


PLAN_WITH_THREE_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [x] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [x] Do first

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

- [ ] **Task 1.3: Third task**
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

_REPLACE_DEFAULTS = dict(
    thread="1", task="2", title="Replaced", task_type="INFRA",
    entrypoint="echo", observable="obs", evidence="ev",
    steps='["step"]', rationale="reason",
)


def _invoke_replace(plan_file, **overrides):
    """Write plan, invoke replace-task with defaults + overrides, return (result, updated_text)."""
    plan_file.write_text(PLAN_WITH_THREE_TASKS)
    d = {**_REPLACE_DEFAULTS, **overrides}
    args = [
        str(plan_file), "--thread", d["thread"], "--task", d["task"],
        "--title", d["title"], "--task-type", d["task_type"],
        "--entrypoint", d["entrypoint"], "--observable", d["observable"],
        "--evidence", d["evidence"], "--steps", d["steps"],
        "--rationale", d["rationale"],
    ]
    result = CliRunner(catch_exceptions=False).invoke(replace_task_cmd, args)
    return result, plan_file.read_text()


class TestReplaceTaskCli:
    """CLI integration: replace-task replaces task content in file via domain model."""

    def test_replaces_task_content_and_writes_file(self, tmp_path):
        result, updated = _invoke_replace(
            tmp_path / "plan.md",
            title="Replaced task", entrypoint="echo replaced",
            observable="Replaced done", evidence="echo replaced-done",
            steps='["New step"]', rationale="Replacing second task",
        )
        assert result.exit_code == 0
        assert "Task 1.2: Replaced task" in updated
        assert "INFRA" in updated
        assert "echo replaced" in updated
        assert "New step" in updated

    def test_preserves_numbering(self, tmp_path):
        result, updated = _invoke_replace(tmp_path / "plan.md")
        assert result.exit_code == 0
        assert "Task 1.1: First task" in updated
        assert "Task 1.2: Replaced" in updated
        assert "Task 1.3: Third task" in updated

    def test_replaced_task_is_incomplete(self, tmp_path):
        result, updated = _invoke_replace(
            tmp_path / "plan.md", task="1", title="New first", task_type="OUTCOME",
        )
        assert result.exit_code == 0
        assert "- [ ] **Task 1.1: New first**" in updated

    def test_outputs_confirmation_message(self, tmp_path):
        result, _ = _invoke_replace(tmp_path / "plan.md")
        assert "Replaced task 1.2" in result.output

    def test_appends_change_history(self, tmp_path):
        result, updated = _invoke_replace(
            tmp_path / "plan.md", rationale="Rewritten for clarity",
        )
        assert result.exit_code == 0
        assert "replace-task" in updated
        assert "Rewritten for clarity" in updated

    def test_error_for_nonexistent_thread(self, tmp_path):
        result, _ = _invoke_replace(tmp_path / "plan.md", thread="99")
        assert result.exit_code == 1
        assert "thread 99 does not exist" in result.output

    def test_error_for_nonexistent_task(self, tmp_path):
        result, _ = _invoke_replace(tmp_path / "plan.md", task="99")
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_error_for_invalid_json_steps(self, tmp_path):
        result, _ = _invoke_replace(tmp_path / "plan.md", steps="not-json")
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


def _invoke_replace_with_task_file(plan_file, task_json=TASK_FILE_JSON, extra_args=None):
    """Write plan and task JSON file, invoke replace-task with --task-file."""
    plan_file.write_text(PLAN_WITH_THREE_TASKS)
    task_file = plan_file.parent / "task.json"
    task_file.write_text(task_json)
    args = [
        str(plan_file), "--thread", "1", "--task", "2",
        "--task-file", str(task_file),
        "--rationale", "Replacing task from file",
    ]
    if extra_args:
        args += extra_args
    result = CliRunner(catch_exceptions=False).invoke(replace_task_cmd, args)
    return result, plan_file.read_text()


class TestReplaceTaskCliWithTaskFile:
    """CLI integration: replace-task supports --task-file JSON input."""

    def test_replaces_using_task_file(self, tmp_path):
        result, updated = _invoke_replace_with_task_file(tmp_path / "plan.md")
        assert result.exit_code == 0
        assert "Task 1.2: File-based task" in updated
        assert "File step 1" in updated
        assert "File step 2" in updated

    def test_replaced_task_is_incomplete(self, tmp_path):
        result, updated = _invoke_replace_with_task_file(tmp_path / "plan.md")
        assert result.exit_code == 0
        assert "- [ ] **Task 1.2: File-based task**" in updated

    def test_error_when_task_file_combined_with_individual_option(self, tmp_path):
        result, _ = _invoke_replace_with_task_file(
            tmp_path / "plan.md", extra_args=["--title", "Override"],
        )
        assert result.exit_code == 1
        assert "replace-task: --task-file and individual task options are mutually exclusive" in result.output

    def test_error_when_no_options_provided(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_TASKS)
        args = [
            str(plan_file), "--thread", "1", "--task", "2",
            "--rationale", "Replacing task",
        ]
        result = CliRunner(catch_exceptions=False).invoke(replace_task_cmd, args)
        assert result.exit_code == 1
        assert "replace-task: either --task-file or all individual task options are required" in result.output

    def test_error_when_task_file_missing_required_field(self, tmp_path):
        incomplete_json = json.dumps({
            "title": "Incomplete",
            "task_type": "OUTCOME",
            "entrypoint": "echo x",
            "observable": "x works",
            "steps": ["Step 1"],
        })
        result, _ = _invoke_replace_with_task_file(
            tmp_path / "plan.md", task_json=incomplete_json,
        )
        assert result.exit_code == 1
        assert "replace-task: --task-file JSON is missing required field: evidence" in result.output

    def test_error_when_task_file_invalid_json(self, tmp_path):
        result, _ = _invoke_replace_with_task_file(
            tmp_path / "plan.md", task_json="not-json",
        )
        assert result.exit_code == 1
        assert "replace-task: --task-file is not valid JSON:" in result.output
