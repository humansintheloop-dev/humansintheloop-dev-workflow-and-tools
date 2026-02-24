"""Claude permissions and settings setup for worktrees."""

import json
import os
import shutil
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


def calculate_claude_permissions(repo_root: str) -> List[str]:
    """Calculate the full list of Claude permissions for a repo root."""
    return REQUIRED_PERMISSIONS + [
        f"Write(/{repo_root}/)",
        f"Edit(/{repo_root}/)",
        f"Bash(rm {repo_root}/*)",
    ]


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

    allow_list = config.get("permissions", {}).get("allow", [])
    for perm in calculate_claude_permissions(repo_root):
        if perm not in allow_list:
            allow_list.append(perm)

    config.setdefault("permissions", {})["allow"] = allow_list
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
