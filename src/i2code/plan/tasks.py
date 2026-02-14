"""Task and step level pure functions."""

import re

from i2code.plan._helpers import append_change_history, _serialize_task, _find_task_boundaries
from i2code.plan.plans import fix_numbering



def mark_step_complete(plan: str, thread_number: int, task_number: int,
                       step_number: int, rationale: str) -> str:
    """Mark a single step as complete.

    Raises ValueError if the step does not exist or is already complete.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')
    task_line_re = re.compile(r'^- \[[ x]\] \*\*Task (\d+)\.(\d+):')
    step_re = re.compile(r'^(\s+- )\[([ x])\]( .+)$')

    current_thread = 0
    in_target_task = False
    step_counter = 0
    target_step_idx = None

    for i, line in enumerate(lines):
        thread_match = thread_heading_re.match(line)
        if thread_match:
            current_thread = int(thread_match.group(1))
            in_target_task = False
            continue

        task_match = task_line_re.match(line)
        if task_match:
            t_num = int(task_match.group(1))
            tk_num = int(task_match.group(2))
            in_target_task = (t_num == thread_number and tk_num == task_number)
            step_counter = 0
            continue

        if in_target_task:
            step_match = step_re.match(line)
            if step_match:
                step_counter += 1
                if step_counter == step_number:
                    target_step_idx = i
                    step_completed = step_match.group(2) == 'x'
                    break
            elif line.strip().startswith('- ') and not line.strip().startswith('- Steps:'):
                # Exited the steps section (hit a metadata line or new task)
                if not line.strip().startswith('- TaskType:') and \
                   not line.strip().startswith('- Entrypoint:') and \
                   not line.strip().startswith('- Observable:') and \
                   not line.strip().startswith('- Evidence:') and \
                   not line.strip().startswith('- Steps:'):
                    in_target_task = False

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"mark-step-complete: thread {thread_number} does not exist")

    # Validate task exists
    task_exists = any(
        task_line_re.match(l) and
        int(task_line_re.match(l).group(1)) == thread_number and
        int(task_line_re.match(l).group(2)) == task_number
        for l in lines
    )
    if not task_exists:
        raise ValueError(f"mark-step-complete: task {thread_number}.{task_number} does not exist")

    if target_step_idx is None:
        raise ValueError(f"mark-step-complete: step {step_number} of task {thread_number}.{task_number} does not exist")

    if step_completed:
        raise ValueError(f"mark-step-complete: step {step_number} of task {thread_number}.{task_number} is already complete")

    # Mark the step complete
    m = step_re.match(lines[target_step_idx])
    lines[target_step_idx] = f"{m.group(1)}[x]{m.group(3)}"

    result = '\n'.join(lines)
    return append_change_history(result, "mark-step-complete", rationale)


def mark_step_incomplete(plan: str, thread_number: int, task_number: int,
                         step_number: int, rationale: str) -> str:
    """Mark a single completed step as incomplete.

    Raises ValueError if the step does not exist or is already incomplete.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')
    task_line_re = re.compile(r'^- \[[ x]\] \*\*Task (\d+)\.(\d+):')
    step_re = re.compile(r'^(\s+- )\[([ x])\]( .+)$')

    current_thread = 0
    in_target_task = False
    step_counter = 0
    target_step_idx = None

    for i, line in enumerate(lines):
        thread_match = thread_heading_re.match(line)
        if thread_match:
            current_thread = int(thread_match.group(1))
            in_target_task = False
            continue

        task_match = task_line_re.match(line)
        if task_match:
            t_num = int(task_match.group(1))
            tk_num = int(task_match.group(2))
            in_target_task = (t_num == thread_number and tk_num == task_number)
            step_counter = 0
            continue

        if in_target_task:
            step_match = step_re.match(line)
            if step_match:
                step_counter += 1
                if step_counter == step_number:
                    target_step_idx = i
                    step_incomplete = step_match.group(2) == ' '
                    break
            elif line.strip().startswith('- ') and not line.strip().startswith('- Steps:'):
                if not line.strip().startswith('- TaskType:') and \
                   not line.strip().startswith('- Entrypoint:') and \
                   not line.strip().startswith('- Observable:') and \
                   not line.strip().startswith('- Evidence:') and \
                   not line.strip().startswith('- Steps:'):
                    in_target_task = False

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"mark-step-incomplete: thread {thread_number} does not exist")

    # Validate task exists
    task_exists = any(
        task_line_re.match(l) and
        int(task_line_re.match(l).group(1)) == thread_number and
        int(task_line_re.match(l).group(2)) == task_number
        for l in lines
    )
    if not task_exists:
        raise ValueError(f"mark-step-incomplete: task {thread_number}.{task_number} does not exist")

    if target_step_idx is None:
        raise ValueError(f"mark-step-incomplete: step {step_number} of task {thread_number}.{task_number} does not exist")

    if step_incomplete:
        raise ValueError(f"mark-step-incomplete: step {step_number} of task {thread_number}.{task_number} is already incomplete")

    # Mark the step incomplete
    m = step_re.match(lines[target_step_idx])
    lines[target_step_idx] = f"{m.group(1)}[ ]{m.group(3)}"

    result = '\n'.join(lines)
    return append_change_history(result, "mark-step-incomplete", rationale)


