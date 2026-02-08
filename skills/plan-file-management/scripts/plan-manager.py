# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Plan file management CLI with subcommands for reading and writing plan files."""

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime


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


def append_change_history(plan: str, operation: str, rationale: str) -> str:
    """Append a change history entry to the plan."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"### {timestamp} - {operation}\n{rationale}\n"

    if "## Change History" in plan:
        # Append to existing change history section
        return plan.rstrip('\n') + '\n\n' + entry
    else:
        # Create the change history section
        return plan.rstrip('\n') + '\n\n---\n\n## Change History\n' + entry


def mark_task_complete(plan: str, thread_number: int, task_number: int, rationale: str | None = None) -> str:
    """Mark a task and all its steps as complete.

    Raises ValueError if the task does not exist or is already complete.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')
    task_line_re = re.compile(r'^- \[[ x]\] \*\*Task (\d+)\.(\d+):')

    current_thread = 0
    task_line_idx = None
    task_end_idx = None

    # Find the target task line
    for i, line in enumerate(lines):
        thread_match = thread_heading_re.match(line)
        if thread_match:
            current_thread = int(thread_match.group(1))
            continue

        task_match = task_line_re.match(line)
        if task_match:
            t_num = int(task_match.group(1))
            tk_num = int(task_match.group(2))
            if task_line_idx is not None and task_end_idx is None:
                # Found the next task - mark end of previous task
                task_end_idx = i
            if t_num == thread_number and tk_num == task_number:
                task_line_idx = i

        # A thread heading or horizontal rule after our task marks the end
        if task_line_idx is not None and task_end_idx is None and i > task_line_idx:
            if thread_heading_re.match(line) or (line.strip() == '---' and i > task_line_idx + 1):
                task_end_idx = i

    if task_line_idx is None:
        # Check if thread exists
        thread_exists = any(
            thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
            for l in lines
        )
        if not thread_exists:
            raise ValueError(f"mark-task-complete: thread {thread_number} does not exist")
        raise ValueError(f"mark-task-complete: task {thread_number}.{task_number} does not exist")

    # Check if already complete
    if "- [x]" in lines[task_line_idx]:
        raise ValueError(
            f"mark-task-complete: task {thread_number}.{task_number} is already complete"
        )

    if task_end_idx is None:
        task_end_idx = len(lines)

    # Mark the task line and all step lines as complete
    step_re = re.compile(r'^(\s+- )\[ \]( .*)$')
    for i in range(task_line_idx, task_end_idx):
        if i == task_line_idx:
            lines[i] = lines[i].replace('- [ ]', '- [x]', 1)
        else:
            step_match = step_re.match(lines[i])
            if step_match:
                lines[i] = f"{step_match.group(1)}[x]{step_match.group(2)}"

    result = '\n'.join(lines)
    if rationale is not None:
        result = append_change_history(result, "mark-task-complete", rationale)
    return result


def mark_task_incomplete(plan: str, thread_number: int, task_number: int, rationale: str | None = None) -> str:
    """Mark a completed task and all its steps as incomplete.

    Raises ValueError if the task does not exist or is already incomplete.
    """
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')
    task_line_re = re.compile(r'^- \[[ x]\] \*\*Task (\d+)\.(\d+):')

    current_thread = 0
    task_line_idx = None
    task_end_idx = None

    # Find the target task line
    for i, line in enumerate(lines):
        thread_match = thread_heading_re.match(line)
        if thread_match:
            current_thread = int(thread_match.group(1))
            continue

        task_match = task_line_re.match(line)
        if task_match:
            t_num = int(task_match.group(1))
            tk_num = int(task_match.group(2))
            if task_line_idx is not None and task_end_idx is None:
                # Found the next task - mark end of previous task
                task_end_idx = i
            if t_num == thread_number and tk_num == task_number:
                task_line_idx = i

        # A thread heading or horizontal rule after our task marks the end
        if task_line_idx is not None and task_end_idx is None and i > task_line_idx:
            if thread_heading_re.match(line) or (line.strip() == '---' and i > task_line_idx + 1):
                task_end_idx = i

    if task_line_idx is None:
        # Check if thread exists
        thread_exists = any(
            thread_heading_re.match(l) and int(thread_heading_re.match(l).group(1)) == thread_number
            for l in lines
        )
        if not thread_exists:
            raise ValueError(f"mark-task-incomplete: thread {thread_number} does not exist")
        raise ValueError(f"mark-task-incomplete: task {thread_number}.{task_number} does not exist")

    # Check if already incomplete
    if "- [ ]" in lines[task_line_idx]:
        raise ValueError(
            f"mark-task-incomplete: task {thread_number}.{task_number} is already incomplete"
        )

    if task_end_idx is None:
        task_end_idx = len(lines)

    # Mark the task line and all step lines as incomplete
    step_re = re.compile(r'^(\s+- )\[x\]( .*)$')
    for i in range(task_line_idx, task_end_idx):
        if i == task_line_idx:
            lines[i] = lines[i].replace('- [x]', '- [ ]', 1)
        else:
            step_match = step_re.match(lines[i])
            if step_match:
                lines[i] = f"{step_match.group(1)}[ ]{step_match.group(2)}"

    result = '\n'.join(lines)
    if rationale is not None:
        result = append_change_history(result, "mark-task-incomplete", rationale)
    return result


