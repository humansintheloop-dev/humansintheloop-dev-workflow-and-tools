"""Tests for GitHub PR management in implement-with-worktree."""

import json
import os
import sys
import subprocess
import tempfile
import pytest

from git import Repo

# Add workflow-scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../workflow-scripts'))


@pytest.mark.unit
class TestPRTitleGeneration:
    """Test PR title generation from slice name."""

    def test_generate_pr_title(self):
        """Should generate PR title from idea and slice name."""
        from implement_with_worktree import generate_pr_title

        title = generate_pr_title("my-feature", "01-project-setup")
        assert title == "[my-feature] 01-project-setup"

    def test_generate_pr_title_preserves_slice_name(self):
        """PR title should preserve the full slice name."""
        from implement_with_worktree import generate_pr_title

        title = generate_pr_title("wt-pr-based-development", "03-feedback-handling")
        assert title == "[wt-pr-based-development] 03-feedback-handling"


@pytest.mark.unit
class TestPRBodyGeneration:
    """Test PR body generation."""

    def test_generate_pr_body(self):
        """Should generate PR body with idea directory reference."""
        from implement_with_worktree import generate_pr_body

        body = generate_pr_body(
            idea_directory="docs/features/my-feature",
            idea_name="my-feature",
            slice_number=1
        )

        assert "docs/features/my-feature" in body
        assert "my-feature" in body
        assert "slice 1" in body.lower() or "slice #1" in body.lower()


@pytest.mark.unit
class TestCheckExistingPR:
    """Test checking for existing PRs (mocked gh output)."""

    def test_find_existing_pr_returns_pr_number(self, monkeypatch):
        """Should return PR number if PR exists for branch."""
        from implement_with_worktree import find_existing_pr

        # Mock gh pr list output
        mock_output = json.dumps([
            {"number": 123, "headRefName": "idea/my-feature/01-project-setup", "isDraft": True},
            {"number": 456, "headRefName": "other-branch", "isDraft": False}
        ])

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        pr_number = find_existing_pr("idea/my-feature/01-project-setup")
        assert pr_number == 123

    def test_find_existing_pr_returns_none_when_not_found(self, monkeypatch):
        """Should return None if no PR exists for branch."""
        from implement_with_worktree import find_existing_pr

        # Mock gh pr list output with no matching PR
        mock_output = json.dumps([
            {"number": 456, "headRefName": "other-branch", "isDraft": False}
        ])

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        pr_number = find_existing_pr("idea/my-feature/01-project-setup")
        assert pr_number is None


@pytest.mark.unit
class TestCheckPRDraftState:
    """Test checking if PR is still in draft state."""

    def test_is_pr_draft_returns_true_for_draft(self, monkeypatch):
        """Should return True if PR is in draft state."""
        from implement_with_worktree import is_pr_draft

        mock_output = json.dumps({"isDraft": True})

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        assert is_pr_draft(123) is True

    def test_is_pr_draft_returns_false_for_ready(self, monkeypatch):
        """Should return False if PR is ready for review."""
        from implement_with_worktree import is_pr_draft

        mock_output = json.dumps({"isDraft": False})

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        assert is_pr_draft(123) is False


@pytest.mark.unit
class TestCreateDraftPRFailure:
    """Test that PR creation failure is treated as fatal error."""

    def test_create_draft_pr_raises_on_failure(self, monkeypatch):
        """Should raise RuntimeError when gh pr create fails."""
        from implement_with_worktree import create_draft_pr

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = ""
                stderr = "pull request create failed: GraphQL: No commits between main and branch"
                returncode = 1
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError) as excinfo:
            create_draft_pr("idea/test/01-setup", "Test PR", "Body", "main")

        assert "No commits" in str(excinfo.value) or "failed" in str(excinfo.value).lower()

    def test_ensure_draft_pr_raises_on_creation_failure(self, monkeypatch):
        """ensure_draft_pr should raise when PR creation fails."""
        from implement_with_worktree import ensure_draft_pr, find_existing_pr

        # Mock find_existing_pr to return None (no existing PR)
        def mock_find(*args, **kwargs):
            return None

        # Mock create_draft_pr to fail
        def mock_create(*args, **kwargs):
            raise RuntimeError("PR creation failed")

        monkeypatch.setattr("implement_with_worktree.find_existing_pr", mock_find)
        monkeypatch.setattr("implement_with_worktree.create_draft_pr", mock_create)

        with pytest.raises(RuntimeError):
            ensure_draft_pr("idea/test/01-setup", "/path/to/idea", "test", 1)


