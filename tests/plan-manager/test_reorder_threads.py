"""Tests for reorder_threads pure function."""

from i2code.plan.threads import reorder_threads


TWO_THREAD_PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Introduction to first thread.

- [ ] **Task 1.1: Alpha task**
  - TaskType: INFRA
  - Entrypoint: `echo alpha`
  - Observable: Alpha happens
  - Evidence: `echo alpha-done`
  - Steps:
    - [ ] Alpha step one
    - [ ] Alpha step two

---

## Steel Thread 2: Second Thread
Introduction to second thread.

- [ ] **Task 2.1: Beta task**
  - TaskType: OUTCOME
  - Entrypoint: `echo beta`
  - Observable: Beta happens
  - Evidence: `echo beta-done`
  - Steps:
    - [ ] Beta step one

---

## Summary
This plan has 2 threads.
"""


THREE_THREAD_PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: First Thread
Intro first.

- [ ] **Task 1.1: Task A**
  - TaskType: INFRA
  - Entrypoint: `echo a`
  - Observable: A
  - Evidence: `echo a`
  - Steps:
    - [ ] Step A

---

## Steel Thread 2: Second Thread
Intro second.

- [ ] **Task 2.1: Task B**
  - TaskType: OUTCOME
  - Entrypoint: `echo b`
  - Observable: B
  - Evidence: `echo b`
  - Steps:
    - [ ] Step B

- [ ] **Task 2.2: Task C**
  - TaskType: OUTCOME
  - Entrypoint: `echo c`
  - Observable: C
  - Evidence: `echo c`
  - Steps:
    - [ ] Step C

---

## Steel Thread 3: Third Thread
Intro third.

- [ ] **Task 3.1: Task D**
  - TaskType: INFRA
  - Entrypoint: `echo d`
  - Observable: D
  - Evidence: `echo d`
  - Steps:
    - [ ] Step D

---

## Summary
This plan has 3 threads.
"""


class TestReorderThreads:
    """reorder_threads rearranges threads and renumbers correctly."""

    def test_swap_two_threads(self):
        result = reorder_threads(TWO_THREAD_PLAN, [2, 1], "Swapped")
        # After swap: old thread 2 becomes thread 1, old thread 1 becomes thread 2
        assert "## Steel Thread 1: Second Thread" in result
        assert "## Steel Thread 2: First Thread" in result

    def test_renumbers_tasks_after_swap(self):
        result = reorder_threads(TWO_THREAD_PLAN, [2, 1], "Swapped")
        # Beta task was in thread 2, now in thread 1
        assert "**Task 1.1: Beta task**" in result
        # Alpha task was in thread 1, now in thread 2
        assert "**Task 2.1: Alpha task**" in result

    def test_preserves_thread_content_after_swap(self):
        result = reorder_threads(TWO_THREAD_PLAN, [2, 1], "Swapped")
        assert "Introduction to second thread." in result
        assert "Introduction to first thread." in result
        assert "Beta step one" in result
        assert "Alpha step one" in result
        assert "Alpha step two" in result

    def test_three_thread_reorder(self):
        result = reorder_threads(THREE_THREAD_PLAN, [3, 1, 2], "Reordered")
        assert "## Steel Thread 1: Third Thread" in result
        assert "## Steel Thread 2: First Thread" in result
        assert "## Steel Thread 3: Second Thread" in result

    def test_three_thread_renumbers_tasks(self):
        result = reorder_threads(THREE_THREAD_PLAN, [3, 1, 2], "Reordered")
        # Thread 3 (Task D) is now thread 1
        assert "**Task 1.1: Task D**" in result
        # Thread 1 (Task A) is now thread 2
        assert "**Task 2.1: Task A**" in result
        # Thread 2 (Tasks B, C) is now thread 3
        assert "**Task 3.1: Task B**" in result
        assert "**Task 3.2: Task C**" in result

    def test_identity_reorder(self):
        result = reorder_threads(TWO_THREAD_PLAN, [1, 2], "No change")
        # Should still have correct numbering
        assert "## Steel Thread 1: First Thread" in result
        assert "## Steel Thread 2: Second Thread" in result
        assert "**Task 1.1: Alpha task**" in result
        assert "**Task 2.1: Beta task**" in result

    def test_appends_change_history(self):
        result = reorder_threads(TWO_THREAD_PLAN, [2, 1], "Swapped for priority")
        assert "## Change History" in result
        assert "reorder-threads" in result
        assert "Swapped for priority" in result


class TestReorderThreadsErrors:
    """reorder_threads returns errors for invalid inputs."""

    def test_error_on_missing_thread(self):
        try:
            reorder_threads(TWO_THREAD_PLAN, [1], "Missing thread 2")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "order" in str(e).lower() or "thread" in str(e).lower()

    def test_error_on_duplicate_thread(self):
        try:
            reorder_threads(TWO_THREAD_PLAN, [1, 1], "Duplicate")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "duplicate" in str(e).lower() or "order" in str(e).lower()

    def test_error_on_nonexistent_thread_number(self):
        try:
            reorder_threads(TWO_THREAD_PLAN, [1, 3], "Thread 3 doesn't exist")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "thread" in str(e).lower() or "order" in str(e).lower()

    def test_error_on_extra_thread(self):
        try:
            reorder_threads(TWO_THREAD_PLAN, [1, 2, 3], "Too many")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "order" in str(e).lower() or "thread" in str(e).lower()
