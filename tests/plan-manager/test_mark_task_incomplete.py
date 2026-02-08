"""Tests for mark_task_incomplete pure function."""

import re

from i2c.plan.tasks import mark_task_incomplete


PLAN_WITH_COMPLETED_TASK = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first thread.

- [x] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [x] Step one
    - [x] Step two

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else happens
  - Evidence: `echo done2`
  - Steps:
    - [ ] Step one

---

## Steel Thread 2: Second Thread
Introduction to second thread.

- [x] **Task 2.1: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello3`
  - Observable: More things
  - Evidence: `echo done3`
  - Steps:
    - [x] Step one

---

## Summary
This plan has 2 threads.
"""


PLAN_WITH_INCOMPLETE_TASK = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [ ] **Task 1.1: Already incomplete**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one

---

## Summary
Done.
"""


class TestMarkTaskIncomplete:
    """mark_task_incomplete marks a completed task and all its steps as incomplete."""

    def test_marks_task_checkbox_incomplete(self):
        result = mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 1, 1, "Reopening task")
        assert "- [ ] **Task 1.1: First task**" in result

    def test_marks_all_steps_incomplete(self):
        result = mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 1, 1, "Reopening task")
        lines = result.split('\n')
        in_task_1_1 = False
        steps_found = []
        for line in lines:
            if "**Task 1.1: First task**" in line:
                in_task_1_1 = True
                continue
            if in_task_1_1 and "**Task 1.2:" in line:
                break
            if in_task_1_1 and re.match(r'^\s+- \[[ x]\] ', line) and "Steps:" not in line:
                steps_found.append(line)

        assert len(steps_found) == 2
        for step in steps_found:
            assert "- [ ]" in step

    def test_does_not_affect_other_tasks(self):
        result = mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 1, 1, "Reopening task")
        assert "- [ ] **Task 1.2: Second task**" in result
        assert "- [x] **Task 2.1: Third task**" in result

    def test_does_not_affect_other_task_steps(self):
        result = mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 2, 1, "Reopening task")
        # Task 1.1 should still be completed
        assert "- [x] **Task 1.1: First task**" in result

    def test_appends_change_history(self):
        result = mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 1, 1, "Reopening task")
        assert "## Change History" in result
        assert "mark-task-incomplete" in result
        assert "Reopening task" in result

    def test_marks_task_in_second_thread(self):
        result = mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 2, 1, "Reopening task")
        assert "- [ ] **Task 2.1: Third task**" in result
        # Other completed task should remain complete
        assert "- [x] **Task 1.1: First task**" in result

    def test_no_change_history_without_rationale(self):
        result = mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 1, 1)
        assert "- [ ] **Task 1.1: First task**" in result
        assert "## Change History" not in result


class TestMarkTaskIncompleteErrors:
    """mark_task_incomplete returns errors for invalid inputs."""

    def test_error_on_already_incomplete_task(self):
        try:
            mark_task_incomplete(PLAN_WITH_INCOMPLETE_TASK, 1, 1, "Already incomplete")
            assert False, "Expected an error"
        except ValueError as e:
            assert "already incomplete" in str(e).lower()

    def test_error_on_nonexistent_thread(self):
        try:
            mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 99, 1, "No such thread")
            assert False, "Expected an error"
        except ValueError as e:
            assert "thread" in str(e).lower()

    def test_error_on_nonexistent_task(self):
        try:
            mark_task_incomplete(PLAN_WITH_COMPLETED_TASK, 1, 99, "No such task")
            assert False, "Expected an error"
        except ValueError as e:
            assert "task" in str(e).lower()
