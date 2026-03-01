"""Idea name resolver: locates ideas by name across state directories."""

import os
from dataclasses import dataclass
from pathlib import Path

LIFECYCLE_STATES = ("draft", "ready", "wip", "completed", "abandoned")


@dataclass(frozen=True)
class IdeaInfo:
    name: str
    state: str
    directory: str


def resolve_idea(name: str, git_root: Path) -> IdeaInfo:
    """Find a single idea by name across all state directories.

    Raises ValueError if no match or multiple matches found.
    """
    matches = [idea for idea in list_ideas(git_root) if idea.name == name]
    if not matches:
        msg = f"Idea not found: {name}"
        raise ValueError(msg)
    if len(matches) > 1:
        states = ", ".join(m.state for m in matches)
        msg = f"Idea '{name}' found in multiple states: {states}"
        raise ValueError(msg)
    return matches[0]


def _ideas_in_state(state: str, state_dir: Path, git_root: Path) -> list[IdeaInfo]:
    """Return all ideas found in a single state directory."""
    if not state_dir.is_dir():
        return []
    return [
        IdeaInfo(name=entry, state=state, directory=str((state_dir / entry).relative_to(git_root)))
        for entry in os.listdir(state_dir)
        if (state_dir / entry).is_dir()
    ]


def list_ideas(git_root: Path) -> list[IdeaInfo]:
    """Scan all state directories and return ideas sorted alphabetically by name."""
    ideas_root = git_root / "docs" / "ideas"
    results = []
    for state in LIFECYCLE_STATES:
        results.extend(_ideas_in_state(state, ideas_root / state, git_root))
    results.sort(key=lambda idea: idea.name)
    return results
