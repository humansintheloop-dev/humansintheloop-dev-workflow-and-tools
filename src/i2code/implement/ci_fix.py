"""CI failure detection and auto-fix."""

import sys
from typing import Optional

from git import Repo as GitRepo

from i2code.implement.claude_runner import run_claude_interactive, run_claude_with_output_capture
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.github_client import GitHubClient
from i2code.implement.pr_helpers import push_branch_to_remote


def _get_failing_workflow_run(branch, sha, gh_client=None):
    """Get failing workflow run for the branch/SHA, if any."""
    if gh_client is None:
        gh_client = GitHubClient()
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

    Returns True if CI passes, False if max retries exceeded.
    """
    if gh_client is None:
        gh_client = GitHubClient()

    worktree_repo = GitRepo(worktree_path)
    current_sha = head_sha

    for attempt in range(1, max_retries + 1):
        print(f"\nCI fix attempt {attempt}/{max_retries}")

        failing_run = _get_failing_workflow_run(slice_branch, current_sha, gh_client=gh_client)
        if not failing_run:
            print("No failing workflow found - CI may have passed")
            return True

        run_id = failing_run.get("databaseId")
        workflow_name = failing_run.get("name", "unknown")
        print(f"  Workflow '{workflow_name}' failed (run {run_id})")

        print("  Fetching failure logs...")
        failure_logs = gh_client.get_workflow_failure_logs(run_id)

        if mock_claude:
            claude_cmd = [mock_claude, f"fix-ci-{run_id}"]
        else:
            claude_cmd = CommandBuilder().build_ci_fix_command(
                run_id, workflow_name, failure_logs, interactive=interactive,
            )

        print("  Invoking Claude to fix CI failure...")
        head_before = worktree_repo.head.commit.hexsha

        if interactive:
            run_claude_interactive(claude_cmd, cwd=worktree_path)
        else:
            run_claude_with_output_capture(claude_cmd, cwd=worktree_path)

        head_after = worktree_repo.head.commit.hexsha

        if head_before == head_after:
            print("  Claude did not make any commits")
            if attempt == max_retries:
                return False
            continue

        print("  Pushing fix...")
        if not push_branch_to_remote(slice_branch):
            print("  Error: Could not push fix", file=sys.stderr)
            return False

        current_sha = head_after

        print("  Waiting for CI to complete...")
        ci_success, new_failing_run = gh_client.wait_for_workflow_completion(
            slice_branch, current_sha,
        )

        if ci_success:
            print("  CI passed!")
            return True

        if new_failing_run:
            print(f"  CI still failing: {new_failing_run.get('name', 'unknown')}")

    print(f"Max retries ({max_retries}) exceeded")
    return False