def insert_task_before(plan: str, thread_number: int, before_task: int,
                       title: str, task_type: str, entrypoint: str,
                       observable: str, evidence: str, steps: list[str],
                       rationale: str) -> str:
    """Insert a task before the specified task within a thread.

    Raises ValueError if thread_number or before_task does not exist.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"insert-task-before: thread {thread_number} does not exist")

    task_bounds = _find_task_boundaries(lines, thread_number)
    task_numbers = {tk_num for _, _, tk_num in task_bounds}

    if before_task not in task_numbers:
        raise ValueError(f"insert-task-before: task {before_task} in thread {thread_number} does not exist")

    new_task_text = _serialize_task(title, task_type, entrypoint, observable, evidence, steps)

    # Find insertion point
    for start, end, tk_num in task_bounds:
        if tk_num == before_task:
            new_lines = lines[:start] + [new_task_text, ''] + lines[start:]
            result = fix_numbering('\n'.join(new_lines))
            return append_change_history(result, "insert-task-before", rationale)

    raise ValueError(f"insert-task-before: task {before_task} in thread {thread_number} does not exist")


def insert_task_after(plan: str, thread_number: int, after_task: int,
                      title: str, task_type: str, entrypoint: str,
                      observable: str, evidence: str, steps: list[str],
                      rationale: str) -> str:
    """Insert a task after the specified task within a thread.

    Raises ValueError if thread_number or after_task does not exist.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"insert-task-after: thread {thread_number} does not exist")

    task_bounds = _find_task_boundaries(lines, thread_number)
    task_numbers = {tk_num for _, _, tk_num in task_bounds}

    if after_task not in task_numbers:
        raise ValueError(f"insert-task-after: task {after_task} in thread {thread_number} does not exist")

    new_task_text = _serialize_task(title, task_type, entrypoint, observable, evidence, steps)

    for start, end, tk_num in task_bounds:
        if tk_num == after_task:
            new_lines = lines[:end] + ['', new_task_text] + lines[end:]
            result = fix_numbering('\n'.join(new_lines))
            return append_change_history(result, "insert-task-after", rationale)

    raise ValueError(f"insert-task-after: task {after_task} in thread {thread_number} does not exist")


def delete_task(plan: str, thread_number: int, task_number: int, rationale: str) -> str:
    """Remove a task from a thread and renumber remaining tasks.

    Raises ValueError if thread_number or task_number does not exist.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"delete-task: thread {thread_number} does not exist")

    task_bounds = _find_task_boundaries(lines, thread_number)
    task_numbers = {tk_num for _, _, tk_num in task_bounds}

    if task_number not in task_numbers:
        raise ValueError(f"delete-task: task {task_number} in thread {thread_number} does not exist")

    for start, end, tk_num in task_bounds:
        if tk_num == task_number:
            new_lines = lines[:start] + lines[end:]
            result = fix_numbering('\n'.join(new_lines))
            return append_change_history(result, "delete-task", rationale)

    raise ValueError(f"delete-task: task {task_number} in thread {thread_number} does not exist")


def replace_task(plan: str, thread_number: int, task_number: int,
                  title: str, task_type: str, entrypoint: str,
                  observable: str, evidence: str, steps: list[str],
                  rationale: str) -> str:
    """Replace a task's content in place within a thread and renumber.

    Raises ValueError if thread_number or task_number does not exist.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"replace-task: thread {thread_number} does not exist")

    task_bounds = _find_task_boundaries(lines, thread_number)
    existing_numbers = {tk_num for _, _, tk_num in task_bounds}

    if task_number not in existing_numbers:
        raise ValueError(f"replace-task: task {task_number} in thread {thread_number} does not exist")

    new_task_text = _serialize_task(title, task_type, entrypoint, observable, evidence, steps)

    for start, end, tk_num in task_bounds:
        if tk_num == task_number:
            new_lines = lines[:start] + new_task_text.split('\n') + lines[end:]
            result = fix_numbering('\n'.join(new_lines))
            return append_change_history(result, "replace-task", rationale)

    raise ValueError(f"replace-task: task {task_number} in thread {thread_number} does not exist")


def reorder_tasks(plan: str, thread_number: int, task_order: list[int],
                   rationale: str) -> str:
    """Reorder tasks within a thread according to the specified ordering and renumber.

    Raises ValueError if thread_number doesn't exist or task_order doesn't contain
    exactly the set of existing task numbers in the thread.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')

    # Validate thread exists
    thread_exists = any(
        thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
        for l in lines
    )
    if not thread_exists:
        raise ValueError(f"reorder-tasks: thread {thread_number} does not exist")

    task_bounds = _find_task_boundaries(lines, thread_number)
    existing_numbers = [tk_num for _, _, tk_num in task_bounds]
    existing_set = set(existing_numbers)

    # Validate task_order
    if len(task_order) != len(set(task_order)):
        raise ValueError("reorder-tasks: --order contains duplicate task numbers")

    order_set = set(task_order)
    if order_set != existing_set:
        missing = existing_set - order_set
        extra = order_set - existing_set
        parts = []
        if missing:
            parts.append(f"missing tasks: {sorted(missing)}")
        if extra:
            parts.append(f"nonexistent tasks: {sorted(extra)}")
        raise ValueError(f"reorder-tasks: --order does not match existing tasks ({', '.join(parts)})")

    # Build a map from task number to its lines
    task_lines_by_num = {}
    for start, end, tk_num in task_bounds:
        task_lines_by_num[tk_num] = lines[start:end]

    # Determine the region to replace (from first task start to last task end)
    first_start = task_bounds[0][0]
    last_end = task_bounds[-1][1]

    # Build reordered task lines
    reordered_task_lines = []
    for tk_num in task_order:
        reordered_task_lines.extend(task_lines_by_num[tk_num])

    new_lines = lines[:first_start] + reordered_task_lines + lines[last_end:]
    result = fix_numbering('\n'.join(new_lines))
    return append_change_history(result, "reorder-tasks", rationale)


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
