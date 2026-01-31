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


@pytest.mark.unit
class TestCreateDraftPRFailure:
    """Test that PR creation failure is treated as fatal error."""

    def test_create_draft_pr_raises_on_failure(self, monkeypatch):
        """Should raise RuntimeError when gh pr create fails."""
        from implement_with_worktree import create_draft_pr

        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = ""
                stderr = "pull request create failed: GraphQL: No commits between main and branch"
                returncode = 1
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError) as excinfo:
            create_draft_pr("idea/test/01-setup", "Test PR", "Body", "main")

        assert "No commits" in str(excinfo.value) or "failed" in str(excinfo.value).lower()

    def test_ensure_draft_pr_raises_on_creation_failure(self, monkeypatch):
        """ensure_draft_pr should raise when PR creation fails."""
        from implement_with_worktree import ensure_draft_pr, find_existing_pr

        # Mock find_existing_pr to return None (no existing PR)
        def mock_find(*args, **kwargs):
            return None

        # Mock create_draft_pr to fail
        def mock_create(*args, **kwargs):
            raise RuntimeError("PR creation failed")

        monkeypatch.setattr("implement_with_worktree.find_existing_pr", mock_find)
        monkeypatch.setattr("implement_with_worktree.create_draft_pr", mock_create)

        with pytest.raises(RuntimeError):
            ensure_draft_pr("idea/test/01-setup", "/path/to/idea", "test", 1)


@pytest.mark.unit
class TestDeferredPRCreation:
    """Test that PR creation is deferred until after first push."""

    def test_setup_only_does_not_create_pr(self, monkeypatch, tmp_path):
        """Running with --setup-only should NOT attempt to create a PR."""
        from implement_with_worktree import main
        import builtins

        # Track if ensure_draft_pr was called
        ensure_draft_pr_called = False

        def mock_ensure_draft_pr(*args, **kwargs):
            nonlocal ensure_draft_pr_called
            ensure_draft_pr_called = True
            return 123

        # Mock all the setup functions to avoid real git/github operations
        monkeypatch.setattr("implement_with_worktree.validate_idea_directory", lambda x: "test-idea")
        monkeypatch.setattr("implement_with_worktree.validate_idea_files", lambda x, y: None)
        monkeypatch.setattr("implement_with_worktree.validate_idea_files_committed", lambda x, y: None)
        monkeypatch.setattr("implement_with_worktree.init_or_load_state", lambda x, y: {"slice_number": 1, "processed_comment_ids": [], "processed_review_ids": []})

        # Mock git operations
        class MockRepo:
            working_tree_dir = str(tmp_path)
            branches = []
            heads = {}
            def create_head(self, name, ref=None):
                pass
            class git:
                @staticmethod
                def worktree(*args):
                    pass
                @staticmethod
                def checkout(*args):
                    pass

        monkeypatch.setattr("implement_with_worktree.Repo", lambda *args, **kwargs: MockRepo())
        monkeypatch.setattr("implement_with_worktree.ensure_integration_branch", lambda r, n: "idea/test-idea/integration")
        monkeypatch.setattr("implement_with_worktree.ensure_worktree", lambda r, n, b: str(tmp_path / "worktree"))
        monkeypatch.setattr("implement_with_worktree.ensure_slice_branch", lambda r, n, s, t, i: "idea/test-idea/01-setup")

        # Create a minimal plan file in the expected location
        plan_file = tmp_path / "test-idea-plan.md"
        plan_file.write_text("# Plan\n- [ ] **Task 1.1: Test task**\n")

        # Mock open to return our plan file for plan file reads
        original_open = builtins.open
        def mock_open(*args, **kwargs):
            if args and "plan" in str(args[0]):
                return original_open(plan_file, *args[1:], **kwargs)
            return original_open(*args, **kwargs)
        monkeypatch.setattr("builtins.open", mock_open)

        # Mock the PR functions
        monkeypatch.setattr("implement_with_worktree.push_branch_to_remote", lambda x: True)
        monkeypatch.setattr("implement_with_worktree.find_existing_pr", lambda x: None)
        monkeypatch.setattr("implement_with_worktree.ensure_draft_pr", mock_ensure_draft_pr)

        # Mock sys.argv for --setup-only
        monkeypatch.setattr("sys.argv", ["implement-with-worktree.sh", str(tmp_path), "--setup-only"])

        # Run main
        try:
            main()
        except SystemExit:
            pass

        # Verify ensure_draft_pr was NOT called
        assert not ensure_draft_pr_called, "ensure_draft_pr should not be called in --setup-only mode"
