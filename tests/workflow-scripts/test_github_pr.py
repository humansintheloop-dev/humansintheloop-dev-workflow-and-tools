"""Tests for GitHub PR management in implement-with-worktree."""

import json
import os
import sys
import subprocess
import tempfile
import pytest

from git import Repo

# Add workflow-scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../workflow-scripts'))


@pytest.mark.unit
class TestPRTitleGeneration:
    """Test PR title generation from slice name."""

    def test_generate_pr_title(self):
        """Should generate PR title from idea and slice name."""
        from implement_with_worktree import generate_pr_title

        title = generate_pr_title("my-feature", "01-project-setup")
        assert title == "[my-feature] 01-project-setup"

    def test_generate_pr_title_preserves_slice_name(self):
        """PR title should preserve the full slice name."""
        from implement_with_worktree import generate_pr_title

        title = generate_pr_title("wt-pr-based-development", "03-feedback-handling")
        assert title == "[wt-pr-based-development] 03-feedback-handling"


@pytest.mark.unit
class TestPRBodyGeneration:
    """Test PR body generation."""

    def test_generate_pr_body(self):
        """Should generate PR body with idea directory reference."""
        from implement_with_worktree import generate_pr_body

        body = generate_pr_body(
            idea_directory="docs/features/my-feature",
            idea_name="my-feature",
            slice_number=1
        )

        assert "docs/features/my-feature" in body
        assert "my-feature" in body
        assert "slice 1" in body.lower() or "slice #1" in body.lower()


@pytest.mark.unit
class TestCheckExistingPR:
    """Test checking for existing PRs (mocked gh output)."""

    def test_find_existing_pr_returns_pr_number(self, monkeypatch):
        """Should return PR number if PR exists for branch."""
        from implement_with_worktree import find_existing_pr

        # Mock gh pr list output
        mock_output = json.dumps([
            {"number": 123, "headRefName": "idea/my-feature/01-project-setup", "isDraft": True},
            {"number": 456, "headRefName": "other-branch", "isDraft": False}
        ])

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        pr_number = find_existing_pr("idea/my-feature/01-project-setup")
        assert pr_number == 123

    def test_find_existing_pr_returns_none_when_not_found(self, monkeypatch):
        """Should return None if no PR exists for branch."""
        from implement_with_worktree import find_existing_pr

        # Mock gh pr list output with no matching PR
        mock_output = json.dumps([
            {"number": 456, "headRefName": "other-branch", "isDraft": False}
        ])

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        pr_number = find_existing_pr("idea/my-feature/01-project-setup")
        assert pr_number is None


@pytest.mark.unit
class TestCheckPRDraftState:
    """Test checking if PR is still in draft state."""

    def test_is_pr_draft_returns_true_for_draft(self, monkeypatch):
        """Should return True if PR is in draft state."""
        from implement_with_worktree import is_pr_draft

        mock_output = json.dumps({"isDraft": True})

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        assert is_pr_draft(123) is True

    def test_is_pr_draft_returns_false_for_ready(self, monkeypatch):
        """Should return False if PR is ready for review."""
        from implement_with_worktree import is_pr_draft

        mock_output = json.dumps({"isDraft": False})

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = mock_output
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        assert is_pr_draft(123) is False
