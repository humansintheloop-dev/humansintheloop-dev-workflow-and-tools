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
