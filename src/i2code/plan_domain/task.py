"""Task entity — owns its raw markdown lines."""

from dataclasses import dataclass
import re


@dataclass
class Task:
    _lines: list[str]

    def to_lines(self, thread_num: int, task_num: int) -> list[str]:
        lines = list(self._lines)
        lines[0] = re.sub(r'Task \d+\.\d+:', f'Task {thread_num}.{task_num}:', lines[0])
        return lines
