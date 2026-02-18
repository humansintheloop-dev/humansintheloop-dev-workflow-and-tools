"""Git infrastructure setup: branch creation, worktree management, permissions."""

import glob
import json
import os
import re
import shutil
import sys

from git import Repo
from git.exc import InvalidGitRepositoryError
from typing import List


def validate_idea_files_committed(idea_directory: str, idea_name: str) -> None:
    """Validate that all idea files are committed to Git."""
    try:
        repo = Repo(idea_directory, search_parent_directories=True)
    except InvalidGitRepositoryError:
        print(f"Error: {idea_directory} is not in a Git repository", file=sys.stderr)
        sys.exit(1)

    repo_root = repo.working_tree_dir

    idea_files_patterns = [
        f"{idea_name}-idea.*",
        f"{idea_name}-discussion.md",
        f"{idea_name}-spec.md",
        f"{idea_name}-plan.md",
    ]

    idea_files = []
    for pattern in idea_files_patterns:
        matches = glob.glob(os.path.join(idea_directory, pattern))
        for match in matches:
            rel_path = os.path.relpath(match, repo_root)
            idea_files.append(rel_path)

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


def ensure_integration_branch(repo: Repo, idea_name: str, isolated: bool = False) -> str:
    """Ensure the integration branch exists, creating it if necessary."""
    branch_name = f"idea/{idea_name}/integration"
    existing_branches = [b.name for b in repo.branches]
    if branch_name not in existing_branches:
        if isolated:
            try:
                remote_ref = repo.remotes.origin.refs[branch_name]
                repo.create_head(branch_name, remote_ref)
            except (IndexError, AttributeError):
                repo.create_head(branch_name)
        else:
            repo.create_head(branch_name)
    return branch_name


def ensure_worktree(repo: Repo, idea_name: str, branch_name: str) -> str:
    """Ensure the worktree exists, creating it if necessary."""
    repo_root = repo.working_tree_dir
    repo_name = os.path.basename(repo_root)
    parent_dir = os.path.dirname(repo_root)
    worktree_path = os.path.join(parent_dir, f"{repo_name}-wt-{idea_name}")

    if not os.path.isdir(worktree_path):
        repo.git.worktree("add", worktree_path, branch_name)

    source_settings = os.path.join(repo_root, ".claude", "settings.local.json")
    if os.path.isfile(source_settings):
        dest_claude_dir = os.path.join(worktree_path, ".claude")
        os.makedirs(dest_claude_dir, exist_ok=True)
        dest_settings = os.path.join(dest_claude_dir, "settings.local.json")
        shutil.copy2(source_settings, dest_settings)

    return worktree_path


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
    result = result.strip('-')
    return result


def ensure_slice_branch(
    repo: Repo, idea_name: str, slice_number: int,
    slice_name: str, integration_branch: str,
) -> str:
    """Ensure the slice branch exists, creating it if necessary."""
    sanitized_name = sanitize_branch_name(slice_name)
    branch_name = f"idea/{idea_name}/{slice_number:02d}-{sanitized_name}"
    existing_branches = [b.name for b in repo.branches]
    if branch_name not in existing_branches:
        integration_ref = repo.heads[integration_branch]
        repo.create_head(branch_name, integration_ref)
    return branch_name


def get_worktree_idea_directory(
    worktree_path: str, main_repo_idea_dir: str, main_repo_root: str,
) -> str:
    """Compute the idea directory path within the worktree."""
    idea_relpath = os.path.relpath(main_repo_idea_dir, main_repo_root)
    return os.path.join(worktree_path, idea_relpath)


def get_next_task(plan_file: str):
    from i2code.plan.plan_file_io import with_plan_file
    with with_plan_file(plan_file) as plan:
        return plan.get_next_task()


def is_task_completed(plan_file: str, thread: int, task: int) -> bool:
    from i2code.plan.plan_file_io import with_plan_file
    with with_plan_file(plan_file) as plan:
        return plan.is_task_completed(thread, task)


def has_ci_workflow_files(repo_path: str) -> bool:
    """Check if GitHub Actions workflow files exist in the repository."""
    workflows_dir = os.path.join(repo_path, ".github", "workflows")
    if not os.path.isdir(workflows_dir):
        return False
    for filename in os.listdir(workflows_dir):
        if filename.endswith(('.yml', '.yaml')):
            return True
    return False
