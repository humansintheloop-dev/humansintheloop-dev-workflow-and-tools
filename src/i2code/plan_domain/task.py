"""Task entity — owns its raw markdown lines."""

from dataclasses import dataclass
import re


_TASK_HEADER_RE = re.compile(r'^- \[([ x])\] \*\*Task \d+\.\d+: (.+)\*\*$')
_STEP_RE = re.compile(r'^\s+- \[([ x])\] (.+)$')


@dataclass
class Task:
    _lines: list[str]

    @property
    def title(self) -> str:
        m = _TASK_HEADER_RE.match(self._lines[0])
        return m.group(2) if m else ''

    @property
    def is_completed(self) -> bool:
        m = _TASK_HEADER_RE.match(self._lines[0])
        return m is not None and m.group(1) == 'x'

    @property
    def task_type(self) -> str:
        return self._extract_metadata('TaskType')

    @property
    def entrypoint(self) -> str:
        return self._extract_metadata('Entrypoint')

    @property
    def observable(self) -> str:
        return self._extract_metadata('Observable')

    @property
    def evidence(self) -> str:
        return self._extract_metadata('Evidence')

    @property
    def steps(self) -> list[dict]:
        return [
            {'description': m.group(2), 'completed': m.group(1) == 'x'}
            for line in self._lines_after_steps_marker()
            if (m := _STEP_RE.match(line))
        ]

    def _lines_after_steps_marker(self) -> list[str]:
        for i, line in enumerate(self._lines[1:], 1):
            if line.strip().startswith('- Steps:'):
                return self._lines[i + 1:]
        return []

    def _extract_metadata(self, key: str) -> str:
        prefix = f'- {key}:'
        for line in self._lines[1:]:
            stripped = line.strip()
            if stripped.startswith(prefix):
                val = stripped[len(prefix):].strip()
                if val.startswith('`') and val.endswith('`'):
                    val = val[1:-1]
                return val
        return ''

    def mark_complete(self) -> None:
        if self.is_completed:
            raise ValueError(f"task is already complete")
        self._lines[0] = self._lines[0].replace('- [ ]', '- [x]', 1)
        for i, line in enumerate(self._lines[1:], 1):
            if _STEP_RE.match(line):
                self._lines[i] = line.replace('[ ]', '[x]', 1)

    def to_lines(self, thread_num: int, task_num: int) -> list[str]:
        lines = list(self._lines)
        lines[0] = re.sub(r'Task \d+\.\d+:', f'Task {thread_num}.{task_num}:', lines[0])
        return lines
