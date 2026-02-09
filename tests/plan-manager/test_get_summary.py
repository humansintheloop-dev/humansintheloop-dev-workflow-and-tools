"""Tests for get_summary pure function."""

from i2code.plan.plans import get_summary


PLAN_WITH_MIXED_TASKS = """\
# Implementation Plan: Test Project

## Idea Type
**B. Enhancement** - Improving an existing feature

---

## Overview
This plan covers the test project implementation with multiple threads.

---

## Steel Thread 1: First Thread
Introduction.

- [x] **Task 1.1: Done task**
  - TaskType: INFRA
  - Entrypoint: `echo done`
  - Observable: Done
  - Evidence: `echo done`
  - Steps:
    - [x] Already done

- [ ] **Task 1.2: Pending task**
  - TaskType: OUTCOME
  - Entrypoint: `echo pending`
  - Observable: Pending
  - Evidence: `echo pending`
  - Steps:
    - [ ] Not done yet

---

## Steel Thread 2: Second Thread
Intro.

- [x] **Task 2.1: Also done**
  - TaskType: OUTCOME
  - Entrypoint: `echo also-done`
  - Observable: Also done
  - Evidence: `echo also-done`
  - Steps:
    - [x] Done

- [ ] **Task 2.2: Not done**
  - TaskType: OUTCOME
  - Entrypoint: `echo not-done`
  - Observable: Not done
  - Evidence: `echo not-done`
  - Steps:
    - [ ] Pending

---

## Summary
A test summary.
"""


class TestGetSummary:
    """get_summary returns plan metadata and progress."""

    def test_returns_plan_name(self):
        result = get_summary(PLAN_WITH_MIXED_TASKS)
        assert result['plan_name'] == 'Test Project'

    def test_returns_idea_type(self):
        result = get_summary(PLAN_WITH_MIXED_TASKS)
        assert '**B. Enhancement**' in result['idea_type']
        assert 'Improving an existing feature' in result['idea_type']

    def test_returns_overview(self):
        result = get_summary(PLAN_WITH_MIXED_TASKS)
        assert 'test project implementation' in result['overview']

    def test_returns_total_threads(self):
        result = get_summary(PLAN_WITH_MIXED_TASKS)
        assert result['total_threads'] == 2

    def test_returns_total_tasks(self):
        result = get_summary(PLAN_WITH_MIXED_TASKS)
        assert result['total_tasks'] == 4

    def test_returns_completed_tasks(self):
        result = get_summary(PLAN_WITH_MIXED_TASKS)
        assert result['completed_tasks'] == 2
