# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Renumber Steel Thread and Task lines in a plan file sequentially."""

import os
import re
import sys
import tempfile


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


def atomic_write(file_path: str, content: str) -> None:
    """Write content to file atomically using temp file + rename."""
    dir_name = os.path.dirname(os.path.abspath(file_path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.rename(tmp_path, file_path)
    except Exception:
        os.unlink(tmp_path)
        raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <plan-file>", file=sys.stderr)
        sys.exit(1)

    plan_file = sys.argv[1]
    with open(plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    atomic_write(plan_file, fix_numbering(plan))
    print(f"Fixed numbering in {plan_file}")
