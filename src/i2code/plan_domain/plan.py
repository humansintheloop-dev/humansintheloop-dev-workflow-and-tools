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

    def get_thread(self, thread: int) -> Thread:
        if thread < 1 or thread > len(self.threads):
            raise ValueError(f"thread {thread} does not exist")
        return self.threads[thread - 1]

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
        self.get_thread(thread).mark_task_complete(task)

    def mark_task_incomplete(self, thread: int, task: int) -> None:
        self.get_thread(thread).mark_task_incomplete(task)

    def insert_task_before(self, thread: int, before_task: int, task: Task) -> None:
        self.get_thread(thread).insert_task_before(before_task, task)

    def insert_task_after(self, thread: int, after_task: int, task: Task) -> None:
        self.get_thread(thread).insert_task_after(after_task, task)

    def replace_task(self, thread: int, task: int, new_task: Task) -> None:
        self.get_thread(thread).replace_task(task, new_task)

    def insert_thread_before(self, before_thread: int, thread: Thread) -> None:
        self.get_thread(before_thread)
        self.threads.insert(before_thread - 1, thread)

    def insert_thread_after(self, after_thread: int, thread: Thread) -> None:
        self.get_thread(after_thread)
        self.threads.insert(after_thread, thread)

    def replace_thread(self, thread: int, new_thread: Thread) -> None:
        self.get_thread(thread)
        self.threads[thread - 1] = new_thread

    def delete_thread(self, thread: int) -> None:
        self.get_thread(thread)
        del self.threads[thread - 1]

    def delete_task(self, thread: int, task: int) -> None:
        self.get_thread(thread).delete_task(task)

    def move_task_before(self, thread: int, task: int, before_task: int) -> None:
        self.get_thread(thread).move_task_before(task, before_task)

    def move_task_after(self, thread: int, task: int, after_task: int) -> None:
        self.get_thread(thread).move_task_after(task, after_task)

    def reorder_threads(self, thread_order: list[int]) -> None:
        if len(thread_order) != len(set(thread_order)):
            raise ValueError("reorder-threads: --order contains duplicate thread numbers")

        existing_set = set(range(1, len(self.threads) + 1))
        order_set = set(thread_order)
        if order_set != existing_set:
            missing = existing_set - order_set
            extra = order_set - existing_set
            parts = []
            if missing:
                parts.append(f"missing threads: {sorted(missing)}")
            if extra:
                parts.append(f"nonexistent threads: {sorted(extra)}")
            raise ValueError(f"reorder-threads: --order does not match existing threads ({', '.join(parts)})")

        self.threads = [self.threads[i - 1] for i in thread_order]

    def reorder_tasks(self, thread: int, task_order: list[int]) -> None:
        self.get_thread(thread).reorder_tasks(task_order)

    def mark_step_complete(self, thread: int, task: int, step: int) -> None:
        self.get_thread(thread).mark_step_complete(task, step)

    def mark_step_incomplete(self, thread: int, task: int, step: int) -> None:
        self.get_thread(thread).mark_step_incomplete(task, step)

    def to_text(self) -> str:
        lines = list(self._preamble_lines)
        for thread_num, thread in enumerate(self.threads, 1):
            lines.extend(thread.to_lines(thread_num))
        lines.extend(self._postamble_lines)
        return '\n'.join(lines)
