"""
implement-with-worktree: Automates Git worktree and GitHub Draft PR-based development.

This script orchestrates the complete lifecycle of implementing a development plan:
from creating Git infrastructure through task execution with Claude Code.
"""

import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from typing import Dict, Any, Optional, List

from git import Repo
from git.exc import InvalidGitRepositoryError



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
        print("Error: Idea files have uncommitted changes:", file=sys.stderr)
        for f in uncommitted:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)




def ensure_integration_branch(repo: Repo, idea_name: str, isolated: bool = False) -> str:
    """Ensure the integration branch exists, creating it if necessary.

    Args:
        repo: GitPython Repo object
        idea_name: Name of the idea
        isolated: When True (inside VM), prefer tracking remote branch over creating from HEAD

    Returns:
        The integration branch name
    """
    branch_name = f"idea/{idea_name}/integration"

    # Check if branch already exists
    existing_branches = [b.name for b in repo.branches]
    if branch_name not in existing_branches:
        if isolated:
            # In isolated mode, try to create a local tracking branch from remote
            try:
                remote_ref = repo.remotes.origin.refs[branch_name]
                repo.create_head(branch_name, remote_ref)
            except (IndexError, AttributeError):
                # Remote branch doesn't exist — fall back to HEAD
                repo.create_head(branch_name)
        else:
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

    # Copy .claude/settings.local.json to worktree if it exists
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
    """Ensure .claude/settings.local.json has required permissions.

    Creates the file if it doesn't exist. Adds any missing permissions
    from REQUIRED_PERMISSIONS to the allow list.

    Args:
        repo_root: Path to the repository root
    """
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


def _default_gh_client():
    from i2code.implement.github_client import GitHubClient
    return GitHubClient()


def find_existing_pr(branch_name: str) -> Optional[int]:
    """Delegate to GitHubClient.find_pr()."""
    return _default_gh_client().find_pr(branch_name)


def is_pr_draft(pr_number: int) -> bool:
    """Delegate to GitHubClient.is_pr_draft()."""
    return _default_gh_client().is_pr_draft(pr_number)


def create_draft_pr(slice_branch: str, title: str, body: str, base_branch: str) -> int:
    """Delegate to GitHubClient.create_draft_pr()."""
    return _default_gh_client().create_draft_pr(slice_branch, title, body, base_branch)



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


def get_pr_url(pr_number: int) -> str:
    """Delegate to GitHubClient.get_pr_url()."""
    return _default_gh_client().get_pr_url(pr_number)


def format_all_feedback(
    review_comments: List[Dict[str, Any]],
    reviews: List[Dict[str, Any]],
    conversation_comments: List[Dict[str, Any]]
) -> str:
    """Format all feedback types into a single string for Claude.

    Args:
        review_comments: List of review comments (on specific code lines)
        reviews: List of PR reviews
        conversation_comments: List of general PR comments

    Returns:
        Formatted string containing all feedback
    """
    sections = []

    if reviews:
        sections.append("## PR Reviews\n")
        for review in reviews:
            state = review.get("state", "COMMENTED")
            body = review.get("body", "").strip()
            user = review.get("user", {}).get("login", "unknown")
            review_id = review.get("id")
            sections.append(f"### Review by {user} (ID: {review_id}, State: {state})")
            if body:
                sections.append(f"{body}\n")
            else:
                sections.append("(No body text)\n")

    if review_comments:
        sections.append("## Review Comments (on specific code lines)\n")
        for comment in review_comments:
            body = comment.get("body", "").strip()
            user = comment.get("user", {}).get("login", "unknown")
            path = comment.get("path", "unknown file")
            line = comment.get("line") or comment.get("original_line", "?")
            comment_id = comment.get("id")
            sections.append(f"### Comment by {user} on {path}:{line} (ID: {comment_id})")
            sections.append(f"{body}\n")

    if conversation_comments:
        sections.append("## General PR Comments\n")
        for comment in conversation_comments:
            body = comment.get("body", "").strip()
            user = comment.get("user", {}).get("login", "unknown")
            comment_id = comment.get("id")
            sections.append(f"### Comment by {user} (ID: {comment_id})")
            sections.append(f"{body}\n")

    return "\n".join(sections)




