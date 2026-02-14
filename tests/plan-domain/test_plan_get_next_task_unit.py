"""Unit tests for Plan.get_next_task()."""

from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.plan import Plan
from i2code.plan_domain.task import Task
from i2code.plan_domain.thread import Thread


class TestPlanGetNextTask:

    def test_returns_none_when_no_threads(self):
        plan = Plan(_preamble_lines=['# Plan'])
        assert plan.get_next_task() is None

    def test_returns_first_incomplete_task(self):
        task = Task(_lines=['- [ ] **Task 1.1: Do something**'])
        thread = Thread(_header_lines=['## Steel Thread 1: Work'], tasks=[task])
        plan = Plan(_preamble_lines=['# Plan'], threads=[thread])

        result = plan.get_next_task()

        assert isinstance(result, NumberedTask)
        assert result.number == TaskNumber(thread=1, task=1)
        assert result.task is task

    def test_skips_completed_tasks(self):
        done = Task(_lines=['- [x] **Task 1.1: Done**'])
        todo = Task(_lines=['- [ ] **Task 1.2: Todo**'])
        thread = Thread(_header_lines=['## Steel Thread 1: Work'], tasks=[done, todo])
        plan = Plan(_preamble_lines=['# Plan'], threads=[thread])

        result = plan.get_next_task()

        assert result.number == TaskNumber(thread=1, task=2)
        assert result.task is todo

    def test_returns_none_when_all_complete(self):
        done = Task(_lines=['- [x] **Task 1.1: Done**'])
        thread = Thread(_header_lines=['## Steel Thread 1: Work'], tasks=[done])
        plan = Plan(_preamble_lines=['# Plan'], threads=[thread])

        assert plan.get_next_task() is None
