"""Validate required fields in plan task blocks.

Each task block (``- [ ] **Task X.Y: ...`` or ``- [x] **Task X.Y: ...``)
must contain TaskType, Entrypoint, Observable, and Evidence fields.
"""

from i2code.plan_domain.parser import parse

_REQUIRED_FIELDS = [
    ("task_type", "TaskType"),
    ("entrypoint", "Entrypoint"),
    ("observable", "Observable"),
    ("evidence", "Evidence"),
]


def _task_errors(thread_num, task_num, task):
    """Return error messages for missing fields or steps in *task*."""
    task_id = f"Task {thread_num}.{task_num}"
    errors = [
        f"Missing {label} in {task_id}"
        for attr, label in _REQUIRED_FIELDS
        if not getattr(task, attr)
    ]
    if not task.steps:
        errors.append(f"{task_id} must contain at least one step")
    return errors


def _thread_errors(thread_num, thread):
    """Return error messages for an empty thread or its tasks."""
    if not thread.tasks:
        return [f"Thread {thread_num} must contain at least one task"]
    errors = []
    for task_num, task in enumerate(thread.tasks, 1):
        errors.extend(_task_errors(thread_num, task_num, task))
    return errors


def validate_plan(plan_text: str) -> tuple[bool, list[str]]:
    """Validate that every task block contains the required contract fields.

    Returns ``(True, [])`` when valid, or ``(False, [error_messages])`` when
    one or more tasks are missing required fields.
    """
    plan = parse(plan_text)
    if not plan.threads:
        return (False, ["Plan must contain at least one thread"])
    errors = []
    for thread_num, thread in enumerate(plan.threads, 1):
        errors.extend(_thread_errors(thread_num, thread))
    return (len(errors) == 0, errors)