def parse_triage_result(claude_output: str) -> Optional[Dict[str, Any]]:
    """Parse the JSON triage result from Claude's output.

    Args:
        claude_output: The raw output from Claude

    Returns:
        Parsed triage dict or None if parsing fails
    """
    # Try to find JSON in the output
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', claude_output, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try parsing the whole output as JSON
    try:
        return json.loads(claude_output.strip())
    except json.JSONDecodeError:
        pass

    return None


def get_feedback_by_ids(
    all_feedback: List[Dict[str, Any]],
    comment_ids: List[int]
) -> List[Dict[str, Any]]:
    """Get feedback items matching the given IDs.

    Args:
        all_feedback: All feedback items
        comment_ids: IDs to filter by

    Returns:
        Matching feedback items
    """
    return [f for f in all_feedback if f.get("id") in comment_ids]


def determine_comment_type(comment_id: int, review_comments: List[Dict], conversation_comments: List[Dict]) -> str:
    """Determine whether a comment ID is a review comment or conversation comment.

    Args:
        comment_id: The comment ID to check
        review_comments: List of review comments
        conversation_comments: List of conversation comments

    Returns:
        'review' if it's a review comment, 'conversation' if general comment
    """
    for c in review_comments:
        if c.get("id") == comment_id:
            return "review"
    return "conversation"


