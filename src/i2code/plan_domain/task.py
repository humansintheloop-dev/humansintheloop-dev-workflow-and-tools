"""Task entity — owns its raw markdown lines."""

from dataclasses import dataclass
import re


_TASK_HEADER_RE = re.compile(r'^- \[([ x])\] \*\*Task \d+\.\d+: (.+)\*\*$')
_STEP_RE = re.compile(r'^\s+- \[([ x])\] (.+)$')
_SINGLE_CODE_SPAN_RE = re.compile(r'^`([^`]+)`$')


def _unwrap_single_code_span(value: str) -> str:
    m = _SINGLE_CODE_SPAN_RE.match(value)
    return m.group(1) if m else value


def _as_code_unless_it_has_code_spans(value: str) -> str:
    return value if '`' in value else f'`{value}`'


@dataclass
class TaskMetadata:
    """Verification contract for a task: type, how to run, what to observe, how to verify."""
    task_type: str
    entrypoint: str
    observable: str
    evidence: str


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
        return _unwrap_single_code_span(self._extract_metadata('Entrypoint'))

    @property
    def observable(self) -> str:
        return self._extract_metadata('Observable')

    @property
    def evidence(self) -> str:
        return _unwrap_single_code_span(self._extract_metadata('Evidence'))

    @property
    def steps(self) -> list[dict]:
        return [
            {'description': m.group(2), 'completed': m.group(1) == 'x'}
            for line in self._lines_after_steps_marker()
            if (m := _STEP_RE.match(line))
        ]

    def to_spec(self) -> dict:
        return {
            'title': self.title,
            'task_type': self.task_type,
            'entrypoint': self.entrypoint,
            'observable': self.observable,
            'evidence': self.evidence,
            'steps': [step['description'] for step in self.steps],
        }

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
                return stripped[len(prefix):].strip()
        return ''

    def mark_complete(self) -> None:
        if self.is_completed:
            raise ValueError("task is already complete")
        self._lines[0] = self._lines[0].replace('- [ ]', '- [x]', 1)
        for i, line in enumerate(self._lines[1:], 1):
            if _STEP_RE.match(line):
                self._lines[i] = line.replace('[ ]', '[x]', 1)

    def mark_step_complete(self, step_number: int) -> None:
        idx = self._validated_step_line_index(step_number)
        match = _STEP_RE.match(self._lines[idx])
        assert match is not None
        if match.group(1) == 'x':
            raise ValueError(f"step {step_number} is already complete")
        self._lines[idx] = self._lines[idx].replace('[ ]', '[x]', 1)

    def mark_step_incomplete(self, step_number: int) -> None:
        idx = self._validated_step_line_index(step_number)
        match = _STEP_RE.match(self._lines[idx])
        assert match is not None
        if match.group(1) == ' ':
            raise ValueError(f"step {step_number} is already incomplete")
        self._lines[idx] = self._lines[idx].replace('[x]', '[ ]', 1)

    def _validated_step_line_index(self, step_number: int) -> int:
        step_indices = [i for i, line in enumerate(self._lines) if _STEP_RE.match(line)]
        if step_number < 1 or step_number > len(step_indices):
            raise ValueError(f"step {step_number} does not exist")
        return step_indices[step_number - 1]

    def mark_incomplete(self) -> None:
        if not self.is_completed:
            raise ValueError("task is already incomplete")
        self._lines[0] = self._lines[0].replace('- [x]', '- [ ]', 1)
        for i, line in enumerate(self._lines[1:], 1):
            if _STEP_RE.match(line):
                self._lines[i] = line.replace('[x]', '[ ]', 1)

    @classmethod
    def create(cls, title: str, metadata: TaskMetadata, steps: list[str]) -> 'Task':
        lines = [f'- [ ] **Task 0.0: {title}**']
        lines.append(f'  - TaskType: {metadata.task_type}')
        lines.append(f'  - Entrypoint: {_as_code_unless_it_has_code_spans(metadata.entrypoint)}')
        lines.append(f'  - Observable: {metadata.observable}')
        lines.append(f'  - Evidence: {_as_code_unless_it_has_code_spans(metadata.evidence)}')
        lines.append('  - Steps:')
        for step in steps:
            lines.append(f'    - [ ] {step}')
        return cls(_lines=lines)

    def to_lines(self, thread_num: int, task_num: int) -> list[str]:
        lines = list(self._lines)
        lines[0] = re.sub(r'Task \d+\.\d+:', f'Task {thread_num}.{task_num}:', lines[0])
        return lines
