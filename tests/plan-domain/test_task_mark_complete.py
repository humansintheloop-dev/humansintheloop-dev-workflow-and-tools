"""Tests for Task.mark_complete() mutation."""

import pytest

from i2code.plan_domain.task import Task


def _make_task(lines_text):
    return Task(_lines=lines_text.strip().split('\n'))


INCOMPLETE_TASK = """\
- [ ] **Task 1.1: Build widget**
  - TaskType: INFRA
  - Entrypoint: `echo build`
  - Observable: Widget exists
  - Evidence: `echo verify`
  - Steps:
    - [ ] Create skeleton
    - [ ] Add tests"""

COMPLETED_TASK = """\
- [x] **Task 1.1: Build widget**
  - TaskType: INFRA
  - Entrypoint: `echo build`
  - Observable: Widget exists
  - Evidence: `echo verify`
  - Steps:
    - [x] Create skeleton
    - [x] Add tests"""


class TestTaskMarkComplete:
    """Task.mark_complete() marks heading and all steps as complete."""

    def test_marks_heading_complete(self):
        task = _make_task(INCOMPLETE_TASK)
        task.mark_complete()
        assert task.is_completed

    def test_marks_all_steps_complete(self):
        task = _make_task(INCOMPLETE_TASK)
        task.mark_complete()
        for step in task.steps:
            assert step['completed']

    def test_raises_if_already_complete(self):
        task = _make_task(COMPLETED_TASK)
        with pytest.raises(ValueError, match="already complete"):
            task.mark_complete()
