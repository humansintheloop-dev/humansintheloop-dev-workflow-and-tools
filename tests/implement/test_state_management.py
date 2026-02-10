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
        from i2code.implement.implement import init_or_load_state

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            state = init_or_load_state(idea_dir, "my-feature")

            state_file = os.path.join(idea_dir, "my-feature-wt-state.json")
            assert os.path.isfile(state_file)

    def test_init_state_returns_default_values(self):
        """New state should have default values."""
        from i2code.implement.implement import init_or_load_state

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            state = init_or_load_state(idea_dir, "my-feature")

            assert state["slice_number"] == 1
            assert state["processed_comment_ids"] == []
            assert state["processed_review_ids"] == []

    def test_load_state_reads_existing_file(self):
        """Should load existing state file."""
        from i2code.implement.implement import init_or_load_state

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            # Create existing state file
            state_file = os.path.join(idea_dir, "my-feature-wt-state.json")
            existing_state = {
                "slice_number": 3,
                "processed_comment_ids": ["IC_abc123"],
                "processed_review_ids": ["PRR_xyz789"]
            }
            with open(state_file, "w") as f:
                json.dump(existing_state, f)

            state = init_or_load_state(idea_dir, "my-feature")

            assert state["slice_number"] == 3
            assert state["processed_comment_ids"] == ["IC_abc123"]
            assert state["processed_review_ids"] == ["PRR_xyz789"]

    def test_save_state_writes_to_file(self):
        """Save state should persist to file."""
        from i2code.implement.implement import init_or_load_state, save_state

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            state = init_or_load_state(idea_dir, "my-feature")
            state["slice_number"] = 5
            state["processed_comment_ids"].append("IC_new123")

            save_state(idea_dir, "my-feature", state)

            # Re-read the file to verify
            state_file = os.path.join(idea_dir, "my-feature-wt-state.json")
            with open(state_file, "r") as f:
                saved_state = json.load(f)

            assert saved_state["slice_number"] == 5
            assert "IC_new123" in saved_state["processed_comment_ids"]

    def test_state_file_location(self):
        """State file should be at <idea-dir>/<idea-name>-wt-state.json."""
        from i2code.implement.implement import init_or_load_state

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-cool-feature")
            os.makedirs(idea_dir)

            init_or_load_state(idea_dir, "my-cool-feature")

            expected_path = os.path.join(idea_dir, "my-cool-feature-wt-state.json")
            assert os.path.isfile(expected_path)
