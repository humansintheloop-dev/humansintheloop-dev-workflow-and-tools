"""Tests for with_plan_file_update context manager."""

import os

from i2code.plan.plan_file_io import with_plan_file_update


PLAN_TEXT = """\
# Implementation Plan: Test

---

## Steel Thread 1: First Thread
Intro.

- [ ] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one

---

## Summary
Done."""


class TestWithPlanFileUpdate:
    """with_plan_file_update only writes the file when content changes."""

    def test_skips_write_when_no_mutation(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_TEXT)
        os.utime(plan_file, (0, 0))

        with with_plan_file_update(str(plan_file)) as _domain_plan:
            pass  # no mutation

        assert os.path.getmtime(plan_file) == 0

    def test_writes_when_mutation_occurs(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_TEXT)
        os.utime(plan_file, (0, 0))

        with with_plan_file_update(str(plan_file)) as domain_plan:
            domain_plan.mark_task_complete(1, 1)

        assert os.path.getmtime(plan_file) != 0
