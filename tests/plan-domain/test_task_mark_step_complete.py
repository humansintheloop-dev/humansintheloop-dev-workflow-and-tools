"""Tests for Task.mark_step_complete() mutation."""

import pytest

from i2code.plan_domain.task import Task


def _make_task(lines_text):
    return Task(_lines=lines_text.strip().split('\n'))


TASK_WITH_INCOMPLETE_STEPS = """\
- [ ] **Task 1.1: Build widget**
  - TaskType: INFRA
  - Entrypoint: `echo build`
  - Observable: Widget exists
  - Evidence: `echo verify`
  - Steps:
    - [ ] Create skeleton
    - [ ] Add tests"""


class TestTaskMarkStepComplete:
    """Task.mark_step_complete() marks a single step as complete."""

    def test_marks_target_step_complete(self):
        task = _make_task(TASK_WITH_INCOMPLETE_STEPS)
        task.mark_step_complete(1)
        assert task.steps[0]['completed']

    def test_does_not_affect_other_steps(self):
        task = _make_task(TASK_WITH_INCOMPLETE_STEPS)
        task.mark_step_complete(1)
        assert not task.steps[1]['completed']

    def test_raises_if_step_already_complete(self):
        task = _make_task(TASK_WITH_INCOMPLETE_STEPS)
        task.mark_step_complete(1)
        with pytest.raises(ValueError, match="already complete"):
            task.mark_step_complete(1)

    def test_raises_if_step_does_not_exist(self):
        task = _make_task(TASK_WITH_INCOMPLETE_STEPS)
        with pytest.raises(ValueError, match="does not exist"):
            task.mark_step_complete(99)
