"""Tests for GitHub PR management in implement-with-worktree."""

import pytest

from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task


@pytest.mark.unit
class TestPRTitleGeneration:
    """Test PR title generation from slice name."""

    def test_generate_pr_title(self):
        """Should generate PR title from idea and slice name."""
        from i2code.implement.pr_helpers import generate_pr_title

        title = generate_pr_title("my-feature", "01-project-setup")
        assert title == "[my-feature] 01-project-setup"

    def test_generate_pr_title_preserves_slice_name(self):
        """PR title should preserve the full slice name."""
        from i2code.implement.pr_helpers import generate_pr_title

        title = generate_pr_title("wt-pr-based-development", "03-feedback-handling")
        assert title == "[wt-pr-based-development] 03-feedback-handling"


@pytest.mark.unit
class TestPRBodyGeneration:
    """Test PR body generation."""

    def test_generate_pr_body(self):
        """Should generate PR body with idea directory reference."""
        from i2code.implement.pr_helpers import generate_pr_body

        body = generate_pr_body(
            idea_directory="docs/features/my-feature",
            idea_name="my-feature",
            slice_number=1
        )

        assert "docs/features/my-feature" in body
        assert "my-feature" in body
        assert "slice 1" in body.lower() or "slice #1" in body.lower()


@pytest.mark.unit
class TestEnsurePrOnGitRepository:
    """Test GitRepository.ensure_pr() orchestration with FakeGitHubClient."""

    def test_ensure_pr_raises_on_creation_failure(self, test_git_repo_with_commit):
        """ensure_pr should raise when PR creation fails."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.git_repository import GitRepository

        class FailingFakeClient(FakeGitHubClient):
            def create_draft_pr(self, *args, **kwargs):
                raise RuntimeError("PR creation failed")

        tmpdir, repo = test_git_repo_with_commit
        fake = FailingFakeClient()
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        with pytest.raises(RuntimeError):
            git_repo.ensure_pr("/path/to/idea", "test", 1)

    def test_ensure_pr_uses_default_branch_from_gh_client(self, test_git_repo_with_commit):
        """ensure_pr should fetch default branch from gh_client."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.git_repository import GitRepository

        tmpdir, repo = test_git_repo_with_commit
        fake = FakeGitHubClient()
        fake.set_next_pr_number(42)
        fake.set_default_branch("develop")
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        git_repo.ensure_pr("/path/to/idea", "test", 1)

        assert len(fake._created_prs) == 1
        assert fake._created_prs[0]["base"] == "develop"

    def test_ensure_pr_reuses_existing_pr(self, test_git_repo_with_commit):
        """ensure_pr should return existing PR number if one exists."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.git_repository import GitRepository

        tmpdir, repo = test_git_repo_with_commit
        fake = FakeGitHubClient()
        fake.set_pr_list([{"number": 77, "headRefName": "idea/test/01-setup"}])
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        result = git_repo.ensure_pr("/path/to/idea", "test", 1)

        assert result == 77
        assert len(fake._created_prs) == 0


@pytest.mark.unit
class TestDeferredPRCreation:
    """Test that PR creation is deferred until after first push."""

    def test_setup_only_does_not_create_pr(self, monkeypatch, tmp_path):
        """Running with --setup-only should NOT attempt to create a PR."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd
        from fake_github_client import FakeGitHubClient
        from unittest.mock import MagicMock

        # Mock all the setup functions to avoid real git/github operations
        monkeypatch.setattr("i2code.implement.implement_command.validate_idea_files_committed", lambda p: None)

        # Mock git operations
        class MockRepo:
            working_tree_dir = str(tmp_path)
            branches = []
            heads = {}
            def create_head(self, name, ref=None):
                pass
            class git:
                @staticmethod
                def worktree(*args):
                    pass
                @staticmethod
                def checkout(*args):
                    pass

        monkeypatch.setattr("i2code.implement.cli.Repo", lambda *args, **kwargs: MockRepo())

        # Also patch the cli module's imported references
        mock_project = MagicMock()
        mock_project.name = "test-idea"
        mock_project.directory = str(tmp_path)
        mock_project.plan_file = str(tmp_path / "test-idea-plan.md")
        mock_project.validate.return_value = mock_project
        mock_project.validate_files.return_value = None
        mock_wt_project = MagicMock()
        mock_wt_project.plan_file = str(tmp_path / "worktree" / "test-idea" / "test-idea-plan.md")
        mock_project.worktree_idea_project = MagicMock(return_value=mock_wt_project)
        monkeypatch.setattr("i2code.implement.cli.IdeaProject", lambda x: mock_project)
        _mock_state = MagicMock(slice_number=1, processed_comment_ids=[], processed_review_ids=[], processed_conversation_ids=[])
        mock_project.get_next_task.return_value = NumberedTask(
            number=TaskNumber(thread=1, task=1),
            task=Task(_lines=["- [ ] **Task 1.1: test-task**"]),
        )
        monkeypatch.setattr("i2code.implement.implement_command.WorkflowState.load", lambda x: _mock_state)
        monkeypatch.setattr("i2code.implement.cli.GitHubClient", lambda: FakeGitHubClient())

        # Track if GitRepository.ensure_pr was called
        mock_git_repo = MagicMock()
        mock_git_repo.ensure_pr = MagicMock(return_value=123)
        monkeypatch.setattr("i2code.implement.cli.GitRepository", lambda *a, **kw: mock_git_repo)
        monkeypatch.setattr("i2code.implement.implement_command.ensure_claude_permissions", lambda x: None)

        # Run via Click test runner
        runner = CliRunner(catch_exceptions=False)
        _result = runner.invoke(implement_cmd, [str(tmp_path), "--setup-only"])

        # Verify ensure_pr was NOT called on the GitRepository
        mock_git_repo.ensure_pr.assert_not_called()


