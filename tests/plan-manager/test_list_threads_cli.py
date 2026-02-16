"""CLI integration tests for list-threads command."""

from click.testing import CliRunner

from i2code.plan.plan_cli import list_threads_cmd


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


class TestListThreadsCli:
    """CLI integration: list-threads outputs thread info via domain model."""

    def test_lists_all_threads_with_completion_status(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_THREE_THREADS)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(list_threads_cmd, [str(plan_file)])

        assert result.exit_code == 0
        assert "Thread 1: Setup Infrastructure (2/2 tasks completed)" in result.output
        assert "Thread 2: Core Feature (1/3 tasks completed)" in result.output
        assert "Thread 3: Documentation (0/1 tasks completed)" in result.output
