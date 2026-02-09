"""Plan-level pure functions."""

import re

from i2code.plan._helpers import _extract_thread_sections, _parse_task_block


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
