"""Tests for mark_task_complete pure function."""

import re

from i2c.plan.tasks import mark_task_complete


PLAN_WITH_INCOMPLETE_TASK = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first thread.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one
    - [ ] Step two

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

- [ ] **Task 2.1: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello3`
  - Observable: More things
  - Evidence: `echo done3`
  - Steps:
    - [ ] Step one

---

## Summary
This plan has 2 threads.
"""


PLAN_WITH_COMPLETED_TASK = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [x] **Task 1.1: Already done**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [x] Step one

---

## Summary
Done.
"""


class TestMarkTaskComplete:
    """mark_task_complete marks a task and all its steps as complete."""

    def test_marks_task_checkbox_complete(self):
        result = mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 1, 1, "Task done")
        assert "- [x] **Task 1.1: First task**" in result

    def test_marks_all_steps_complete(self):
        result = mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 1, 1, "Task done")
        # The steps under task 1.1 should be marked complete
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
            assert "- [x]" in step

    def test_does_not_affect_other_tasks(self):
        result = mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 1, 1, "Task done")
        assert "- [ ] **Task 1.2: Second task**" in result
        assert "- [ ] **Task 2.1: Third task**" in result

    def test_does_not_affect_other_task_steps(self):
        result = mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 1, 1, "Task done")
        lines = result.split('\n')
        in_task_1_2 = False
        for line in lines:
            if "**Task 1.2: Second task**" in line:
                in_task_1_2 = True
                continue
            if in_task_1_2 and line.startswith("---"):
                break
            if in_task_1_2 and re.match(r'^\s+- \[', line) and "Steps:" not in line:
                assert "- [ ]" in line

    def test_appends_change_history(self):
        result = mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 1, 1, "Task done")
        assert "## Change History" in result
        assert "mark-task-complete" in result
        assert "Task done" in result

    def test_marks_task_in_second_thread(self):
        result = mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 2, 1, "Task done")
        assert "- [x] **Task 2.1: Third task**" in result
        # Other tasks should remain incomplete
        assert "- [ ] **Task 1.1: First task**" in result
        assert "- [ ] **Task 1.2: Second task**" in result

    def test_no_change_history_without_rationale(self):
        result = mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 1, 1)
        assert "- [x] **Task 1.1: First task**" in result
        assert "## Change History" not in result


class TestMarkTaskCompleteErrors:
    """mark_task_complete returns errors for invalid inputs."""

    def test_error_on_already_complete_task(self):
        try:
            mark_task_complete(PLAN_WITH_COMPLETED_TASK, 1, 1, "Already done")
            assert False, "Expected an error"
        except ValueError as e:
            assert "already complete" in str(e).lower()

    def test_error_on_nonexistent_thread(self):
        try:
            mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 99, 1, "No such thread")
            assert False, "Expected an error"
        except ValueError as e:
            assert "thread" in str(e).lower()

    def test_error_on_nonexistent_task(self):
        try:
            mark_task_complete(PLAN_WITH_INCOMPLETE_TASK, 1, 99, "No such task")
            assert False, "Expected an error"
        except ValueError as e:
            assert "task" in str(e).lower()
