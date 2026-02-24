"""PR helper functions: title/body generation, push helpers."""

import glob
import os
import subprocess
import sys
from typing import List, Optional

from i2code.implement.github_client import GitHubClient


def _default_gh_client():
    return GitHubClient()


def extract_title_from_idea_file(idea_directory: str, idea_name: str) -> str:
    """Extract the title from the idea file's first markdown heading.

    Looks for a file matching `<idea_name>-idea.*` in the idea directory.
    Returns the text after `# ` on the first heading line, or falls back
    to the idea_name if no heading is found or the file doesn't exist.
    """
    pattern = os.path.join(idea_directory, f"{idea_name}-idea.*")
    matches = glob.glob(pattern)
    if not matches:
        return idea_name
    try:
        with open(matches[0], "r") as f:
            for line in f:
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        return idea_name
    return idea_name


def generate_pr_title(idea_name: str, idea_directory: str) -> str:
    """Generate a PR title from the idea file heading.

    Extracts the title from the idea file's first markdown heading,
    falling back to the idea_name if no heading is found.
    """
    return extract_title_from_idea_file(idea_directory, idea_name)


def generate_pr_body(idea_directory: str) -> str:
    """Generate a minimal PR body with the idea directory reference."""
    return f"**Idea directory:** `{idea_directory}`"


def find_existing_pr(branch_name: str) -> Optional[int]:
    """Delegate to GitHubClient.find_pr()."""
    return _default_gh_client().find_pr(branch_name)


def is_pr_draft(pr_number: int) -> bool:
    """Delegate to GitHubClient.is_pr_draft()."""
    return _default_gh_client().is_pr_draft(pr_number)


def create_draft_pr(branch_name: str, title: str, body: str, base_branch: str) -> int:
    """Delegate to GitHubClient.create_draft_pr()."""
    return _default_gh_client().create_draft_pr(branch_name, title, body, base_branch)


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
    """Build the git push command for a branch."""
    cmd = ["git", "push", "origin", branch_name]
    if force:
        cmd.insert(2, "--force-with-lease")
    return cmd