@pytest.mark.unit
class TestFormatAllFeedback:
    """Test formatting all feedback types for Claude."""

    def test_format_all_feedback_includes_reviews(self):
        """Should format PR reviews with state and body."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        reviews = [
            {"id": 1, "state": "CHANGES_REQUESTED", "body": "Please fix the tests",
             "user": {"login": "reviewer1"}}
        ]

        result = PullRequestReviewProcessor._format_all_feedback([], reviews, [])

        assert "## PR Reviews" in result
        assert "CHANGES_REQUESTED" in result
        assert "Please fix the tests" in result
        assert "reviewer1" in result

    def test_format_all_feedback_includes_review_comments(self):
        """Should format review comments with file path and line."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        review_comments = [
            {"id": 2, "body": "This variable name is unclear",
             "path": "src/main.py", "line": 42, "user": {"login": "reviewer2"}}
        ]

        result = PullRequestReviewProcessor._format_all_feedback(review_comments, [], [])

        assert "## Review Comments" in result
        assert "src/main.py:42" in result
        assert "This variable name is unclear" in result

    def test_format_all_feedback_includes_conversation_comments(self):
        """Should format general PR comments."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        conversation_comments = [
            {"id": 3, "body": "Great work overall!", "user": {"login": "lead"}}
        ]

        result = PullRequestReviewProcessor._format_all_feedback([], [], conversation_comments)

        assert "## General PR Comments" in result
        assert "Great work overall!" in result
        assert "lead" in result

    def test_format_all_feedback_combines_all_types(self):
        """Should combine all feedback types into one formatted string."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        reviews = [{"id": 1, "state": "APPROVED", "body": "LGTM", "user": {"login": "r1"}}]
        review_comments = [{"id": 2, "body": "Nitpick", "path": "a.py", "line": 1, "user": {"login": "r2"}}]
        conversation_comments = [{"id": 3, "body": "Thanks", "user": {"login": "r3"}}]

        result = PullRequestReviewProcessor._format_all_feedback(review_comments, reviews, conversation_comments)

        assert "## PR Reviews" in result
        assert "## Review Comments" in result
        assert "## General PR Comments" in result