def process_pr_feedback(
    pr_number: int,
    pr_url: str,
    state,
    worktree_path: str,
    slice_branch: str,
    interactive: bool = True,
    mock_claude: Optional[str] = None,
    skip_ci_wait: bool = False,
    ci_timeout: int = 600,
    gh_client=None,
) -> tuple:
    """Process new PR feedback using triage-based approach.

    Flow:
    1. Fetch and filter new feedback
    2. Invoke Claude to triage (categorize as will_fix or needs_clarification)
    3. Reply to comments needing clarification
    4. For each fix group: invoke Claude, push, reply with SHA, verify CI

    Args:
        pr_number: The PR number
        pr_url: The PR URL
        state: WorkflowState instance (will be modified with processed IDs)
        worktree_path: Path to the worktree
        slice_branch: Branch name for pushing
        interactive: If True, run Claude interactively
        mock_claude: Optional path to mock script for testing
        skip_ci_wait: If True, skip waiting for CI
        ci_timeout: Timeout for CI in seconds

    Returns:
        Tuple of (had_feedback, made_changes):
        - had_feedback: True if there was new feedback to process
        - made_changes: True if Claude made code changes (commits)
    """
    from git import Repo as GitRepo

    if gh_client is None:
        gh_client = _default_gh_client()

    # Fetch all feedback types
    review_comments = gh_client.fetch_pr_comments(pr_number)
    reviews = gh_client.fetch_pr_reviews(pr_number)
    conversation_comments = gh_client.fetch_pr_conversation_comments(pr_number)

    # Filter to new/unprocessed
    new_review_comments = get_new_feedback(
        review_comments, state.processed_comment_ids
    )
    new_reviews = get_new_feedback(
        reviews, state.processed_review_ids
    )
    new_conversation = get_new_feedback(
        conversation_comments, state.processed_conversation_ids
    )

    # Check if there's any new feedback
    if not new_review_comments and not new_reviews and not new_conversation:
        return (False, False)

    print(f"Found new feedback: {len(new_reviews)} review(s), "
          f"{len(new_review_comments)} review comment(s), "
          f"{len(new_conversation)} general comment(s)")

    # Combine all feedback for triage
    all_new_feedback = new_review_comments + new_reviews + new_conversation
    feedback_content = format_all_feedback(
        new_review_comments, new_reviews, new_conversation
    )

    # Step 1: Triage - ask Claude to categorize feedback
    print("Triaging feedback...")
    if mock_claude:
        triage_cmd = [mock_claude, f"triage-{pr_number}"]
    else:
        from i2code.implement.command_builder import CommandBuilder
        triage_cmd = CommandBuilder().build_triage_command(feedback_content, interactive=False)

    triage_result = run_claude_with_output_capture(triage_cmd, cwd=worktree_path)

    triage = parse_triage_result(triage_result.stdout)
    if not triage:
        print("Warning: Could not parse triage result, marking all as processed")
        # Mark all as processed to avoid infinite loop
        state.mark_comments_processed([c["id"] for c in new_review_comments])
        state.mark_reviews_processed([r["id"] for r in new_reviews])
        state.mark_conversations_processed([c["id"] for c in new_conversation])
        return (True, False)

    will_fix = triage.get("will_fix", [])
    needs_clarification = triage.get("needs_clarification", [])

    print(f"Triage result: {len(will_fix)} fix group(s), "
          f"{len(needs_clarification)} needing clarification")

    # Step 2: Reply to comments needing clarification
    for item in needs_clarification:
        comment_id = item.get("comment_id")
        question = item.get("question", "Could you please clarify?")

        comment_type = determine_comment_type(
            comment_id, new_review_comments, new_conversation
        )

        print(f"Asking for clarification on comment {comment_id}...")
        if comment_type == "review":
            success = gh_client.reply_to_review_comment(pr_number, comment_id, question)
        else:
            success = gh_client.reply_to_pr_comment(pr_number, f"Re: comment {comment_id}\n\n{question}")

        if success:
            print(f"  Replied to comment {comment_id}")
        else:
            print(f"  Warning: Failed to reply to comment {comment_id}")

    # Step 3: Process each fix group
    worktree_repo = GitRepo(worktree_path)
    made_any_changes = False

    for fix_group in will_fix:
        comment_ids = fix_group.get("comment_ids", [])
        description = fix_group.get("description", "Address feedback")

        if not comment_ids:
            continue

        print(f"\nFixing: {description}")
        print(f"  Comments: {comment_ids}")

        # Get the specific feedback for this group
        group_feedback = get_feedback_by_ids(all_new_feedback, comment_ids)
        group_content = format_all_feedback(
            [f for f in group_feedback if f in new_review_comments],
            [f for f in group_feedback if f in new_reviews],
            [f for f in group_feedback if f in new_conversation]
        )

        # Invoke Claude to fix
        head_before = worktree_repo.head.commit.hexsha

        if mock_claude:
            fix_cmd = [mock_claude, f"fix-{pr_number}-{comment_ids[0]}"]
        else:
            from i2code.implement.command_builder import CommandBuilder
            fix_cmd = CommandBuilder().build_fix_command(pr_url, group_content, description, interactive=interactive)

        print("  Invoking Claude to fix...")
        if interactive:
            fix_result = run_claude_interactive(fix_cmd, cwd=worktree_path)
        else:
            fix_result = run_claude_with_output_capture(fix_cmd, cwd=worktree_path)

        head_after = worktree_repo.head.commit.hexsha

        if head_before == head_after:
            print("  Warning: Claude did not make any commits for this fix")
            continue

        made_any_changes = True
        commit_sha = head_after[:8]
        print(f"  Committed: {commit_sha}")

        # Push the commit
        print("  Pushing...")
        if not push_branch_to_remote(slice_branch):
            print("  Error: Could not push fix", file=sys.stderr)
            return (True, True)  # Return early, let caller handle

        # Reply to each comment with the commit SHA
        for comment_id in comment_ids:
            comment_type = determine_comment_type(
                comment_id, new_review_comments, new_conversation
            )

            reply_body = f"Fixed in {commit_sha}"
            if comment_type == "review":
                success = gh_client.reply_to_review_comment(pr_number, comment_id, reply_body)
            else:
                success = gh_client.reply_to_pr_comment(pr_number, f"Re: comment {comment_id}\n\n{reply_body}")

            if success:
                print(f"  Replied to comment {comment_id}: {reply_body}")
            else:
                print(f"  Warning: Failed to reply to comment {comment_id}")

        # Wait for CI
        if not skip_ci_wait:
            print("  Waiting for CI...")
            ci_success, failing_run = gh_client.wait_for_workflow_completion(
                slice_branch, head_after, timeout_seconds=ci_timeout
            )

            if not ci_success and failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"  CI failed: {workflow_name}")
                # Don't return here - let the main loop handle CI fix
            elif ci_success:
                print("  CI passed!")

    # Mark all feedback as processed
    state.mark_comments_processed([c["id"] for c in new_review_comments])
    state.mark_reviews_processed([r["id"] for r in new_reviews])
    state.mark_conversations_processed([c["id"] for c in new_conversation])

    return (True, made_any_changes)


def has_ci_workflow_files(repo_path: str) -> bool:
    """Check if GitHub Actions workflow files exist in the repository.

    Args:
        repo_path: Path to the repository

    Returns:
        True if at least one workflow file exists, False otherwise
    """
    workflows_dir = os.path.join(repo_path, ".github", "workflows")
    if not os.path.isdir(workflows_dir):
        return False

    for filename in os.listdir(workflows_dir):
        if filename.endswith(('.yml', '.yaml')):
            return True

    return False


