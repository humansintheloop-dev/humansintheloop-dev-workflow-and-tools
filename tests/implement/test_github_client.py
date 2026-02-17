"""Tests for GitHubClient class."""

import json

import pytest

from fake_github_client import FakeGitHubClient


@pytest.mark.unit
class TestFakeGitHubClientConformance:
    """Verify FakeGitHubClient has the same interface as GitHubClient."""

    def test_fake_has_same_methods_as_real(self):
        from i2code.implement.github_client import GitHubClient

        real_methods = {"find_pr", "create_draft_pr", "is_pr_draft",
                        "get_pr_state", "get_pr_url", "mark_pr_ready"}

        for method in real_methods:
            assert hasattr(GitHubClient, method), f"GitHubClient missing {method}"
            assert hasattr(FakeGitHubClient, method), f"FakeGitHubClient missing {method}"


@pytest.mark.unit
class TestGitHubClientFindPR:
    """Test GitHubClient.find_pr() via subprocess."""

    def test_find_pr_returns_number_when_found(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        pr_list = [
            {"number": 42, "headRefName": "idea/test/01-setup", "isDraft": True},
            {"number": 99, "headRefName": "other-branch", "isDraft": False},
        ]

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps(pr_list)
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.find_pr("idea/test/01-setup") == 42

    def test_find_pr_returns_none_when_not_found(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps([{"number": 99, "headRefName": "other"}])
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.find_pr("idea/test/01-setup") is None

    def test_find_pr_returns_none_on_gh_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                stderr = "error"
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.find_pr("idea/test/01-setup") is None


@pytest.mark.unit
class TestGitHubClientCreateDraftPR:
    """Test GitHubClient.create_draft_pr()."""

    def test_create_draft_pr_returns_pr_number(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = "https://github.com/owner/repo/pull/55\n"
                stderr = ""
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        pr_number = client.create_draft_pr("idea/test/01-setup", "Title", "Body", "main")
        assert pr_number == 55

    def test_create_draft_pr_raises_on_failure(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                stderr = "No commits between main and branch"
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        with pytest.raises(RuntimeError, match="No commits"):
            client.create_draft_pr("idea/test/01-setup", "Title", "Body", "main")


@pytest.mark.unit
class TestGitHubClientIsPRDraft:
    """Test GitHubClient.is_pr_draft()."""

    def test_is_pr_draft_returns_true_for_draft(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps({"isDraft": True})
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.is_pr_draft(42) is True

    def test_is_pr_draft_returns_false_for_ready(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps({"isDraft": False})
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.is_pr_draft(42) is False

    def test_is_pr_draft_returns_false_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.is_pr_draft(42) is False


@pytest.mark.unit
class TestGitHubClientGetPRState:
    """Test GitHubClient.get_pr_state()."""

    def test_get_pr_state_returns_state(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps({"state": "OPEN"})
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.get_pr_state(42) == "OPEN"

    def test_get_pr_state_returns_empty_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.get_pr_state(42) == ""


@pytest.mark.unit
class TestGitHubClientGetPRUrl:
    """Test GitHubClient.get_pr_url()."""

    def test_get_pr_url_returns_url(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = "https://github.com/owner/repo/pull/42\n"
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.get_pr_url(42) == "https://github.com/owner/repo/pull/42"

    def test_get_pr_url_returns_empty_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.get_pr_url(42) == ""


@pytest.mark.unit
class TestGitHubClientMarkPRReady:
    """Test GitHubClient.mark_pr_ready()."""

    def test_mark_pr_ready_returns_true_on_success(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.mark_pr_ready(42) is True

    def test_mark_pr_ready_returns_false_on_failure(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.mark_pr_ready(42) is False


@pytest.mark.unit
class TestGitHubClientRunGhHelper:
    """Test that GitHubClient uses _run_gh() internally."""

    def test_run_gh_used_for_all_operations(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        assert hasattr(GitHubClient, '_run_gh'), "GitHubClient must have _run_gh() helper"


@pytest.mark.unit
class TestFakeGitHubClient:
    """Test FakeGitHubClient behavior matches expected interface."""

    def test_find_pr_with_matching_branch(self):
        fake = FakeGitHubClient()
        fake.set_pr_list([{"number": 42, "headRefName": "my-branch", "isDraft": True}])
        assert fake.find_pr("my-branch") == 42

    def test_find_pr_no_match(self):
        fake = FakeGitHubClient()
        fake.set_pr_list([{"number": 42, "headRefName": "other-branch"}])
        assert fake.find_pr("my-branch") is None

    def test_create_draft_pr(self):
        fake = FakeGitHubClient()
        fake.set_next_pr_number(77)
        pr = fake.create_draft_pr("branch", "Title", "Body", "main")
        assert pr == 77

    def test_is_pr_draft(self):
        fake = FakeGitHubClient()
        fake.set_pr_view(42, {"isDraft": True})
        assert fake.is_pr_draft(42) is True
        assert fake.is_pr_draft(99) is False

    def test_get_pr_state(self):
        fake = FakeGitHubClient()
        fake.set_pr_state(42, "OPEN")
        assert fake.get_pr_state(42) == "OPEN"
        assert fake.get_pr_state(99) == ""

    def test_get_pr_url(self):
        fake = FakeGitHubClient()
        fake.set_pr_url(42, "https://github.com/owner/repo/pull/42")
        assert fake.get_pr_url(42) == "https://github.com/owner/repo/pull/42"
        assert fake.get_pr_url(99) == ""

    def test_mark_pr_ready(self):
        fake = FakeGitHubClient()
        assert fake.mark_pr_ready(42) is True
        assert 42 in fake._ready_prs

    def test_calls_are_recorded(self):
        fake = FakeGitHubClient()
        fake.find_pr("branch")
        fake.is_pr_draft(42)
        assert fake.calls == [("find_pr", "branch"), ("is_pr_draft", 42)]
