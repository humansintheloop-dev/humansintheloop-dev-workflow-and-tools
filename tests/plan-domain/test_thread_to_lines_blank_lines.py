"""Tests for blank lines between tasks in Thread.to_lines() output."""

from i2code.plan_domain.parser import parse
from i2code.plan_domain.task import Task, TaskMetadata


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second

---

## Summary
Done."""


def _new_task(title="New"):
    return Task.create(title, TaskMetadata("INFRA", "echo new", "New", "echo new-done"), ["Do new"])


def _is_task_title(line):
    return line.startswith('- [')


def _has_blank_line_before_each_task(lines):
    """Check that every task title line (after the first) is preceded by a blank line."""
    for i, line in enumerate(lines):
        if not _is_task_title(line):
            continue
        if i > 0 and lines[i - 1] != '':
            return False
    return True


class TestThreadToLinesBlankLines:
    """Thread.to_lines() emits a blank line between consecutive tasks."""

    def test_parsed_thread_has_blank_lines_between_tasks(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        lines = thread.to_lines(1)
        assert _has_blank_line_before_each_task(lines)

    def test_created_thread_has_blank_lines_between_tasks(self):
        from i2code.plan_domain.thread import Thread
        thread = Thread.create("Test Thread", "Intro.", [
            {"title": "First", "task_type": "INFRA", "entrypoint": "echo 1", "observable": "O1", "evidence": "E1", "steps": ["S1"]},
            {"title": "Second", "task_type": "OUTCOME", "entrypoint": "echo 2", "observable": "O2", "evidence": "E2", "steps": ["S2"]},
        ])
        lines = thread.to_lines(1)
        assert _has_blank_line_before_each_task(lines)

    def test_insert_task_before_has_blank_lines_between_tasks(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.insert_task_before(1, _new_task())
        lines = thread.to_lines(1)
        assert _has_blank_line_before_each_task(lines)

    def test_insert_task_after_has_blank_lines_between_tasks(self):
        plan = parse(PLAN_TEXT)
        thread = plan.threads[0]
        thread.insert_task_after(1, _new_task())
        lines = thread.to_lines(1)
        assert _has_blank_line_before_each_task(lines)
