"""Tests for go_cmd.plan_validator — validate required fields in plan task blocks."""

import pytest

from i2code.go_cmd.plan_validator import validate_plan


VALID_PLAN = """\
# Implementation Plan

## Steel Thread 1: Feature

- [ ] **Task 1.1: Do something useful**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/ -v`
  - Observable: Something observable happens
  - Evidence: Tests pass
  - Steps:
    - [ ] Step one
    - [ ] Step two

- [ ] **Task 1.2: Do another thing**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: Infrastructure is set up
  - Evidence: CI passes
  - Steps:
    - [ ] Step one
"""


@pytest.mark.unit
class TestValidPlanPasses:

    def test_valid_plan_returns_true(self):
        is_valid, errors = validate_plan(VALID_PLAN)

        assert is_valid is True

    def test_valid_plan_returns_no_errors(self):
        is_valid, errors = validate_plan(VALID_PLAN)

        assert errors == []


@pytest.mark.unit
class TestMissingTaskTypeFails:

    PLAN_MISSING_TASK_TYPE = """\
## Steel Thread 1: Feature

- [ ] **Task 1.1: Missing TaskType**
  - Entrypoint: `command`
  - Observable: Something
  - Evidence: Something
"""

    def test_returns_false(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_TASK_TYPE)

        assert is_valid is False

    def test_error_mentions_task_type(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_TASK_TYPE)

        assert any("TaskType" in e for e in errors)

    def test_error_mentions_task_identifier(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_TASK_TYPE)

        assert any("Task 1.1" in e for e in errors)


@pytest.mark.unit
class TestMissingEvidenceFails:

    PLAN_MISSING_EVIDENCE = """\
## Steel Thread 2: Feature

- [ ] **Task 2.1: Missing Evidence**
  - TaskType: OUTCOME
  - Entrypoint: `command`
  - Observable: Something
"""

    def test_returns_false(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_EVIDENCE)

        assert is_valid is False

    def test_error_mentions_evidence(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_EVIDENCE)

        assert any("Evidence" in e for e in errors)


@pytest.mark.unit
class TestMultipleErrorsReportsAll:

    PLAN_MULTIPLE_MISSING = """\
## Steel Thread 1: Feature

- [ ] **Task 1.1: Missing two fields**
  - TaskType: OUTCOME
  - Observable: Something

- [ ] **Task 1.2: Missing all fields**
"""

    def test_returns_false(self):
        is_valid, errors = validate_plan(self.PLAN_MULTIPLE_MISSING)

        assert is_valid is False

    def test_reports_all_errors(self):
        is_valid, errors = validate_plan(self.PLAN_MULTIPLE_MISSING)

        # Task 1.1 is missing Entrypoint, Evidence, and steps
        # Task 1.2 is missing all four fields and steps
        assert len(errors) == 8

    def test_reports_errors_for_both_tasks(self):
        is_valid, errors = validate_plan(self.PLAN_MULTIPLE_MISSING)

        errors_text = "\n".join(errors)
        assert "Task 1.1" in errors_text
        assert "Task 1.2" in errors_text


@pytest.mark.unit
class TestPlanWithNoThreadsFails:

    def test_empty_string_is_invalid(self):
        is_valid, errors = validate_plan("")

        assert is_valid is False

    def test_empty_string_reports_no_threads_error(self):
        is_valid, errors = validate_plan("")

        assert any("at least one thread" in e for e in errors)

    def test_plan_with_no_threads_is_invalid(self):
        plan = "# Plan\n\nSome text but no threads.\n"

        is_valid, errors = validate_plan(plan)

        assert is_valid is False


@pytest.mark.unit
class TestThreadWithNoTasksFails:

    PLAN_EMPTY_THREAD = """\
## Steel Thread 1: Feature

## Steel Thread 2: Another Feature

- [ ] **Task 2.1: Some task**
  - TaskType: OUTCOME
  - Entrypoint: `command`
  - Observable: Something
  - Evidence: Something
  - Steps:
    - [ ] Step one
"""

    def test_returns_false(self):
        is_valid, errors = validate_plan(self.PLAN_EMPTY_THREAD)

        assert is_valid is False

    def test_error_mentions_thread_number(self):
        is_valid, errors = validate_plan(self.PLAN_EMPTY_THREAD)

        assert any("Thread 1" in e for e in errors)

    def test_error_mentions_at_least_one_task(self):
        is_valid, errors = validate_plan(self.PLAN_EMPTY_THREAD)

        assert any("at least one task" in e for e in errors)


@pytest.mark.unit
class TestTaskWithNoStepsFails:

    PLAN_NO_STEPS = """\
## Steel Thread 1: Feature

- [ ] **Task 1.1: Missing steps**
  - TaskType: OUTCOME
  - Entrypoint: `command`
  - Observable: Something
  - Evidence: Something
"""

    def test_returns_false(self):
        is_valid, errors = validate_plan(self.PLAN_NO_STEPS)

        assert is_valid is False

    def test_error_mentions_task(self):
        is_valid, errors = validate_plan(self.PLAN_NO_STEPS)

        assert any("Task 1.1" in e for e in errors)

    def test_error_mentions_at_least_one_step(self):
        is_valid, errors = validate_plan(self.PLAN_NO_STEPS)

        assert any("at least one step" in e for e in errors)


@pytest.mark.unit
class TestCompletedTasksStillValidated:

    PLAN_COMPLETED_MISSING_FIELDS = """\
## Steel Thread 1: Feature

- [x] **Task 1.1: Completed but missing fields**
  - TaskType: OUTCOME
  - Observable: Something
  - Steps:
    - [x] Step one
"""

    PLAN_COMPLETED_VALID = """\
## Steel Thread 1: Feature

- [x] **Task 1.1: Completed and valid**
  - TaskType: OUTCOME
  - Entrypoint: `command`
  - Observable: Something
  - Evidence: Tests pass
  - Steps:
    - [x] Step one
"""

    def test_completed_task_with_missing_fields_fails(self):
        is_valid, errors = validate_plan(self.PLAN_COMPLETED_MISSING_FIELDS)

        assert is_valid is False

    def test_completed_task_with_all_fields_passes(self):
        is_valid, errors = validate_plan(self.PLAN_COMPLETED_VALID)

        assert is_valid is True


@pytest.mark.unit
class TestMissingEntrypointFails:

    PLAN_MISSING_ENTRYPOINT = """\
## Steel Thread 3: Feature

- [ ] **Task 3.1: Missing Entrypoint**
  - TaskType: OUTCOME
  - Observable: Something
  - Evidence: Something
"""

    def test_returns_false(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_ENTRYPOINT)

        assert is_valid is False

    def test_error_mentions_entrypoint(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_ENTRYPOINT)

        assert any("Entrypoint" in e for e in errors)


@pytest.mark.unit
class TestMissingObservableFails:

    PLAN_MISSING_OBSERVABLE = """\
## Steel Thread 3: Feature

- [ ] **Task 3.2: Missing Observable**
  - TaskType: OUTCOME
  - Entrypoint: `command`
  - Evidence: Something
"""

    def test_returns_false(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_OBSERVABLE)

        assert is_valid is False

    def test_error_mentions_observable(self):
        is_valid, errors = validate_plan(self.PLAN_MISSING_OBSERVABLE)

        assert any("Observable" in e for e in errors)
