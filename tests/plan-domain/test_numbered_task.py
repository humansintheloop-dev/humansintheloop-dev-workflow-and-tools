"""Unit tests for NumberedTask.print()."""

from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task


class TestNumberedTaskPrint:

    def test_formats_task_for_display(self):
        task = Task(_lines=[
            '- [ ] **Task 1.1: Do something**',
            '  - TaskType: OUTCOME',
            '  - Entrypoint: `echo go`',
            '  - Observable: It works',
            '  - Evidence: `echo ok`',
            '  - Steps:',
            '    - [ ] First step',
            '    - [x] Second step',
        ])
        numbered = NumberedTask(number=TaskNumber(thread=2, task=3), task=task)

        expected = (
            "Thread 2, Task 2.3: Do something\n"
            "  TaskType: OUTCOME\n"
            "  Entrypoint: echo go\n"
            "  Observable: It works\n"
            "  Evidence: echo ok\n"
            "  Steps:\n"
            "    1. [ ] First step\n"
            "    2. [x] Second step"
        )
        assert numbered.print() == expected
