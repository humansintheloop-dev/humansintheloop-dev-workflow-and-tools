"""Plan-level pure functions."""

import re

from i2code.plan._helpers import _extract_thread_sections, _parse_task_block



def get_thread(plan: str, thread_number: int) -> dict:
    """Return full thread content including introduction, tasks, and steps.

    Raises ValueError if thread_number does not exist.
    """
    _, threads, _ = _extract_thread_sections(plan)

    thread_text = None
    for num, text in threads:
        if num == thread_number:
            thread_text = text
            break

    if thread_text is None:
        raise ValueError(f"get-thread: thread {thread_number} does not exist")

    lines = thread_text.split('\n')

    # Extract title from heading
    heading_re = re.compile(r'^## Steel Thread \d+: (.+)$')
    title = heading_re.match(lines[0]).group(1)

    # Find task line indices
    task_line_re = re.compile(r'^- \[[ x]\] \*\*Task \d+\.\d+:')
    task_starts = []
    for i, line in enumerate(lines):
        if task_line_re.match(line):
            task_starts.append(i)

    # Extract introduction (between heading and first task)
    if task_starts:
        intro_lines = lines[1:task_starts[0]]
    else:
        intro_lines = lines[1:]
    introduction = '\n'.join(intro_lines).strip()

    # Parse each task
    tasks = []
    for idx, start in enumerate(task_starts):
        if idx + 1 < len(task_starts):
            end = task_starts[idx + 1]
        else:
            end = len(lines)
        task = _parse_task_block(lines, start, end, thread_number)
        if task:
            tasks.append(task)

    return {
        'number': thread_number,
        'title': title,
        'introduction': introduction,
        'tasks': tasks,
    }
