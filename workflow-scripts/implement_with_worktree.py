#!/usr/bin/env python3
"""
implement-with-worktree: Automates Git worktree and GitHub Draft PR-based development.

This script orchestrates the complete lifecycle of implementing a development plan:
from creating Git infrastructure through task execution with Claude Code.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from typing import Dict, Any, Optional, List

from git import Repo
from git.exc import InvalidGitRepositoryError


def validate_idea_directory(idea_directory: str) -> str:
    """Validate that the idea directory exists and return the idea name.

    Args:
        idea_directory: Path to the idea directory

    Returns:
        The idea name (last component of the path)

    Raises:
        SystemExit: If the directory does not exist
    """
    if not os.path.isdir(idea_directory):
        print(f"Error: Directory not found: {idea_directory}", file=sys.stderr)
        sys.exit(1)

    idea_name = os.path.basename(os.path.normpath(idea_directory))
    return idea_name


def validate_idea_files(idea_directory: str, idea_name: str) -> None:
    """Validate that all required idea files exist.

    Required files:
    - <idea-name>-idea.md or <idea-name>-idea.txt
    - <idea-name>-discussion.md
    - <idea-name>-spec.md
    - <idea-name>-plan.md

    Args:
        idea_directory: Path to the idea directory
        idea_name: Name of the idea (used for file naming)

    Raises:
        SystemExit: If any required files are missing
    """
    missing_files = []

    # Check for idea file (can be .md or .txt)
    idea_pattern = os.path.join(idea_directory, f"{idea_name}-idea.*")
    idea_files = glob.glob(idea_pattern)
    if not idea_files:
        missing_files.append(f"{idea_name}-idea.md (or .txt)")

    # Check for other required files
    for suffix in ["discussion.md", "spec.md", "plan.md"]:
        filepath = os.path.join(idea_directory, f"{idea_name}-{suffix}")
        if not os.path.isfile(filepath):
            missing_files.append(f"{idea_name}-{suffix}")

    if missing_files:
        print(f"Error: Missing required idea files in {idea_directory}:", file=sys.stderr)
        for f in missing_files:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)


def validate_idea_files_committed(idea_directory: str, idea_name: str) -> None:
    """Validate that all idea files are committed to Git.

    Args:
        idea_directory: Path to the idea directory
        idea_name: Name of the idea (used for file naming)

    Raises:
        SystemExit: If any idea files have uncommitted changes or are untracked
    """
    try:
        # Find the git repository root by searching up from idea_directory
        repo = Repo(idea_directory, search_parent_directories=True)
    except InvalidGitRepositoryError:
        print(f"Error: {idea_directory} is not in a Git repository", file=sys.stderr)
        sys.exit(1)

    repo_root = repo.working_tree_dir

    # Build list of idea file patterns to check
    idea_files_patterns = [
        f"{idea_name}-idea.*",
        f"{idea_name}-discussion.md",
        f"{idea_name}-spec.md",
        f"{idea_name}-plan.md",
    ]

    # Get all files in the idea directory that match our patterns
    idea_files = []
    for pattern in idea_files_patterns:
        matches = glob.glob(os.path.join(idea_directory, pattern))
        for match in matches:
            rel_path = os.path.relpath(match, repo_root)
            idea_files.append(rel_path)

    # Check for uncommitted changes using GitPython
    uncommitted = []

    # Check for modified files (staged or unstaged)
    changed_files = [item.a_path for item in repo.index.diff(None)]  # Unstaged changes

    # Check staged changes - but only if there are commits (HEAD exists)
    try:
        changed_files += [item.a_path for item in repo.index.diff("HEAD")]
    except Exception:
        # No commits yet - all tracked files are staged but not committed
        pass

    # Check for untracked files
    untracked = repo.untracked_files

    for idea_file in idea_files:
        if idea_file in changed_files:
            uncommitted.append(idea_file)
        elif idea_file in untracked:
            uncommitted.append(idea_file)

    if uncommitted:
        print(f"Error: Idea files have uncommitted changes:", file=sys.stderr)
        for f in uncommitted:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)


def get_state_file_path(idea_directory: str, idea_name: str) -> str:
    """Return the path to the state file for the given idea."""
    return os.path.join(idea_directory, f"{idea_name}-wt-state.json")


def init_or_load_state(idea_directory: str, idea_name: str) -> Dict[str, Any]:
    """Initialize or load the state file.

    If the state file doesn't exist, creates it with default values.
    If it exists, loads and returns its contents.

    Args:
        idea_directory: Path to the idea directory
        idea_name: Name of the idea

    Returns:
        Dictionary containing the state
    """
    state_file = get_state_file_path(idea_directory, idea_name)

    if os.path.isfile(state_file):
        with open(state_file, "r") as f:
            return json.load(f)

    # Default state for new file
    default_state = {
        "slice_number": 1,
        "processed_comment_ids": [],
        "processed_review_ids": []
    }

    # Write default state to file
    with open(state_file, "w") as f:
        json.dump(default_state, f, indent=2)

    return default_state


def save_state(idea_directory: str, idea_name: str, state: Dict[str, Any]) -> None:
    """Save the state to the state file.

    Args:
        idea_directory: Path to the idea directory
        idea_name: Name of the idea
        state: State dictionary to save
    """
    state_file = get_state_file_path(idea_directory, idea_name)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def ensure_integration_branch(repo: Repo, idea_name: str) -> str:
    """Ensure the integration branch exists, creating it if necessary.

    Args:
        repo: GitPython Repo object
        idea_name: Name of the idea

    Returns:
        The integration branch name
    """
    branch_name = f"idea/{idea_name}/integration"

    # Check if branch already exists
    existing_branches = [b.name for b in repo.branches]
    if branch_name not in existing_branches:
        # Create the branch from current HEAD
        repo.create_head(branch_name)

    return branch_name


def ensure_worktree(repo: Repo, idea_name: str, branch_name: str) -> str:
    """Ensure the worktree exists, creating it if necessary.

    Args:
        repo: GitPython Repo object
        idea_name: Name of the idea
        branch_name: Branch to checkout in the worktree

    Returns:
        The absolute path to the worktree directory
    """
    # Get repo name from working directory
    repo_root = repo.working_tree_dir
    repo_name = os.path.basename(repo_root)
    parent_dir = os.path.dirname(repo_root)

    # Worktree path: ../<repo-name>-wt-<idea-name>
    worktree_path = os.path.join(parent_dir, f"{repo_name}-wt-{idea_name}")

    # Check if worktree already exists by checking if the directory exists
    # and is a valid worktree (has .git file pointing to main repo)
    if not os.path.isdir(worktree_path):
        # Create the worktree
        repo.git.worktree("add", worktree_path, branch_name)

    return worktree_path


def sanitize_branch_name(name: str) -> str:
    """Sanitize a string for use in a Git branch name.

    Args:
        name: The string to sanitize

    Returns:
        A sanitized string suitable for a branch name
    """
    # Convert to lowercase
    result = name.lower()
    # Replace any non-alphanumeric characters with dashes
    result = re.sub(r'[^a-z0-9]+', '-', result)
    # Collapse multiple dashes
    result = re.sub(r'-+', '-', result)
    # Strip leading and trailing dashes
    result = result.strip('-')
    return result


def ensure_slice_branch(
    repo: Repo,
    idea_name: str,
    slice_number: int,
    slice_name: str,
    integration_branch: str
) -> str:
    """Ensure the slice branch exists, creating it if necessary.

    Args:
        repo: GitPython Repo object
        idea_name: Name of the idea
        slice_number: The slice number (will be zero-padded)
        slice_name: Name for this slice (will be sanitized)
        integration_branch: The integration branch to create from

    Returns:
        The slice branch name
    """
    sanitized_name = sanitize_branch_name(slice_name)
    branch_name = f"idea/{idea_name}/{slice_number:02d}-{sanitized_name}"

    # Check if branch already exists
    existing_branches = [b.name for b in repo.branches]
    if branch_name not in existing_branches:
        # Create the branch from integration branch
        integration_ref = repo.heads[integration_branch]
        repo.create_head(branch_name, integration_ref)

    return branch_name


# GitHub PR Management Functions

def generate_pr_title(idea_name: str, slice_branch_suffix: str) -> str:
    """Generate a PR title from idea name and slice branch suffix.

    Args:
        idea_name: Name of the idea
        slice_branch_suffix: The slice part of the branch name (e.g., "01-project-setup")

    Returns:
        PR title string
    """
    return f"[{idea_name}] {slice_branch_suffix}"


def generate_pr_body(idea_directory: str, idea_name: str, slice_number: int) -> str:
    """Generate a PR body with idea directory reference.

    Args:
        idea_directory: Path to the idea directory
        idea_name: Name of the idea
        slice_number: Current slice number

    Returns:
        PR body markdown string
    """
    return f"""## Slice #{slice_number} for {idea_name}

