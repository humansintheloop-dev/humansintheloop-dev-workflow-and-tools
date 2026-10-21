"""Acceptance tests: JSON from get-thread/get-task round-trips through replace-task/replace-thread."""

import json
from pathlib import Path

from click.testing import CliRunner

from i2code.plan.plan_cli import get_task_cmd, get_thread_cmd
from i2code.plan.task_cli import replace_task_cmd
from i2code.plan.thread_cli import replace_thread_cmd


SCHEMA_DIR = (
    Path(__file__).resolve().parents[2]
    / "claude-code-plugins/idea-to-code/skills/plan-file-management/references"
)

CHANGE_HISTORY_SEPARATOR = "\n\n---\n\n## Change History"

PLAN_WITH_CODE_SPANS = """\
# Implementation Plan: Round Trip

## Idea Type
**A. Feature** - A test feature

---

## Overview
A plan whose Entrypoint and Evidence lines use code spans in several ways.

---

## Steel Thread 1: Code spans
Introduction to the thread.

It has two paragraphs.

- [ ] **Task 1.1: Whole value is one code span**
  - TaskType: INFRA
  - Entrypoint: `echo setup`
  - Observable: Setup is done
  - Evidence: `echo verified`
  - Steps:
    - [ ] Create the file

- [ ] **Task 1.2: Evidence mixes code spans and prose**
  - TaskType: OUTCOME
  - Entrypoint: `vmr-push.sh` in `$SRC_ROOT/x`
  - Observable: `status` prints `ok`
  - Evidence: `vmr-wait-for-circleci.sh`, run in `$SRC_ROOT/x` after the push, exits 0
  - Steps:
    - [ ] Write the test
    - [ ] Implement the code

- [ ] **Task 1.3: Value starts and ends with separate code spans**
  - TaskType: OUTCOME
  - Entrypoint: `make build` then `make test`
  - Observable: Both pass
  - Evidence: `pytest tests/` and `uvx pyright`
  - Steps:
    - [ ] Run both

- [ ] **Task 1.4: Value wrapped in two backticks**
  - TaskType: OUTCOME
  - Entrypoint: ``echo double``
  - Observable: Double wrapped
  - Evidence: ``echo double-done``
  - Steps:
    - [ ] Leave it as it is

---

## Summary
Done.
"""


def _get_thread_json(plan_file, thread):
    result = CliRunner(catch_exceptions=False).invoke(
        get_thread_cmd, [str(plan_file), "--thread", str(thread), "--json"]
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _get_task_json(plan_file, thread, task):
    result = CliRunner(catch_exceptions=False).invoke(
        get_task_cmd, [str(plan_file), "--thread", str(thread), "--task", str(task), "--json"]
    )
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _replace_task(plan_file, thread, task, task_json):
    task_file = plan_file.parent / f"task-{thread}-{task}.json"
    task_file.write_text(json.dumps(task_json))
    result = CliRunner(catch_exceptions=False).invoke(replace_task_cmd, [
        str(plan_file), "--thread", str(thread), "--task", str(task),
        "--task-file", str(task_file), "--rationale", "round trip",
    ])
    assert result.exit_code == 0, result.output


def _replace_thread(plan_file, thread, thread_json):
    tasks_file = plan_file.parent / f"tasks-{thread}.json"
    tasks_file.write_text(json.dumps(thread_json["tasks"]))
    result = CliRunner(catch_exceptions=False).invoke(replace_thread_cmd, [
        str(plan_file), "--thread", str(thread),
        "--title", thread_json["title"], "--introduction", thread_json["introduction"],
        "--tasks-file", str(tasks_file), "--rationale", "round trip",
    ])
    assert result.exit_code == 0, result.output


def _schema_properties(schema_name):
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    assert set(schema["required"]) == set(schema["properties"])
    return set(schema["properties"])


def _without_change_history(plan_text):
    return plan_text.split(CHANGE_HISTORY_SEPARATOR)[0] + "\n"


class TestGetThreadJsonRoundTrip:

    def test_replacing_each_task_with_its_json_leaves_plan_unchanged(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_CODE_SPANS)

        thread_json = _get_thread_json(plan_file, 1)
        for task_num, task_json in enumerate(thread_json["tasks"], 1):
            _replace_task(plan_file, 1, task_num, task_json)

        assert _without_change_history(plan_file.read_text()) == PLAN_WITH_CODE_SPANS

    def test_replacing_thread_with_its_json_leaves_plan_unchanged(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_CODE_SPANS)

        _replace_thread(plan_file, 1, _get_thread_json(plan_file, 1))

        assert _without_change_history(plan_file.read_text()) == PLAN_WITH_CODE_SPANS

    def test_json_has_exactly_the_schema_properties(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_CODE_SPANS)

        thread_json = _get_thread_json(plan_file, 1)

        assert set(thread_json) == _schema_properties("thread.schema.json")
        for task_json in thread_json["tasks"]:
            assert set(task_json) == _schema_properties("task.schema.json")
            assert all(isinstance(step, str) for step in task_json["steps"])


class TestGetTaskJsonRoundTrip:

    def test_replacing_each_task_with_its_json_leaves_plan_unchanged(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_CODE_SPANS)

        for task_num in range(1, 5):
            _replace_task(plan_file, 1, task_num, _get_task_json(plan_file, 1, task_num))

        assert _without_change_history(plan_file.read_text()) == PLAN_WITH_CODE_SPANS
