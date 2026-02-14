"""Tests for Plan.get_next_task() returning NumberedTask from plan files."""

from i2code.plan_domain.parser import parse
from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber


PLAN_WITH_INCOMPLETE = """\
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

## Summary
Done.
"""


class TestPlanGetNextTaskAcceptance:
    """Acceptance: parse a plan file, call Plan.get_next_task(), get a NumberedTask."""

    def test_returns_numbered_task_from_plan_file(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE)

        plan = parse(plan_file.read_text())
        result = plan.get_next_task()

        assert isinstance(result, NumberedTask)
        assert result.number == TaskNumber(thread=1, task=1)
        assert result.task.title == 'First task'

    def test_print_formats_task_for_display(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_INCOMPLETE)

        plan = parse(plan_file.read_text())
        result = plan.get_next_task()

        expected = (
            "Thread 1, Task 1.1: First task\n"
            "  TaskType: INFRA\n"
            "  Entrypoint: echo hello\n"
            "  Observable: Something happens\n"
            "  Evidence: echo done\n"
            "  Steps:\n"
            "    1. [ ] Step one\n"
            "    2. [ ] Step two"
        )
        assert result.print() == expected

    def test_skips_completed_task(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_FIRST_COMPLETE)

        plan = parse(plan_file.read_text())
        result = plan.get_next_task()

        assert result.number == TaskNumber(thread=1, task=2)
        assert result.task.title == 'Second task'

