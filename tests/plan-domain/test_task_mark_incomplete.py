"""Tests for Task.mark_incomplete() mutation."""

import pytest

from i2code.plan_domain.task import Task


def _make_task(lines_text):
    return Task(_lines=lines_text.strip().split('\n'))


COMPLETED_TASK = """\
- [x] **Task 1.1: Build widget**
  - TaskType: INFRA
  - Entrypoint: `echo build`
  - Observable: Widget exists
  - Evidence: `echo verify`
  - Steps:
    - [x] Create skeleton
    - [x] Add tests"""

INCOMPLETE_TASK = """\
- [ ] **Task 1.1: Build widget**
  - TaskType: INFRA
  - Entrypoint: `echo build`
  - Observable: Widget exists
  - Evidence: `echo verify`
  - Steps:
    - [ ] Create skeleton
    - [ ] Add tests"""


class TestTaskMarkIncomplete:
    """Task.mark_incomplete() marks heading and all steps as incomplete."""

    def test_marks_heading_incomplete(self):
        task = _make_task(COMPLETED_TASK)
        task.mark_incomplete()
        assert not task.is_completed

    def test_marks_all_steps_incomplete(self):
        task = _make_task(COMPLETED_TASK)
        task.mark_incomplete()
        for step in task.steps:
            assert not step['completed']

    def test_raises_if_already_incomplete(self):
        task = _make_task(INCOMPLETE_TASK)
        with pytest.raises(ValueError, match="already incomplete"):
            task.mark_incomplete()
