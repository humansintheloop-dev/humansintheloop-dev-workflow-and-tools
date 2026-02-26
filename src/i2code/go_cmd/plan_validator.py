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


def _find_matching_field(line: str) -> str | None:
    """Return the field name if *line* matches a required field pattern."""
    for field, pattern in _FIELD_PATTERNS.items():
        if pattern.match(line):
            return field
    return None


def _collect_field(line: str, found_fields: set[str]) -> None:
    """Add the matching field (if any) from *line* to *found_fields*."""
    field = _find_matching_field(line)
    if field:
        found_fields.add(field)


def _missing_fields_errors(task_id: str, found_fields: set[str]) -> list[str]:
    """Return error messages for each required field missing from *found_fields*."""
    return [f"Missing {field} in {task_id}" for field in _REQUIRED_FIELDS if field not in found_fields]


def _parse_task_blocks(plan_text: str) -> list[tuple[str, set[str]]]:
    """Parse *plan_text* into a list of ``(task_id, found_fields)`` tuples."""
    blocks: list[tuple[str, set[str]]] = []
    current_task: str | None = None
    found_fields: set[str] = set()

    for line in plan_text.splitlines():
        header_match = _TASK_HEADER_RE.match(line)
        if header_match:
            if current_task is not None:
                blocks.append((current_task, found_fields))
            current_task = f"Task {header_match.group(1)}"
            found_fields = set()
        elif current_task is not None:
            _collect_field(line, found_fields)

    if current_task is not None:
        blocks.append((current_task, found_fields))

    return blocks


def validate_plan(plan_text: str) -> tuple[bool, list[str]]:
    """Validate that every task block contains the required contract fields.

    Returns ``(True, [])`` when valid, or ``(False, [error_messages])`` when
    one or more tasks are missing required fields.
    """
    errors: list[str] = []
    for task_id, found_fields in _parse_task_blocks(plan_text):
        errors.extend(_missing_fields_errors(task_id, found_fields))
    return (len(errors) == 0, errors)
