"""Tests for fix_numbering pure function."""

from i2c.plan.plans import fix_numbering


CORRECTLY_NUMBERED_PLAN = """\
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

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else happens
  - Evidence: `echo done2`
  - Steps:
    - [ ] Step one

---

## Steel Thread 2: Second Thread
Introduction to second thread.

- [ ] **Task 2.1: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello3`
  - Observable: More things
  - Evidence: `echo done3`
  - Steps:
    - [ ] Step one

---

## Summary
This plan has 2 threads.
"""


MISNUMBERED_PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 5: First Thread
Introduction to first thread.

- [ ] **Task 5.3: First task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something happens
  - Evidence: `echo done`
  - Steps:
    - [ ] Step one
    - [ ] Step two

- [ ] **Task 5.7: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else happens
  - Evidence: `echo done2`
  - Steps:
    - [ ] Step one

---

## Steel Thread 9: Second Thread
Introduction to second thread.

- [ ] **Task 9.1: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello3`
  - Observable: More things
  - Evidence: `echo done3`
  - Steps:
    - [ ] Step one

---

## Summary
This plan has 2 threads.
"""


class TestFixNumberingCorrectPlan:
    """fix_numbering on a correctly numbered plan should return identical output."""

    def test_round_trip_preserves_correctly_numbered_plan(self):
        result = fix_numbering(CORRECTLY_NUMBERED_PLAN)
        assert result == CORRECTLY_NUMBERED_PLAN


class TestFixNumberingMisnumbered:
    """fix_numbering should renumber threads and tasks sequentially."""

    def test_renumbers_thread_headings(self):
        result = fix_numbering(MISNUMBERED_PLAN)
        assert "## Steel Thread 1: First Thread" in result
        assert "## Steel Thread 2: Second Thread" in result
        assert "## Steel Thread 5:" not in result
        assert "## Steel Thread 9:" not in result

    def test_renumbers_task_references(self):
        result = fix_numbering(MISNUMBERED_PLAN)
        assert "**Task 1.1: First task**" in result
        assert "**Task 1.2: Second task**" in result
        assert "**Task 2.1: Third task**" in result
        assert "**Task 5.3:" not in result
        assert "**Task 5.7:" not in result
        assert "**Task 9.1:" not in result

    def test_preserves_non_numbered_content(self):
        result = fix_numbering(MISNUMBERED_PLAN)
        assert "# Implementation Plan: Test Plan" in result
        assert "## Idea Type" in result
        assert "## Overview" in result
        assert "## Summary" in result
        assert "Introduction to first thread." in result
        assert "Introduction to second thread." in result

    def test_preserves_task_metadata(self):
        result = fix_numbering(MISNUMBERED_PLAN)
        assert "TaskType: INFRA" in result
        assert "Entrypoint: `echo hello`" in result
        assert "Observable: Something happens" in result
        assert "Evidence: `echo done`" in result

    def test_preserves_steps(self):
        result = fix_numbering(MISNUMBERED_PLAN)
        assert "    - [ ] Step one" in result
        assert "    - [ ] Step two" in result

    def test_misnumbered_produces_correct_output(self):
        """After fix_numbering, the output should match the correctly numbered plan."""
        result = fix_numbering(MISNUMBERED_PLAN)
        assert result == CORRECTLY_NUMBERED_PLAN


class TestFixNumberingCompletedTasks:
    """fix_numbering should handle completed tasks correctly."""

    PLAN_WITH_COMPLETED = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 3: Only Thread
Intro.

- [x] **Task 3.5: Done task**
  - TaskType: INFRA
  - Entrypoint: `echo hello`
  - Observable: Something
  - Evidence: `echo done`
  - Steps:
    - [x] Step one

- [ ] **Task 3.8: Pending task**
  - TaskType: OUTCOME
  - Entrypoint: `echo hello2`
  - Observable: Something else
  - Evidence: `echo done2`
  - Steps:
    - [ ] Step one

---

## Summary
Done.
"""

    def test_renumbers_completed_tasks(self):
        result = fix_numbering(self.PLAN_WITH_COMPLETED)
        assert "## Steel Thread 1: Only Thread" in result
        assert "- [x] **Task 1.1: Done task**" in result
        assert "- [ ] **Task 1.2: Pending task**" in result

    def test_preserves_completion_status(self):
        result = fix_numbering(self.PLAN_WITH_COMPLETED)
        assert "- [x] **Task 1.1: Done task**" in result
        assert "- [ ] **Task 1.2: Pending task**" in result
        assert "    - [x] Step one" in result


class TestFixNumberingSingleThread:
    """fix_numbering with a single thread."""

    SINGLE_THREAD = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
Overview.

---

## Steel Thread 7: Sole Thread
Intro.

- [ ] **Task 7.1: Only task**
  - TaskType: INFRA
  - Entrypoint: `echo hi`
  - Observable: Works
  - Evidence: `echo ok`
  - Steps:
    - [ ] Do it

---

## Summary
One thread.
"""

    def test_renumbers_single_thread(self):
        result = fix_numbering(self.SINGLE_THREAD)
        assert "## Steel Thread 1: Sole Thread" in result
        assert "**Task 1.1: Only task**" in result