def _extract_thread_sections(plan: str) -> tuple[str, list[tuple[int, str]], str]:
    """Split a plan into preamble, thread sections, and postamble.

    Returns (preamble, [(thread_number, thread_text), ...], postamble).
    The preamble is everything before the first Steel Thread heading.
    Each thread_text includes the heading through to (but not including) the next
    thread heading or the Summary/Change History section.
    The postamble is the Summary section and everything after.
    """
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')
    lines = plan.split('\n')

    # Find thread heading line indices
    thread_starts = []
    for i, line in enumerate(lines):
        m = thread_heading_re.match(line)
        if m:
            thread_starts.append((i, int(m.group(1))))

    if not thread_starts:
        return plan, [], ""

    preamble = '\n'.join(lines[:thread_starts[0][0]])
    if preamble and not preamble.endswith('\n'):
        preamble += '\n'

    # Find where postamble starts (Summary section or Change History if no Summary)
    postamble_start = len(lines)
    for i in range(thread_starts[-1][0] + 1, len(lines)):
        if lines[i].startswith('## Summary') or lines[i].startswith('## Change History'):
            # Include the --- separator before the section if present
            if i > 0 and lines[i - 1].strip() == '---':
                postamble_start = i - 1
            else:
                postamble_start = i
            break

    threads = []
    for idx, (start, num) in enumerate(thread_starts):
        if idx + 1 < len(thread_starts):
            end = thread_starts[idx + 1][0]
        else:
            end = postamble_start
        thread_text = '\n'.join(lines[start:end])
        threads.append((num, thread_text))

    postamble = '\n'.join(lines[postamble_start:])
    if postamble and not postamble.startswith('\n'):
        postamble = '\n' + postamble

    return preamble, threads, postamble


def _parse_task_block(lines: list[str], start: int, end: int, thread_num: int) -> dict:
    """Parse a task block from lines[start:end] into a dict with full metadata."""
    task_line = lines[start]
    task_re = re.compile(r'^- \[([ x])\] \*\*Task (\d+)\.(\d+): (.+)\*\*$')
    m = task_re.match(task_line)
    if not m:
        return None

    completed = m.group(1) == 'x'
    task_number = int(m.group(3))
    title = m.group(4)

    task_type = entrypoint = observable = evidence = ''
    steps = []
    in_steps = False

    for i in range(start + 1, end):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('- TaskType:'):
            task_type = stripped[len('- TaskType:'):].strip()
        elif stripped.startswith('- Entrypoint:'):
            val = stripped[len('- Entrypoint:'):].strip()
            # Strip backticks
            if val.startswith('`') and val.endswith('`'):
                val = val[1:-1]
            entrypoint = val
        elif stripped.startswith('- Observable:'):
            observable = stripped[len('- Observable:'):].strip()
        elif stripped.startswith('- Evidence:'):
            val = stripped[len('- Evidence:'):].strip()
            if val.startswith('`') and val.endswith('`'):
                val = val[1:-1]
            evidence = val
        elif stripped.startswith('- Steps:'):
            in_steps = True
        elif in_steps and re.match(r'^\s+- \[[ x]\] ', line):
            step_match = re.match(r'^\s+- \[([ x])\] (.+)$', line)
            if step_match:
                steps.append({
                    'description': step_match.group(2),
                    'completed': step_match.group(1) == 'x'
                })

    return {
        'thread_number': thread_num,
        'task_number': task_number,
        'title': title,
        'completed': completed,
        'task_type': task_type,
        'entrypoint': entrypoint,
        'observable': observable,
        'evidence': evidence,
        'steps': steps,
    }


