"""Tests for reorder-tasks: rearranges tasks within a thread and renumbers."""

from i2code.plan.tasks import reorder_tasks


PLAN_WITH_THREE_TASKS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
Test plan.

---

## Steel Thread 1: Setup
Intro to setup.

- [x] **Task 1.1: First task**
  - TaskType: INFRA
  - Entrypoint: `echo first`
  - Observable: First done
  - Evidence: `echo first`
  - Steps:
    - [x] Step A
    - [x] Step B

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second done
  - Evidence: `echo second`
  - Steps:
    - [ ] Step C
    - [ ] Step D

- [ ] **Task 1.3: Third task**
  - TaskType: OUTCOME
  - Entrypoint: `echo third`
  - Observable: Third done
  - Evidence: `echo third`
  - Steps:
    - [ ] Step E

---

## Summary
Done.
"""

TWO_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
Test plan.

---

## Steel Thread 1: Alpha
Alpha intro.

- [ ] **Task 1.1: A1**
  - TaskType: INFRA
  - Entrypoint: `echo a1`
  - Observable: A1
  - Evidence: `echo a1`
  - Steps:
    - [ ] Do A1

- [ ] **Task 1.2: A2**
  - TaskType: INFRA
  - Entrypoint: `echo a2`
  - Observable: A2
  - Evidence: `echo a2`
  - Steps:
    - [ ] Do A2

---

## Steel Thread 2: Beta
Beta intro.

- [ ] **Task 2.1: B1**
  - TaskType: OUTCOME
  - Entrypoint: `echo b1`
  - Observable: B1
  - Evidence: `echo b1`
  - Steps:
    - [ ] Do B1

---

## Summary
Done.
"""


class TestReorderTasks:
    """reorder_tasks rearranges tasks within a thread and renumbers."""

    def test_reverse_three_tasks(self):
        result = reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [3, 2, 1], "Reversed tasks")
        # After reorder: old task 3 is now 1.1, old task 2 is now 1.2, old task 1 is now 1.3
        assert '**Task 1.1: Third task**' in result
        assert '**Task 1.2: Second task**' in result
        assert '**Task 1.3: First task**' in result

    def test_move_last_to_first(self):
        result = reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [3, 1, 2], "Moved task 3 to front")
        assert '**Task 1.1: Third task**' in result
        assert '**Task 1.2: First task**' in result
        assert '**Task 1.3: Second task**' in result

    def test_preserves_task_content(self):
        result = reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [3, 2, 1], "Reversed")
        # Task 1.1 (originally Third task) should have its steps
        assert 'Step E' in result
        # Task 1.3 (originally First task) should be complete
        assert '- [x] **Task 1.3: First task**' in result
        assert '    - [x] Step A' in result
        assert '    - [x] Step B' in result

    def test_preserves_completion_status(self):
        result = reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [2, 3, 1], "Moved completed task to end")
        # First task (complete) is now 1.3
        assert '- [x] **Task 1.3: First task**' in result
        # Second task (incomplete) is now 1.1
        assert '- [ ] **Task 1.1: Second task**' in result

    def test_appends_change_history(self):
        result = reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [3, 2, 1], "Reversed for priority")
        assert '## Change History' in result
        assert 'reorder-tasks' in result
        assert 'Reversed for priority' in result

    def test_does_not_affect_other_threads(self):
        result = reorder_tasks(TWO_THREADS, 1, [2, 1], "Swapped in thread 1")
        # Thread 1 tasks are swapped
        assert '**Task 1.1: A2**' in result
        assert '**Task 1.2: A1**' in result
        # Thread 2 is unchanged
        assert '**Task 2.1: B1**' in result

    def test_error_nonexistent_thread(self):
        import pytest
        with pytest.raises(ValueError, match="reorder-tasks:.*does not exist"):
            reorder_tasks(PLAN_WITH_THREE_TASKS, 99, [1, 2, 3], "reason")

    def test_error_wrong_task_count(self):
        import pytest
        with pytest.raises(ValueError, match="reorder-tasks:"):
            reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [1, 2], "reason")

    def test_error_duplicate_task_numbers(self):
        import pytest
        with pytest.raises(ValueError, match="reorder-tasks:"):
            reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [1, 1, 2], "reason")

    def test_error_nonexistent_task_number(self):
        import pytest
        with pytest.raises(ValueError, match="reorder-tasks:"):
            reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [1, 2, 99], "reason")

    def test_identity_reorder_preserves_content(self):
        result = reorder_tasks(PLAN_WITH_THREE_TASKS, 1, [1, 2, 3], "No-op reorder")
        # Should still have change history, but content should be identical modulo that
        assert '**Task 1.1: First task**' in result
        assert '**Task 1.2: Second task**' in result
        assert '**Task 1.3: Third task**' in result
