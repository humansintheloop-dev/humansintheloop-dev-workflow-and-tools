"""Parser should strip trailing blank lines from each task's _lines."""

from i2code.plan_domain.parser import parse


PLAN_WITH_BLANK_LINES_BETWEEN_TASKS = """\
# Plan

---

## Steel Thread 1: Work

- [ ] **Task 1.1: First task**
  - TaskType: OUTCOME
  - Entrypoint: `echo first`
  - Observable: First works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do first thing

- [ ] **Task 1.2: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do second thing
"""


class TestParserStripsTrailingBlanks:

    def test_first_task_lines_do_not_end_with_blank(self):
        plan = parse(PLAN_WITH_BLANK_LINES_BETWEEN_TASKS)
        first_task = plan.threads[0].tasks[0]
        assert first_task._lines[-1] != '', (
            f"Task _lines should not end with blank line, got: {first_task._lines}"
        )

    def test_last_task_lines_do_not_end_with_blank(self):
        plan = parse(PLAN_WITH_BLANK_LINES_BETWEEN_TASKS)
        last_task = plan.threads[0].tasks[-1]
        assert last_task._lines[-1] != '', (
            f"Task _lines should not end with blank line, got: {last_task._lines}"
        )
