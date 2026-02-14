"""Tests for Task.mark_step_incomplete() mutation."""

import pytest

from i2code.plan_domain.task import Task


def _make_task(lines_text):
    return Task(_lines=lines_text.strip().split('\n'))


TASK_WITH_COMPLETED_STEPS = """\
- [ ] **Task 1.1: Build widget**
  - TaskType: INFRA
  - Entrypoint: `echo build`
  - Observable: Widget exists
  - Evidence: `echo verify`
  - Steps:
    - [x] Create skeleton
    - [x] Add tests"""


class TestTaskMarkStepIncomplete:
    """Task.mark_step_incomplete() marks a single step as incomplete."""

    def test_marks_target_step_incomplete(self):
        task = _make_task(TASK_WITH_COMPLETED_STEPS)
        task.mark_step_incomplete(1)
        assert not task.steps[0]['completed']

    def test_does_not_affect_other_steps(self):
        task = _make_task(TASK_WITH_COMPLETED_STEPS)
        task.mark_step_incomplete(1)
        assert task.steps[1]['completed']

    def test_raises_if_step_already_incomplete(self):
        task = _make_task(TASK_WITH_COMPLETED_STEPS)
        task.mark_step_incomplete(1)
        with pytest.raises(ValueError, match="already incomplete"):
            task.mark_step_incomplete(1)

    def test_raises_if_step_does_not_exist(self):
        task = _make_task(TASK_WITH_COMPLETED_STEPS)
        with pytest.raises(ValueError, match="does not exist"):
            task.mark_step_incomplete(99)