def get_next_task(plan: str) -> dict | None:
    """Return the first uncompleted task across the plan, or None if all complete."""
    lines = plan.split('\n')
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')
    task_line_re = re.compile(r'^- \[[ x]\] \*\*Task \d+\.\d+:')

    current_thread = 0
    task_starts = []

    for i, line in enumerate(lines):
        m = thread_heading_re.match(line)
        if m:
            current_thread = int(m.group(1))
            continue

        if task_line_re.match(line):
            task_starts.append((i, current_thread))

    # Determine task boundaries
    for idx, (start, thread_num) in enumerate(task_starts):
        if idx + 1 < len(task_starts):
            end = task_starts[idx + 1][0]
        else:
            # Find end: next --- or thread heading or end of file
            end = len(lines)
            for j in range(start + 1, len(lines)):
                if thread_heading_re.match(lines[j]) or lines[j].strip() == '---':
                    end = j
                    break

        task = _parse_task_block(lines, start, end, thread_num)
        if task and not task['completed']:
            return task

    return None


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


def list_threads(plan: str) -> list[dict]:
    """Return all threads with their numbers, titles, and completion status."""
    _, threads, _ = _extract_thread_sections(plan)
    task_re = re.compile(r'^- \[([ x])\] \*\*Task \d+\.\d+:')
    heading_re = re.compile(r'^## Steel Thread (\d+): (.+)$')

    result = []
    for num, text in threads:
        lines = text.split('\n')
        title = ''
        m = heading_re.match(lines[0])
        if m:
            title = m.group(2)

        total_tasks = 0
        completed_tasks = 0
        for line in lines:
            tm = task_re.match(line)
            if tm:
                total_tasks += 1
                if tm.group(1) == 'x':
                    completed_tasks += 1

        result.append({
            'number': num,
            'title': title,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
        })

    return result


def get_summary(plan: str) -> dict:
    """Return plan metadata and progress summary."""
    lines = plan.split('\n')

    # Extract plan name from heading
    plan_name = ''
    for line in lines:
        m = re.match(r'^# Implementation Plan: (.+)$', line)
        if m:
            plan_name = m.group(1)
            break

    # Extract idea type section
    idea_type = ''
    in_idea_type = False
    for line in lines:
        if line.startswith('## Idea Type'):
            in_idea_type = True
            continue
        if in_idea_type:
            if line.startswith('##') or line.strip() == '---':
                break
            if line.strip():
                idea_type = line.strip()

    # Extract overview section
    overview_lines = []
    in_overview = False
    for line in lines:
        if line.startswith('## Overview'):
            in_overview = True
            continue
        if in_overview:
            if line.startswith('##') or line.strip() == '---':
                break
            overview_lines.append(line)
    overview = '\n'.join(overview_lines).strip()

    # Count threads and tasks
    _, threads, _ = _extract_thread_sections(plan)
    total_threads = len(threads)

    task_re = re.compile(r'^- \[([ x])\] \*\*Task \d+\.\d+:')
    total_tasks = 0
    completed_tasks = 0
    for line in lines:
        m = task_re.match(line)
        if m:
            total_tasks += 1
            if m.group(1) == 'x':
                completed_tasks += 1

    return {
        'plan_name': plan_name,
        'idea_type': idea_type,
        'overview': overview,
        'total_threads': total_threads,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
    }


def _serialize_thread(title: str, introduction: str, tasks: list[dict]) -> str:
    """Convert structured thread data to markdown text.

    The thread number and task numbers use placeholder 0 since
    fix_numbering will assign correct numbers.
    """
    lines = [f"## Steel Thread 0: {title}"]
    lines.append(introduction)
    lines.append("")

    for task in tasks:
        lines.append(f"- [ ] **Task 0.0: {task['title']}**")
        lines.append(f"  - TaskType: {task['task_type']}")
        lines.append(f"  - Entrypoint: `{task['entrypoint']}`")
        lines.append(f"  - Observable: {task['observable']}")
        lines.append(f"  - Evidence: `{task['evidence']}`")
        lines.append("  - Steps:")
        for step in task['steps']:
            lines.append(f"    - [ ] {step}")
        lines.append("")

    return '\n'.join(lines)


def insert_thread_before(plan: str, before_thread: int, title: str,
                          introduction: str, tasks: list[dict], rationale: str) -> str:
    """Insert a new thread before the specified thread and renumber.

    Raises ValueError if before_thread does not exist.
    """
    preamble, threads, postamble = _extract_thread_sections(plan)
    existing_numbers = {num for num, _ in threads}

    if before_thread not in existing_numbers:
        raise ValueError(f"insert-thread-before: thread {before_thread} does not exist")

    new_thread_text = _serialize_thread(title, introduction, tasks)

    reordered = []
    for num, text in threads:
        if num == before_thread:
            reordered.append((0, new_thread_text))
        reordered.append((num, text))

    assembled = preamble + '\n'.join(text for _, text in reordered) + postamble
    result = fix_numbering(assembled)
    return append_change_history(result, "insert-thread-before", rationale)


