"""Parse a plan markdown string into domain objects."""

import re

from i2code.plan_domain.plan import Plan
from i2code.plan_domain.thread import Thread
from i2code.plan_domain.task import Task


_THREAD_HEADING_RE = re.compile(r'^## (?:Steel )?Thread (\d+):')
_TASK_LINE_RE = re.compile(r'^- \[[ x]\] \*\*Task \d+\.\d+:')


def parse(text: str) -> Plan:
    lines = text.split('\n')
    thread_starts = _find_matching_lines(lines, _THREAD_HEADING_RE)

    if not thread_starts:
        return Plan(_preamble_lines=lines)

    postamble_start = _find_postamble_start(lines, thread_starts[-1])

    return Plan(
        _preamble_lines=lines[:thread_starts[0]],
        threads=_parse_threads(lines, thread_starts, postamble_start),
        _postamble_lines=lines[postamble_start:],
    )


def _parse_threads(lines: list[str], thread_starts: list[int], end: int) -> list[Thread]:
    return [
        _parse_thread(lines[start:end])
        for start, end in _consecutive_ranges(thread_starts, end)
    ]


def _parse_thread(lines: list[str]) -> Thread:
    task_starts = _find_matching_lines(lines, _TASK_LINE_RE)

    if not task_starts:
        return Thread(_header_lines=lines)

    tasks = [
        Task(_lines=lines[start:end])
        for start, end in _consecutive_ranges(task_starts, len(lines))
    ]

    return Thread(_header_lines=lines[:task_starts[0]], tasks=tasks)


def _find_matching_lines(lines: list[str], pattern: re.Pattern) -> list[int]:
    return [i for i, line in enumerate(lines) if pattern.match(line)]


def _find_postamble_start(lines: list[str], last_thread_start: int) -> int:
    for i in range(last_thread_start + 1, len(lines)):
        if lines[i].startswith('## ') and not _THREAD_HEADING_RE.match(lines[i]):
            if i > 0 and lines[i - 1].strip() == '---':
                return i - 1
            return i
    return len(lines)


def _consecutive_ranges(starts: list[int], end: int) -> list[tuple[int, int]]:
    return [
        (starts[i], starts[i + 1] if i + 1 < len(starts) else end)
        for i in range(len(starts))
    ]
