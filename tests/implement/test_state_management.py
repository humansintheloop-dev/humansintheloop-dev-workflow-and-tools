"""Tests for state file management in implement-with-worktree."""

import json
import os
import tempfile
import pytest


@pytest.mark.unit
class TestStateFileManagement:
    """Test state file initialization and loading."""

    def test_init_state_creates_file_when_not_exists(self):
        """State file should be created if it doesn't exist."""
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-feature-wt-state.json")

            WorkflowState.load(state_file)

            assert os.path.isfile(state_file)

    def test_init_state_returns_default_values(self):
        """New state should have default values."""
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-feature-wt-state.json")

            state = WorkflowState.load(state_file)

            assert state.slice_number == 1
            assert state.processed_comment_ids == []
            assert state.processed_review_ids == []

    def test_load_state_reads_existing_file(self):
        """Should load existing state file."""
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-feature-wt-state.json")
            existing_state = {
                "slice_number": 3,
                "processed_comment_ids": ["IC_abc123"],
                "processed_review_ids": ["PRR_xyz789"]
            }
            with open(state_file, "w") as f:
                json.dump(existing_state, f)

            state = WorkflowState.load(state_file)

            assert state.slice_number == 3
            assert state.processed_comment_ids == ["IC_abc123"]
            assert state.processed_review_ids == ["PRR_xyz789"]

    def test_save_state_writes_to_file(self):
        """Save state should persist to file."""
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-feature-wt-state.json")

            state = WorkflowState.load(state_file)
            state.mark_comments_processed(["IC_new123"])

            state.save()

            # Re-read the file to verify
            with open(state_file, "r") as f:
                saved_state = json.load(f)

            assert saved_state["slice_number"] == 1
            assert "IC_new123" in saved_state["processed_comment_ids"]

    def test_state_file_location(self):
        """State file should be at <idea-dir>/<idea-name>-wt-state.json."""
        from i2code.implement.workflow_state import WorkflowState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "my-cool-feature-wt-state.json")

            WorkflowState.load(state_file)

            assert os.path.isfile(state_file)
