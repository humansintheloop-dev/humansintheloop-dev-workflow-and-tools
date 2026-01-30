#!/usr/bin/env python3
"""
implement-with-worktree: Automates Git worktree and GitHub Draft PR-based development.

This script orchestrates the complete lifecycle of implementing a development plan:
from creating Git infrastructure through task execution with Claude Code.
"""

import argparse
import glob
import os
import sys

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

    # For now, just print the parsed arguments (implementation will come in later tasks)
    print(f"Idea directory: {args.idea_directory}")
    print(f"Idea name: {idea_name}")
    print(f"Cleanup: {args.cleanup}")


if __name__ == "__main__":
    main()
