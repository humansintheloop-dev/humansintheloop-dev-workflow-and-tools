"""GithubActionsMonitor: waits for CI completion and reports results."""


class GithubActionsMonitor:
    """Monitors GitHub Actions CI status for a branch.

    Args:
        git_repo: GitRepository (or FakeGitRepository) for CI operations.
        skip_ci_wait: When True, skip waiting for CI entirely.
        ci_timeout: Timeout in seconds for CI completion.
    """

    def __init__(self, git_repo, skip_ci_wait, ci_timeout):
        self._git_repo = git_repo
        self._skip_ci_wait = skip_ci_wait
        self._ci_timeout = ci_timeout

    def wait_for_ci(self):
        """Wait for CI completion if configured."""
        if not self._skip_ci_wait:
            print("Waiting for CI to complete...")
            ci_success, failing_run = self._git_repo.wait_for_ci(
                timeout_seconds=self._ci_timeout,
            )

            if not ci_success and failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"CI failed: {workflow_name}. Will fix on next iteration.")
            elif ci_success:
                print("CI passed!")