@pytest.mark.unit
class TestDeferredPRCreation:
    """Test that PR creation is deferred until after first push."""

    def test_setup_only_does_not_create_pr(self, monkeypatch, tmp_path):
        """Running with --setup-only should NOT attempt to create a PR."""
        from implement_with_worktree import main
        import builtins

        # Track if ensure_draft_pr was called
        ensure_draft_pr_called = False

        def mock_ensure_draft_pr(*args, **kwargs):
            nonlocal ensure_draft_pr_called
            ensure_draft_pr_called = True
            return 123

        # Mock all the setup functions to avoid real git/github operations
        monkeypatch.setattr("implement_with_worktree.validate_idea_directory", lambda x: "test-idea")
        monkeypatch.setattr("implement_with_worktree.validate_idea_files", lambda x, y: None)
        monkeypatch.setattr("implement_with_worktree.validate_idea_files_committed", lambda x, y: None)
        monkeypatch.setattr("implement_with_worktree.init_or_load_state", lambda x, y: {"slice_number": 1, "processed_comment_ids": [], "processed_review_ids": []})

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

        monkeypatch.setattr("implement_with_worktree.Repo", lambda *args, **kwargs: MockRepo())
        monkeypatch.setattr("implement_with_worktree.ensure_integration_branch", lambda r, n: "idea/test-idea/integration")
        monkeypatch.setattr("implement_with_worktree.ensure_worktree", lambda r, n, b: str(tmp_path / "worktree"))
        monkeypatch.setattr("implement_with_worktree.ensure_slice_branch", lambda r, n, s, t, i: "idea/test-idea/01-setup")

        # Create a minimal plan file in the expected location
        plan_file = tmp_path / "test-idea-plan.md"
        plan_file.write_text("# Plan\n- [ ] **Task 1.1: Test task**\n")

        # Mock open to return our plan file for plan file reads
        original_open = builtins.open
        def mock_open(*args, **kwargs):
            if args and "plan" in str(args[0]):
                return original_open(plan_file, *args[1:], **kwargs)
            return original_open(*args, **kwargs)
        monkeypatch.setattr("builtins.open", mock_open)

        # Mock the PR functions
        monkeypatch.setattr("implement_with_worktree.push_branch_to_remote", lambda x: True)
        monkeypatch.setattr("implement_with_worktree.find_existing_pr", lambda x: None)
        monkeypatch.setattr("implement_with_worktree.ensure_draft_pr", mock_ensure_draft_pr)

        # Mock sys.argv for --setup-only
        monkeypatch.setattr("sys.argv", ["implement-with-worktree.sh", str(tmp_path), "--setup-only"])

        # Run main
        try:
            main()
        except SystemExit:
            pass

        # Verify ensure_draft_pr was NOT called
        assert not ensure_draft_pr_called, "ensure_draft_pr should not be called in --setup-only mode"


@pytest.mark.unit
class TestFetchPRConversationComments:
    """Test fetching general PR conversation comments."""

    def test_fetch_pr_conversation_comments_returns_comments(self, monkeypatch):
        """Should return list of conversation comments."""
        from implement_with_worktree import fetch_pr_conversation_comments

        mock_output = json.dumps([
            {"id": 1001, "body": "This looks great!", "user": {"login": "reviewer1"}},
            {"id": 1002, "body": "Can you add more tests?", "user": {"login": "reviewer2"}}
        ])

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        comments = fetch_pr_conversation_comments(123)
        assert len(comments) == 2
        assert comments[0]["id"] == 1001
        assert comments[1]["body"] == "Can you add more tests?"

    def test_fetch_pr_conversation_comments_returns_empty_on_error(self, monkeypatch):
        """Should return empty list on API error."""
        from implement_with_worktree import fetch_pr_conversation_comments

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = ""
                stderr = "API error"
                returncode = 1
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        comments = fetch_pr_conversation_comments(123)
        assert comments == []


@pytest.mark.unit
class TestGetPRUrl:
    """Test getting PR URL."""

    def test_get_pr_url_returns_url(self, monkeypatch):
        """Should return the PR URL."""
        from implement_with_worktree import get_pr_url

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "https://github.com/owner/repo/pull/123\n"
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        url = get_pr_url(123)
        assert url == "https://github.com/owner/repo/pull/123"

    def test_get_pr_url_returns_empty_on_error(self, monkeypatch):
        """Should return empty string on error."""
        from implement_with_worktree import get_pr_url

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = ""
                returncode = 1
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        url = get_pr_url(123)
        assert url == ""


