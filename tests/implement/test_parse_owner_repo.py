"""Tests for parse_owner_repo URL parser used by PullRequestReviewProcessor."""

import pytest

from i2code.implement.pull_request_review_processor import parse_owner_repo


@pytest.mark.unit
class TestParseOwnerRepo:
    """Test parsing owner/repo from git remote URLs."""

    def test_https_with_credentials(self):
        assert parse_owner_repo(
            "https://x-access-token:ghs_abc123@github.com/my-org/my-repo.git"
        ) == ("my-org", "my-repo")

    def test_ssh(self):
        assert parse_owner_repo(
            "git@github.com:my-org/my-repo.git"
        ) == ("my-org", "my-repo")

    def test_https(self):
        assert parse_owner_repo(
            "https://github.com/my-org/my-repo.git"
        ) == ("my-org", "my-repo")

    def test_https_without_dot_git(self):
        assert parse_owner_repo(
            "https://github.com/my-org/my-repo"
        ) == ("my-org", "my-repo")
