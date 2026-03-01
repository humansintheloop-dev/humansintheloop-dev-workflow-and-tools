"""Transition rule engine for idea lifecycle state changes."""

from pathlib import Path

from i2code.idea_resolver import LIFECYCLE_STATES

_ORDERED_STATES = [s for s in LIFECYCLE_STATES if s != "abandoned"]


def validate_transition(old_state: str, new_state: str, idea_dir: Path) -> str | None:
    """Validate a state transition and return an error message if blocked.

    Returns None if the transition is allowed, or a string describing
    the violated rule if blocked.
    """
    if new_state == "abandoned":
        return None

    old_idx = _ORDERED_STATES.index(old_state) if old_state in _ORDERED_STATES else -1
    new_idx = _ORDERED_STATES.index(new_state) if new_state in _ORDERED_STATES else -1

    if new_idx < old_idx:
        return (
            f"Backward transition from {old_state} to {new_state} is not allowed"
        )

    if new_idx > old_idx + 1:
        return (
            f"Skipping states from {old_state} to {new_state} is not allowed"
        )

    if _requires_plan(old_state, new_state) and not _has_plan(idea_dir):
        return (
            f"Transition from {old_state} to {new_state} requires a plan file"
        )

    return None


def _requires_plan(old_state: str, new_state: str) -> bool:
    return (old_state, new_state) in {("draft", "ready"), ("ready", "wip")}


def _has_plan(idea_dir: Path) -> bool:
    return any(idea_dir.glob("*-plan.md"))
