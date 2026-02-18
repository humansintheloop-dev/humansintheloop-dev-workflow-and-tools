"""CLI integration tests for fix-numbering command."""

from click.testing import CliRunner

from i2code.plan.plan_cli import fix_numbering_cmd


MISNUMBERED_PLAN = """\
# Implementation Plan: Test Plan

## Idea Type
**A. Feature** - A test feature

---

## Overview
This is a test plan.

---

## Steel Thread 5: First Thread
Introduction to first.

- [ ] **Task 5.3: Alpha task**
  - TaskType: INFRA
  - Entrypoint: `echo alpha`
  - Observable: Alpha happens
  - Evidence: `echo alpha-done`
  - Steps:
    - [ ] Alpha step one

## Steel Thread 9: Second Thread
Introduction to second.

- [ ] **Task 9.1: Beta task**
  - TaskType: OUTCOME
  - Entrypoint: `echo beta`
  - Observable: Beta happens
  - Evidence: `echo beta-done`
  - Steps:
    - [ ] Beta step one

---

## Summary
Done.
"""


class TestFixNumberingCli:
    """CLI integration: fix-numbering renumbers via domain model round-trip."""

    def test_renumbers_misnumbered_plan(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(MISNUMBERED_PLAN)

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(fix_numbering_cmd, [str(plan_file)])

        assert result.exit_code == 0
        updated = plan_file.read_text()
        assert "Steel Thread 1: First Thread" in updated
        assert "Steel Thread 2: Second Thread" in updated
        assert "Task 1.1: Alpha task" in updated
        assert "Task 2.1: Beta task" in updated

    def test_does_not_write_when_already_correct(self, tmp_path):
        """When numbering is already correct, file should not be rewritten."""
        correctly_numbered = MISNUMBERED_PLAN.replace(
            "Steel Thread 5", "Steel Thread 1"
        ).replace(
            "Steel Thread 9", "Steel Thread 2"
        ).replace(
            "Task 5.3", "Task 1.1"
        ).replace(
            "Task 9.1", "Task 2.1"
        )
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(correctly_numbered)
        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(fix_numbering_cmd, [str(plan_file)])

        assert result.exit_code == 0
