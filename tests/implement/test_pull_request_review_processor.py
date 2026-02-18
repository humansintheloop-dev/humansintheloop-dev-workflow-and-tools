"""Tests for PullRequestReviewProcessor class."""

import json

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.claude_runner import ClaudeResult

from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState
from fake_claude_runner import FakeClaudeRunner
from i2code.implement.implement_opts import ImplementOpts


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
        triage_result = ClaudeResult(returncode=0, stdout=triage_json, stderr="")

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
        triage_result = ClaudeResult(returncode=0, stdout=triage_json, stderr="")
        # Claude "makes a commit" by advancing head_sha
        fix_result = ClaudeResult(returncode=0, stdout="", stderr="")

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
        triage_result = ClaudeResult(returncode=0, stdout=triage_json, stderr="")
        fix_result = ClaudeResult(returncode=0, stdout="", stderr="")

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
        triage_result = ClaudeResult(returncode=0, stdout=triage_json, stderr="")
        fix_result = ClaudeResult(returncode=0, stdout="", stderr="")

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
        triage_result = ClaudeResult(returncode=0, stdout=triage_json, stderr="")
        fix_result = ClaudeResult(returncode=0, stdout="", stderr="")

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
