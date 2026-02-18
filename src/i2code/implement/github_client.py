"""GitHubClient: wraps all `gh` CLI calls for PR and feedback operations."""

import json
import subprocess
import time
from typing import Any, Dict, List, Optional


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

    def fetch_pr_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        result = self._run_gh(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments",
             "--jq", "."]
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)

    def fetch_pr_reviews(self, pr_number: int) -> List[Dict[str, Any]]:
        result = self._run_gh(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/reviews",
             "--jq", "."]
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)

    def fetch_pr_conversation_comments(self, pr_number: int) -> List[Dict[str, Any]]:
        result = self._run_gh(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{pr_number}/comments",
             "--jq", "."]
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)

    def reply_to_review_comment(self, pr_number: int, comment_id: int, body: str) -> bool:
        result = self._run_gh(
            ["gh", "api",
             f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments/{comment_id}/replies",
             "-f", f"body={body}"]
        )
        return result.returncode == 0

    def reply_to_pr_comment(self, pr_number: int, body: str) -> bool:
        result = self._run_gh(
            ["gh", "pr", "comment", str(pr_number), "--body", body]
        )
        return result.returncode == 0

    def fetch_failed_checks(self, pr_number: int) -> List[Dict[str, Any]]:
        result = self._run_gh(
            ["gh", "pr", "checks", str(pr_number), "--json", "name,state",
             "--jq", '.[] | "\\(.name)\\t\\(.state)"']
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        failed = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2 and parts[1].lower() == "fail":
                failed.append({"name": parts[0], "state": parts[1]})
        return failed

    def get_workflow_runs_for_commit(self, branch: str, sha: str) -> List[Dict[str, Any]]:
        result = self._run_gh(
            ["gh", "run", "list", "--branch", branch, "-c", sha,
             "--json", "databaseId,status,conclusion,name,headSha"]
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return json.loads(result.stdout)

    def get_workflow_failure_logs(self, run_id: int) -> str:
        result = self._run_gh(
            ["gh", "run", "view", str(run_id), "--log-failed"]
        )
        if result.returncode != 0:
            return f"Error fetching logs: {result.stderr}"
        return result.stdout

    def wait_for_workflow_completion(
        self, branch: str, sha: str, timeout_seconds: int = 600
    ) -> tuple:
        start_time = time.time()
        poll_interval = 10

        runs = []
        while not runs:
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                print(f"Timeout waiting for CI runs to appear after {timeout_seconds}s")
                return (False, None)
            runs = self.get_workflow_runs_for_commit(branch, sha)
            if not runs:
                print("  No workflow runs found yet, waiting...")
                time.sleep(poll_interval)

        for run in runs:
            if run.get("status") != "completed":
                run_id = run.get("databaseId")
                run_name = run.get("name", "unknown")
                print(f"  Watching workflow '{run_name}' (run {run_id})...")
                self._run_gh(
                    ["gh", "run", "watch", str(run_id)],
                    timeout=timeout_seconds,
                )

        runs = self.get_workflow_runs_for_commit(branch, sha)
        for run in runs:
            if run.get("conclusion") == "failure":
                return (False, run)

        return (True, None)

    def get_default_branch(self) -> str:
        result = self._run_gh(
            ["gh", "repo", "view", "--json", "defaultBranchRef",
             "--jq", ".defaultBranchRef.name"]
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to detect default branch: {result.stderr}")
        return result.stdout.strip()
