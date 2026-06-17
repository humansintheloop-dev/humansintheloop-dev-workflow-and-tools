"""Tests for PullRequestReviewProcessor early-exit paths.

Covers skip preconditions (no PR / not pushed) and the no-feedback case.
"""

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState
from fake_claude_runner import FakeClaudeRunner
from i2code.implement.implement_opts import ImplementOpts

from pull_request_review_processor_helpers import make_processor


def _make_skip_processor(pr_number=None, pushed=False):
    """Create a minimal processor for testing skip conditions."""
    fake_gh = FakeGitHubClient()
    fake_repo = FakeGitRepository(working_tree_dir="/tmp", gh_client=fake_gh)
    if pr_number:
        fake_repo.pr_number = pr_number
    fake_repo.set_pushed(pushed)
    processor = PullRequestReviewProcessor(
        opts=ImplementOpts(idea_directory="/tmp/idea"),
        git_repo=fake_repo,
        state=FakeWorkflowState(),
        claude_runner=FakeClaudeRunner(),
    )
    return processor, fake_gh


@pytest.mark.unit
class TestPullRequestReviewProcessorSkipConditions:
    """PullRequestReviewProcessor skips feedback when preconditions not met."""

    def test_skips_when_no_pr_number(self):
        processor, fake_gh = _make_skip_processor(pushed=True)
        assert processor.process_feedback() is False
        assert not any(c[0] == "get_pr_url" for c in fake_gh.calls)

    def test_skips_when_not_pushed(self):
        processor, fake_gh = _make_skip_processor(pr_number=42)
        assert processor.process_feedback() is False
        assert not any(c[0] == "fetch_pr_comments" for c in fake_gh.calls)


@pytest.mark.unit
class TestProcessPrFeedbackNoFeedback:
    """process_pr_feedback returns (False, False) when no new feedback."""

    def test_no_new_feedback_returns_false_false(self):
        processor, _, _, _, _ = make_processor(comments=[], reviews=[], conversation_comments=[])
        had_feedback, made_changes = processor.process_pr_feedback()
        assert had_feedback is False
        assert made_changes is False