def get_failing_workflow_run(branch: str, sha: str, gh_client=None) -> Optional[Dict[str, Any]]:
    """Get failing workflow run for the branch/SHA, if any.

    Args:
        branch: The branch name
        sha: The commit SHA
        gh_client: GitHubClient instance

    Returns:
        The first failing workflow run dict, or None if no failures
    """
    if gh_client is None:
        gh_client = _default_gh_client()
    runs = gh_client.get_workflow_runs_for_commit(branch, sha)

    for run in runs:
        if run.get("conclusion") == "failure":
            return run

    return None



def fix_ci_failure(
    slice_branch: str,
    head_sha: str,
    worktree_path: str,
    max_retries: int = 3,
    interactive: bool = True,
    mock_claude: Optional[str] = None,
    gh_client=None,
) -> bool:
    """Attempt to fix CI failure for a branch.

    Loop:
    1. Get failing workflow run for branch/SHA
    2. Get failure logs
    3. Invoke Claude to fix
    4. Push fix
    5. Wait for CI completion
    6. If still failing, retry (up to max_retries)

    Args:
        slice_branch: The branch name
        head_sha: The current HEAD SHA
        worktree_path: Path to the worktree
        max_retries: Maximum retry attempts (default 3)
        interactive: If True, run Claude interactively
        mock_claude: Optional path to mock script for testing

    Returns:
        True if CI passes, False if max retries exceeded
    """
    from git import Repo as GitRepo

    if gh_client is None:
        gh_client = _default_gh_client()

    worktree_repo = GitRepo(worktree_path)
    current_sha = head_sha

    for attempt in range(1, max_retries + 1):
        print(f"\nCI fix attempt {attempt}/{max_retries}")

        # Get the failing workflow run
        failing_run = get_failing_workflow_run(slice_branch, current_sha, gh_client=gh_client)
        if not failing_run:
            print("No failing workflow found - CI may have passed")
            return True

        run_id = failing_run.get("databaseId")
        workflow_name = failing_run.get("name", "unknown")
        print(f"  Workflow '{workflow_name}' failed (run {run_id})")

        # Get failure logs
        print("  Fetching failure logs...")
        failure_logs = gh_client.get_workflow_failure_logs(run_id)

        # Build and run Claude command to fix
        if mock_claude:
            claude_cmd = [mock_claude, f"fix-ci-{run_id}"]
        else:
            from i2code.implement.command_builder import CommandBuilder
            claude_cmd = CommandBuilder().build_ci_fix_command(
                run_id, workflow_name, failure_logs, interactive=interactive
            )

        print("  Invoking Claude to fix CI failure...")
        head_before = worktree_repo.head.commit.hexsha

        if interactive:
            claude_result = run_claude_interactive(claude_cmd, cwd=worktree_path)
        else:
            claude_result = run_claude_with_output_capture(claude_cmd, cwd=worktree_path)

        head_after = worktree_repo.head.commit.hexsha

        # Check if Claude made a fix
        if head_before == head_after:
            print("  Claude did not make any commits")
            if attempt == max_retries:
                return False
            continue

        # Push the fix
        print("  Pushing fix...")
        if not push_branch_to_remote(slice_branch):
            print("  Error: Could not push fix", file=sys.stderr)
            return False

        current_sha = head_after

        # Wait for CI to complete
        print("  Waiting for CI to complete...")
        ci_success, new_failing_run = gh_client.wait_for_workflow_completion(
            slice_branch, current_sha
        )

        if ci_success:
            print("  CI passed!")
            return True

        if new_failing_run:
            print(f"  CI still failing: {new_failing_run.get('name', 'unknown')}")

    print(f"Max retries ({max_retries}) exceeded")
    return False


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


def get_remote_main_head(branch: str, remote: str = "origin") -> str:
    """Get the current HEAD SHA of the remote main branch.

    Fetches from the remote first to ensure we have the latest refs.

    Args:
        branch: The branch name
        remote: The remote name (default: "origin")

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


def rebase_integration_branch(integration_branch: str, base_branch: str) -> bool:
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


def get_rebase_conflict_message(integration_branch: str, base_branch: str) -> str:
    """Generate a message explaining rebase conflict and how to resolve it.

    Args:
        integration_branch: The integration branch that had conflicts
        base_branch: The base branch to rebase onto

    Returns:
        A human-readable message with instructions
    """
    return f"""
