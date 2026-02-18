"""Tests for PullRequestReviewProcessor class."""

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState
from i2code.implement.implement_opts import ImplementOpts


@pytest.mark.unit
class TestPullRequestReviewProcessorSkipConditions:
    """PullRequestReviewProcessor skips feedback when preconditions not met."""

    def test_skips_when_no_pr_number(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/tmp", gh_client=fake_gh)
        fake_repo.set_pushed(True)
        # No pr_number set
        fake_state = FakeWorkflowState()
        opts = ImplementOpts(idea_directory="/tmp/idea")

        processor = PullRequestReviewProcessor(
            opts=opts,
            git_repo=fake_repo,
            state=fake_state,
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
        opts = ImplementOpts(idea_directory="/tmp/idea")

        processor = PullRequestReviewProcessor(
            opts=opts,
            git_repo=fake_repo,
            state=fake_state,
        )

        result = processor.process_feedback()

        assert result is False
        assert not any(c[0] == "fetch_pr_comments" for c in fake_gh.calls)
