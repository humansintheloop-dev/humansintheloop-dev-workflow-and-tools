"""Tests for mark_step_complete pure function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
mark_step_complete = _mod.mark_step_complete


PLAN_WITH_STEPS = """\
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
    - [ ] Step one
    - [ ] Step two
    - [ ] Step three

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second thing
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Another step

---

## Summary
Done.
"""


PLAN_WITH_COMPLETED_STEP = """\
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
    - [x] Already done step
    - [ ] Not done step

---

## Summary
Done.
"""


class TestMarkStepComplete:
    """mark_step_complete changes a step from unchecked to checked."""

    def test_marks_step_complete(self):
        result = mark_step_complete(PLAN_WITH_STEPS, 1, 1, 1, "Done step one")
        assert '    - [x] Step one' in result
        assert '    - [ ] Step two' in result
        assert '    - [ ] Step three' in result

    def test_marks_second_step_complete(self):
        result = mark_step_complete(PLAN_WITH_STEPS, 1, 1, 2, "Done step two")
        assert '    - [ ] Step one' in result
        assert '    - [x] Step two' in result
        assert '    - [ ] Step three' in result

    def test_marks_step_in_second_task(self):
        result = mark_step_complete(PLAN_WITH_STEPS, 1, 2, 1, "Done another step")
        assert '    - [x] Another step' in result
        # First task steps unchanged
        assert '    - [ ] Step one' in result

    def test_appends_change_history(self):
        result = mark_step_complete(PLAN_WITH_STEPS, 1, 1, 1, "Completed first step")
        assert '## Change History' in result
        assert 'mark-step-complete' in result
        assert 'Completed first step' in result

    def test_does_not_affect_task_checkbox(self):
        result = mark_step_complete(PLAN_WITH_STEPS, 1, 1, 1, "Done")
        assert '- [ ] **Task 1.1: First task**' in result


class TestMarkStepCompleteErrors:
    """mark_step_complete returns errors for invalid inputs."""

    def test_error_on_already_complete_step(self):
        import pytest
        with pytest.raises(ValueError, match="already complete"):
            mark_step_complete(PLAN_WITH_COMPLETED_STEP, 1, 1, 1, "Already done")

    def test_error_on_nonexistent_step(self):
        import pytest
        with pytest.raises(ValueError, match="does not exist"):
            mark_step_complete(PLAN_WITH_STEPS, 1, 1, 99, "No such step")

    def test_error_on_nonexistent_task(self):
        import pytest
        with pytest.raises(ValueError, match="does not exist"):
            mark_step_complete(PLAN_WITH_STEPS, 1, 99, 1, "No such task")

    def test_error_on_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="does not exist"):
            mark_step_complete(PLAN_WITH_STEPS, 99, 1, 1, "No such thread")
