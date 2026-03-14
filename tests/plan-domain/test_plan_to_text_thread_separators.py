"""Tests for --- separators between threads in Plan.to_text() output."""

from i2code.plan_domain.parser import parse
from i2code.plan_domain.thread import Thread


TWO_THREAD_PLAN = """\
# Implementation Plan: Test

---

## Steel Thread 1: First
Intro one.

- [ ] **Task 1.1: Task A**
  - TaskType: INFRA
  - Entrypoint: `echo a`
  - Observable: A
  - Evidence: `echo a-done`
  - Steps:
    - [ ] Do A

---

## Steel Thread 2: Second
Intro two.

- [ ] **Task 2.1: Task B**
  - TaskType: OUTCOME
  - Entrypoint: `echo b`
  - Observable: B
  - Evidence: `echo b-done`
  - Steps:
    - [ ] Do B
"""


def _new_thread(title="New Thread", intro="New intro."):
    return Thread.create(title, intro, [
        {"title": "New Task", "task_type": "INFRA", "entrypoint": "echo new",
         "observable": "New", "evidence": "echo new-done", "steps": ["Do new"]},
    ])


def _separator_positions(text):
    """Return line indices where '---' appears, excluding preamble separators."""
    lines = text.split('\n')
    return [i for i, line in enumerate(lines) if line.strip() == '---']


def _thread_heading_positions(text):
    """Return line indices of Steel Thread headings."""
    lines = text.split('\n')
    return [i for i, line in enumerate(lines) if line.startswith('## Steel Thread')]


def _assert_separators_between_all_threads(text, expected_thread_count):
    """Assert that --- separators appear between every consecutive pair of threads."""
    headings = _thread_heading_positions(text)
    assert len(headings) == expected_thread_count, (
        f"Expected {expected_thread_count} thread headings, got {len(headings)}"
    )
    lines = text.split('\n')
    for i in range(len(headings) - 1):
        between = lines[headings[i]:headings[i + 1]]
        assert '---' in between, (
            f"No --- separator between thread at line {headings[i]} "
            f"and thread at line {headings[i + 1]}"
        )


class TestPlanToTextThreadSeparators:
    """Plan.to_text() emits --- separators between consecutive threads."""

    def test_insert_thread_before_has_separators_between_all_threads(self):
        plan = parse(TWO_THREAD_PLAN)
        plan.insert_thread_before(1, _new_thread())
        _assert_separators_between_all_threads(plan.to_text(), 3)

    def test_insert_thread_after_has_separators_between_all_threads(self):
        plan = parse(TWO_THREAD_PLAN)
        plan.insert_thread_after(2, _new_thread())
        _assert_separators_between_all_threads(plan.to_text(), 3)

    def test_replace_thread_has_separators_between_all_threads(self):
        plan = parse(TWO_THREAD_PLAN)
        plan.replace_thread(1, _new_thread("Replaced", "Replaced intro."))
        _assert_separators_between_all_threads(plan.to_text(), 2)

    def test_round_trip_two_thread_plan(self):
        plan = parse(TWO_THREAD_PLAN)
        result = plan.to_text()
        assert result == TWO_THREAD_PLAN


PLAN_WITH_POSTAMBLE = """\
# Implementation Plan: Test

---

## Steel Thread 1: First
Intro one.

- [ ] **Task 1.1: Task A**
  - TaskType: INFRA
  - Entrypoint: `echo a`
  - Observable: A
  - Evidence: `echo a-done`
  - Steps:
    - [ ] Do A

---

## Change History
- Changed something
"""


class TestPlanToTextPostambleSeparator:
    """Plan.to_text() emits --- separator between last thread and postamble."""

    def test_separator_between_last_thread_and_postamble(self):
        plan = parse(PLAN_WITH_POSTAMBLE)
        result = plan.to_text()
        assert '\n---\n' in result.split('## Steel Thread 1')[1].split('## Change History')[0], (
            "Expected --- separator between last thread and postamble"
        )

    def test_round_trip_plan_with_postamble(self):
        plan = parse(PLAN_WITH_POSTAMBLE)
        result = plan.to_text()
        assert result == PLAN_WITH_POSTAMBLE
