"""Parser should strip trailing '---' and blank lines from each thread's lines."""

from i2code.plan_domain.parser import parse


PLAN_WITH_TWO_THREADS = """\
# Plan

---

## Steel Thread 1: First thread

- [ ] **Task 1.1: First task**
  - TaskType: OUTCOME
  - Entrypoint: `echo first`
  - Observable: First works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do first thing

---

## Steel Thread 2: Second thread

- [ ] **Task 2.1: Second task**
  - TaskType: OUTCOME
  - Entrypoint: `echo second`
  - Observable: Second works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do second thing
"""


class TestParserStripsThreadSeparators:

    def test_first_thread_lines_do_not_end_with_separator(self):
        plan = parse(PLAN_WITH_TWO_THREADS)
        first_thread = plan.threads[0]
        all_lines = first_thread.to_lines(1)
        assert all_lines[-1].strip() != '---', (
            f"Thread lines should not end with '---', got: {all_lines}"
        )

    def test_first_thread_lines_do_not_end_with_blank(self):
        plan = parse(PLAN_WITH_TWO_THREADS)
        first_thread = plan.threads[0]
        all_lines = first_thread.to_lines(1)
        assert all_lines[-1] != '', (
            f"Thread lines should not end with blank line, got: {all_lines}"
        )

    def test_first_thread_last_task_lines_do_not_end_with_separator(self):
        plan = parse(PLAN_WITH_TWO_THREADS)
        last_task = plan.threads[0].tasks[-1]
        assert last_task._lines[-1].strip() != '---', (
            f"Last task _lines should not end with '---', got: {last_task._lines}"
        )

    def test_first_thread_last_task_lines_do_not_end_with_blank(self):
        plan = parse(PLAN_WITH_TWO_THREADS)
        last_task = plan.threads[0].tasks[-1]
        assert last_task._lines[-1] != '', (
            f"Last task _lines should not end with blank line, got: {last_task._lines}"
        )

    def test_first_thread_header_lines_do_not_end_with_separator(self):
        plan = parse(PLAN_WITH_TWO_THREADS)
        first_thread = plan.threads[0]
        assert first_thread._header_lines[-1].strip() != '---', (
            f"Header lines should not end with '---', got: {first_thread._header_lines}"
        )
