"""Tests for GithubActionsMonitor class."""

import pytest

from i2code.implement.github_actions_monitor import GithubActionsMonitor

from fake_github_client import FakeGitHubClient


@pytest.mark.unit
class TestGithubActionsMonitorWaitForCI:
    """GithubActionsMonitor.wait_for_ci(branch, head_sha) delegates to gh_client or skips."""

    def test_wait_for_ci_delegates_to_gh_client(self, capsys):
        fake_gh = FakeGitHubClient()
        fake_gh.set_workflow_completion_result(
            "idea/test/01-setup", "abc123", (True, None),
        )
        monitor = GithubActionsMonitor(
            gh_client=fake_gh, skip_ci_wait=False, ci_timeout=300,
        )

        monitor.wait_for_ci("idea/test/01-setup", "abc123")

        assert ("wait_for_workflow_completion", "idea/test/01-setup", "abc123") in fake_gh.calls

        captured = capsys.readouterr()
        assert "Waiting for CI" in captured.out
        assert "CI passed" in captured.out

    def test_wait_for_ci_passes_timeout_to_gh_client(self):
        """Verify the ci_timeout is passed through to wait_for_workflow_completion."""
        calls_with_timeout = []

        class TimeoutCapturingClient(FakeGitHubClient):
            def wait_for_workflow_completion(self, branch, sha, timeout_seconds=600):
                calls_with_timeout.append(timeout_seconds)
                return (True, None)

        fake_gh = TimeoutCapturingClient()
        monitor = GithubActionsMonitor(
            gh_client=fake_gh, skip_ci_wait=False, ci_timeout=300,
        )

        monitor.wait_for_ci("idea/test/01-setup", "abc123")

        assert calls_with_timeout == [300]

    def test_wait_for_ci_skips_when_skip_ci_wait_is_true(self):
        fake_gh = FakeGitHubClient()
        monitor = GithubActionsMonitor(
            gh_client=fake_gh, skip_ci_wait=True, ci_timeout=300,
        )

        monitor.wait_for_ci("idea/test/01-setup", "abc123")

        assert not any(c[0] == "wait_for_workflow_completion" for c in fake_gh.calls)

    def test_wait_for_ci_reports_failure(self, capsys):
        fake_gh = FakeGitHubClient()
        fake_gh.set_workflow_completion_result(
            "idea/test/01-setup", "abc123", (False, {"name": "Build"}),
        )
        monitor = GithubActionsMonitor(
            gh_client=fake_gh, skip_ci_wait=False, ci_timeout=600,
        )

        monitor.wait_for_ci("idea/test/01-setup", "abc123")

        captured = capsys.readouterr()
        assert "CI failed: Build" in captured.out