@pytest.mark.unit
class TestGetNewFeedback:
    """Test filtering feedback to unprocessed items."""

    def test_get_new_feedback_filters_processed(self):
        """Should filter out already processed feedback."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        all_feedback = [
            {"id": 1, "body": "Old comment"},
            {"id": 2, "body": "New comment"},
            {"id": 3, "body": "Another new comment"}
        ]
        processed_ids = [1]

        new_feedback = PullRequestReviewProcessor._get_new_feedback(all_feedback, processed_ids)

        assert len(new_feedback) == 2
        assert all(f["id"] in [2, 3] for f in new_feedback)

    def test_get_new_feedback_returns_all_when_none_processed(self):
        """Should return all feedback when nothing processed yet."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        all_feedback = [
            {"id": 1, "body": "Comment 1"},
            {"id": 2, "body": "Comment 2"}
        ]

        new_feedback = PullRequestReviewProcessor._get_new_feedback(all_feedback, [])

        assert len(new_feedback) == 2

    def test_get_new_feedback_returns_empty_when_all_processed(self):
        """Should return empty list when all feedback processed."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        all_feedback = [{"id": 1, "body": "Comment"}]
        processed_ids = [1]

        new_feedback = PullRequestReviewProcessor._get_new_feedback(all_feedback, processed_ids)

        assert new_feedback == []


@pytest.mark.unit
class TestParseTriageResult:
    """Test parsing JSON triage result from Claude."""

    def test_parse_triage_result_with_json_code_block(self):
        """Should parse JSON from markdown code block."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
        parse_triage_result = PullRequestReviewProcessor._parse_triage_result

        output = '''Here's the triage:
```json
{
  "will_fix": [{"comment_ids": [1, 2], "description": "Fix typo"}],
  "needs_clarification": []
}
```
'''
        result = parse_triage_result(output)

        assert result is not None
        assert len(result["will_fix"]) == 1
        assert result["will_fix"][0]["comment_ids"] == [1, 2]

    def test_parse_triage_result_with_plain_json(self):
        """Should parse plain JSON output."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
        parse_triage_result = PullRequestReviewProcessor._parse_triage_result

        output = '{"will_fix": [], "needs_clarification": [{"comment_id": 5, "question": "What?"}]}'
        result = parse_triage_result(output)

        assert result is not None
        assert len(result["needs_clarification"]) == 1
        assert result["needs_clarification"][0]["comment_id"] == 5

    def test_parse_triage_result_returns_none_on_invalid(self):
        """Should return None for invalid JSON."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
        parse_triage_result = PullRequestReviewProcessor._parse_triage_result

        result = parse_triage_result("This is not JSON at all")

        assert result is None


@pytest.mark.unit
class TestGetFeedbackByIds:
    """Test filtering feedback by IDs."""

    def test_get_feedback_by_ids_returns_matching(self):
        """Should return only feedback with matching IDs."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        all_feedback = [
            {"id": 1, "body": "Comment 1"},
            {"id": 2, "body": "Comment 2"},
            {"id": 3, "body": "Comment 3"}
        ]

        result = PullRequestReviewProcessor._get_feedback_by_ids(all_feedback, [1, 3])

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3

    def test_get_feedback_by_ids_returns_empty_for_no_matches(self):
        """Should return empty list when no IDs match."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        all_feedback = [{"id": 1, "body": "Comment"}]

        result = PullRequestReviewProcessor._get_feedback_by_ids(all_feedback, [99])

        assert result == []


@pytest.mark.unit
class TestDetermineCommentType:
    """Test determining comment type from ID."""

    def test_determine_comment_type_review(self):
        """Should return 'review' for review comment IDs."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        review_comments = [{"id": 100, "body": "Review comment"}]
        conversation_comments = [{"id": 200, "body": "General comment"}]

        result = PullRequestReviewProcessor._determine_comment_type(100, review_comments, conversation_comments)

        assert result == "review"

    def test_determine_comment_type_conversation(self):
        """Should return 'conversation' for non-review comment IDs."""
        from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

        review_comments = [{"id": 100, "body": "Review comment"}]
        conversation_comments = [{"id": 200, "body": "General comment"}]

        result = PullRequestReviewProcessor._determine_comment_type(200, review_comments, conversation_comments)

        assert result == "conversation"
