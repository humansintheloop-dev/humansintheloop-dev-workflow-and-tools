"""Task and step level pure functions."""

import re

from i2code.plan._helpers import append_change_history, _find_task_boundaries
from i2code.plan.plans import fix_numbering


def move_task_before(plan: str, thread_number: int, task_number: int,
                     before_task: int, rationale: str) -> str:
    """Move a task to before another task within the same thread and renumber.

    Raises ValueError if thread_number, task_number, or before_task does not exist,
    or if task_number equals before_task.
    """
    if task_number == before_task:
        raise ValueError(f"move-task-before: cannot move task to before the same task")

    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"move-task-before: thread {thread_number} does not exist")

    task_bounds = _find_task_boundaries(lines, thread_number)
    existing_numbers = {tk_num for _, _, tk_num in task_bounds}

    if task_number not in existing_numbers:
        raise ValueError(f"move-task-before: task {task_number} in thread {thread_number} does not exist")
    if before_task not in existing_numbers:
        raise ValueError(f"move-task-before: task {before_task} in thread {thread_number} does not exist")

    # Build new order: remove task_number, insert it before before_task
    order = [tk_num for _, _, tk_num in task_bounds if tk_num != task_number]
    insert_idx = next(i for i, n in enumerate(order) if n == before_task)
    order.insert(insert_idx, task_number)

    # Build reordered task lines
    task_lines_by_num = {}
    for start, end, tk_num in task_bounds:
        task_lines_by_num[tk_num] = lines[start:end]

    first_start = task_bounds[0][0]
    last_end = task_bounds[-1][1]

    reordered_task_lines = []
    for tk_num in order:
        reordered_task_lines.extend(task_lines_by_num[tk_num])

    new_lines = lines[:first_start] + reordered_task_lines + lines[last_end:]
    result = fix_numbering('\n'.join(new_lines))
    return append_change_history(result, "move-task-before", rationale)


def move_task_after(plan: str, thread_number: int, task_number: int,
                    after_task: int, rationale: str) -> str:
    """Move a task to after another task within the same thread and renumber.

    Raises ValueError if thread_number, task_number, or after_task does not exist,
    or if task_number equals after_task.
    """
    if task_number == after_task:
        raise ValueError(f"move-task-after: cannot move task to after the same task")

    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"move-task-after: thread {thread_number} does not exist")

    task_bounds = _find_task_boundaries(lines, thread_number)
    existing_numbers = {tk_num for _, _, tk_num in task_bounds}

    if task_number not in existing_numbers:
        raise ValueError(f"move-task-after: task {task_number} in thread {thread_number} does not exist")
    if after_task not in existing_numbers:
        raise ValueError(f"move-task-after: task {after_task} in thread {thread_number} does not exist")

    # Build new order: remove task_number, insert it after after_task
    order = [tk_num for _, _, tk_num in task_bounds if tk_num != task_number]
    insert_idx = next(i for i, n in enumerate(order) if n == after_task) + 1
    order.insert(insert_idx, task_number)

    # Build reordered task lines
    task_lines_by_num = {}
    for start, end, tk_num in task_bounds:
        task_lines_by_num[tk_num] = lines[start:end]

    first_start = task_bounds[0][0]
    last_end = task_bounds[-1][1]

    reordered_task_lines = []
    for tk_num in order:
        reordered_task_lines.extend(task_lines_by_num[tk_num])

    new_lines = lines[:first_start] + reordered_task_lines + lines[last_end:]
    result = fix_numbering('\n'.join(new_lines))
    return append_change_history(result, "move-task-after", rationale)
