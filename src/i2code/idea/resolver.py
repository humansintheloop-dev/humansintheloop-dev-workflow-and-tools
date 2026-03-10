"""Idea name resolver: locates ideas by name across active/archived directories."""

import os
import warnings
from dataclasses import dataclass
from pathlib import Path

from i2code.idea.metadata import read_metadata

LIFECYCLE_STATES = ("draft", "ready", "wip", "completed", "abandoned")


@dataclass(frozen=True)
class IdeaInfo:
    name: str
    state: str
    directory: str


def resolve_idea(name: str, git_root: Path) -> IdeaInfo:
    """Find a single idea by name in active/ and archived/ directories.

    Raises ValueError if no match found.
    """
    matches = [idea for idea in list_ideas(git_root, include_archived=True) if idea.name == name]
    if not matches:
        msg = f"Idea not found: {name}"
        raise ValueError(msg)
    if len(matches) > 1:
        states = ", ".join(m.state for m in matches)
        msg = f"Idea '{name}' found in multiple states: {states}"
        raise ValueError(msg)
    return matches[0]


def _read_state_from_metadata(idea_dir: Path, name: str) -> str:
    """Read lifecycle state from an idea's metadata file.

    Returns 'unknown' and emits a warning if the metadata file is missing.
    """
    metadata_path = idea_dir / f"{name}-metadata.yaml"
    try:
        data = read_metadata(metadata_path)
        return data.get("state", "unknown")
    except FileNotFoundError:
        warnings.warn(f"Metadata file not found for idea '{name}': {metadata_path}", stacklevel=2)
        return "unknown"


def _ideas_in_location(location_dir: Path, git_root: Path) -> list[IdeaInfo]:
    """Return all ideas found in a location directory (active/ or archived/)."""
    if not location_dir.is_dir():
        return []
    results = []
    for entry in os.listdir(location_dir):
        entry_path = location_dir / entry
        if entry_path.is_dir():
            state = _read_state_from_metadata(entry_path, entry)
            directory = str(entry_path.relative_to(git_root))
            results.append(IdeaInfo(name=entry, state=state, directory=directory))
    return results


_IDEAS_PREFIX = ("docs", "ideas")


def _find_state_in_parts(parts):
    """Search path parts for a 'docs/ideas/{state}' sequence."""
    triplets = zip(parts, parts[1:], parts[2:])
    for first, second, third in triplets:
        if (first, second) == _IDEAS_PREFIX and third in LIFECYCLE_STATES:
            return third
    return None


def state_from_path(path: Path) -> str:
    """Extract the lifecycle state from an idea directory path.

    Deprecated: Use metadata files instead. Will be removed in a future version.
    """
    result = _find_state_in_parts(path.resolve().parts)
    if result is not None:
        return result
    msg = f"Cannot determine lifecycle state from path: {path}"
    raise ValueError(msg)


def _ideas_in_legacy_state_dir(state: str, state_dir: Path, git_root: Path) -> list[IdeaInfo]:
    """Return ideas from a legacy state directory (docs/ideas/{state}/)."""
    if not state_dir.is_dir():
        return []
    return [
        IdeaInfo(name=entry, state=state, directory=str((state_dir / entry).relative_to(git_root)))
        for entry in os.listdir(state_dir)
        if (state_dir / entry).is_dir()
    ]


def list_ideas(git_root: Path, *, include_archived: bool = False) -> list[IdeaInfo]:
    """Scan active/ (and optionally archived/) directories and return ideas sorted by name.

    Also scans legacy state directories for backward compatibility.
    """
    ideas_root = git_root / "docs" / "ideas"
    results = list(_ideas_in_location(ideas_root / "active", git_root))
    if include_archived:
        results.extend(_ideas_in_location(ideas_root / "archived", git_root))
    # Legacy: scan old state directories for backward compatibility
    for state in LIFECYCLE_STATES:
        results.extend(_ideas_in_legacy_state_dir(state, ideas_root / state, git_root))
    results.sort(key=lambda idea: idea.name)
    return results
