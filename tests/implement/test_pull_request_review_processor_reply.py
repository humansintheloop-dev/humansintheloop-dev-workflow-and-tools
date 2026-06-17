"""Tests for PullRequestReviewProcessor reply paths.

Covers the i2code-marker prefix on both push-and-reply (fixes posted back to
the PR) and reply-with-clarifications (questions sent back to the reviewer).
"""

import pytest

from pull_request_review_processor_helpers import make_processor


I2CODE_MARKER = "<!-- i2code -->"


def _get_reply_body(fake_gh, call_name):
    """Extract the reply body from the single matching call on fake_gh."""
    reply_calls = [c for c in fake_gh.calls if c[0] == call_name]
    assert len(reply_calls) == 1, f"Expected 1 {call_name} call, got {len(reply_calls)}"
    body_index = 3 if call_name == "reply_to_review_comment" else 2
    return reply_calls[0][body_index]


def _assert_marker_prefixed(body, *expected_substrings):
    """Assert body starts with the i2code marker and contains expected substrings."""
    assert body.startswith(f"{I2CODE_MARKER}\n"), f"Expected marker prefix, got: {body!r}"
    for substring in expected_substrings:
        assert substring in body, f"Expected {substring!r} in body: {body!r}"


def _push_and_reply_body(comment_id, review_comments, conversation_comments):
    """Call _push_and_reply and return the reply body posted to the matching call."""
    processor, fake_gh, fake_repo, _, _ = make_processor()
    fake_repo.set_head_sha("aaa111")
    processor._push_and_reply("abc12345", [comment_id], review_comments, conversation_comments)
    call_name = "reply_to_review_comment" if review_comments else "reply_to_pr_comment"
    return _get_reply_body(fake_gh, call_name)


def _clarification_reply_body(comment_id, question, review_comments, conversation_comments):
    """Call _reply_with_clarifications and return the reply body."""
    processor, fake_gh, _, _, _ = make_processor()
    processor._reply_with_clarifications(
        [{"comment_id": comment_id, "question": question}],
        42, review_comments, conversation_comments,
    )
    call_name = "reply_to_review_comment" if review_comments else "reply_to_pr_comment"
    return _get_reply_body(fake_gh, call_name)


@pytest.mark.unit
class TestPushAndReplyMarker:
    """_push_and_reply prepends i2code marker to reply bodies."""

    def test_review_comment_reply_starts_with_marker(self):
        body = _push_and_reply_body(100, [{"id": 100, "body": "Fix this"}], [])
        _assert_marker_prefixed(body, "Fixed in abc12345")

    def test_conversation_comment_reply_starts_with_marker(self):
        body = _push_and_reply_body(200, [], [{"id": 200, "body": "General note"}])
        _assert_marker_prefixed(body)


@pytest.mark.unit
class TestReplyWithClarificationsMarker:
    """_reply_with_clarifications prepends i2code marker to clarification replies."""

    def test_review_comment_clarification_starts_with_marker(self):
        body = _clarification_reply_body(100, "Could you elaborate?", [{"id": 100, "body": "What does this do?"}], [])
        _assert_marker_prefixed(body, "Could you elaborate?")

    def test_conversation_comment_clarification_starts_with_marker(self):
        body = _clarification_reply_body(200, "Can you explain further?", [], [{"id": 200, "body": "Why this approach?"}])
        _assert_marker_prefixed(body, "Re: comment 200", "Can you explain further?")
