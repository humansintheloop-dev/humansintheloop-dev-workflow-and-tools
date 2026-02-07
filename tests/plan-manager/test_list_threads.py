"""Tests for list_threads pure function."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'skills', 'plan-file-management', 'scripts'))

from importlib import import_module
_mod = import_module('plan-manager')
list_threads = _mod.list_threads


PLAN_WITH_THREE_THREADS = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 1: Setup Infrastructure
Introduction.

- [x] **Task 1.1: Create project**
  - TaskType: INFRA
  - Entrypoint: `echo setup`
  - Observable: Project created
  - Evidence: `echo done`
  - Steps:
    - [x] Init project

- [x] **Task 1.2: Add CI**
  - TaskType: INFRA
  - Entrypoint: `echo ci`
  - Observable: CI works
  - Evidence: `echo ci-done`
  - Steps:
    - [x] Add workflow

---

## Steel Thread 2: Core Feature
Introduction to core.

- [x] **Task 2.1: Implement parser**
  - TaskType: OUTCOME
  - Entrypoint: `echo parse`
  - Observable: Parser works
  - Evidence: `echo parsed`
  - Steps:
    - [x] Write parser

- [ ] **Task 2.2: Implement formatter**
  - TaskType: OUTCOME
  - Entrypoint: `echo format`
  - Observable: Formatter works
  - Evidence: `echo formatted`
  - Steps:
    - [ ] Write formatter

- [ ] **Task 2.3: Integration test**
  - TaskType: OUTCOME
  - Entrypoint: `echo test`
  - Observable: Tests pass
  - Evidence: `echo tested`
  - Steps:
    - [ ] Write integration test

---

## Steel Thread 3: Documentation
Docs thread.

- [ ] **Task 3.1: Write docs**
  - TaskType: OUTCOME
  - Entrypoint: `echo docs`
  - Observable: Docs exist
  - Evidence: `echo docs-done`
  - Steps:
    - [ ] Write README

---

## Summary
Done.
"""


class TestListThreads:
    """list_threads returns all threads with completion status."""

    def test_returns_all_threads(self):
        result = list_threads(PLAN_WITH_THREE_THREADS)
        assert len(result) == 3

    def test_returns_thread_numbers(self):
        result = list_threads(PLAN_WITH_THREE_THREADS)
        assert result[0]['number'] == 1
        assert result[1]['number'] == 2
        assert result[2]['number'] == 3

    def test_returns_thread_titles(self):
        result = list_threads(PLAN_WITH_THREE_THREADS)
        assert result[0]['title'] == 'Setup Infrastructure'
        assert result[1]['title'] == 'Core Feature'
        assert result[2]['title'] == 'Documentation'

    def test_returns_total_tasks(self):
        result = list_threads(PLAN_WITH_THREE_THREADS)
        assert result[0]['total_tasks'] == 2
        assert result[1]['total_tasks'] == 3
        assert result[2]['total_tasks'] == 1

    def test_returns_completed_tasks(self):
        result = list_threads(PLAN_WITH_THREE_THREADS)
        assert result[0]['completed_tasks'] == 2
        assert result[1]['completed_tasks'] == 1
        assert result[2]['completed_tasks'] == 0