Rebase conflict detected on {integration_branch}!

The main branch has advanced and there are conflicts that require manual resolution.

To resolve:
1. Navigate to the worktree directory
2. Run: git rebase origin/{base_branch}
3. Resolve the conflicts in each file
4. Run: git add <resolved-files>
5. Run: git rebase --continue
6. Re-run this script to continue

The script will now pause. Press Enter when ready to exit, or Ctrl+C to abort.
"""


# PR Completion Functions

def mark_pr_ready(pr_number: int) -> bool:
    """Delegate to GitHubClient.mark_pr_ready()."""
    return _default_gh_client().mark_pr_ready(pr_number)


def get_pr_state(pr_number: int) -> str:
    """Delegate to GitHubClient.get_pr_state()."""
    return _default_gh_client().get_pr_state(pr_number)


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


# Slice Rollover Functions

def should_rollover(pr_number: int, has_unpushed_commits: bool, gh_client=None) -> bool:
    """Check if we should rollover to a new slice.

    Rollover is needed when:
    1. The PR is no longer in Draft state (someone marked it ready)
    2. We have unpushed commits (work that can't be pushed to old slice)

    Args:
        pr_number: The PR number to check
        has_unpushed_commits: Whether there are local commits not pushed
        gh_client: GitHubClient instance (uses default if None)

    Returns:
        True if rollover is needed, False otherwise
    """
    if gh_client is None:
        from i2code.implement.github_client import GitHubClient
        gh_client = GitHubClient()

    if not has_unpushed_commits:
        return False

    if gh_client.is_pr_draft(pr_number):
        return False

    return True


def generate_next_slice_branch(
    idea_name: str,
    current_slice_number: int,
    slice_name: str
) -> str:
    """Generate the branch name for the next slice.

    Args:
        idea_name: Name of the idea
        current_slice_number: Current slice number
        slice_name: Name for the new slice

    Returns:
        The next slice branch name
    """
    next_number = current_slice_number + 1
    sanitized_name = sanitize_branch_name(slice_name)
    return f"idea/{idea_name}/{next_number:02d}-{sanitized_name}"


# Interrupt Handling Functions

# Global state for interrupt handler
_interrupt_state = {
    "state_file": None,
    "state": None
}


def register_signal_handlers():
    """Register signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _handle_interrupt)


def _handle_interrupt(signum, frame):
    """Internal handler for SIGINT signal."""
    print("\nInterrupted! Saving state...")
    if _interrupt_state["state_file"] and _interrupt_state["state"]:
        cleanup_on_interrupt(
            _interrupt_state["state_file"],
            _interrupt_state["state"]
        )
    sys.exit(1)


def cleanup_on_interrupt(
    state_file: str,
    state
) -> None:
    """Clean up and save state when interrupted.

    Args:
        state_file: Path to the state file (unused, kept for backward compat)
        state: WorkflowState instance to save
    """
    state.save()
    print("State saved. You can resume by running the script again.")


# Plan Helpers

def get_next_task(plan_file: str):
    from i2code.plan.plan_file_io import with_plan_file
    with with_plan_file(plan_file) as plan:
        return plan.get_next_task()


def is_task_completed(plan_file: str, thread: int, task: int) -> bool:
    from i2code.plan.plan_file_io import with_plan_file
    with with_plan_file(plan_file) as plan:
        return plan.is_task_completed(thread, task)


# Claude Invocation Functions

def get_worktree_idea_directory(
    worktree_path: str,
    main_repo_idea_dir: str,
    main_repo_root: str
) -> str:
    """Compute the idea directory path within the worktree.

    Args:
        worktree_path: Absolute path to the worktree
        main_repo_idea_dir: Absolute path to idea directory in main repo
        main_repo_root: Absolute path to main repo root

    Returns:
        Absolute path to the idea directory within the worktree
    """
    idea_relpath = os.path.relpath(main_repo_idea_dir, main_repo_root)
    return os.path.join(worktree_path, idea_relpath)