def insert_thread_after(plan: str, after_thread: int, title: str,
                         introduction: str, tasks: list[dict], rationale: str) -> str:
    """Insert a new thread after the specified thread and renumber.

    Raises ValueError if after_thread does not exist.
    """
    preamble, threads, postamble = _extract_thread_sections(plan)
    existing_numbers = {num for num, _ in threads}

    if after_thread not in existing_numbers:
        raise ValueError(f"insert-thread-after: thread {after_thread} does not exist")

    new_thread_text = _serialize_thread(title, introduction, tasks)

    reordered = []
    for num, text in threads:
        reordered.append((num, text))
        if num == after_thread:
            reordered.append((0, new_thread_text))

    assembled = preamble + '\n'.join(text for _, text in reordered) + postamble
    result = fix_numbering(assembled)
    return append_change_history(result, "insert-thread-after", rationale)


def delete_thread(plan: str, thread_number: int, rationale: str) -> str:
    """Remove a thread entirely and renumber remaining threads.

    Raises ValueError if thread_number does not exist.
    """
    preamble, threads, postamble = _extract_thread_sections(plan)
    existing_numbers = {num for num, _ in threads}

    if thread_number not in existing_numbers:
        raise ValueError(f"delete-thread: thread {thread_number} does not exist")

    remaining = [(num, text) for num, text in threads if num != thread_number]
    assembled = preamble + '\n'.join(text for _, text in remaining) + postamble
    result = fix_numbering(assembled)
    return append_change_history(result, "delete-thread", rationale)


def _serialize_task(title: str, task_type: str, entrypoint: str,
                    observable: str, evidence: str, steps: list[str]) -> str:
    """Convert structured task data to markdown lines."""
    lines = [f"- [ ] **Task 0.0: {title}**"]
    lines.append(f"  - TaskType: {task_type}")
    lines.append(f"  - Entrypoint: `{entrypoint}`")
    lines.append(f"  - Observable: {observable}")
    lines.append(f"  - Evidence: `{evidence}`")
    lines.append("  - Steps:")
    for step in steps:
        lines.append(f"    - [ ] {step}")
    return '\n'.join(lines)


def _find_task_boundaries(lines: list[str], thread_number: int) -> list[tuple[int, int, int]]:
    """Find task boundaries within a specific thread.

    Returns list of (start_line, end_line, task_number) for each task in the thread.
    """
    thread_heading_re = re.compile(r'^## Steel Thread (\d+):')
    task_line_re = re.compile(r'^- \[[ x]\] \*\*Task (\d+)\.(\d+):')

    current_thread = 0
    tasks = []

    for i, line in enumerate(lines):
        m = thread_heading_re.match(line)
        if m:
            current_thread = int(m.group(1))
            continue

        tm = task_line_re.match(line)
        if tm:
            t_num = int(tm.group(1))
            tk_num = int(tm.group(2))
            if t_num == thread_number:
                tasks.append((i, tk_num))
            elif current_thread > thread_number:
                break

    # Determine end boundaries
    result = []
    for idx, (start, tk_num) in enumerate(tasks):
        if idx + 1 < len(tasks):
            end = tasks[idx + 1][0]
        else:
            # Find end: next task, thread heading, ---, or end of file
            end = len(lines)
            for j in range(start + 1, len(lines)):
                if thread_heading_re.match(lines[j]) or lines[j].strip() == '---':
                    end = j
                    break
                if task_line_re.match(lines[j]):
                    end = j
                    break
        result.append((start, end, tk_num))

    return result


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


def replace_thread(plan: str, thread_number: int, title: str,
                    introduction: str, tasks: list[dict], rationale: str) -> str:
    """Replace a thread's content in place and renumber.

    Raises ValueError if thread_number does not exist.
    """
    preamble, threads, postamble = _extract_thread_sections(plan)
    existing_numbers = {num for num, _ in threads}

    if thread_number not in existing_numbers:
        raise ValueError(f"replace-thread: thread {thread_number} does not exist")

    new_thread_text = _serialize_thread(title, introduction, tasks)

    replaced = []
    for num, text in threads:
        if num == thread_number:
            replaced.append((num, new_thread_text))
        else:
            replaced.append((num, text))

    assembled = preamble + '\n'.join(text for _, text in replaced) + postamble
    result = fix_numbering(assembled)
    return append_change_history(result, "replace-thread", rationale)


