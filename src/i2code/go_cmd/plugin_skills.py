"""Enumerate installed idea-to-code plugin skills."""

import os
import sys
from pathlib import Path


def list_plugin_skills(cache_dir=None):
    """List installed idea-to-code plugin skills as comma-separated names.

    Searches cache_dir (or $PLUGIN_CACHE_DIR, default ~/.claude/plugins/cache)
    for the idea-to-code plugin. Returns skill names prefixed with
    "idea-to-code:" in comma-separated format. Prints a warning to stderr
    if the plugin is not found.
    """
    if cache_dir is None:
        cache_dir = os.environ.get(
            "PLUGIN_CACHE_DIR",
            os.path.expanduser("~/.claude/plugins/cache"),
        )

    cache_path = Path(cache_dir)
    skills_dir = _find_skills_dir(cache_path)

    if skills_dir is None:
        print(f"Warning: idea-to-code plugin not found in {cache_dir}", file=sys.stderr)
        return ""

    skill_names = sorted(
        entry.name for entry in skills_dir.iterdir() if entry.is_dir()
    )

    return ", ".join(f"idea-to-code:{name}" for name in skill_names)


def _find_skills_dir(cache_path):
    """Find the skills directory under an idea-to-code plugin in cache_path."""
    if not cache_path.is_dir():
        return None

    for path in cache_path.rglob("skills"):
        if path.is_dir() and "idea-to-code" in str(path):
            return path

    return None
