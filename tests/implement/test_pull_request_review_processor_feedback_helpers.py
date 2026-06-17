"""Tests for PullRequestReviewProcessor static feedback-collection helpers.

Covers _get_new_feedback (unprocessed filter), _get_feedback_by_ids
(ID-based filter), and _determine_comment_type (review vs. conversation).
"""

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor


@pytest.mark.unit
class TestGetNewFeedback:
    """Test filtering feedback to unprocessed items."""

    def test_get_new_feedback_filters_processed(self):
        """Should filter out already processed feedback."""
        all_feedback = [{"id": 1, "body": "Old"}, {"id": 2, "body": "New"}, {"id": 3, "body": "Another"}]
        new_feedback = PullRequestReviewProcessor._get_new_feedback(all_feedback, [1])
        assert len(new_feedback) == 2
        assert all(f["id"] in [2, 3] for f in new_feedback)

    def test_get_new_feedback_returns_all_when_none_processed(self):
        """Should return all feedback when nothing processed yet."""
        all_feedback = [{"id": 1, "body": "Comment 1"}, {"id": 2, "body": "Comment 2"}]
        assert len(PullRequestReviewProcessor._get_new_feedback(all_feedback, [])) == 2

    def test_get_new_feedback_returns_empty_when_all_processed(self):
        """Should return empty list when all feedback processed."""
        assert PullRequestReviewProcessor._get_new_feedback([{"id": 1, "body": "Comment"}], [1]) == []


@pytest.mark.unit
class TestGetFeedbackByIds:
    """Test filtering feedback by IDs."""

    def test_get_feedback_by_ids_returns_matching(self):
        """Should return only feedback with matching IDs."""
        all_feedback = [{"id": 1, "body": "C1"}, {"id": 2, "body": "C2"}, {"id": 3, "body": "C3"}]
        result = PullRequestReviewProcessor._get_feedback_by_ids(all_feedback, [1, 3])
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 3

    def test_get_feedback_by_ids_returns_empty_for_no_matches(self):
        """Should return empty list when no IDs match."""
        assert PullRequestReviewProcessor._get_feedback_by_ids([{"id": 1, "body": "Comment"}], [99]) == []


@pytest.mark.unit
class TestDetermineCommentType:
    """Test determining comment type from ID."""

    def test_determine_comment_type_review(self):
        """Should return 'review' for review comment IDs."""
        result = PullRequestReviewProcessor._determine_comment_type(
            100, [{"id": 100, "body": "Review"}], [{"id": 200, "body": "General"}],
        )
        assert result == "review"

    def test_determine_comment_type_conversation(self):
        """Should return 'conversation' for non-review comment IDs."""
        result = PullRequestReviewProcessor._determine_comment_type(
            200, [{"id": 100, "body": "Review"}], [{"id": 200, "body": "General"}],
        )
        assert result == "conversation"
