"""Git infrastructure setup: branch creation, worktree management."""

import os
import re
import sys

from git import Repo
from git.exc import InvalidGitRepositoryError


def validate_idea_files_committed(project) -> None:
    """Validate that all idea files are committed to Git."""
    repo = _open_repo(project.directory)
    repo_root = repo.working_tree_dir
    idea_files = [os.path.relpath(f, repo_root) for f in project.find_idea_files()]
    uncommitted = _find_uncommitted(repo, idea_files)
    if uncommitted:
        _report_uncommitted_and_exit(uncommitted)


def _open_repo(directory):
    """Open the Git repository containing the given directory."""
    try:
        return Repo(directory, search_parent_directories=True)
    except InvalidGitRepositoryError:
        print(f"Error: {directory} is not in a Git repository", file=sys.stderr)
        sys.exit(1)


def _find_uncommitted(repo, idea_files):
    """Return idea files that have uncommitted changes or are untracked."""
    changed_files = _changed_files(repo)
    untracked = set(repo.untracked_files)
    return [f for f in idea_files if f in changed_files or f in untracked]


def _changed_files(repo):
    """Return the set of files with staged or unstaged changes."""
    changed = {item.a_path for item in repo.index.diff(None)}
    try:
        changed.update(item.a_path for item in repo.index.diff("HEAD"))
    except Exception:
        pass
    return changed


def _report_uncommitted_and_exit(uncommitted):
    """Print uncommitted idea files and exit."""
    print("Error: Idea files have uncommitted changes:", file=sys.stderr)
    for f in uncommitted:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)


def sanitize_branch_name(name: str) -> str:
    """Sanitize a string for use in a Git branch name."""
    result = name.lower()
    result = re.sub(r'[^a-z0-9]+', '-', result)
    result = re.sub(r'-+', '-', result)
    return result.strip('-')


def has_ci_workflow_files(repo_path: str) -> bool:
    """Check if GitHub Actions workflow files exist in the repository."""
    workflows_dir = os.path.join(repo_path, ".github", "workflows")
    if not os.path.isdir(workflows_dir):
        return False
    for filename in os.listdir(workflows_dir):
        if filename.endswith(('.yml', '.yaml')):
            return True
    return False
