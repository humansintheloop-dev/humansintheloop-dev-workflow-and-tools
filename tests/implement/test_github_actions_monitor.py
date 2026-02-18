"""Tests for GithubActionsMonitor class."""

import pytest

from i2code.implement.github_actions_monitor import GithubActionsMonitor

from fake_git_repository import FakeGitRepository


@pytest.mark.unit
class TestGithubActionsMonitorWaitForCI:
    """GithubActionsMonitor.wait_for_ci() delegates to git_repo or skips."""

    def test_wait_for_ci_delegates_to_git_repo(self, capsys):
        fake_repo = FakeGitRepository()
        monitor = GithubActionsMonitor(
            git_repo=fake_repo, skip_ci_wait=False, ci_timeout=300,
        )

        monitor.wait_for_ci()

        assert any(c[0] == "wait_for_ci" for c in fake_repo.calls)
        # Verify timeout was passed through
        wait_call = [c for c in fake_repo.calls if c[0] == "wait_for_ci"][0]
        assert wait_call[1] == 300

        captured = capsys.readouterr()
        assert "Waiting for CI" in captured.out
        assert "CI passed" in captured.out

    def test_wait_for_ci_skips_when_skip_ci_wait_is_true(self, capsys):
        fake_repo = FakeGitRepository()
        monitor = GithubActionsMonitor(
            git_repo=fake_repo, skip_ci_wait=True, ci_timeout=300,
        )

        monitor.wait_for_ci()

        assert not any(c[0] == "wait_for_ci" for c in fake_repo.calls)

    def test_wait_for_ci_reports_failure(self, capsys):
        fake_repo = FakeGitRepository()
        fake_repo.wait_for_ci = lambda timeout_seconds=600: (
            fake_repo.calls.append(("wait_for_ci", timeout_seconds))
            or (False, {"name": "Build"})
        )
        monitor = GithubActionsMonitor(
            git_repo=fake_repo, skip_ci_wait=False, ci_timeout=600,
        )

        monitor.wait_for_ci()

        captured = capsys.readouterr()
        assert "CI failed: Build" in captured.out
