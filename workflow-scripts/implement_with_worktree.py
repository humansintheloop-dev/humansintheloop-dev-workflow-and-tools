#!/usr/bin/env python3
"""
implement-with-worktree: Automates Git worktree and GitHub Draft PR-based development.

This script orchestrates the complete lifecycle of implementing a development plan:
from creating Git infrastructure through task execution with Claude Code.
"""

import argparse
import os
import sys


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

    # For now, just print the parsed arguments (implementation will come in later tasks)
    print(f"Idea directory: {args.idea_directory}")
    print(f"Idea name: {idea_name}")
    print(f"Cleanup: {args.cleanup}")


if __name__ == "__main__":
    main()
