"""Tests for WorkflowState class."""

import json
import os
import tempfile
import pytest


@pytest.mark.unit
class TestWorkflowStateDefaultState:
    """Test default state creation."""

    def test_creates_file_when_not_exists(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-feature-wt-state.json")

            WorkflowState.load(state_file)

            assert os.path.isfile(state_file)

    def test_returns_default_values(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-feature-wt-state.json")

            state = WorkflowState.load(state_file)

            assert state.slice_number == 1
            assert state.processed_comment_ids == []
            assert state.processed_review_ids == []
            assert state.processed_conversation_ids == []

    def test_includes_processed_conversation_ids(self, tmp_path):
        from i2code.implement.workflow_state import WorkflowState

        idea_dir = tmp_path / "test-idea"
        idea_dir.mkdir()

        state = WorkflowState.load(str(idea_dir / "test-idea-wt-state.json"))

        assert state.processed_conversation_ids == []


@pytest.mark.unit
class TestWorkflowStateLoad:
    """Test loading existing state."""

    def test_loads_existing_file(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-feature-wt-state.json")
            existing = {
                "slice_number": 3,
                "processed_comment_ids": [101, 102],
                "processed_review_ids": [201],
                "processed_conversation_ids": [301, 302]
            }
            with open(state_file, "w") as f:
                json.dump(existing, f)

            state = WorkflowState.load(state_file)

            assert state.slice_number == 3
            assert state.processed_comment_ids == [101, 102]
            assert state.processed_review_ids == [201]
            assert state.processed_conversation_ids == [301, 302]

    def test_loads_file_missing_conversation_ids_defaults_empty(self):
        """Old state files may not have processed_conversation_ids."""
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            existing = {
                "slice_number": 2,
                "processed_comment_ids": [101],
                "processed_review_ids": [201],
            }
            with open(state_file, "w") as f:
                json.dump(existing, f)

            state = WorkflowState.load(state_file)

            assert state.processed_conversation_ids == []


@pytest.mark.unit
class TestWorkflowStateSave:
    """Test saving state."""

    def test_save_persists_to_file(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")

            state = WorkflowState.load(state_file)
            state.save()

            with open(state_file, "r") as f:
                saved = json.load(f)

            assert saved["slice_number"] == 1
            assert saved["processed_comment_ids"] == []
            assert saved["processed_review_ids"] == []
            assert saved["processed_conversation_ids"] == []

    def test_save_after_modifications(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")

            state = WorkflowState.load(state_file)
            state.mark_comments_processed([101, 102])
            state.mark_reviews_processed([201])
            state.save()

            reloaded = WorkflowState.load(state_file)
            assert reloaded.processed_comment_ids == [101, 102]
            assert reloaded.processed_review_ids == [201]


@pytest.mark.unit
class TestWorkflowStateMarkProcessed:
    """Test mark_*_processed methods."""

    def test_mark_comments_processed_appends_ids(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")

            state = WorkflowState.load(state_file)
            state.mark_comments_processed([101, 102])

            assert state.processed_comment_ids == [101, 102]

    def test_mark_comments_processed_accumulates(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")

            state = WorkflowState.load(state_file)
            state.mark_comments_processed([101])
            state.mark_comments_processed([102, 103])

            assert state.processed_comment_ids == [101, 102, 103]

    def test_mark_reviews_processed_appends_ids(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")

            state = WorkflowState.load(state_file)
            state.mark_reviews_processed([201, 202])

            assert state.processed_review_ids == [201, 202]

    def test_mark_conversations_processed_appends_ids(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")

            state = WorkflowState.load(state_file)
            state.mark_conversations_processed([301, 302])

            assert state.processed_conversation_ids == [301, 302]

    def test_mark_conversations_processed_accumulates(self):
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")

            state = WorkflowState.load(state_file)
            state.mark_conversations_processed([301])
            state.mark_conversations_processed([302])

            assert state.processed_conversation_ids == [301, 302]
