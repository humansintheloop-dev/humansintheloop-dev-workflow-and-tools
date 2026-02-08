"""Plan-level pure functions."""

import re


def fix_numbering(plan: str) -> str:
    """Renumber all threads and tasks sequentially.

    Threads are numbered starting from 1, and tasks are numbered
    as N.M where N is the thread number and M is the task position.
    """
    lines = plan.split('\n')
    result = []
    thread_counter = 0
    task_counter = 0

    thread_heading_re = re.compile(r'^(## Steel Thread )\d+(:.*)')
    task_line_re = re.compile(r'^(- \[[ x]\] \*\*Task )\d+\.\d+(:.*)$')

    for line in lines:
        thread_match = thread_heading_re.match(line)
        if thread_match:
            thread_counter += 1
            task_counter = 0
            line = f"{thread_match.group(1)}{thread_counter}{thread_match.group(2)}"
        else:
            task_match = task_line_re.match(line)
            if task_match:
                task_counter += 1
                line = f"{task_match.group(1)}{thread_counter}.{task_counter}{task_match.group(2)}"

        result.append(line)

    return '\n'.join(result)
