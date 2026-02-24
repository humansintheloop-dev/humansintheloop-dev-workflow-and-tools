"""Worktree project setup: copy settings and run setup scripts."""

import os
import subprocess

from i2code.implement.claude_permissions import setup_claude_settings_local_json


def setup_project(dest_root, source_root=None):
    """Set up a project by copying configuration, ensuring permissions, and running setup scripts."""
    setup_claude_settings_local_json(dest_root, source_root)
    _run_setup_project_script(dest_root)


def _run_setup_project_script(project_root):
    """Run dev-scripts/setup-project.sh if it exists in the project."""
    script = os.path.join(project_root, "dev-scripts", "setup-project.sh")
    if os.path.isfile(script):
        subprocess.run([script], cwd=project_root, check=True)
