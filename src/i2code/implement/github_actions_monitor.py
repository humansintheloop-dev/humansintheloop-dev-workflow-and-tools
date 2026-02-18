"""GithubActionsMonitor: waits for CI completion and reports results."""


class GithubActionsMonitor:
    """Monitors GitHub Actions CI status for a branch.

    Args:
        gh_client: GitHubClient (or FakeGitHubClient) for CI operations.
        skip_ci_wait: When True, skip waiting for CI entirely.
        ci_timeout: Timeout in seconds for CI completion.
    """

    def __init__(self, gh_client, skip_ci_wait, ci_timeout):
        self._gh_client = gh_client
        self._skip_ci_wait = skip_ci_wait
        self._ci_timeout = ci_timeout

    def wait_for_ci(self, branch, head_sha):
        """Wait for CI completion if configured."""
        if not self._skip_ci_wait:
            print("Waiting for CI to complete...")
            ci_success, failing_run = self._gh_client.wait_for_workflow_completion(
                branch, head_sha, timeout_seconds=self._ci_timeout,
            )

            if not ci_success and failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"CI failed: {workflow_name}. Will fix on next iteration.")
            elif ci_success:
                print("CI passed!")
