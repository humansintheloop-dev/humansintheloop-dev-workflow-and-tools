"""Tests for plan helpers: get_next_task and is_task_completed."""

import pytest


PLAN_WITH_UNCOMPLETED_TASK = """\
# Implementation Plan

## Steel Thread 1: Setup

- [ ] **Task 1.1: Create project structure**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Project compiles
  - Evidence: `pytest`
  - Steps:
    - [ ] Create directory layout
"""

PLAN_ALL_COMPLETED = """\
# Implementation Plan

## Steel Thread 1: Setup

- [x] **Task 1.1: Create project structure**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Project compiles
  - Evidence: `pytest`
  - Steps:
    - [x] Create directory layout
"""


@pytest.mark.unit
class TestGetNextTask:

    def test_returns_numbered_task_for_first_uncompleted(self, tmp_path):
        from i2code.implement.git_setup import get_next_task

        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(PLAN_WITH_UNCOMPLETED_TASK)

        result = get_next_task(str(plan_file))

        assert result is not None
        assert result.number.thread == 1
        assert result.number.task == 1
        assert result.task.title == "Create project structure"

    def test_returns_none_when_all_complete(self, tmp_path):
        from i2code.implement.git_setup import get_next_task

        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(PLAN_ALL_COMPLETED)

        result = get_next_task(str(plan_file))

        assert result is None


@pytest.mark.unit
class TestIsTaskCompleted:

    def test_completed_task_returns_true(self, tmp_path):
        from i2code.implement.git_setup import is_task_completed

        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(PLAN_ALL_COMPLETED)

        assert is_task_completed(str(plan_file), thread=1, task=1) is True

    def test_uncompleted_task_returns_false(self, tmp_path):
        from i2code.implement.git_setup import is_task_completed

        plan_file = tmp_path / "test-plan.md"
        plan_file.write_text(PLAN_WITH_UNCOMPLETED_TASK)

        assert is_task_completed(str(plan_file), thread=1, task=1) is False
