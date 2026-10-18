"""Unit tests for Plan.incomplete_threads_before()."""

from i2code.plan_domain.plan import Plan
from i2code.plan_domain.task import Task
from i2code.plan_domain.thread import Thread


def _thread(number, *tasks):
    return Thread(_header_lines=[f'## Steel Thread {number}: Work'], tasks=list(tasks))


def _task(thread, task, completed):
    checkbox = '[x]' if completed else '[ ]'
    return Task(_lines=[f'- {checkbox} **Task {thread}.{task}: Task {thread}.{task}**'])


class TestPlanIncompleteThreadsBefore:

    def test_returns_earlier_threads_with_an_incomplete_task_in_ascending_order(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(1, _task(1, 1, completed=False)),
            _thread(2, _task(2, 1, completed=True), _task(2, 2, completed=False)),
            _thread(3, _task(3, 1, completed=False)),
        ])

        assert plan.incomplete_threads_before(3) == [1, 2]

    def test_omits_complete_earlier_threads(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(1, _task(1, 1, completed=True)),
            _thread(2, _task(2, 1, completed=False)),
            _thread(3, _task(3, 1, completed=False)),
        ])

        assert plan.incomplete_threads_before(3) == [2]

    def test_returns_empty_list_for_thread_1(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(1, _task(1, 1, completed=False)),
            _thread(2, _task(2, 1, completed=False)),
        ])

        assert plan.incomplete_threads_before(1) == []
