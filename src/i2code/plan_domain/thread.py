"""Thread entity — owns its header lines, contains Tasks."""

from dataclasses import dataclass, field
import re

from i2code.plan_domain.task import Task


@dataclass
class Thread:
    _header_lines: list[str]
    tasks: list[Task] = field(default_factory=list)

    def get_task(self, task_number: int) -> Task:
        if task_number < 1 or task_number > len(self.tasks):
            raise ValueError(f"task {task_number} does not exist")
        return self.tasks[task_number - 1]

    def mark_task_complete(self, task_number: int) -> None:
        self.get_task(task_number).mark_complete()

    def mark_task_incomplete(self, task_number: int) -> None:
        self.get_task(task_number).mark_incomplete()

    def mark_step_complete(self, task_number: int, step: int) -> None:
        self.get_task(task_number).mark_step_complete(step)

    def mark_step_incomplete(self, task_number: int, step: int) -> None:
        self.get_task(task_number).mark_step_incomplete(step)

    def insert_task_before(self, before_task: int, task: Task) -> None:
        self.get_task(before_task)
        self.tasks.insert(before_task - 1, task)

    def insert_task_after(self, after_task: int, task: Task) -> None:
        self.get_task(after_task)
        self.tasks.insert(after_task, task)

    def insert_task(self, index: int, task: Task) -> None:
        self.tasks.insert(index, task)

    def replace_task(self, task_number: int, task: Task) -> None:
        self.get_task(task_number)
        self.tasks[task_number - 1] = task

    def delete_task(self, task_number: int) -> None:
        self.get_task(task_number)
        del self.tasks[task_number - 1]

    def move_task_before(self, task_number: int, before_task: int) -> None:
        if task_number == before_task:
            raise ValueError("move-task-before: cannot move task to before the same task")
        self.get_task(task_number)
        self.get_task(before_task)
        current_order = list(range(1, len(self.tasks) + 1))
        new_order = [n for n in current_order if n != task_number]
        insert_idx = new_order.index(before_task)
        new_order.insert(insert_idx, task_number)
        self.reorder_tasks(new_order)

    def move_task_after(self, task_number: int, after_task: int) -> None:
        if task_number == after_task:
            raise ValueError("move-task-after: cannot move task to after the same task")
        self.get_task(task_number)
        self.get_task(after_task)
        current_order = list(range(1, len(self.tasks) + 1))
        new_order = [n for n in current_order if n != task_number]
        insert_idx = new_order.index(after_task) + 1
        new_order.insert(insert_idx, task_number)
        self.reorder_tasks(new_order)

    def reorder_tasks(self, task_order: list[int]) -> None:
        if len(task_order) != len(set(task_order)):
            raise ValueError("reorder-tasks: --order contains duplicate task numbers")

        existing_set = set(range(1, len(self.tasks) + 1))
        order_set = set(task_order)
        if order_set != existing_set:
            missing = existing_set - order_set
            extra = order_set - existing_set
            parts = []
            if missing:
                parts.append(f"missing tasks: {sorted(missing)}")
            if extra:
                parts.append(f"nonexistent tasks: {sorted(extra)}")
            raise ValueError(f"reorder-tasks: --order does not match existing tasks ({', '.join(parts)})")

        self.tasks = [self.tasks[i - 1] for i in task_order]

    def to_lines(self, thread_number: int) -> list[str]:
        lines = list(self._header_lines)
        lines[0] = re.sub(r'Steel Thread \d+:', f'Steel Thread {thread_number}:', lines[0])
        for task_num, task in enumerate(self.tasks, 1):
            lines.extend(task.to_lines(thread_number, task_num))
        return lines
