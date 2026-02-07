"""Tests for get_next_task pure function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
get_next_task = _mod.get_next_task


PLAN_WITH_FIRST_INCOMPLETE = """\
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

---

## Summary
Done.
"""


PLAN_WITH_FIRST_COMPLETE = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction.

- [x] **Task 1.1: Done task**
  - TaskType: INFRA
  - Entrypoint: `echo done-cmd`
  - Observable: Already done
  - Evidence: `echo verified`
  - Steps:
    - [x] Step already done

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second thing happens
  - Evidence: `echo second-done`
  - Steps:
    - [ ] Do second thing

---

## Steel Thread 2: Second Thread
Intro.

- [ ] **Task 2.1: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo third`
  - Observable: Third thing
  - Evidence: `echo third-done`
  - Steps:
    - [ ] Do third thing

---

## Summary
Done.
"""


ALL_COMPLETE_PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Intro.

- [x] **Task 1.1: Done task**
  - TaskType: INFRA
  - Entrypoint: `echo done`
  - Observable: Done
  - Evidence: `echo done`
  - Steps:
    - [x] All done

---

## Summary
All done.
"""


class TestGetNextTask:
    """get_next_task returns the first uncompleted task."""

    def test_returns_first_incomplete_task(self):
        result = get_next_task(PLAN_WITH_FIRST_INCOMPLETE)
        assert result['thread_number'] == 1
        assert result['task_number'] == 1
        assert result['title'] == 'First task'

    def test_returns_task_metadata(self):
        result = get_next_task(PLAN_WITH_FIRST_INCOMPLETE)
        assert result['task_type'] == 'INFRA'
        assert result['entrypoint'] == 'echo hello'
        assert result['observable'] == 'Something happens'
        assert result['evidence'] == 'echo done'

    def test_returns_task_steps(self):
        result = get_next_task(PLAN_WITH_FIRST_INCOMPLETE)
        assert len(result['steps']) == 2
        assert result['steps'][0]['description'] == 'Step one'
        assert result['steps'][0]['completed'] is False
        assert result['steps'][1]['description'] == 'Step two'

    def test_skips_completed_task(self):
        result = get_next_task(PLAN_WITH_FIRST_COMPLETE)
        assert result['thread_number'] == 1
        assert result['task_number'] == 2
        assert result['title'] == 'Second task'

    def test_returns_none_when_all_complete(self):
        result = get_next_task(ALL_COMPLETE_PLAN)
        assert result is None
