"""Git infrastructure setup: branch creation, worktree management, permissions."""

import json
import os
import re
import sys

from git import Repo
from git.exc import InvalidGitRepositoryError
from typing import List


def validate_idea_files_committed(project) -> None:
    """Validate that all idea files are committed to Git."""
    try:
        repo = Repo(project.directory, search_parent_directories=True)
    except InvalidGitRepositoryError:
        print(f"Error: {project.directory} is not in a Git repository", file=sys.stderr)
        sys.exit(1)

    repo_root = repo.working_tree_dir

    idea_files = [
        os.path.relpath(f, repo_root) for f in project.find_idea_files()
    ]

    uncommitted = []
    changed_files = [item.a_path for item in repo.index.diff(None)]
    try:
        changed_files += [item.a_path for item in repo.index.diff("HEAD")]
    except Exception:
        pass

    untracked = repo.untracked_files

    for idea_file in idea_files:
        if idea_file in changed_files:
            uncommitted.append(idea_file)
        elif idea_file in untracked:
            uncommitted.append(idea_file)

    if uncommitted:
        print("Error: Idea files have uncommitted changes:", file=sys.stderr)
        for f in uncommitted:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)



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
