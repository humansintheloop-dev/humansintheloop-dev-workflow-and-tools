"""GitHubClient: wraps all `gh` CLI calls for PR operations."""

import json
import subprocess
from typing import Optional


class GitHubClient:
    """Wraps GitHub CLI (gh) calls for PR operations.

    All subprocess calls go through _run_gh() for consistency.
    """

    def _run_gh(self, args, **kwargs):
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            **kwargs,
        )

    def find_pr(self, branch_name: str) -> Optional[int]:
        result = self._run_gh(
            ["gh", "pr", "list", "--json", "number,headRefName,isDraft", "--state", "open"]
        )
        if result.returncode != 0:
            return None
        prs = json.loads(result.stdout)
        for pr in prs:
            if pr.get("headRefName") == branch_name:
                return pr.get("number")
        return None

    def create_draft_pr(self, slice_branch: str, title: str, body: str, base_branch: str) -> int:
        result = self._run_gh(
            ["gh", "pr", "create",
             "--draft",
             "--title", title,
             "--body", body,
             "--head", slice_branch,
             "--base", base_branch]
        )
        if result.returncode != 0:
            raise RuntimeError(f"PR creation failed: {result.stderr}")
        url = result.stdout.strip()
        try:
            return int(url.split("/")[-1])
        except (ValueError, IndexError):
            raise RuntimeError(f"Could not parse PR number from: {url}")

    def is_pr_draft(self, pr_number: int) -> bool:
        result = self._run_gh(
            ["gh", "pr", "view", str(pr_number), "--json", "isDraft"]
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        return data.get("isDraft", False)

    def get_pr_state(self, pr_number: int) -> str:
        result = self._run_gh(
            ["gh", "pr", "view", str(pr_number), "--json", "state"]
        )
        if result.returncode != 0:
            return ""
        data = json.loads(result.stdout)
        return data.get("state", "")

    def get_pr_url(self, pr_number: int) -> str:
        result = self._run_gh(
            ["gh", "pr", "view", str(pr_number), "--json", "url", "--jq", ".url"]
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()

    def mark_pr_ready(self, pr_number: int) -> bool:
        result = self._run_gh(
            ["gh", "pr", "ready", str(pr_number)]
        )
        return result.returncode == 0
