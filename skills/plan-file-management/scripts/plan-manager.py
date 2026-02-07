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

    return preamble, threads, postamble


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
