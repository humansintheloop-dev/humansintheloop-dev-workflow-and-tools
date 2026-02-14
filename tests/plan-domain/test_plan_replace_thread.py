"""Tests for Plan.replace_thread() method."""

import pytest

from i2code.plan_domain.parser import parse
from i2code.plan_domain.thread import Thread


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro first.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First
  - Evidence: `echo first-done`
  - Steps:
    - [ ] Do first

## Steel Thread 2: Second Thread
Intro second.

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


NEW_TASKS = [
    {
        "title": "New task A",
        "task_type": "INFRA",
        "entrypoint": "echo new-a",
        "observable": "New A works",
        "evidence": "echo new-a-done",
        "steps": ["Step A1", "Step A2"],
    },
]


class TestPlanReplaceThread:
    """Plan.replace_thread() replaces a thread in place and validates inputs."""

    def test_replaces_thread_content(self):
        plan = parse(PLAN_TEXT)
        new_thread = Thread.create(title="Replaced", introduction="New intro.", tasks=NEW_TASKS)
        plan.replace_thread(1, new_thread)
        text = plan.to_text()
        assert "Steel Thread 1: Replaced" in text
        assert "New intro." in text
        assert "Task 1.1: New task A" in text

    def test_error_for_nonexistent_thread(self):
        plan = parse(PLAN_TEXT)
        new_thread = Thread.create(title="T", introduction="I", tasks=NEW_TASKS)
        with pytest.raises(ValueError, match="thread 99 does not exist"):
            plan.replace_thread(99, new_thread)
