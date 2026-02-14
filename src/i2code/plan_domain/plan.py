"""Plan aggregate root — owns preamble/postamble lines, contains Threads."""

from dataclasses import dataclass, field

from i2code.plan_domain.numbered_task import NumberedTask
from i2code.plan_domain.task import Task
from i2code.plan_domain.thread import Thread


@dataclass
class Plan:
    _preamble_lines: list[str]
    threads: list[Thread] = field(default_factory=list)
    _postamble_lines: list[str] = field(default_factory=list)

    def get_next_task(self) -> NumberedTask | None:
        from i2code.plan_domain.numbered_task import TaskNumber
        for thread_num, thread in enumerate(self.threads, 1):
            for task_num, task in enumerate(thread.tasks, 1):
                if not task.is_completed:
                    return NumberedTask(
                        number=TaskNumber(thread=thread_num, task=task_num),
                        task=task,
                    )
        return None

    def mark_task_complete(self, thread: int, task: int) -> None:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"mark-task-complete: thread {thread} does not exist")
        t = self.threads[thread - 1]
        if task < 1 or task > len(t.tasks):
            raise ValueError(f"mark-task-complete: task {thread}.{task} does not exist")
        t.tasks[task - 1].mark_complete()

    def mark_task_incomplete(self, thread: int, task: int) -> None:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"mark-task-incomplete: thread {thread} does not exist")
        t = self.threads[thread - 1]
        if task < 1 or task > len(t.tasks):
            raise ValueError(f"mark-task-incomplete: task {thread}.{task} does not exist")
        t.tasks[task - 1].mark_incomplete()

    def insert_task_before(self, thread: int, before_task: int, task: Task) -> None:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"insert-task-before: thread {thread} does not exist")
        t = self.threads[thread - 1]
        if before_task < 1 or before_task > len(t.tasks):
            raise ValueError(f"insert-task-before: task {thread}.{before_task} does not exist")
        t.insert_task(before_task - 1, task)

    def insert_task_after(self, thread: int, after_task: int, task: Task) -> None:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"insert-task-after: thread {thread} does not exist")
        t = self.threads[thread - 1]
        if after_task < 1 or after_task > len(t.tasks):
            raise ValueError(f"insert-task-after: task {thread}.{after_task} does not exist")
        t.insert_task(after_task, task)

    def delete_task(self, thread: int, task: int) -> None:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"delete-task: thread {thread} does not exist")
        t = self.threads[thread - 1]
        if task < 1 or task > len(t.tasks):
            raise ValueError(f"delete-task: task {thread}.{task} does not exist")
        t.delete_task(task)

    def mark_step_complete(self, thread: int, task: int, step: int) -> None:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"mark-step-complete: thread {thread} does not exist")
        t = self.threads[thread - 1]
        if task < 1 or task > len(t.tasks):
            raise ValueError(f"mark-step-complete: task {thread}.{task} does not exist")
        try:
            t.tasks[task - 1].mark_step_complete(step)
        except ValueError as e:
            raise ValueError(f"mark-step-complete: {e}") from e

    def mark_step_incomplete(self, thread: int, task: int, step: int) -> None:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"mark-step-incomplete: thread {thread} does not exist")
        t = self.threads[thread - 1]
        if task < 1 or task > len(t.tasks):
            raise ValueError(f"mark-step-incomplete: task {thread}.{task} does not exist")
        try:
            t.tasks[task - 1].mark_step_incomplete(step)
        except ValueError as e:
            raise ValueError(f"mark-step-incomplete: {e}") from e

    def to_text(self) -> str:
        lines = list(self._preamble_lines)
        for thread_num, thread in enumerate(self.threads, 1):
            lines.extend(thread.to_lines(thread_num))
        lines.extend(self._postamble_lines)
        return '\n'.join(lines)
