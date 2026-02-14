"""Thread entity — owns its header lines, contains Tasks."""

from dataclasses import dataclass, field
import re

from i2code.plan_domain.task import Task


@dataclass
class Thread:
    _header_lines: list[str]
    tasks: list[Task] = field(default_factory=list)

    def insert_task(self, index: int, task: Task) -> None:
        self.tasks.insert(index, task)

    def delete_task(self, task_number: int) -> None:
        if task_number < 1 or task_number > len(self.tasks):
            raise ValueError(f"task {task_number} does not exist")
        del self.tasks[task_number - 1]

    def to_lines(self, thread_number: int) -> list[str]:
        lines = list(self._header_lines)
        lines[0] = re.sub(r'Steel Thread \d+:', f'Steel Thread {thread_number}:', lines[0])
        for task_num, task in enumerate(self.tasks, 1):
            lines.extend(task.to_lines(thread_number, task_num))
        return lines
