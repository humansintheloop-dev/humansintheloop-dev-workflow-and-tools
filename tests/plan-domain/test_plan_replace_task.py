"""Tests for Plan.replace_task() delegation."""

import pytest

from i2code.plan_domain.parser import parse
from i2code.plan_domain.task import Task


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

- [ ] **Task 1.3: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo third`
  - Observable: Third
  - Evidence: `echo third-done`
  - Steps:
    - [ ] Do third

---

## Summary
Done."""


class TestPlanReplaceTask:
    """Plan.replace_task() delegates to Thread and validates inputs."""

    def test_replaces_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("Replaced", "INFRA", "echo r", "R done", "echo r-done", ["Step R"])
        plan.replace_task(1, 2, new_task)
        assert plan.threads[0].tasks[1].title == "Replaced"

    def test_renumbers_in_output(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("Replaced", "INFRA", "echo r", "R done", "echo r-done", ["Step R"])
        plan.replace_task(1, 2, new_task)
        text = plan.to_text()
        assert "Task 1.1: First task" in text
        assert "Task 1.2: Replaced" in text
        assert "Task 1.3: Third task" in text

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New", "INFRA", "echo", "obs", "ev", ["step"])
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.replace_task(99, 1, new_task)

    def test_error_for_nonexistent_task(self):
        plan = parse(PLAN_TEXT)
        new_task = Task.create("New", "INFRA", "echo", "obs", "ev", ["step"])
        with pytest.raises(ValueError, match="task 99 does not exist"):
            plan.replace_task(1, 99, new_task)
