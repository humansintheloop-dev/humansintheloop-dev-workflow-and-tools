"""Unit tests for Plan.get_next_task_in_thread()."""

from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.plan import Plan
from i2code.plan_domain.task import Task
from i2code.plan_domain.thread import Thread


def _thread(number, *tasks):
    return Thread(_header_lines=[f'## Steel Thread {number}: Work'], tasks=list(tasks))


def _task(thread, task, completed):
    checkbox = '[x]' if completed else '[ ]'
    return Task(_lines=[f'- {checkbox} **Task {thread}.{task}: Task {thread}.{task}**'])


class TestPlanGetNextTaskInThread:

    def test_returns_first_incomplete_task_of_thread(self):
        done = _task(1, 1, completed=True)
        todo = _task(1, 2, completed=False)
        plan = Plan(_preamble_lines=['# Plan'], threads=[_thread(1, done, todo)])

        result = plan.get_next_task_in_thread(1)

        assert isinstance(result, NumberedTask)
        assert result.number == TaskNumber(thread=1, task=2)
        assert result.task is todo

    def test_returns_none_when_thread_has_no_incomplete_task(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(1, _task(1, 1, completed=True)),
            _thread(2, _task(2, 1, completed=False)),
        ])

        assert plan.get_next_task_in_thread(1) is None

    def test_skips_incomplete_tasks_in_earlier_and_later_threads(self):
        selected = _task(2, 1, completed=False)
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(1, _task(1, 1, completed=False)),
            _thread(2, selected),
            _thread(3, _task(3, 1, completed=False)),
        ])

        result = plan.get_next_task_in_thread(2)

        assert result.number == TaskNumber(thread=2, task=1)
        assert result.task is selected