**Idea directory:** `{idea_directory}`

This PR implements slice #{slice_number} of the development plan.
"""


def find_existing_pr(branch_name: str) -> Optional[int]:
    """Find an existing PR for the given branch.

    Args:
        branch_name: The branch name to search for

    Returns:
        PR number if found, None otherwise
    """
    result = subprocess.run(
        ["gh", "pr", "list", "--json", "number,headRefName,isDraft", "--state", "open"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    prs = json.loads(result.stdout)
    for pr in prs:
        if pr.get("headRefName") == branch_name:
            return pr.get("number")

    return None


def is_pr_draft(pr_number: int) -> bool:
    """Check if a PR is in draft state.

    Args:
        pr_number: The PR number to check

    Returns:
        True if PR is draft, False if ready for review
    """
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "isDraft"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return False

    data = json.loads(result.stdout)
    return data.get("isDraft", False)


# Task Parsing Functions

def parse_tasks_from_plan(plan_content: str) -> List[str]:
    """Parse uncompleted top-level tasks from a plan file content.

    Tasks are identified by lines starting with "- [ ]" (uncompleted checkbox)
    and containing bold text (** markers), which distinguishes main tasks from subtasks.

    Args:
        plan_content: The full content of the plan file

    Returns:
        List of task descriptions (the text after the checkbox)
    """
    tasks = []
    # Match lines that start with "- [ ]" and contain bold text (**...**)
    # This distinguishes main tasks from subtasks
    pattern = r'^- \[ \] (\*\*.+\*\*.*)$'

    for line in plan_content.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            task_text = match.group(1)
            tasks.append(task_text)

    return tasks


def get_first_task_name(plan_content: str) -> str:
    """Get the name of the first uncompleted task for slice naming.

    Args:
        plan_content: The full content of the plan file

    Returns:
        The first task name, or "implementation" if no tasks found
    """
    tasks = parse_tasks_from_plan(plan_content)
    if not tasks:
        return "implementation"

    # Extract a usable name from the task description
    # Remove markdown formatting like **bold**
    task = tasks[0]
    task = re.sub(r'\*\*([^*]+)\*\*', r'\1', task)

    # Try to extract the task title (after "Task X.X:")
    title_match = re.search(r'Task \d+\.\d+:\s*(.+)', task)
    if title_match:
        return title_match.group(1).strip()

    return task.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Implement a development plan using Git worktrees and GitHub Draft PRs"
    )
    parser.add_argument(
        "idea_directory",
        metavar="idea-directory",
        help="Path to idea directory (e.g., docs/features/my-feature)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Perform cleanup (remove worktree, delete local branches) after PR is merged/closed"
    )

    args = parser.parse_args()

    # Validate idea directory exists
    idea_name = validate_idea_directory(args.idea_directory)

    # Validate required idea files exist
    validate_idea_files(args.idea_directory, idea_name)

    # Validate idea files are committed to Git
    validate_idea_files_committed(args.idea_directory, idea_name)

    # Initialize or load state
    state = init_or_load_state(args.idea_directory, idea_name)

    # For now, just print the parsed arguments (implementation will come in later tasks)
    print(f"Idea directory: {args.idea_directory}")
    print(f"Idea name: {idea_name}")
    print(f"Cleanup: {args.cleanup}")
    print(f"State: {state}")


if __name__ == "__main__":
    main()
