"""Shared test helpers for PullRequestReviewProcessor tests."""

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState
from fake_claude_runner import FakeClaudeRunner
from i2code.implement.implement_opts import ImplementOpts


def make_processor(**overrides):
    """Create a PullRequestReviewProcessor with common test defaults.

    All parameters are keyword-only overrides to the defaults dict.
    """
    defaults = dict(
        pr_number=42, pushed=True, branch="idea/test/01-slice",
        working_tree_dir="/tmp/worktree", non_interactive=True,
        mock_claude=None, skip_ci_wait=True, ci_timeout=600,
        pr_url="https://github.com/org/repo/pull/42",
        comments=None, reviews=None, conversation_comments=None,
    )
    defaults.update(overrides)
    d = defaults

    fake_gh = FakeGitHubClient()
    if d["pr_number"] and d["pr_url"]:
        fake_gh.set_pr_url(d["pr_number"], d["pr_url"])
    if d["comments"] is not None:
        fake_gh.set_pr_comments(d["pr_number"], d["comments"])
    if d["reviews"] is not None:
        fake_gh.set_pr_reviews(d["pr_number"], d["reviews"])
    if d["conversation_comments"] is not None:
        fake_gh.set_pr_conversation_comments(d["pr_number"], d["conversation_comments"])

    fake_repo = FakeGitRepository(working_tree_dir=d["working_tree_dir"], gh_client=fake_gh)
    fake_repo.pr_number = d["pr_number"]
    fake_repo.branch = d["branch"]
    fake_repo.set_pushed(d["pushed"])

    fake_state = FakeWorkflowState()
    fake_claude = FakeClaudeRunner()

    opts = ImplementOpts(
        idea_directory="/tmp/idea",
        non_interactive=d["non_interactive"],
        mock_claude=d["mock_claude"],
        skip_ci_wait=d["skip_ci_wait"],
        ci_timeout=d["ci_timeout"],
    )

    processor = PullRequestReviewProcessor(
        opts=opts, git_repo=fake_repo, state=fake_state, claude_runner=fake_claude,
    )

    return processor, fake_gh, fake_repo, fake_state, fake_claude
