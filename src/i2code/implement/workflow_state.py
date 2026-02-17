"""WorkflowState: encapsulates workflow state persistence."""

import json
import os
from typing import List


class WorkflowState:
    """Owns load/save of workflow state and processed-ID tracking."""

    def __init__(self, state_file: str, data: dict):
        self._state_file = state_file
        self._data = data

    @classmethod
    def load(cls, state_file: str) -> "WorkflowState":
        """Load state from file, creating with defaults if it doesn't exist."""
        if os.path.isfile(state_file):
            with open(state_file, "r") as f:
                data = json.load(f)
            data.setdefault("processed_conversation_ids", [])
        else:
            data = {
                "slice_number": 1,
                "processed_comment_ids": [],
                "processed_review_ids": [],
                "processed_conversation_ids": [],
            }
            with open(state_file, "w") as f:
                json.dump(data, f, indent=2)

        return cls(state_file, data)

    def save(self) -> None:
        """Persist current state to disk."""
        with open(self._state_file, "w") as f:
            json.dump(self._data, f, indent=2)

    @property
    def slice_number(self) -> int:
        return self._data["slice_number"]

    @property
    def processed_comment_ids(self) -> List:
        return self._data["processed_comment_ids"]

    @property
    def processed_review_ids(self) -> List:
        return self._data["processed_review_ids"]

    @property
    def processed_conversation_ids(self) -> List:
        return self._data["processed_conversation_ids"]

    def mark_comments_processed(self, ids: List) -> None:
        self._data["processed_comment_ids"].extend(ids)

    def mark_reviews_processed(self, ids: List) -> None:
        self._data["processed_review_ids"].extend(ids)

    def mark_conversations_processed(self, ids: List) -> None:
        self._data["processed_conversation_ids"].extend(ids)
