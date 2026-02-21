"""Tests for PullRequestReviewProcessor class."""

import json
import os

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.claude_runner import CapturedOutput, ClaudeResult

from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState
from fake_claude_runner import FakeClaudeRunner
from i2code.implement.implement_opts import ImplementOpts

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PR6_FEEDBACK_FILE = os.path.join(FIXTURE_DIR, "pr6_feedback.json")
PR6_TRIAGE_STDOUT_FILE = os.path.join(FIXTURE_DIR, "pr6_triage_stdout.txt")


def _make_processor(
    pr_number=42,
    pushed=True,
    branch="idea/test/01-slice",
    working_tree_dir="/tmp/worktree",
    non_interactive=True,
    mock_claude=None,
    skip_ci_wait=True,
    ci_timeout=600,
    pr_url="https://github.com/org/repo/pull/42",
    comments=None,
    reviews=None,
    conversation_comments=None,
):
    """Create a PullRequestReviewProcessor with common test defaults."""
    fake_gh = FakeGitHubClient()
    if pr_number and pr_url:
        fake_gh.set_pr_url(pr_number, pr_url)
    if comments is not None:
        fake_gh.set_pr_comments(pr_number, comments)
    if reviews is not None:
        fake_gh.set_pr_reviews(pr_number, reviews)
    if conversation_comments is not None:
        fake_gh.set_pr_conversation_comments(pr_number, conversation_comments)

    fake_repo = FakeGitRepository(working_tree_dir=working_tree_dir, gh_client=fake_gh)
    fake_repo.pr_number = pr_number
    fake_repo.branch = branch
    fake_repo.set_pushed(pushed)

    fake_state = FakeWorkflowState()
    fake_claude = FakeClaudeRunner()

    opts = ImplementOpts(
        idea_directory="/tmp/idea",
        non_interactive=non_interactive,
        mock_claude=mock_claude,
        skip_ci_wait=skip_ci_wait,
        ci_timeout=ci_timeout,
    )

    processor = PullRequestReviewProcessor(
        opts=opts,
        git_repo=fake_repo,
        state=fake_state,
        claude_runner=fake_claude,
    )

    return processor, fake_gh, fake_repo, fake_state, fake_claude


