"""Worktree project setup: copy settings and run setup scripts."""

import os
import subprocess

from i2code.implement.claude_permissions import setup_claude_settings_local_json


def setup_project(git_repo):
    """Set up a project by copying configuration, ensuring permissions, and running setup scripts."""
    if not git_repo.is_worktree:
        return
    setup_claude_settings_local_json(git_repo.working_tree_dir, git_repo.main_repo_dir)
    _run_setup_project_script(git_repo.working_tree_dir)


def _run_setup_project_script(project_root):
    """Run dev-scripts/setup-project.sh if it exists in the project."""
    script = os.path.join(project_root, "dev-scripts", "setup-project.sh")
    if os.path.isfile(script):
        subprocess.run([script], cwd=project_root, check=True)