def ensure_project_setup(
    repo: Repo,
    idea_directory: str,
    idea_name: str,
    integration_branch: str,
    interactive: bool = True,
    mock_claude: Optional[str] = None,
    ci_fix_retries: int = 3,
    ci_timeout: int = 600,
    skip_ci_wait: bool = False,
    gh_client=None,
) -> bool:
    """Ensure project scaffolding exists on the integration branch.

    Returns True if setup succeeded (CI passes), False otherwise.
    """
    if gh_client is None:
        gh_client = _default_gh_client()

    repo.git.checkout(integration_branch)

    head_before = repo.head.commit.hexsha

    run_scaffolding(idea_directory, cwd=repo.working_tree_dir, interactive=interactive, mock_claude=mock_claude)

    head_after = repo.head.commit.hexsha

    if head_before == head_after:
        return True

    push_branch_to_remote(integration_branch)

    if skip_ci_wait:
        return True

    ci_success, failing_run = gh_client.wait_for_workflow_completion(
        integration_branch, head_after, timeout_seconds=ci_timeout
    )

    if not ci_success and failing_run:
        return fix_ci_failure(
            integration_branch,
            head_after,
            repo.working_tree_dir,
            max_retries=ci_fix_retries,
            interactive=interactive,
            mock_claude=mock_claude,
            gh_client=gh_client,
        )

    return ci_success


def run_scaffolding(idea_directory: str, cwd: str, interactive: bool = True, mock_claude: Optional[str] = None):
    """Invoke Claude to generate project scaffolding."""
    from i2code.implement.command_builder import CommandBuilder
    cmd = CommandBuilder().build_scaffolding_command(idea_directory, interactive=interactive, mock_claude=mock_claude)
    if interactive:
        result = run_claude_interactive(cmd, cwd=cwd)
    else:
        result = run_claude_with_output_capture(cmd, cwd=cwd)

    if interactive or "<SUCCESS>" in result.stdout or "<NOTHING-TO-DO>" in result.stdout:
        return

    print("Error: Scaffolding failed.", file=sys.stderr)
    if result.error_message:
        print(f"  {result.error_message}", file=sys.stderr)
    if result.permission_denials:
        print(f"  Permission denied for {len(result.permission_denials)} action(s)", file=sys.stderr)
    for msg in result.last_messages:
        msg_type = msg.get('type', 'unknown')
        if msg_type == 'assistant':
            for item in msg.get('message', {}).get('content', []):
                if item.get('type') == 'text':
                    print(f"  Claude: {item['text']}", file=sys.stderr)
        elif msg_type == 'result':
            text = msg.get('result', '')
            if text:
                print(f"  Result: {text}", file=sys.stderr)
    sys.exit(1)


from i2code.implement.claude_runner import ClaudeResult  # noqa: E402


def run_claude_with_output_capture(cmd: List[str], cwd: str) -> ClaudeResult:
    """Run Claude command, capturing output while displaying progress.

    For stream-json output, prints a dot for each JSON message received.
    At the end, parses the result to check for errors and permission denials.

    Args:
        cmd: Command to run as list
        cwd: Working directory

    Returns:
        ClaudeResult with returncode, stdout, stderr, and parsed error info
    """
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout_chunks: List[str] = []
    stderr_chunks: List[str] = []

    def read_stdout_stream_json(pipe, chunks: List[str]):
        """Read stream-json output, printing a dot for each JSON blob."""
        buffer = ""
        while True:
            chunk = pipe.read1(4096) if hasattr(pipe, 'read1') else pipe.read(4096)
            if not chunk:
                break
            text = chunk.decode('utf-8', errors='replace')
            chunks.append(text)
            buffer += text

            # Count complete JSON objects (each ends with newline in stream-json)
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    sys.stdout.write('.')
                    sys.stdout.flush()

    def read_stderr(pipe, chunks: List[str]):
        """Read stderr output."""
        while True:
            chunk = pipe.read1(4096) if hasattr(pipe, 'read1') else pipe.read(4096)
            if not chunk:
                break
            text = chunk.decode('utf-8', errors='replace')
            chunks.append(text)
            sys.stderr.write(text)
            sys.stderr.flush()

    # Start threads to read stdout and stderr concurrently
    stdout_thread = threading.Thread(
        target=read_stdout_stream_json,
        args=(process.stdout, stdout_chunks)
    )
    stderr_thread = threading.Thread(
        target=read_stderr,
        args=(process.stderr, stderr_chunks)
    )

    stdout_thread.start()
    stderr_thread.start()

    # Wait for process to complete
    process.wait()

    # Wait for reader threads to finish
    stdout_thread.join()
    stderr_thread.join()

    # Print newline after dots
    sys.stdout.write('\n')
    sys.stdout.flush()

    # Parse the output to extract error information
    full_stdout = ''.join(stdout_chunks)
    permission_denials = []
    error_message = None
    all_messages: List[Dict[str, Any]] = []

    # Parse all JSON messages
    for line in full_stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            all_messages.append(msg)
            if msg.get('type') == 'result':
                permission_denials = msg.get('permission_denials', [])
                if msg.get('is_error'):
                    error_message = msg.get('result', 'Unknown error')
                elif permission_denials:
                    error_message = f"Permission denied for {len(permission_denials)} action(s)"
        except json.JSONDecodeError:
            continue

    # Keep last 5 messages for debugging
    last_messages = all_messages[-5:] if all_messages else []

    return ClaudeResult(
        returncode=process.returncode,
        stdout=full_stdout,
        stderr=''.join(stderr_chunks),
        permission_denials=permission_denials,
        error_message=error_message,
        last_messages=last_messages
    )


