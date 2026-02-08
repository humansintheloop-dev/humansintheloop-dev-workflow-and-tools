"""Shared internal functions used by plan operation modules."""

import os
import re
import tempfile
from datetime import datetime


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
