"""ProjectSetup: copy settings and run setup scripts for worktrees and clones."""

import os
import subprocess

from i2code.implement.claude_permissions import setup_claude_settings_local_json


class ProjectSetup:
    """Handles project setup for worktrees and clones."""

    def setup_worktree(self, git_repo):
        """Set up a worktree project — skips if not a worktree."""
        if not git_repo.is_worktree:
            return
        self._setup(git_repo)

    def setup_clone(self, git_repo):
        """Set up a clone — always runs regardless of is_worktree."""
        self._setup(git_repo)

    def _setup(self, git_repo):
        setup_claude_settings_local_json(git_repo.working_tree_dir, git_repo.main_repo_dir)
        _run_setup_project_script(git_repo.working_tree_dir)


def _run_setup_project_script(project_root):
    """Run dev-scripts/setup-project.sh if it exists in the project."""
    script = os.path.join(project_root, "dev-scripts", "setup-project.sh")
    if os.path.isfile(script):
        subprocess.run([script], cwd=project_root, check=True)