@pytest.mark.unit
class TestFormatAllFeedback:
    """Test formatting all feedback types for Claude."""

    def test_format_all_feedback_includes_reviews(self):
        """Should format PR reviews with state and body."""
        from implement_with_worktree import format_all_feedback

        reviews = [
            {"id": 1, "state": "CHANGES_REQUESTED", "body": "Please fix the tests",
             "user": {"login": "reviewer1"}}
        ]

        result = format_all_feedback([], reviews, [])

        assert "## PR Reviews" in result
        assert "CHANGES_REQUESTED" in result
        assert "Please fix the tests" in result
        assert "reviewer1" in result

    def test_format_all_feedback_includes_review_comments(self):
        """Should format review comments with file path and line."""
        from implement_with_worktree import format_all_feedback

        review_comments = [
            {"id": 2, "body": "This variable name is unclear",
             "path": "src/main.py", "line": 42, "user": {"login": "reviewer2"}}
        ]

        result = format_all_feedback(review_comments, [], [])

        assert "## Review Comments" in result
        assert "src/main.py:42" in result
        assert "This variable name is unclear" in result

    def test_format_all_feedback_includes_conversation_comments(self):
        """Should format general PR comments."""
        from implement_with_worktree import format_all_feedback

        conversation_comments = [
            {"id": 3, "body": "Great work overall!", "user": {"login": "lead"}}
        ]

        result = format_all_feedback([], [], conversation_comments)

        assert "## General PR Comments" in result
        assert "Great work overall!" in result
        assert "lead" in result

    def test_format_all_feedback_combines_all_types(self):
        """Should combine all feedback types into one formatted string."""
        from implement_with_worktree import format_all_feedback

        reviews = [{"id": 1, "state": "APPROVED", "body": "LGTM", "user": {"login": "r1"}}]
        review_comments = [{"id": 2, "body": "Nitpick", "path": "a.py", "line": 1, "user": {"login": "r2"}}]
        conversation_comments = [{"id": 3, "body": "Thanks", "user": {"login": "r3"}}]

        result = format_all_feedback(review_comments, reviews, conversation_comments)

        assert "## PR Reviews" in result
        assert "## Review Comments" in result
        assert "## General PR Comments" in result


@pytest.mark.unit
class TestBuildTriageCommand:
    """Test building Claude command for triaging feedback."""

    def test_build_triage_command_interactive(self):
        """Should build interactive Claude command for triage."""
        from implement_with_worktree import build_triage_command

        cmd = build_triage_command(
            feedback_content="Please add tests",
            interactive=True
        )

        assert cmd[0] == "claude"
        assert len(cmd) == 2  # claude + prompt
        assert "Please add tests" in cmd[1]
        assert "will_fix" in cmd[1]
        assert "needs_clarification" in cmd[1]

    def test_build_triage_command_non_interactive(self):
        """Should build non-interactive Claude command with -p flag."""
        from implement_with_worktree import build_triage_command

        cmd = build_triage_command(
            feedback_content="Fix the bug",
            interactive=False
        )

        assert "claude" in cmd
        assert "-p" in cmd
        assert "--verbose" in cmd

    def test_build_triage_command_requests_json_output(self):
        """Should request JSON output format."""
        from implement_with_worktree import build_triage_command

        cmd = build_triage_command(
            feedback_content="Some feedback",
            interactive=True
        )

        prompt = cmd[1]
        assert "json" in prompt.lower()
        assert "comment_ids" in prompt


@pytest.mark.unit
class TestBuildFixCommand:
    """Test building Claude command for fixing feedback."""

    def test_build_fix_command_interactive(self):
        """Should build interactive Claude command for fixing."""
        from implement_with_worktree import build_fix_command

        cmd = build_fix_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_content="Please add tests",
            fix_description="Add unit tests",
            interactive=True
        )

        assert cmd[0] == "claude"
        assert len(cmd) == 2  # claude + prompt
        assert "Please add tests" in cmd[1]
        assert "Add unit tests" in cmd[1]

    def test_build_fix_command_non_interactive(self):
        """Should build non-interactive Claude command with -p flag."""
        from implement_with_worktree import build_fix_command

        cmd = build_fix_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_content="Fix the bug",
            fix_description="Fix null pointer",
            interactive=False
        )

        assert "claude" in cmd
        assert "-p" in cmd
        assert "--verbose" in cmd