@pytest.mark.unit
class TestPullRequestReviewProcessorSkipConditions:
    """PullRequestReviewProcessor skips feedback when preconditions not met."""

    def test_skips_when_no_pr_number(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/tmp", gh_client=fake_gh)
        fake_repo.set_pushed(True)
        # No pr_number set
        fake_state = FakeWorkflowState()
        fake_claude = FakeClaudeRunner()
        opts = ImplementOpts(idea_directory="/tmp/idea")

        processor = PullRequestReviewProcessor(
            opts=opts,
            git_repo=fake_repo,
            state=fake_state,
            claude_runner=fake_claude,
        )

        result = processor.process_feedback()

        assert result is False
        assert not any(c[0] == "get_pr_url" for c in fake_gh.calls)

    def test_skips_when_not_pushed(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/tmp", gh_client=fake_gh)
        fake_repo.pr_number = 42
        # pushed is False by default
        fake_state = FakeWorkflowState()
        fake_claude = FakeClaudeRunner()
        opts = ImplementOpts(idea_directory="/tmp/idea")

        processor = PullRequestReviewProcessor(
            opts=opts,
            git_repo=fake_repo,
            state=fake_state,
            claude_runner=fake_claude,
        )

        result = processor.process_feedback()

        assert result is False
        assert not any(c[0] == "fetch_pr_comments" for c in fake_gh.calls)


@pytest.mark.unit
class TestProcessPrFeedbackNoFeedback:
    """process_pr_feedback returns (False, False) when no new feedback."""

    def test_no_new_feedback_returns_false_false(self):
        processor, fake_gh, _, _, _ = _make_processor(
            comments=[], reviews=[], conversation_comments=[],
        )

        had_feedback, made_changes = processor.process_pr_feedback()

        assert had_feedback is False
        assert made_changes is False


@pytest.mark.unit
class TestProcessPrFeedbackTriage:
    """process_pr_feedback triages feedback using claude_runner."""

    def test_triage_uses_claude_runner_run_with_capture(self):
        """Triage invokes claude_runner.run_with_capture, not module-level function."""
        triage_json = json.dumps({"will_fix": [], "needs_clarification": []})
        triage_result = ClaudeResult(returncode=0, output=CapturedOutput(triage_json))

        processor, _, fake_repo, _, fake_claude = _make_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
        )
        fake_claude.set_result(triage_result)

        processor.process_pr_feedback()

        assert len(fake_claude.calls) == 1
        method, _cmd, cwd = fake_claude.calls[0]
        assert method == "run_with_capture"
        assert cwd == fake_repo.working_tree_dir


@pytest.mark.unit
class TestProcessPrFeedbackFixGroup:
    """process_pr_feedback processes fix groups using injected collaborators."""

    def _triage_with_fix(self, comment_ids, description="Fix issue"):
        return json.dumps({
            "will_fix": [{"comment_ids": comment_ids, "description": description}],
            "needs_clarification": [],
        })

    def test_fix_uses_git_repo_head_sha_not_gitrepo(self):
        """HEAD tracking uses self._git_repo.head_sha, not GitRepo(worktree_path)."""
        triage_json = self._triage_with_fix([1])
        triage_result = ClaudeResult(returncode=0, output=CapturedOutput(triage_json))
        # Claude "makes a commit" by advancing head_sha
        fix_result = ClaudeResult(returncode=0)

        processor, _, fake_repo, _, fake_claude = _make_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
            non_interactive=True,
        )
        fake_repo.set_head_sha("aaa111")

        def advance_head():
            fake_repo.set_head_sha("bbb222")

        fake_claude.set_results([triage_result, fix_result])
        fake_claude.set_side_effects([lambda: None, advance_head])

        had_feedback, made_changes = processor.process_pr_feedback()

        assert had_feedback is True
        assert made_changes is True

    def test_fix_uses_git_repo_push_not_push_branch_to_remote(self):
        """Push uses self._git_repo.push(), not push_branch_to_remote()."""
        triage_json = self._triage_with_fix([1])
        triage_result = ClaudeResult(returncode=0, output=CapturedOutput(triage_json))
        fix_result = ClaudeResult(returncode=0)

        processor, _, fake_repo, _, fake_claude = _make_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
            non_interactive=True,
        )
        fake_repo.set_head_sha("aaa111")

        def advance_head():
            fake_repo.set_head_sha("bbb222")

        fake_claude.set_results([triage_result, fix_result])
        fake_claude.set_side_effects([lambda: None, advance_head])

        processor.process_pr_feedback()

        push_calls = [c for c in fake_repo.calls if c[0] == "push"]
        assert len(push_calls) == 1

    def test_fix_interactive_uses_run_interactive(self):
        """Interactive mode uses claude_runner.run_interactive for fix."""
        triage_json = self._triage_with_fix([1])
        triage_result = ClaudeResult(returncode=0, output=CapturedOutput(triage_json))
        fix_result = ClaudeResult(returncode=0)

        processor, _, fake_repo, _, fake_claude = _make_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
            non_interactive=False,  # interactive mode
        )
        fake_repo.set_head_sha("aaa111")

        def advance_head():
            fake_repo.set_head_sha("bbb222")

        fake_claude.set_results([triage_result, fix_result])
        fake_claude.set_side_effects([lambda: None, advance_head])

        processor.process_pr_feedback()

        # First call is triage (run_with_capture), second is fix (run_interactive)
        assert fake_claude.calls[0][0] == "run_with_capture"
        assert fake_claude.calls[1][0] == "run_interactive"

    def test_fix_marks_all_feedback_processed(self):
        """After processing, all feedback IDs are marked processed in state."""
        triage_json = self._triage_with_fix([1])
        triage_result = ClaudeResult(returncode=0, output=CapturedOutput(triage_json))
        fix_result = ClaudeResult(returncode=0)

        processor, _, fake_repo, fake_state, fake_claude = _make_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
            reviews=[{"id": 10, "body": "looks bad", "state": "CHANGES_REQUESTED", "user": {"login": "u"}}],
            conversation_comments=[{"id": 20, "body": "general note", "user": {"login": "u"}}],
        )
        fake_repo.set_head_sha("aaa111")

        def advance_head():
            fake_repo.set_head_sha("bbb222")

        fake_claude.set_results([triage_result, fix_result])
        fake_claude.set_side_effects([lambda: None, advance_head])

        processor.process_pr_feedback()

        assert 1 in fake_state.processed_comment_ids
        assert 10 in fake_state.processed_review_ids
        assert 20 in fake_state.processed_conversation_ids


