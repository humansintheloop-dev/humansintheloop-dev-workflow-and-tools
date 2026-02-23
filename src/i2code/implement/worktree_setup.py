"""Worktree project setup: copy settings and run setup scripts."""

import os
import shutil
import subprocess

from i2code.implement.git_setup import ensure_claude_permissions


def setup_project(dest_root, source_root=None):
    """Set up a project by copying configuration, ensuring permissions, and running setup scripts."""
    if source_root is not None:
        _copy_settings_local_json(source_root, dest_root)
    ensure_claude_permissions(dest_root)
    _run_setup_project_script(dest_root)


def _copy_settings_local_json(source_root, dest_root):
    """Copy .claude/settings.local.json from source to destination if it exists."""
    source_settings = os.path.join(source_root, ".claude", "settings.local.json")
    if os.path.isfile(source_settings):
        dest_claude_dir = os.path.join(dest_root, ".claude")
        os.makedirs(dest_claude_dir, exist_ok=True)
        dest_settings = os.path.join(dest_claude_dir, "settings.local.json")
        shutil.copy2(source_settings, dest_settings)


def _run_setup_project_script(project_root):
    """Run dev-scripts/setup-project.sh if it exists in the project."""
    script = os.path.join(project_root, "dev-scripts", "setup-project.sh")
    if os.path.isfile(script):
        subprocess.run([script], cwd=project_root, check=True)
