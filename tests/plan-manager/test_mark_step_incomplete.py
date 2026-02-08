"""Tests for mark_step_incomplete pure function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
mark_step_incomplete = _mod.mark_step_incomplete


PLAN_WITH_COMPLETED_STEPS = """\
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
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [x] Step one
    - [x] Step two
    - [x] Step three

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second thing
  - Evidence: `echo second-done`
  - Steps:
    - [x] Another step

---

## Summary
Done.
"""


PLAN_WITH_INCOMPLETE_STEP = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [ ] Not done step
    - [x] Done step

---

## Summary
Done.
"""


class TestMarkStepIncomplete:
    """mark_step_incomplete changes a step from checked to unchecked."""

    def test_marks_step_incomplete(self):
        result = mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 1, 1, 1, "Reopening step one")
        assert '    - [ ] Step one' in result
        assert '    - [x] Step two' in result
        assert '    - [x] Step three' in result

    def test_marks_second_step_incomplete(self):
        result = mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 1, 1, 2, "Reopening step two")
        assert '    - [x] Step one' in result
        assert '    - [ ] Step two' in result
        assert '    - [x] Step three' in result

    def test_marks_step_in_second_task(self):
        result = mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 1, 2, 1, "Reopening another step")
        assert '    - [ ] Another step' in result
        # First task steps unchanged
        assert '    - [x] Step one' in result

    def test_appends_change_history(self):
        result = mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 1, 1, 1, "Reopening first step")
        assert '## Change History' in result
        assert 'mark-step-incomplete' in result
        assert 'Reopening first step' in result

    def test_does_not_affect_task_checkbox(self):
        result = mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 1, 1, 1, "Reopening")
        assert '- [x] **Task 1.1: First task**' in result


class TestMarkStepIncompleteErrors:
    """mark_step_incomplete returns errors for invalid inputs."""

    def test_error_on_already_incomplete_step(self):
        import pytest
        with pytest.raises(ValueError, match="already incomplete"):
            mark_step_incomplete(PLAN_WITH_INCOMPLETE_STEP, 1, 1, 1, "Already incomplete")

    def test_error_on_nonexistent_step(self):
        import pytest
        with pytest.raises(ValueError, match="does not exist"):
            mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 1, 1, 99, "No such step")

    def test_error_on_nonexistent_task(self):
        import pytest
        with pytest.raises(ValueError, match="does not exist"):
            mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 1, 99, 1, "No such task")

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="does not exist"):
            mark_step_incomplete(PLAN_WITH_COMPLETED_STEPS, 99, 1, 1, "No such thread")
