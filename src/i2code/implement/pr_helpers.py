"""PR helper functions: title/body generation, feedback processing helpers."""

import json
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

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


def get_new_feedback(
    all_feedback: List[Dict[str, Any]], processed_ids: List[int],
) -> List[Dict[str, Any]]:
    """Filter feedback to only include items not yet processed."""
    return [f for f in all_feedback if f.get("id") not in processed_ids]


def get_pr_url(pr_number: int) -> str:
    """Delegate to GitHubClient.get_pr_url()."""
    return _default_gh_client().get_pr_url(pr_number)


def format_all_feedback(
    review_comments: List[Dict[str, Any]],
    reviews: List[Dict[str, Any]],
    conversation_comments: List[Dict[str, Any]],
) -> str:
    """Format all feedback types into a single string for Claude."""
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
    """Parse the JSON triage result from Claude's output."""
    json_match = re.search(r'```json\s*(.*?)\s*```', claude_output, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(claude_output.strip())
    except json.JSONDecodeError:
        pass
    return None


def get_feedback_by_ids(
    all_feedback: List[Dict[str, Any]], comment_ids: List[int],
) -> List[Dict[str, Any]]:
    """Get feedback items matching the given IDs."""
    return [f for f in all_feedback if f.get("id") in comment_ids]


def determine_comment_type(
    comment_id: int, review_comments: List[Dict], conversation_comments: List[Dict],
) -> str:
    """Determine whether a comment ID is a review comment or conversation comment."""
    for c in review_comments:
        if c.get("id") == comment_id:
            return "review"
    return "conversation"


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