@pytest.mark.unit
class TestFormatAllFeedback:
    """Test formatting all feedback types for Claude."""

    def test_format_all_feedback_includes_reviews(self):
        """Should format PR reviews with state and body."""
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
        conversation_comments = [
            {"id": 3, "body": "Great work overall!", "user": {"login": "lead"}}
        ]

        result = PullRequestReviewProcessor._format_all_feedback([], [], conversation_comments)

        assert "## General PR Comments" in result
        assert "Great work overall!" in result
        assert "lead" in result

    def test_format_all_feedback_combines_all_types(self):
        """Should combine all feedback types into one formatted string."""
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
        all_feedback = [
            {"id": 1, "body": "Comment 1"},
            {"id": 2, "body": "Comment 2"}
        ]

        new_feedback = PullRequestReviewProcessor._get_new_feedback(all_feedback, [])

        assert len(new_feedback) == 2

    def test_get_new_feedback_returns_empty_when_all_processed(self):
        """Should return empty list when all feedback processed."""
        all_feedback = [{"id": 1, "body": "Comment"}]
        processed_ids = [1]

        new_feedback = PullRequestReviewProcessor._get_new_feedback(all_feedback, processed_ids)

        assert new_feedback == []


@pytest.mark.unit
class TestParseTriageResult:
    """Test parsing JSON triage result from Claude."""

    def test_parse_triage_result_with_json_code_block(self):
        """Should parse JSON from markdown code block."""
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
        parse_triage_result = PullRequestReviewProcessor._parse_triage_result

        output = '{"will_fix": [], "needs_clarification": [{"comment_id": 5, "question": "What?"}]}'
        result = parse_triage_result(output)

        assert result is not None
        assert len(result["needs_clarification"]) == 1
        assert result["needs_clarification"][0]["comment_id"] == 5

    def test_parse_triage_result_returns_none_on_invalid(self):
        """Should return None for invalid JSON."""
        parse_triage_result = PullRequestReviewProcessor._parse_triage_result

        result = parse_triage_result("This is not JSON at all")

        assert result is None


@pytest.mark.unit
class TestGetFeedbackByIds:
    """Test filtering feedback by IDs."""

    def test_get_feedback_by_ids_returns_matching(self):
        """Should return only feedback with matching IDs."""
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
        all_feedback = [{"id": 1, "body": "Comment"}]

        result = PullRequestReviewProcessor._get_feedback_by_ids(all_feedback, [99])

        assert result == []


@pytest.mark.unit
class TestDetermineCommentType:
    """Test determining comment type from ID."""

    def test_determine_comment_type_review(self):
        """Should return 'review' for review comment IDs."""
        review_comments = [{"id": 100, "body": "Review comment"}]
        conversation_comments = [{"id": 200, "body": "General comment"}]

        result = PullRequestReviewProcessor._determine_comment_type(100, review_comments, conversation_comments)

        assert result == "review"

    def test_determine_comment_type_conversation(self):
        """Should return 'conversation' for non-review comment IDs."""
        review_comments = [{"id": 100, "body": "Review comment"}]
        conversation_comments = [{"id": 200, "body": "General comment"}]

        result = PullRequestReviewProcessor._determine_comment_type(200, review_comments, conversation_comments)

        assert result == "conversation"


