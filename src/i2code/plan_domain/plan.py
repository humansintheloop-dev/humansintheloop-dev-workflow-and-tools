"""Plan aggregate root — owns preamble/postamble lines, contains Threads."""

from dataclasses import dataclass, field

from i2code.plan_domain.numbered_task import NumberedTask
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

    def to_text(self) -> str:
        lines = list(self._preamble_lines)
        for thread_num, thread in enumerate(self.threads, 1):
            lines.extend(thread.to_lines(thread_num))
        lines.extend(self._postamble_lines)
        return '\n'.join(lines)
