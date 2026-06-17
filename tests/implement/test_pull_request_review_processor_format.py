"""Tests for PullRequestReviewProcessor._format_all_feedback.

Covers how each feedback category (PR reviews, review comments, conversation
comments) is rendered into the combined feedback string passed to Claude.
"""

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor


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