def reorder_threads(plan: str, thread_order: list[int], rationale: str) -> str:
    """Reorder threads according to the specified ordering and renumber.

    Raises ValueError if thread_order doesn't contain exactly the set of
    existing thread numbers.
    """
    preamble, threads, postamble = _extract_thread_sections(plan)

    existing_numbers = {num for num, _ in threads}
    order_set = set(thread_order)

    if len(thread_order) != len(set(thread_order)):
        raise ValueError("reorder-threads: --order contains duplicate thread numbers")

    if order_set != existing_numbers:
        missing = existing_numbers - order_set
        extra = order_set - existing_numbers
        parts = []
        if missing:
            parts.append(f"missing threads: {sorted(missing)}")
        if extra:
            parts.append(f"nonexistent threads: {sorted(extra)}")
        raise ValueError(f"reorder-threads: --order does not match existing threads ({', '.join(parts)})")

    # Build lookup by thread number
    thread_by_num = {num: text for num, text in threads}

    # Reassemble in new order
    reordered = [thread_by_num[n] for n in thread_order]
    assembled = preamble + '\n'.join(reordered) + postamble

    result = fix_numbering(assembled)
    return append_change_history(result, "reorder-threads", rationale)


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


def cmd_get_next_task(args):
    """Handle the get-next-task subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    task = get_next_task(plan)
    if task is None:
        print("All tasks are complete.")
    else:
        print(f"Thread {task['thread_number']}, Task {task['thread_number']}.{task['task_number']}: {task['title']}")
        print(f"  TaskType: {task['task_type']}")
        print(f"  Entrypoint: {task['entrypoint']}")
        print(f"  Observable: {task['observable']}")
        print(f"  Evidence: {task['evidence']}")
        print(f"  Steps:")
        for i, step in enumerate(task['steps'], 1):
            status = 'x' if step['completed'] else ' '
            print(f"    {i}. [{status}] {step['description']}")


def _cmd_insert_task(args, insert_fn, position_arg, operation_name):
    """Shared handler for insert-task-before and insert-task-after."""
    import json
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        steps = json.loads(args.steps)
    except json.JSONDecodeError as e:
        print(f"{operation_name}: --steps is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = insert_fn(plan, args.thread, position_arg, args.title,
                           args.task_type, args.entrypoint, args.observable,
                           args.evidence, steps, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Inserted task '{args.title}' in thread {args.thread}")


def cmd_insert_task_before(args):
    """Handle the insert-task-before subcommand."""
    _cmd_insert_task(args, insert_task_before, args.before, "insert-task-before")


def cmd_insert_task_after(args):
    """Handle the insert-task-after subcommand."""
    _cmd_insert_task(args, insert_task_after, args.after, "insert-task-after")


def cmd_delete_task(args):
    """Handle the delete-task subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        result = delete_task(plan, args.thread, args.task, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Deleted task {args.thread}.{args.task}")


def cmd_replace_thread(args):
    """Handle the replace-thread subcommand."""
    import json
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        tasks = json.loads(args.tasks)
    except json.JSONDecodeError as e:
        print(f"replace-thread: --tasks is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = replace_thread(plan, args.thread, args.title, args.introduction, tasks, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Replaced thread {args.thread}")


def cmd_delete_thread(args):
    """Handle the delete-thread subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        result = delete_thread(plan, args.thread, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Deleted thread {args.thread}")


def cmd_mark_step_complete(args):
    """Handle the mark-step-complete subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        result = mark_step_complete(plan, args.thread, args.task, args.step, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Marked step {args.step} of task {args.thread}.{args.task} as complete")


def cmd_list_threads(args):
    """Handle the list-threads subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    threads = list_threads(plan)
    for t in threads:
        print(f"Thread {t['number']}: {t['title']} ({t['completed_tasks']}/{t['total_tasks']} tasks completed)")


def cmd_get_summary(args):
    """Handle the get-summary subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    summary = get_summary(plan)
    print(f"Plan: {summary['plan_name']}")
    print(f"Idea Type: {summary['idea_type']}")
    print(f"Overview: {summary['overview']}")
    print(f"Threads: {summary['total_threads']}")
    print(f"Tasks: {summary['completed_tasks']}/{summary['total_tasks']} completed")


def cmd_get_thread(args):
    """Handle the get-thread subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        thread = get_thread(plan, args.thread)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print(f"Thread {thread['number']}: {thread['title']}")
    print()
    print(thread['introduction'])
    print()
    for task in thread['tasks']:
        status = 'x' if task['completed'] else ' '
        print(f"- [{status}] Task {task['thread_number']}.{task['task_number']}: {task['title']}")
        print(f"  TaskType: {task['task_type']}")
        print(f"  Entrypoint: {task['entrypoint']}")
        print(f"  Observable: {task['observable']}")
        print(f"  Evidence: {task['evidence']}")
        print(f"  Steps:")
        for i, step in enumerate(task['steps'], 1):
            step_status = 'x' if step['completed'] else ' '
            print(f"    {i}. [{step_status}] {step['description']}")
        print()


def cmd_fix_numbering(args):
    """Handle the fix-numbering subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    result = fix_numbering(plan)
    atomic_write(args.plan_file, result)
    print(f"Fixed numbering in {args.plan_file}")


def cmd_reorder_threads(args):
    """Handle the reorder-threads subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        order = [int(n.strip()) for n in args.order.split(',')]
    except ValueError:
        print("reorder-threads: --order must be comma-separated integers", file=sys.stderr)
        sys.exit(1)

    try:
        result = reorder_threads(plan, order, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Reordered threads to [{args.order}]")


def _cmd_insert_thread(args, insert_fn, position_arg):
    """Shared handler for insert-thread-before and insert-thread-after."""
    import json
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        tasks = json.loads(args.tasks)
    except json.JSONDecodeError as e:
        print(f"insert-thread: --tasks is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = insert_fn(plan, position_arg, args.title, args.introduction, tasks, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Inserted thread '{args.title}'")


def cmd_insert_thread_before(args):
    """Handle the insert-thread-before subcommand."""
    _cmd_insert_thread(args, insert_thread_before, args.before)


def cmd_insert_thread_after(args):
    """Handle the insert-thread-after subcommand."""
    _cmd_insert_thread(args, insert_thread_after, args.after)


def cmd_reorder_tasks(args):
    """Handle the reorder-tasks subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        order = [int(n.strip()) for n in args.order.split(',')]
    except ValueError:
        print("reorder-tasks: --order must be comma-separated integers", file=sys.stderr)
        sys.exit(1)

    try:
        result = reorder_tasks(plan, args.thread, order, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Reordered tasks in thread {args.thread} to [{args.order}]")


def cmd_move_task_before(args):
    """Handle the move-task-before subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        result = move_task_before(plan, args.thread, args.task, args.before, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Moved task {args.thread}.{args.task} before task {args.thread}.{args.before}")


def cmd_move_task_after(args):
    """Handle the move-task-after subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        result = move_task_after(plan, args.thread, args.task, args.after, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Moved task {args.thread}.{args.task} after task {args.thread}.{args.after}")


def cmd_replace_task(args):
    """Handle the replace-task subcommand."""
    import json
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        steps = json.loads(args.steps)
    except json.JSONDecodeError as e:
        print(f"replace-task: --steps is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = replace_task(plan, args.thread, args.task, args.title,
                              args.task_type, args.entrypoint, args.observable,
                              args.evidence, steps, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Replaced task {args.thread}.{args.task}")


def cmd_mark_task_complete(args):
    """Handle the mark-task-complete subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        result = mark_task_complete(plan, args.thread, args.task, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Marked task {args.thread}.{args.task} as complete")


def cmd_mark_task_incomplete(args):
    """Handle the mark-task-incomplete subcommand."""
    with open(args.plan_file, 'r', encoding='utf-8') as f:
        plan = f.read()

    try:
        result = mark_task_incomplete(plan, args.thread, args.task, args.rationale)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    atomic_write(args.plan_file, result)
    print(f"Marked task {args.thread}.{args.task} as incomplete")


def build_parser():
    """Build the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description='Plan file management CLI'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # fix-numbering
    fix_num = subparsers.add_parser('fix-numbering',
                                     help='Renumber all threads and tasks sequentially')
    fix_num.add_argument('plan_file', help='Path to the plan file')
    fix_num.set_defaults(func=cmd_fix_numbering)

    # get-next-task
    get_next = subparsers.add_parser('get-next-task',
                                      help='Get the first uncompleted task')
    get_next.add_argument('plan_file', help='Path to the plan file')
    get_next.set_defaults(func=cmd_get_next_task)

    # list-threads
    list_thr = subparsers.add_parser('list-threads',
                                      help='List all threads with completion status')
    list_thr.add_argument('plan_file', help='Path to the plan file')
    list_thr.set_defaults(func=cmd_list_threads)

    # get-summary
    get_sum = subparsers.add_parser('get-summary',
                                     help='Get plan metadata and progress summary')
    get_sum.add_argument('plan_file', help='Path to the plan file')
    get_sum.set_defaults(func=cmd_get_summary)

    # get-thread
    get_thr = subparsers.add_parser('get-thread',
                                     help='Get full thread content with tasks and steps')
    get_thr.add_argument('plan_file', help='Path to the plan file')
    get_thr.add_argument('--thread', type=int, required=True, help='Thread number')
    get_thr.set_defaults(func=cmd_get_thread)

    # reorder-threads
    reorder = subparsers.add_parser('reorder-threads',
                                     help='Reorder threads according to a specified ordering')
    reorder.add_argument('plan_file', help='Path to the plan file')
    reorder.add_argument('--order', required=True,
                         help='Comma-separated thread numbers in desired order (e.g., 3,1,2)')
    reorder.add_argument('--rationale', required=True, help='Reason for the change')
    reorder.set_defaults(func=cmd_reorder_threads)

    # insert-thread-before
    insert_before = subparsers.add_parser('insert-thread-before',
                                           help='Insert a thread before a specified thread')
    insert_before.add_argument('plan_file', help='Path to the plan file')
    insert_before.add_argument('--before', type=int, required=True, help='Thread number to insert before')
    insert_before.add_argument('--title', required=True, help='Thread title')
    insert_before.add_argument('--introduction', required=True, help='Thread introduction text')
    insert_before.add_argument('--tasks', required=True, help='Tasks as JSON array')
    insert_before.add_argument('--rationale', required=True, help='Reason for the change')
    insert_before.set_defaults(func=cmd_insert_thread_before)

    # insert-thread-after
    insert_after = subparsers.add_parser('insert-thread-after',
                                          help='Insert a thread after a specified thread')
    insert_after.add_argument('plan_file', help='Path to the plan file')
    insert_after.add_argument('--after', type=int, required=True, help='Thread number to insert after')
    insert_after.add_argument('--title', required=True, help='Thread title')
    insert_after.add_argument('--introduction', required=True, help='Thread introduction text')
    insert_after.add_argument('--tasks', required=True, help='Tasks as JSON array')
    insert_after.add_argument('--rationale', required=True, help='Reason for the change')
    insert_after.set_defaults(func=cmd_insert_thread_after)

    # mark-task-complete
    mark_task = subparsers.add_parser('mark-task-complete',
                                       help='Mark a task and all its steps as complete')
    mark_task.add_argument('plan_file', help='Path to the plan file')
    mark_task.add_argument('--thread', type=int, required=True, help='Thread number')
    mark_task.add_argument('--task', type=int, required=True, help='Task number')
    mark_task.add_argument('--rationale', default=None, help='Reason for the change (optional)')
    mark_task.set_defaults(func=cmd_mark_task_complete)

    # mark-step-complete
    mark_step = subparsers.add_parser('mark-step-complete',
                                       help='Mark a single step as complete')
    mark_step.add_argument('plan_file', help='Path to the plan file')
    mark_step.add_argument('--thread', type=int, required=True, help='Thread number')
    mark_step.add_argument('--task', type=int, required=True, help='Task number')
    mark_step.add_argument('--step', type=int, required=True, help='Step number')
    mark_step.add_argument('--rationale', required=True, help='Reason for the change')
    mark_step.set_defaults(func=cmd_mark_step_complete)

    # replace-thread
    rep_thread = subparsers.add_parser('replace-thread',
                                        help='Replace a thread with new content')
    rep_thread.add_argument('plan_file', help='Path to the plan file')
    rep_thread.add_argument('--thread', type=int, required=True, help='Thread number to replace')
    rep_thread.add_argument('--title', required=True, help='New thread title')
    rep_thread.add_argument('--introduction', required=True, help='New thread introduction')
    rep_thread.add_argument('--tasks', required=True, help='New tasks as JSON array')
    rep_thread.add_argument('--rationale', required=True, help='Reason for the change')
    rep_thread.set_defaults(func=cmd_replace_thread)

    # delete-thread
    del_thread = subparsers.add_parser('delete-thread',
                                        help='Remove a thread entirely')
    del_thread.add_argument('plan_file', help='Path to the plan file')
    del_thread.add_argument('--thread', type=int, required=True, help='Thread number to delete')
    del_thread.add_argument('--rationale', required=True, help='Reason for the change')
    del_thread.set_defaults(func=cmd_delete_thread)

    # insert-task-before
    ins_task_before = subparsers.add_parser('insert-task-before',
                                             help='Insert a task before a specified task')
    ins_task_before.add_argument('plan_file', help='Path to the plan file')
    ins_task_before.add_argument('--thread', type=int, required=True, help='Thread number')
    ins_task_before.add_argument('--before', type=int, required=True, help='Task number to insert before')
    ins_task_before.add_argument('--title', required=True, help='Task title')
    ins_task_before.add_argument('--task-type', required=True, help='INFRA or OUTCOME')
    ins_task_before.add_argument('--entrypoint', required=True, help='Entrypoint command')
    ins_task_before.add_argument('--observable', required=True, help='Observable outcome')
    ins_task_before.add_argument('--evidence', required=True, help='Evidence command')
    ins_task_before.add_argument('--steps', required=True, help='Steps as JSON array of strings')
    ins_task_before.add_argument('--rationale', required=True, help='Reason for the change')
    ins_task_before.set_defaults(func=cmd_insert_task_before)

    # insert-task-after
    ins_task_after = subparsers.add_parser('insert-task-after',
                                            help='Insert a task after a specified task')
    ins_task_after.add_argument('plan_file', help='Path to the plan file')
    ins_task_after.add_argument('--thread', type=int, required=True, help='Thread number')
    ins_task_after.add_argument('--after', type=int, required=True, help='Task number to insert after')
    ins_task_after.add_argument('--title', required=True, help='Task title')
    ins_task_after.add_argument('--task-type', required=True, help='INFRA or OUTCOME')
    ins_task_after.add_argument('--entrypoint', required=True, help='Entrypoint command')
    ins_task_after.add_argument('--observable', required=True, help='Observable outcome')
    ins_task_after.add_argument('--evidence', required=True, help='Evidence command')
    ins_task_after.add_argument('--steps', required=True, help='Steps as JSON array of strings')
    ins_task_after.add_argument('--rationale', required=True, help='Reason for the change')
    ins_task_after.set_defaults(func=cmd_insert_task_after)

    # reorder-tasks
    reorder_tasks_p = subparsers.add_parser('reorder-tasks',
                                             help='Reorder tasks within a thread')
    reorder_tasks_p.add_argument('plan_file', help='Path to the plan file')
    reorder_tasks_p.add_argument('--thread', type=int, required=True, help='Thread number')
    reorder_tasks_p.add_argument('--order', required=True,
                                 help='Comma-separated task numbers in desired order (e.g., 3,1,2)')
    reorder_tasks_p.add_argument('--rationale', required=True, help='Reason for the change')
    reorder_tasks_p.set_defaults(func=cmd_reorder_tasks)

    # move-task-before
    move_before = subparsers.add_parser('move-task-before',
                                         help='Move a task to before another task within a thread')
    move_before.add_argument('plan_file', help='Path to the plan file')
    move_before.add_argument('--thread', type=int, required=True, help='Thread number')
    move_before.add_argument('--task', type=int, required=True, help='Task number to move')
    move_before.add_argument('--before', type=int, required=True, help='Task number to move before')
    move_before.add_argument('--rationale', required=True, help='Reason for the change')
    move_before.set_defaults(func=cmd_move_task_before)

    # move-task-after
    move_after = subparsers.add_parser('move-task-after',
                                        help='Move a task to after another task within a thread')
    move_after.add_argument('plan_file', help='Path to the plan file')
    move_after.add_argument('--thread', type=int, required=True, help='Thread number')
    move_after.add_argument('--task', type=int, required=True, help='Task number to move')
    move_after.add_argument('--after', type=int, required=True, help='Task number to move after')
    move_after.add_argument('--rationale', required=True, help='Reason for the change')
    move_after.set_defaults(func=cmd_move_task_after)

    # replace-task
    rep_task = subparsers.add_parser('replace-task',
                                      help='Replace a task with new content')
    rep_task.add_argument('plan_file', help='Path to the plan file')
    rep_task.add_argument('--thread', type=int, required=True, help='Thread number')
    rep_task.add_argument('--task', type=int, required=True, help='Task number to replace')
    rep_task.add_argument('--title', required=True, help='New task title')
    rep_task.add_argument('--task-type', required=True, help='INFRA or OUTCOME')
    rep_task.add_argument('--entrypoint', required=True, help='Entrypoint command')
    rep_task.add_argument('--observable', required=True, help='Observable outcome')
    rep_task.add_argument('--evidence', required=True, help='Evidence command')
    rep_task.add_argument('--steps', required=True, help='Steps as JSON array of strings')
    rep_task.add_argument('--rationale', required=True, help='Reason for the change')
    rep_task.set_defaults(func=cmd_replace_task)

    # delete-task
    del_task = subparsers.add_parser('delete-task',
                                      help='Remove a task from a thread')
    del_task.add_argument('plan_file', help='Path to the plan file')
    del_task.add_argument('--thread', type=int, required=True, help='Thread number')
    del_task.add_argument('--task', type=int, required=True, help='Task number to delete')
    del_task.add_argument('--rationale', required=True, help='Reason for the change')
    del_task.set_defaults(func=cmd_delete_task)

    # mark-task-incomplete
    mark_task_inc = subparsers.add_parser('mark-task-incomplete',
                                           help='Mark a completed task and all its steps as incomplete')
    mark_task_inc.add_argument('plan_file', help='Path to the plan file')
    mark_task_inc.add_argument('--thread', type=int, required=True, help='Thread number')
    mark_task_inc.add_argument('--task', type=int, required=True, help='Task number')
    mark_task_inc.add_argument('--rationale', default=None, help='Reason for the change (optional)')
    mark_task_inc.set_defaults(func=cmd_mark_task_incomplete)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
