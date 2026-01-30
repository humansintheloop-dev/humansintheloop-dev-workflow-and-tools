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


def create_draft_pr(
    slice_branch: str,
    title: str,
    body: str,
    base_branch: str = "main"
) -> Optional[int]:
    """Create a Draft PR for the slice branch.

    Args:
        slice_branch: The head branch for the PR
        title: PR title
        body: PR body/description
        base_branch: The base branch to merge into

    Returns:
        PR number if created, None if failed
    """
    result = subprocess.run(
        ["gh", "pr", "create",
         "--draft",
         "--title", title,
         "--body", body,
         "--head", slice_branch,
         "--base", base_branch],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error creating PR: {result.stderr}", file=sys.stderr)
        return None

    # Parse PR number from output URL (e.g., https://github.com/owner/repo/pull/123)
    url = result.stdout.strip()
    try:
        pr_number = int(url.split("/")[-1])
        return pr_number
    except (ValueError, IndexError):
        return None


def ensure_draft_pr(
    slice_branch: str,
    idea_directory: str,
    idea_name: str,
    slice_number: int
) -> Optional[int]:
    """Ensure a Draft PR exists for the slice branch.

    Creates a new Draft PR if none exists, otherwise returns the existing PR number.

    Args:
        slice_branch: The slice branch name
        idea_directory: Path to the idea directory
        idea_name: Name of the idea
        slice_number: Current slice number

    Returns:
        PR number if exists or created, None if failed
    """
    # Check for existing PR
    existing_pr = find_existing_pr(slice_branch)
    if existing_pr is not None:
        print(f"Reusing existing PR #{existing_pr}")
        return existing_pr

    # Generate PR title and body
    slice_suffix = slice_branch.split("/")[-1]  # e.g., "01-project-setup"
    title = generate_pr_title(idea_name, slice_suffix)
    body = generate_pr_body(idea_directory, idea_name, slice_number)

    # Create new Draft PR
    pr_number = create_draft_pr(slice_branch, title, body)
    if pr_number:
        print(f"Created Draft PR #{pr_number}")
    return pr_number


def push_branch_to_remote(branch_name: str) -> bool:
    """Push a branch to the remote origin.

    Args:
        branch_name: The branch name to push

    Returns:
        True if push succeeded, False otherwise
    """
    result = subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error pushing branch: {result.stderr}", file=sys.stderr)
        return False

    return True


# Feedback Detection Functions

def fetch_pr_comments(pr_number: int) -> List[Dict[str, Any]]:
    """Fetch comments on a PR from GitHub API.

    Args:
        pr_number: The PR number to fetch comments for

    Returns:
        List of comment dictionaries with 'id' and 'body' fields
    """
    result = subprocess.run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments",
         "--jq", "."],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return []

    return json.loads(result.stdout)


def fetch_pr_reviews(pr_number: int) -> List[Dict[str, Any]]:
    """Fetch reviews on a PR from GitHub API.

    Args:
        pr_number: The PR number to fetch reviews for

    Returns:
        List of review dictionaries with 'id' and 'state' fields
    """
    result = subprocess.run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/reviews",
         "--jq", "."],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return []

    return json.loads(result.stdout)


def get_new_feedback(
    all_feedback: List[Dict[str, Any]],
    processed_ids: List[int]
) -> List[Dict[str, Any]]:
    """Filter feedback to only include items not yet processed.

    Args:
        all_feedback: List of feedback items (comments or reviews)
        processed_ids: List of IDs that have already been processed

    Returns:
        List of feedback items with IDs not in processed_ids
    """
    return [f for f in all_feedback if f.get("id") not in processed_ids]


