"""FakeWorkflowState: test double for WorkflowState.

Separated into its own module so tests can import it unambiguously
regardless of pytest's conftest resolution order.
"""


class FakeWorkflowState:
    """Test double for WorkflowState that tracks state in memory.

    Usage:
        fake = FakeWorkflowState()
        fake.mark_comments_processed(["c1", "c2"])
        assert fake.processed_comment_ids == ["c1", "c2"]
    """

    def __init__(self):
        self._slice_number = 1
        self._processed_comment_ids = []
        self._processed_review_ids = []
        self._processed_conversation_ids = []
        self._saved = False

    @property
    def slice_number(self):
        return self._slice_number

    @property
    def processed_comment_ids(self):
        return self._processed_comment_ids

    @property
    def processed_review_ids(self):
        return self._processed_review_ids

    @property
    def processed_conversation_ids(self):
        return self._processed_conversation_ids

    def mark_comments_processed(self, ids):
        self._processed_comment_ids.extend(ids)

    def mark_reviews_processed(self, ids):
        self._processed_review_ids.extend(ids)

    def mark_conversations_processed(self, ids):
        self._processed_conversation_ids.extend(ids)

    def save(self):
        self._saved = True

    @property
    def saved(self):
        return self._saved
