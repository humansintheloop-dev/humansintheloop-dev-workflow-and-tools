"""GithubActionsBuildFixer: detects and fixes CI failures on current HEAD."""

import sys
from typing import Any, Dict, Optional

from i2code.implement.command_builder import CommandBuilder


class GithubActionsBuildFixerFactory:
    """Creates GithubActionsBuildFixer instances with a specific git_repo."""

    def __init__(self, opts, claude_runner=None):
        self._opts = opts
        self._claude_runner = claude_runner

    def create(self, git_repo):
        return GithubActionsBuildFixer(
            opts=self._opts,
            git_repo=git_repo,
            claude_runner=self._claude_runner,
        )


class GithubActionsBuildFixer:
    """Checks for failing CI on the current HEAD and attempts to fix it.

    Args:
        opts: ImplementOpts with execution parameters.
        git_repo: GitRepository (or FakeGitRepository) for branch/push/CI operations.
        claude_runner: ClaudeRunner (or FakeClaudeRunner) for invoking Claude.
    """

    def __init__(self, opts, git_repo, claude_runner=None):
        self._opts = opts
        self._git_repo = git_repo
        self._claude_runner = claude_runner

    def _get_failing_workflow_run(
        self, branch: str, sha: str,
    ) -> Optional[Dict[str, Any]]:
        """Get failing workflow run for the branch/SHA, if any."""
        runs = self._git_repo.gh_client.get_workflow_runs_for_commit(branch, sha)
        for run in runs:
            if run.get("conclusion") == "failure":
                return run
        return None

    def check_and_fix_ci(self):
        """Check for failing CI on current HEAD and attempt to fix it.

        Returns True if a CI failure was found (caller should loop back).
        """
        if not self._git_repo.branch_has_been_pushed():
            return False

        failing_run = self._get_failing_workflow_run(
            self._git_repo.branch, self._git_repo.head_sha,
        )

        if not failing_run:
            return False

        workflow_name = failing_run.get("name", "unknown")
        print(f"CI build failing for HEAD ({self._git_repo.head_sha[:8]}): {workflow_name}")
        print("Attempting to fix CI failure...")

        if not self.fix_ci_failure():
            print("Error: Could not fix CI failure after max retries", file=sys.stderr)
            sys.exit(1)

        return True

    def fix_ci_failure(self):
        """Attempt to fix CI failure using tracked branch and HEAD.

        Returns:
            True if CI passes, False if max retries exceeded.
        """
        max_retries = self._opts.ci_fix_retries
        current_sha = self._git_repo.head_sha

        for attempt in range(1, max_retries + 1):
            print(f"\nCI fix attempt {attempt}/{max_retries}")

            failing_run = self._get_failing_workflow_run(
                self._git_repo.branch, current_sha,
            )
            if not failing_run:
                print("No failing workflow found - CI may have passed")
                return True

            run_id = failing_run.get("databaseId")
            workflow_name = failing_run.get("name", "unknown")
            print(f"  Workflow '{workflow_name}' failed (run {run_id})")

            print("  Fetching failure logs...")
            failure_logs = self._git_repo.gh_client.get_workflow_failure_logs(run_id)

            head_before = self._git_repo.head_sha
            self._invoke_claude_for_fix(run_id, workflow_name, failure_logs)

            if not self._git_repo.head_advanced_since(head_before):
                print("  Claude did not make any commits")
                continue

            passed = self._push_and_wait_for_ci(current_sha)
            if passed:
                return True
            current_sha = self._git_repo.head_sha

        print(f"Max retries ({max_retries}) exceeded")
        return False

    def _push_and_wait_for_ci(self, current_sha):
        print("  Pushing fix...")
        if not self._git_repo.push():
            print("  Error: Could not push fix", file=sys.stderr)
            return False

        current_sha = self._git_repo.head_sha
        print("  Waiting for CI to complete...")
        ci_success, new_failing_run = self._git_repo.gh_client.wait_for_workflow_completion(
            self._git_repo.branch, current_sha,
        )

        if ci_success:
            print("  CI passed!")
            return True

        if new_failing_run:
            print(f"  CI still failing: {new_failing_run.get('name', 'unknown')}")
        return False

    def _invoke_claude_for_fix(self, run_id, workflow_name, failure_logs):
        """Build and run the Claude command for a CI fix."""
        interactive = not self._opts.non_interactive

        if self._opts.mock_claude:
            claude_cmd = [self._opts.mock_claude, f"fix-ci-{run_id}"]
        else:
            claude_cmd = CommandBuilder().build_ci_fix_command(
                run_id, workflow_name, failure_logs, interactive=interactive,
            )

        print("  Invoking Claude to fix CI failure...")
        self._claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)