def fetch_failed_checks(pr_number: int) -> List[Dict[str, Any]]:
    """Fetch failed status checks for a PR.

    Args:
        pr_number: The PR number to check

    Returns:
        List of failed check dictionaries with 'name' field
    """
    result = subprocess.run(
        ["gh", "pr", "checks", str(pr_number), "--json", "name,state",
         "--jq", '.[] | "\\(.name)\\t\\(.state)"'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    failed = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) >= 2:
            name, state = parts[0], parts[1]
            if state.lower() == "fail":
                failed.append({"name": name, "state": state})

    return failed


# Main Branch Advancement Functions

def has_main_advanced(original_head: str, current_head: str) -> bool:
    """Check if the main branch has advanced since we started.

    Args:
        original_head: The HEAD SHA of main at start
        current_head: The current HEAD SHA of main

    Returns:
        True if main has new commits, False otherwise
    """
    return original_head != current_head


def get_remote_main_head(remote: str = "origin", branch: str = "main") -> str:
    """Get the current HEAD SHA of the remote main branch.

    Fetches from the remote first to ensure we have the latest refs.

    Args:
        remote: The remote name (default: "origin")
        branch: The branch name (default: "main")

    Returns:
        The SHA of the remote main branch HEAD
    """
    # Fetch from remote first
    subprocess.run(
        ["git", "fetch", remote, branch],
        capture_output=True,
        text=True
    )

    # Get the HEAD SHA using ls-remote
    result = subprocess.run(
        ["git", "ls-remote", remote, f"refs/heads/{branch}"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 or not result.stdout.strip():
        return ""

    # Output format: "SHA\trefs/heads/branch"
    return result.stdout.split()[0]


def rebase_integration_branch(integration_branch: str, base_branch: str = "main") -> bool:
    """Attempt to rebase the integration branch onto the updated main.

    If rebase has conflicts, aborts the rebase and returns False.

    Args:
        integration_branch: The integration branch name
        base_branch: The branch to rebase onto (default: "main")

    Returns:
        True if rebase succeeded, False if there were conflicts
    """
    # Checkout integration branch first
    subprocess.run(
        ["git", "checkout", integration_branch],
        capture_output=True,
        text=True
    )

    # Attempt rebase
    result = subprocess.run(
        ["git", "rebase", f"origin/{base_branch}"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # Rebase failed, abort it
        subprocess.run(
            ["git", "rebase", "--abort"],
            capture_output=True,
            text=True
        )
        return False

    return True


def update_slice_after_rebase(slice_branch: str) -> bool:
    """Force push the slice branch after a successful rebase.

    Args:
        slice_branch: The slice branch name

    Returns:
        True if push succeeded, False otherwise
    """
    result = subprocess.run(
        ["git", "push", "--force-with-lease", "origin", slice_branch],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def get_rebase_conflict_message(integration_branch: str) -> str:
    """Generate a message explaining rebase conflict and how to resolve it.

    Args:
        integration_branch: The integration branch that had conflicts

    Returns:
        A human-readable message with instructions
    """
    return f"""
Rebase conflict detected on {integration_branch}!

The main branch has advanced and there are conflicts that require manual resolution.

To resolve:
1. Navigate to the worktree directory
2. Run: git rebase origin/main
3. Resolve the conflicts in each file
4. Run: git add <resolved-files>
5. Run: git rebase --continue
6. Re-run this script to continue

The script will now pause. Press Enter when ready to exit, or Ctrl+C to abort.
"""


# PR Completion Functions

def mark_pr_ready(pr_number: int) -> bool:
    """Mark a PR as ready for review (convert from Draft to Ready).

    Args:
        pr_number: The PR number to mark as ready

    Returns:
        True if successful, False otherwise
    """
    result = subprocess.run(
        ["gh", "pr", "ready", str(pr_number)],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def get_pr_state(pr_number: int) -> str:
    """Get the current state of a PR (OPEN, MERGED, or CLOSED).

    Args:
        pr_number: The PR number to check

    Returns:
        The PR state string, or empty string on error
    """
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "state"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return ""

    data = json.loads(result.stdout)
    return data.get("state", "")


def is_pr_complete(state: str) -> bool:
    """Check if a PR state indicates completion.

    Args:
        state: The PR state (OPEN, MERGED, or CLOSED)

    Returns:
        True if PR is merged or closed, False if still open
    """
    return state in ("MERGED", "CLOSED")


# Cleanup Functions

def remove_worktree(worktree_path: str) -> bool:
    """Remove a git worktree.

    Args:
        worktree_path: Path to the worktree to remove

    Returns:
        True if successful, False otherwise
    """
    result = subprocess.run(
        ["git", "worktree", "remove", worktree_path],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def delete_local_branch(branch_name: str) -> bool:
    """Delete a local git branch.

    Args:
        branch_name: Name of the branch to delete

    Returns:
        True if successful, False otherwise
    """
    result = subprocess.run(
        ["git", "branch", "-D", branch_name],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


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


# Claude Invocation Functions

def build_claude_command(
    idea_directory: str,
    task_description: str,
    prompt_template: str
) -> List[str]:
    """Build the command to invoke Claude Code for a task.

    Args:
        idea_directory: Path to the idea directory
        task_description: The task to implement
        prompt_template: Name of the prompt template file

    Returns:
        Command as a list suitable for subprocess
    """
    # Build the prompt that will be passed to Claude
    prompt = f"""You are implementing the following application:

* Idea: @{idea_directory}/*-idea.*
* Specification: @{idea_directory}/*-spec.md
* Implementation tasks: @{idea_directory}/*-plan.md

Your task:

{task_description}

Follow the active TDD and plan-tracking skills:

Do not work on future tasks until the current one is complete.
If all tasks are complete, stop and report success.
"""

    return [
        "claude",
        "--print", prompt_template,
        "-p", prompt
    ]


def build_feedback_command(
    pr_url: str,
    feedback_type: str,
    feedback_content: str
) -> List[str]:
    """Build the command to invoke Claude Code for handling feedback.

    Args:
        pr_url: The PR URL
        feedback_type: Type of feedback (review_comment, review, check_failure)
        feedback_content: The feedback content to address

    Returns:
        Command as a list suitable for subprocess
    """
    prompt = f"""You are addressing feedback on a pull request.

* PR URL: {pr_url}
* Feedback type: {feedback_type}

The feedback to address:

{feedback_content}

Your task:

1. Understand the feedback and what changes are being requested
2. Make the necessary code changes to address the feedback
3. Commit your changes with a clear message explaining how you addressed the feedback
"""

    return [
        "claude",
        "--print", "wt-handle-feedback.md",
        "-p", prompt
    ]


def build_push_command(branch_name: str, force: bool = False) -> List[str]:
    """Build the git push command for the slice branch.

    Args:
        branch_name: The branch name to push
        force: If True, use --force-with-lease for safe force push

    Returns:
        Command as a list suitable for subprocess
    """
    cmd = ["git", "push", "origin", branch_name]
    if force:
        cmd.insert(2, "--force-with-lease")
    return cmd


def push_to_slice_branch(slice_branch: str, pr_number: int, force: bool = False) -> bool:
    """Push to slice branch after verifying PR is still in Draft state.

    Args:
        slice_branch: The slice branch name to push to
        pr_number: The PR number to check Draft state
        force: If True, use force-with-lease

    Returns:
        True if push succeeded, False if PR is not Draft or push failed
    """
    # Verify PR is still in Draft state
    if not is_pr_draft(pr_number):
        print(f"Error: PR #{pr_number} is no longer in Draft state", file=sys.stderr)
        return False

    # Build and execute push command
    cmd = build_push_command(slice_branch, force=force)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: Push failed: {result.stderr}", file=sys.stderr)
        return False

    return True


def check_claude_success(exit_code: int, head_before: str, head_after: str) -> bool:
    """Check if Claude invocation was successful.

    Success requires:
    1. Exit code of 0
    2. HEAD advanced (a commit was made)

    Args:
        exit_code: The exit code from Claude
        head_before: Git HEAD SHA before invocation
        head_after: Git HEAD SHA after invocation

    Returns:
        True if successful, False otherwise
    """
    return exit_code == 0 and head_before != head_after


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
    parser.add_argument(
        "--mock-claude",
        metavar="SCRIPT",
        help="Use mock script instead of Claude (for testing)"
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Only set up infrastructure (branches, worktree, PR), don't execute tasks"
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

    # Get repo from idea directory
    repo = Repo(args.idea_directory, search_parent_directories=True)

    # Create or reuse integration branch
    integration_branch = ensure_integration_branch(repo, idea_name)
    print(f"Integration branch: {integration_branch}")

    # Create or reuse worktree
    worktree_path = ensure_worktree(repo, idea_name, integration_branch)
    print(f"Worktree: {worktree_path}")

    # Read plan file to get first task name for slice naming
    # Use the original idea directory path for initial read
    original_plan_file = os.path.join(args.idea_directory, f"{idea_name}-plan.md")
    with open(original_plan_file, "r") as f:
        plan_content = f.read()
    first_task_name = get_first_task_name(plan_content)

    # Calculate the plan file path in the worktree for the task execution loop
    # The idea directory structure is preserved in the worktree
    idea_dir_relpath = os.path.relpath(args.idea_directory, repo.working_tree_dir)
    worktree_plan_file = os.path.join(worktree_path, idea_dir_relpath, f"{idea_name}-plan.md")

    # Create or reuse slice branch
    slice_branch = ensure_slice_branch(
        repo, idea_name, state["slice_number"], first_task_name, integration_branch
    )
    print(f"Slice branch: {slice_branch}")

    # Checkout slice branch in the worktree
    worktree_repo = Repo(worktree_path)
    worktree_repo.git.checkout(slice_branch)

    # Push slice branch to remote (needed before creating PR)
    if not push_branch_to_remote(slice_branch):
        print("Warning: Could not push slice branch to remote", file=sys.stderr)

    # Create or reuse Draft PR
    pr_number = ensure_draft_pr(
        slice_branch, args.idea_directory, idea_name, state["slice_number"]
    )
    if pr_number:
        print(f"PR: #{pr_number}")

    # Skip task execution if --setup-only was provided
    if args.setup_only:
        print("Setup complete. Exiting (--setup-only mode).")
        return

    # Execute tasks one by one until all are complete
    while True:
        # Re-read plan file from the worktree to get current uncompleted tasks
        with open(worktree_plan_file, "r") as f:
            plan_content = f.read()

        tasks = parse_tasks_from_plan(plan_content)
        if not tasks:
            print("All tasks completed!")
            break

        tasks_before = len(tasks)
        print(f"Found {tasks_before} uncompleted task(s)")

        # Execute next uncompleted task
        current_task = tasks[0]
        print(f"Executing task: {current_task}")

        # Get HEAD before Claude invocation
        head_before = worktree_repo.head.commit.hexsha

        # Build and run Claude command (or mock script for testing)
        if args.mock_claude:
            claude_cmd = [args.mock_claude, current_task]
            print(f"Using mock Claude: {args.mock_claude}")
        else:
            claude_cmd = build_claude_command(
                args.idea_directory,
                current_task,
                "implement-plan.md"
            )
            print(f"Invoking Claude: {' '.join(claude_cmd)}")

        # Run Claude (or mock) interactively
        claude_result = subprocess.run(claude_cmd, cwd=worktree_path)

        # Get HEAD after Claude invocation
        head_after = worktree_repo.head.commit.hexsha

        # Re-read plan to check if task was marked complete
        with open(worktree_plan_file, "r") as f:
            updated_plan_content = f.read()
        tasks_after = len(parse_tasks_from_plan(updated_plan_content))

        # Verify success: exit code 0, HEAD advanced, AND task count decreased
        if not check_claude_success(claude_result.returncode, head_before, head_after):
            print(f"Error: Task execution failed.", file=sys.stderr)
            print(f"  Exit code: {claude_result.returncode}", file=sys.stderr)
            print(f"  HEAD before: {head_before}", file=sys.stderr)
            print(f"  HEAD after: {head_after}", file=sys.stderr)
            sys.exit(1)

        if tasks_after >= tasks_before:
            print(f"Error: Task was not marked complete in plan file.", file=sys.stderr)
            print(f"  Tasks before: {tasks_before}", file=sys.stderr)
            print(f"  Tasks after: {tasks_after}", file=sys.stderr)
            sys.exit(1)

        print(f"Task completed successfully. Pushing changes...")

        # Push the commit
        if pr_number and not push_to_slice_branch(slice_branch, pr_number):
            print("Warning: Could not push commit to slice branch", file=sys.stderr)


if __name__ == "__main__":
    main()
