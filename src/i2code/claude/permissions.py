"""Claude Code permissions: allowed tools, settings setup, and worktree permissions."""

import json
import os
import shutil
from pathlib import Path
from typing import List


REQUIRED_PERMISSIONS = [
    "Bash(git commit:*)",
    "Bash(git check-ignore:*)",
    "Bash(mkdir -p:*)",
    "Bash(./test-scripts/test-*.sh)",
    "Bash(docker compose config:*)",
    "Bash(java -version)",
    "Bash(gradle --version)",
    "Bash(i2code:*)",
]

DENIED_PERMISSIONS = [
    "Bash(git push:*)",
]


def _resolve_path(path: str) -> str:
    """Resolve a path to an absolute filesystem path."""
    return str(Path(path).resolve())


def build_read_only_tools_flag(repo_root: str) -> str:
    """Build the --allowedTools flag value granting only Read access.

    Used for batch-mode commands where Claude should output to stdout
    rather than writing files directly.
    """
    repo = _resolve_path(repo_root)
    return f"Read(/{repo}/**)"


def build_allowed_tools_flag(repo_root: str, idea_dir: str) -> str:
    """Build the --allowedTools flag value for claude CLI.

    Returns a comma-separated string granting Read access to the repo root
    and Write/Edit access to the idea directory.
    Uses / prefix for absolute paths per Claude Code permission syntax.
    """
    repo = _resolve_path(repo_root)
    idea = _resolve_path(idea_dir)
    return (
        f"Read(/{repo}/**),"
        f"Write(/{idea}/**),"
        f"Edit(/{idea}/**)"
    )


def calculate_claude_permissions(repo_root: str) -> List[str]:
    """Calculate the full list of Claude permissions for a repo root."""
    return REQUIRED_PERMISSIONS + [
        f"Write(/{repo_root}/**)",
        f"Edit(/{repo_root}/**)",
        f"Bash(rm {repo_root}/*)",
    ]


def _merge_permissions(existing: List[str], required: List[str]) -> List[str]:
    """Merge required permissions into an existing list, preserving order."""
    for perm in required:
        if perm not in existing:
            existing.append(perm)
    return existing


def ensure_claude_permissions(repo_root: str) -> None:
    """Ensure .claude/settings.local.json has required permissions."""
    settings_dir = os.path.join(repo_root, ".claude")
    settings_file = os.path.join(settings_dir, "settings.local.json")

    if os.path.isfile(settings_file):
        with open(settings_file, "r") as f:
            config = json.load(f)
    else:
        os.makedirs(settings_dir, exist_ok=True)
        config = {}

    permissions = config.setdefault("permissions", {})
    permissions["allow"] = _merge_permissions(permissions.get("allow", []), calculate_claude_permissions(repo_root))
    permissions["deny"] = _merge_permissions(permissions.get("deny", []), DENIED_PERMISSIONS)
    with open(settings_file, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def setup_claude_settings_local_json(dest_root, source_root=None):
    """Copy settings.local.json from source (if provided) and ensure Claude permissions."""
    copy_source_settings(dest_root, source_root)
    ensure_claude_permissions(dest_root)


def copy_source_settings(dest_root, source_root=None):
    """Copy .claude/settings.local.json from source to dest if source_root is provided."""
    if source_root is not None:
        _copy_settings_local_json(source_root, dest_root)


def _copy_settings_local_json(source_root, dest_root):
    """Copy .claude/settings.local.json from source to destination if it exists."""
    source_settings = os.path.join(source_root, ".claude", "settings.local.json")
    if os.path.isfile(source_settings):
        dest_claude_dir = os.path.join(dest_root, ".claude")
        os.makedirs(dest_claude_dir, exist_ok=True)
        dest_settings = os.path.join(dest_claude_dir, "settings.local.json")
        shutil.copy2(source_settings, dest_settings)
