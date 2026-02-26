"""Validate required fields in plan task blocks.

Rewrites the AWK validation logic from scripts/make-plan.sh:22-66 in Python.
Each task block (``- [ ] **Task X.Y: ...`` or ``- [x] **Task X.Y: ...``)
must contain TaskType, Entrypoint, Observable, and Evidence fields.
"""

import re

_TASK_HEADER_RE = re.compile(r"^- \[[ x]\] \*\*Task (\d+\.\d+):")

_REQUIRED_FIELDS = ("TaskType", "Entrypoint", "Observable", "Evidence")

_FIELD_PATTERNS = {
    field: re.compile(rf"^\s*- {field}:") for field in _REQUIRED_FIELDS
}


def validate_plan(plan_text: str) -> tuple[bool, list[str]]:
    """Validate that every task block contains the required contract fields.

    Returns ``(True, [])`` when valid, or ``(False, [error_messages])`` when
    one or more tasks are missing required fields.
    """
    errors: list[str] = []
    current_task: str | None = None
    found_fields: set[str] = set()

    def check_current_task() -> None:
        if current_task is None:
            return
        for field in _REQUIRED_FIELDS:
            if field not in found_fields:
                errors.append(f"Missing {field} in {current_task}")

    for line in plan_text.splitlines():
        header_match = _TASK_HEADER_RE.match(line)
        if header_match:
            check_current_task()
            current_task = f"Task {header_match.group(1)}"
            found_fields = set()
            continue

        if current_task is not None:
            for field, pattern in _FIELD_PATTERNS.items():
                if pattern.match(line):
                    found_fields.add(field)

    check_current_task()

    return (len(errors) == 0, errors)