@pytest.mark.unit
class TestGetNewFeedback:
    """Test filtering feedback to unprocessed items."""

    def test_get_new_feedback_filters_processed(self):
        """Should filter out already processed feedback."""
        from implement_with_worktree import get_new_feedback

        all_feedback = [
            {"id": 1, "body": "Old comment"},
            {"id": 2, "body": "New comment"},
            {"id": 3, "body": "Another new comment"}
        ]
        processed_ids = [1]

        new_feedback = get_new_feedback(all_feedback, processed_ids)

        assert len(new_feedback) == 2
        assert all(f["id"] in [2, 3] for f in new_feedback)

    def test_get_new_feedback_returns_all_when_none_processed(self):
        """Should return all feedback when nothing processed yet."""
        from implement_with_worktree import get_new_feedback

        all_feedback = [
            {"id": 1, "body": "Comment 1"},
            {"id": 2, "body": "Comment 2"}
        ]

        new_feedback = get_new_feedback(all_feedback, [])

        assert len(new_feedback) == 2

    def test_get_new_feedback_returns_empty_when_all_processed(self):
        """Should return empty list when all feedback processed."""
        from implement_with_worktree import get_new_feedback

        all_feedback = [{"id": 1, "body": "Comment"}]
        processed_ids = [1]

        new_feedback = get_new_feedback(all_feedback, processed_ids)

        assert new_feedback == []


@pytest.mark.unit
class TestDefaultStateIncludesConversationIds:
    """Test that default state includes processed_conversation_ids."""

    def test_init_state_includes_processed_conversation_ids(self, tmp_path):
        """Default state should include processed_conversation_ids."""
        from implement_with_worktree import init_or_load_state

        idea_dir = tmp_path / "test-idea"
        idea_dir.mkdir()

        state = init_or_load_state(str(idea_dir), "test-idea")

        assert "processed_conversation_ids" in state
        assert state["processed_conversation_ids"] == []


@pytest.mark.unit
class TestParseTriageResult:
    """Test parsing JSON triage result from Claude."""

    def test_parse_triage_result_with_json_code_block(self):
        """Should parse JSON from markdown code block."""
        from implement_with_worktree import parse_triage_result

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
        from implement_with_worktree import parse_triage_result

        output = '{"will_fix": [], "needs_clarification": [{"comment_id": 5, "question": "What?"}]}'
        result = parse_triage_result(output)

        assert result is not None
        assert len(result["needs_clarification"]) == 1
        assert result["needs_clarification"][0]["comment_id"] == 5

    def test_parse_triage_result_returns_none_on_invalid(self):
        """Should return None for invalid JSON."""
        from implement_with_worktree import parse_triage_result

        result = parse_triage_result("This is not JSON at all")

        assert result is None


@pytest.mark.unit
class TestReplyToReviewComment:
    """Test replying to review comments."""

    def test_reply_to_review_comment_success(self, monkeypatch):
        """Should return True on successful reply."""
        from implement_with_worktree import reply_to_review_comment

        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = reply_to_review_comment(123, 456, "Fixed!")
        assert result is True

    def test_reply_to_review_comment_failure(self, monkeypatch):
        """Should return False on API error."""
        from implement_with_worktree import reply_to_review_comment

        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 1
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = reply_to_review_comment(123, 456, "Fixed!")
        assert result is False


@pytest.mark.unit
class TestReplyToPRComment:
    """Test adding general PR comments."""

    def test_reply_to_pr_comment_success(self, monkeypatch):
        """Should return True on successful comment."""
        from implement_with_worktree import reply_to_pr_comment

        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = reply_to_pr_comment(123, "Thanks for the review!")
        assert result is True


@pytest.mark.unit
class TestGetFeedbackByIds:
    """Test filtering feedback by IDs."""

    def test_get_feedback_by_ids_returns_matching(self):
        """Should return only feedback with matching IDs."""
        from implement_with_worktree import get_feedback_by_ids

        all_feedback = [
            {"id": 1, "body": "Comment 1"},
            {"id": 2, "body": "Comment 2"},
            {"id": 3, "body": "Comment 3"}
        ]

        result = get_feedback_by_ids(all_feedback, [1, 3])

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3

    def test_get_feedback_by_ids_returns_empty_for_no_matches(self):
        """Should return empty list when no IDs match."""
        from implement_with_worktree import get_feedback_by_ids

        all_feedback = [{"id": 1, "body": "Comment"}]

        result = get_feedback_by_ids(all_feedback, [99])

        assert result == []


@pytest.mark.unit
class TestDetermineCommentType:
    """Test determining comment type from ID."""

    def test_determine_comment_type_review(self):
        """Should return 'review' for review comment IDs."""
        from implement_with_worktree import determine_comment_type

        review_comments = [{"id": 100, "body": "Review comment"}]
        conversation_comments = [{"id": 200, "body": "General comment"}]

        result = determine_comment_type(100, review_comments, conversation_comments)

        assert result == "review"

    def test_determine_comment_type_conversation(self):
        """Should return 'conversation' for non-review comment IDs."""
        from implement_with_worktree import determine_comment_type

        review_comments = [{"id": 100, "body": "Review comment"}]
        conversation_comments = [{"id": 200, "body": "General comment"}]

        result = determine_comment_type(200, review_comments, conversation_comments)

        assert result == "conversation"