PR6_REPO = "humansintheloop-dev/humansintheloop-dev-workflow-and-tools"
PR6_NUMBER = 6


@pytest.mark.unit
class TestTriageFeedbackLogging:
    """Test that _triage_feedback logs prompt and response to file."""

    @pytest.fixture
    def pr6_feedback(self):
        assert os.path.exists(PR6_FEEDBACK_FILE), (
            f"Fixture not found: {PR6_FEEDBACK_FILE}\n"
            f"Run: uv run --with pytest pytest tests/implement/test_triage_failure_logging.py -m gather_fixtures"
        )
        with open(PR6_FEEDBACK_FILE) as f:
            return json.load(f)

    @pytest.fixture
    def home_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        return tmp_path

    def _make_triage_processor(self, claude_stdout):
        worktree_name = "myrepo-wt-improve-modularity"

        fake_gh = FakeGitHubClient()
        fake_gh.set_pr_url(PR6_NUMBER, f"https://github.com/{PR6_REPO}/pull/{PR6_NUMBER}")

        fake_repo = FakeGitRepository(
            working_tree_dir=f"/worktrees/{worktree_name}",
            gh_client=fake_gh,
        )
        fake_repo.pr_number = PR6_NUMBER
        fake_repo.branch = "idea/improve-modularity/01-extract-ideaproject-class"
        fake_repo.set_pushed(True)

        fake_state = FakeWorkflowState()
        fake_claude = FakeClaudeRunner()
        fake_claude.set_result(ClaudeResult(returncode=0, output=CapturedOutput(claude_stdout)))

        opts = ImplementOpts(
            idea_directory="/tmp/idea",
            non_interactive=True,
            skip_ci_wait=True,
        )

        processor = PullRequestReviewProcessor(
            opts=opts, git_repo=fake_repo, state=fake_state, claude_runner=fake_claude,
        )

        return processor, worktree_name

    def test_logs_feedback_content_on_triage_parse_failure(self, pr6_feedback, home_dir):
        processor, worktree_name = self._make_triage_processor("not json at all")

        review_comments = pr6_feedback["review_comments"]
        feedback_content = PullRequestReviewProcessor._format_all_feedback(
            review_comments, pr6_feedback["reviews"], pr6_feedback["conversation_comments"],
        )

        result = processor._triage_feedback(feedback_content, PR6_NUMBER)

        assert result is None

        log_file = home_dir / ".hitl" / worktree_name / "logs" / "log.log"
        assert log_file.exists(), f"Expected log file at {log_file}"

        log_content = log_file.read_text()
        assert "--- prompt ---" in log_content
        assert "--- claude response ---" in log_content
        assert "not json at all" in log_content

        for comment in review_comments:
            body = comment.get("body", "").strip()
            if body:
                assert body in log_content, f"Expected review comment body in log: {body[:60]}..."
                break

    def test_parses_real_claude_triage_response(self, pr6_feedback, home_dir):
        with open(PR6_TRIAGE_STDOUT_FILE) as f:
            triage_stdout = f.read()

        processor, _ = self._make_triage_processor(triage_stdout)

        feedback_content = PullRequestReviewProcessor._format_all_feedback(
            pr6_feedback["review_comments"], pr6_feedback["reviews"], pr6_feedback["conversation_comments"],
        )

        result = processor._triage_feedback(feedback_content, PR6_NUMBER)

        assert result is not None, "Expected triage to parse successfully"
        assert "will_fix" in result
        assert "needs_clarification" in result
        assert len(result["will_fix"]) > 0
