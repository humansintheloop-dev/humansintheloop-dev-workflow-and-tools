"""PR helper functions: title/body generation, push helpers."""

import subprocess
import sys
from typing import List, Optional

from i2code.implement.git_setup import sanitize_branch_name
from i2code.implement.github_client import GitHubClient


def _default_gh_client():
    return GitHubClient()


def generate_pr_title(idea_name: str, slice_branch_suffix: str) -> str:
    """Generate a PR title from idea name and slice branch suffix."""
    return f"[{idea_name}] {slice_branch_suffix}"


def generate_pr_body(idea_directory: str, idea_name: str, slice_number: int) -> str:
    """Generate a PR body with idea directory reference."""
    return f"""## Slice #{slice_number} for {idea_name}

**Idea directory:** `{idea_directory}`

This PR implements slice #{slice_number} of the development plan.
"""


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
    """Push a branch to the remote origin."""
    result = subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Error pushing branch: {result.stderr}", file=sys.stderr)
        return False
    return True


def get_pr_url(pr_number: int) -> str:
    """Delegate to GitHubClient.get_pr_url()."""
    return _default_gh_client().get_pr_url(pr_number)


def mark_pr_ready(pr_number: int) -> bool:
    """Delegate to GitHubClient.mark_pr_ready()."""
    return _default_gh_client().mark_pr_ready(pr_number)


def get_pr_state(pr_number: int) -> str:
    """Delegate to GitHubClient.get_pr_state()."""
    return _default_gh_client().get_pr_state(pr_number)


def is_pr_complete(state: str) -> bool:
    """Check if a PR state indicates completion."""
    return state in ("MERGED", "CLOSED")


def build_push_command(branch_name: str, force: bool = False) -> List[str]:
    """Build the git push command for the slice branch."""
    cmd = ["git", "push", "origin", branch_name]
    if force:
        cmd.insert(2, "--force-with-lease")
    return cmd


def push_to_slice_branch(
    slice_branch: str, pr_number: int, force: bool = False, gh_client=None,
) -> bool:
    """Push to slice branch after verifying PR is still in Draft state."""
    if gh_client is None:
        gh_client = _default_gh_client()
    if not gh_client.is_pr_draft(pr_number):
        print(f"Error: PR #{pr_number} is no longer in Draft state", file=sys.stderr)
        return False
    cmd = build_push_command(slice_branch, force=force)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: Push failed: {result.stderr}", file=sys.stderr)
        return False
    return True


def should_rollover(pr_number: int, has_unpushed_commits: bool, gh_client=None) -> bool:
    """Check if we should rollover to a new slice."""
    if gh_client is None:
        gh_client = _default_gh_client()
    if not has_unpushed_commits:
        return False
    if gh_client.is_pr_draft(pr_number):
        return False
    return True


def generate_next_slice_branch(
    idea_name: str, current_slice_number: int, slice_name: str,
) -> str:
    """Generate the branch name for the next slice."""
    next_number = current_slice_number + 1
    sanitized_name = sanitize_branch_name(slice_name)
    return f"idea/{idea_name}/{next_number:02d}-{sanitized_name}"
