"""Tests for Plan.is_task_completed."""

import pytest

from i2code.plan_domain.parser import parse


PLAN = """\
# Implementation Plan

## Steel Thread 1: Setup

- [x] **Task 1.1: Completed task**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Project compiles
  - Evidence: `pytest`
  - Steps:
    - [x] Create directory layout

- [ ] **Task 1.2: Incomplete task**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Tests pass
  - Evidence: `pytest`
  - Steps:
    - [ ] Write tests
"""


@pytest.mark.unit
class TestIsTaskCompleted:

    def test_completed_task_returns_true(self):
        plan = parse(PLAN)
        assert plan.is_task_completed(thread=1, task=1) is True

    def test_incomplete_task_returns_false(self):
        plan = parse(PLAN)
        assert plan.is_task_completed(thread=1, task=2) is False
