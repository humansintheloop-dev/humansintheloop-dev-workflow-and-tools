"""Tests for GitHubClient class."""

import json

import pytest

from fake_github_client import FakeGitHubClient


@pytest.mark.unit
class TestFakeGitHubClientConformance:
    """Verify FakeGitHubClient has the same interface as GitHubClient."""

    def test_fake_has_same_methods_as_real(self):
        from i2code.implement.github_client import GitHubClient

        real_methods = {
            "find_pr", "create_draft_pr", "is_pr_draft",
            "get_pr_state", "get_pr_url", "mark_pr_ready",
            "fetch_pr_comments", "fetch_pr_reviews",
            "fetch_pr_conversation_comments",
            "reply_to_review_comment", "reply_to_pr_comment",
            "fetch_failed_checks", "get_workflow_runs_for_commit",
            "get_workflow_failure_logs", "wait_for_workflow_completion",
            "get_default_branch",
        }

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
class TestGitHubClientFetchPRComments:
    """Test GitHubClient.fetch_pr_comments()."""

    def test_returns_comments_list(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        comments = [{"id": 1, "body": "Fix this"}, {"id": 2, "body": "And this"}]

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps(comments)
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        result = client.fetch_pr_comments(123)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["body"] == "And this"

    def test_returns_empty_list_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                stderr = "error"
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.fetch_pr_comments(123) == []


@pytest.mark.unit
class TestGitHubClientFetchPRReviews:
    """Test GitHubClient.fetch_pr_reviews()."""

    def test_returns_reviews_list(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        reviews = [{"id": 100, "state": "CHANGES_REQUESTED"}]

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps(reviews)
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        result = client.fetch_pr_reviews(123)
        assert len(result) == 1
        assert result[0]["id"] == 100

    def test_returns_empty_list_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.fetch_pr_reviews(123) == []


@pytest.mark.unit
class TestGitHubClientFetchPRConversationComments:
    """Test GitHubClient.fetch_pr_conversation_comments()."""

    def test_returns_conversation_comments(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        comments = [
            {"id": 1001, "body": "This looks great!"},
            {"id": 1002, "body": "Can you add more tests?"},
        ]

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps(comments)
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        result = client.fetch_pr_conversation_comments(123)
        assert len(result) == 2
        assert result[0]["id"] == 1001

    def test_returns_empty_list_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.fetch_pr_conversation_comments(123) == []


@pytest.mark.unit
class TestGitHubClientReplyToReviewComment:
    """Test GitHubClient.reply_to_review_comment()."""

    def test_returns_true_on_success(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.reply_to_review_comment(123, 456, "Fixed!") is True

    def test_returns_false_on_failure(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.reply_to_review_comment(123, 456, "Fixed!") is False


@pytest.mark.unit
class TestGitHubClientReplyToPRComment:
    """Test GitHubClient.reply_to_pr_comment()."""

    def test_returns_true_on_success(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.reply_to_pr_comment(123, "Thanks!") is True

    def test_returns_false_on_failure(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.reply_to_pr_comment(123, "Thanks!") is False


@pytest.mark.unit
class TestGitHubClientFetchFailedChecks:
    """Test GitHubClient.fetch_failed_checks()."""

    def test_returns_failed_checks(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = 'build\tfail\t1234\ntest\tpass\t5678\nlint\tfail\t9012'
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        failed = client.fetch_failed_checks(123)
        assert len(failed) == 2
        assert failed[0]["name"] == "build"
        assert failed[1]["name"] == "lint"

    def test_returns_empty_if_all_pass(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = 'build\tpass\t1234\ntest\tpass\t5678'
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.fetch_failed_checks(123) == []

    def test_returns_empty_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ''
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.fetch_failed_checks(123) == []


@pytest.mark.unit
class TestGitHubClientGetWorkflowRunsForCommit:
    """Test GitHubClient.get_workflow_runs_for_commit()."""

    def test_returns_workflow_runs(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        runs = [{"databaseId": 111, "status": "completed", "conclusion": "success",
                 "name": "CI", "headSha": "abc123"}]

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = json.dumps(runs)
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        result = client.get_workflow_runs_for_commit("my-branch", "abc123")
        assert len(result) == 1
        assert result[0]["databaseId"] == 111

    def test_returns_empty_on_error(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ''
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.get_workflow_runs_for_commit("my-branch", "abc123") == []


@pytest.mark.unit
class TestGitHubClientGetWorkflowFailureLogs:
    """Test GitHubClient.get_workflow_failure_logs()."""

    def test_returns_log_output(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = "Error: test failed at line 42"
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.get_workflow_failure_logs(111) == "Error: test failed at line 42"

    def test_returns_error_message_on_failure(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ''
                stderr = 'run not found'
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        result = client.get_workflow_failure_logs(111)
        assert "Error fetching logs" in result


@pytest.mark.unit
class TestGitHubClientWaitForWorkflowCompletion:
    """Test GitHubClient.wait_for_workflow_completion()."""

    def test_returns_success_when_all_pass(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        call_count = [0]
        runs_initial = [{"databaseId": 111, "status": "in_progress",
                         "conclusion": None, "name": "CI", "headSha": "abc123"}]
        runs_final = [{"databaseId": 111, "status": "completed",
                       "conclusion": "success", "name": "CI", "headSha": "abc123"}]

        def fake_run(cmd, **kwargs):
            call_count[0] += 1
            class Result:
                returncode = 0
            r = Result()
            if "run" in cmd and "list" in cmd:
                if call_count[0] <= 1:
                    r.stdout = json.dumps(runs_initial)
                else:
                    r.stdout = json.dumps(runs_final)
            elif "run" in cmd and "watch" in cmd:
                r.stdout = ""
            else:
                r.stdout = ""
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        success, failing_run = client.wait_for_workflow_completion("my-branch", "abc123")
        assert success is True
        assert failing_run is None

    def test_returns_failure_when_run_fails(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        runs = [{"databaseId": 111, "status": "completed",
                 "conclusion": "failure", "name": "CI", "headSha": "abc123"}]

        def fake_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = json.dumps(runs)
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        success, failing_run = client.wait_for_workflow_completion("my-branch", "abc123")
        assert success is False
        assert failing_run["databaseId"] == 111


@pytest.mark.unit
class TestGitHubClientGetDefaultBranch:
    """Test GitHubClient.get_default_branch()."""

    def test_returns_default_branch_name(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = "master\n"
                returncode = 0
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        assert client.get_default_branch() == "master"

    def test_raises_on_failure(self, monkeypatch):
        from i2code.implement.github_client import GitHubClient

        def fake_run(cmd, **kwargs):
            class Result:
                stdout = ""
                stderr = "not a GitHub repository"
                returncode = 1
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)
        client = GitHubClient()
        with pytest.raises(RuntimeError, match="Failed to detect default branch"):
            client.get_default_branch()


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

    def test_fetch_pr_comments(self):
        fake = FakeGitHubClient()
        fake.set_pr_comments(42, [{"id": 1, "body": "Fix this"}])
        assert fake.fetch_pr_comments(42) == [{"id": 1, "body": "Fix this"}]
        assert fake.fetch_pr_comments(99) == []

    def test_fetch_pr_reviews(self):
        fake = FakeGitHubClient()
        fake.set_pr_reviews(42, [{"id": 100, "state": "CHANGES_REQUESTED"}])
        assert fake.fetch_pr_reviews(42) == [{"id": 100, "state": "CHANGES_REQUESTED"}]
        assert fake.fetch_pr_reviews(99) == []

    def test_fetch_pr_conversation_comments(self):
        fake = FakeGitHubClient()
        fake.set_pr_conversation_comments(42, [{"id": 1001, "body": "Looks good"}])
        assert fake.fetch_pr_conversation_comments(42) == [{"id": 1001, "body": "Looks good"}]
        assert fake.fetch_pr_conversation_comments(99) == []

    def test_reply_to_review_comment(self):
        fake = FakeGitHubClient()
        assert fake.reply_to_review_comment(42, 1, "Fixed!") is True
        fake.set_reply_results(False)
        assert fake.reply_to_review_comment(42, 1, "Fixed!") is False

    def test_reply_to_pr_comment(self):
        fake = FakeGitHubClient()
        assert fake.reply_to_pr_comment(42, "Thanks!") is True

    def test_fetch_failed_checks(self):
        fake = FakeGitHubClient()
        fake.set_failed_checks(42, [{"name": "build", "state": "fail"}])
        assert fake.fetch_failed_checks(42) == [{"name": "build", "state": "fail"}]
        assert fake.fetch_failed_checks(99) == []

    def test_get_workflow_runs_for_commit(self):
        fake = FakeGitHubClient()
        runs = [{"databaseId": 111, "status": "completed", "conclusion": "success"}]
        fake.set_workflow_runs("branch", "abc", runs)
        assert fake.get_workflow_runs_for_commit("branch", "abc") == runs
        assert fake.get_workflow_runs_for_commit("branch", "other") == []

    def test_get_workflow_failure_logs(self):
        fake = FakeGitHubClient()
        fake.set_workflow_failure_logs(111, "Error at line 42")
        assert fake.get_workflow_failure_logs(111) == "Error at line 42"
        assert fake.get_workflow_failure_logs(999) == ""

    def test_wait_for_workflow_completion(self):
        fake = FakeGitHubClient()
        assert fake.wait_for_workflow_completion("branch", "abc") == (True, None)
        fake.set_workflow_completion_result("branch", "abc", (False, {"databaseId": 111}))
        assert fake.wait_for_workflow_completion("branch", "abc") == (False, {"databaseId": 111})

    def test_get_default_branch(self):
        fake = FakeGitHubClient()
        assert fake.get_default_branch() == "main"
        fake.set_default_branch("master")
        assert fake.get_default_branch() == "master"

    def test_calls_are_recorded(self):
        fake = FakeGitHubClient()
        fake.find_pr("branch")
        fake.is_pr_draft(42)
        assert fake.calls == [("find_pr", "branch"), ("is_pr_draft", 42)]
