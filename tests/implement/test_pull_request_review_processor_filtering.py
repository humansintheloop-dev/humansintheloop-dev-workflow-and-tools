"""Tests for PullRequestReviewProcessor._fetch_unprocessed_feedback filters.

Covers the two filters applied to fetched PR feedback: self-authored comments
identified by the i2code marker, and comments belonging to resolved review
threads. Both filters mark the excluded IDs processed in state.
"""

import pytest

from pull_request_review_processor_helpers import make_processor


@pytest.mark.unit
class TestSelfCommentFiltering:
    """_fetch_unprocessed_feedback filters out comments with i2code marker."""

    def test_filters_out_marker_comments_and_marks_processed(self):
        """Comments starting with <!-- i2code --> are excluded and their IDs marked processed."""
        user_comment = {"id": 1, "body": "Please fix the typo", "user": {"login": "reviewer"}}
        self_comment = {"id": 2, "body": "<!-- i2code -->\nFixed in abc123", "user": {"login": "bot"}}
        another_user_comment = {"id": 3, "body": "Also check line 10", "user": {"login": "reviewer"}}

        processor, _, _, fake_state, _ = make_processor(
            comments=[user_comment, self_comment, another_user_comment],
            reviews=[],
            conversation_comments=[],
        )

        review_comments, reviews, conversation = processor._fetch_unprocessed_feedback(42)

        assert len(review_comments) == 2
        assert all(c["id"] in [1, 3] for c in review_comments)
        assert 2 in fake_state.processed_comment_ids

    def test_filters_marker_from_conversation_comments(self):
        """Marker filtering also applies to conversation comments."""
        user_comment = {"id": 10, "body": "Nice work", "user": {"login": "reviewer"}}
        self_comment = {"id": 11, "body": "<!-- i2code -->\nRe: comment 10\n\nClarification", "user": {"login": "bot"}}

        processor, _, _, fake_state, _ = make_processor(
            comments=[],
            reviews=[],
            conversation_comments=[user_comment, self_comment],
        )

        review_comments, reviews, conversation = processor._fetch_unprocessed_feedback(42)

        assert len(conversation) == 1
        assert conversation[0]["id"] == 10
        assert 11 in fake_state.processed_conversation_ids

    def test_user_followup_after_i2code_reply_is_included(self):
        """Scenario 4: user comment → i2code reply → user follow-up.

        The i2code reply is filtered out but both user comments are returned.
        """
        user_comment = {"id": 1, "body": "Why is this function public?", "user": {"login": "reviewer"}}
        i2code_reply = {"id": 2, "body": "<!-- i2code -->\nIt's public because it's called from integration tests.", "user": {"login": "reviewer"}}
        user_followup = {"id": 3, "body": "OK, but can we make it package-private instead?", "user": {"login": "reviewer"}}

        processor, _, _, fake_state, _ = make_processor(
            comments=[user_comment, i2code_reply, user_followup],
            reviews=[],
            conversation_comments=[],
        )

        review_comments, reviews, conversation = processor._fetch_unprocessed_feedback(42)

        assert len(review_comments) == 2
        assert review_comments[0]["id"] == 1
        assert review_comments[1]["id"] == 3
        assert 2 in fake_state.processed_comment_ids
        assert 1 not in fake_state.processed_comment_ids
        assert 3 not in fake_state.processed_comment_ids


@pytest.mark.unit
class TestResolvedThreadFiltering:
    """_fetch_unprocessed_feedback filters out comments in resolved review threads."""

    def test_resolved_thread_comments_excluded_and_marked_processed(self):
        """Comments whose IDs are in the resolved-thread set are excluded and marked processed."""
        user_comment = {"id": 1, "body": "Please fix the typo", "user": {"login": "reviewer"}}
        resolved_comment = {"id": 2, "body": "Consider a constant here", "user": {"login": "reviewer"}}
        another_user_comment = {"id": 3, "body": "Also check line 10", "user": {"login": "reviewer"}}

        processor, fake_gh, _, fake_state, _ = make_processor(
            comments=[user_comment, resolved_comment, another_user_comment],
            reviews=[],
            conversation_comments=[],
        )
        fake_gh.set_resolved_review_comment_ids("test", "repo", 42, {2})

        review_comments, reviews, conversation = processor._fetch_unprocessed_feedback(42)

        assert len(review_comments) == 2
        assert all(c["id"] in [1, 3] for c in review_comments)
        assert 2 in fake_state.processed_comment_ids
        assert 1 not in fake_state.processed_comment_ids
        assert 3 not in fake_state.processed_comment_ids

    def test_mixed_resolved_and_unresolved_threads_returns_only_unresolved(self):
        """Scenario 6: three threads (A resolved, B unresolved, C resolved) — only B returned."""
        thread_a_comment = {"id": 10, "body": "Thread A feedback", "user": {"login": "reviewer"}}
        thread_b_comment = {"id": 20, "body": "Thread B feedback", "user": {"login": "reviewer"}}
        thread_c_comment = {"id": 30, "body": "Thread C feedback", "user": {"login": "reviewer"}}

        processor, fake_gh, _, fake_state, _ = make_processor(
            comments=[thread_a_comment, thread_b_comment, thread_c_comment],
            reviews=[],
            conversation_comments=[],
        )
        fake_gh.set_resolved_review_comment_ids("test", "repo", 42, {10, 30})

        review_comments, reviews, conversation = processor._fetch_unprocessed_feedback(42)

        assert len(review_comments) == 1
        assert review_comments[0]["id"] == 20
        assert 10 in fake_state.processed_comment_ids
        assert 30 in fake_state.processed_comment_ids
        assert 20 not in fake_state.processed_comment_ids
