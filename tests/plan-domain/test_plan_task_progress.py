"""Unit tests for Plan.task_progress()."""

from i2code.plan_domain.plan import Plan, TaskProgress
from i2code.plan_domain.task import Task
from i2code.plan_domain.thread import Thread


def _task(completed: bool) -> Task:
    marker = "x" if completed else " "
    return Task(_lines=[f'- [{marker}] **Task 1.1: something**'])


def _thread(*tasks: Task) -> Thread:
    return Thread(_header_lines=['## Steel Thread 1: Work'], tasks=list(tasks))


class TestPlanTaskProgress:

    def test_single_pending_task(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[_thread(_task(False))])
        assert plan.task_progress() == TaskProgress(current=1, total=1)

    def test_single_completed_task(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[_thread(_task(True))])
        assert plan.task_progress() == TaskProgress(current=2, total=1)

    def test_first_of_three_pending(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(_task(False), _task(False), _task(False)),
        ])
        assert plan.task_progress() == TaskProgress(current=1, total=3)

    def test_two_of_three_completed(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(_task(True), _task(True), _task(False)),
        ])
        assert plan.task_progress() == TaskProgress(current=3, total=3)

    def test_counts_across_multiple_threads(self):
        plan = Plan(_preamble_lines=['# Plan'], threads=[
            _thread(_task(True)),
            _thread(_task(False), _task(False)),
        ])
        assert plan.task_progress() == TaskProgress(current=2, total=3)

    def test_no_threads(self):
        plan = Plan(_preamble_lines=['# Plan'])
        assert plan.task_progress() == TaskProgress(current=1, total=0)