def run_claude_interactive(cmd: List[str], cwd: str) -> ClaudeResult:
    """Run Claude command interactively, inheriting terminal.

    In interactive mode, Claude needs direct access to the terminal
    for its TUI, so we don't capture stdout/stderr.

    Args:
        cmd: Command to run as list
        cwd: Working directory

    Returns:
        ClaudeResult with just the returncode (no captured output)
    """
    result = subprocess.run(cmd, cwd=cwd)

    return ClaudeResult(
        returncode=result.returncode,
        stdout="",
        stderr="",
        permission_denials=[],
        error_message=None,
        last_messages=[]
    )


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


def push_to_slice_branch(slice_branch: str, pr_number: int, force: bool = False, gh_client=None) -> bool:
    """Push to slice branch after verifying PR is still in Draft state.

    Args:
        slice_branch: The slice branch name to push to
        pr_number: The PR number to check Draft state
        force: If True, use force-with-lease
        gh_client: GitHubClient instance (uses default if None)

    Returns:
        True if push succeeded, False if PR is not Draft or push failed
    """
    if gh_client is None:
        from i2code.implement.github_client import GitHubClient
        gh_client = GitHubClient()

    # Verify PR is still in Draft state
    if not gh_client.is_pr_draft(pr_number):
        print(f"Error: PR #{pr_number} is no longer in Draft state", file=sys.stderr)
        return False

    # Build and execute push command
    cmd = build_push_command(slice_branch, force=force)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: Push failed: {result.stderr}", file=sys.stderr)
        return False

    return True



def print_task_failure_diagnostics(
    claude_result: 'ClaudeResult',
    head_before: str,
    head_after: str,
) -> None:
    """Print diagnostic information when a Claude task execution fails."""
    print("\nError: Task execution failed.", file=sys.stderr)
    print(f"  Exit code: {claude_result.returncode}", file=sys.stderr)
    print(f"  HEAD before: {head_before}", file=sys.stderr)
    print(f"  HEAD after: {head_after}", file=sys.stderr)

    if claude_result.permission_denials:
        print(f"\nPermission denied for {len(claude_result.permission_denials)} action(s):", file=sys.stderr)
        for denial in claude_result.permission_denials:
            tool_name = denial.get('tool_name', 'Unknown')
            tool_input = denial.get('tool_input', {})
            cmd = tool_input.get('command', tool_input.get('description', 'N/A'))
            print(f"  - {tool_name}: {cmd}", file=sys.stderr)
        print("\nAdd missing permissions to .claude/settings.local.json", file=sys.stderr)

    if claude_result.error_message:
        print(f"\nClaude error: {claude_result.error_message}", file=sys.stderr)

    if claude_result.last_messages:
        print(f"\nLast {len(claude_result.last_messages)} messages from Claude:", file=sys.stderr)
        for msg in claude_result.last_messages:
            msg_type = msg.get('type', 'unknown')
            if msg_type == 'assistant':
                content = msg.get('message', {}).get('content', [])
                for item in content:
                    if item.get('type') == 'text':
                        text = item.get('text', '')[:200]
                        print(f"  [{msg_type}] {text}...", file=sys.stderr)
            elif msg_type == 'result':
                result = msg.get('result', '')[:200]
                print(f"  [{msg_type}] {result}...", file=sys.stderr)
            else:
                print(f"  [{msg_type}]", file=sys.stderr)


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


