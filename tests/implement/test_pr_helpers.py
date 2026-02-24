"""Tests for PR helper functions in implement-with-worktree."""

import os
import tempfile

import pytest


@pytest.mark.unit
class TestExtractTitleFromIdeaFile:
    """Test extracting title from idea file heading."""

    def test_extracts_heading_from_idea_file(self):
        from i2code.implement.pr_helpers import extract_title_from_idea_file

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)
            idea_file = os.path.join(idea_dir, "my-feature-idea.md")
            with open(idea_file, "w") as f:
                f.write("# My Great Feature\n\nSome description.\n")

            title = extract_title_from_idea_file(idea_dir, "my-feature")

            assert title == "My Great Feature"

    def test_falls_back_to_idea_name_when_no_heading(self):
        from i2code.implement.pr_helpers import extract_title_from_idea_file

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)
            idea_file = os.path.join(idea_dir, "my-feature-idea.md")
            with open(idea_file, "w") as f:
                f.write("No heading here, just text.\n")

            title = extract_title_from_idea_file(idea_dir, "my-feature")

            assert title == "my-feature"

    def test_falls_back_to_idea_name_when_file_missing(self):
        from i2code.implement.pr_helpers import extract_title_from_idea_file

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            title = extract_title_from_idea_file(idea_dir, "my-feature")

            assert title == "my-feature"


@pytest.mark.unit
class TestPRTitleGeneration:
    """Test PR title generation from idea name and directory."""

    def test_generate_pr_title_uses_idea_file_heading(self):
        """Should derive title from the idea file heading."""
        from i2code.implement.pr_helpers import generate_pr_title

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)
            idea_file = os.path.join(idea_dir, "my-feature-idea.md")
            with open(idea_file, "w") as f:
                f.write("# My Great Feature\n\nDescription.\n")

            title = generate_pr_title("my-feature", idea_dir)

            assert title == "My Great Feature"

    def test_generate_pr_title_falls_back_to_idea_name(self):
        """Should fall back to idea name when no idea file exists."""
        from i2code.implement.pr_helpers import generate_pr_title

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            title = generate_pr_title("my-feature", idea_dir)

            assert title == "my-feature"


@pytest.mark.unit
class TestPRBodyGeneration:
    """Test PR body generation."""

    def test_generate_pr_body_minimal_format(self):
        """Should generate minimal PR body with just the idea directory link."""
        from i2code.implement.pr_helpers import generate_pr_body

        body = generate_pr_body(idea_directory="docs/features/my-feature")

        assert body == "**Idea directory:** `docs/features/my-feature`"


@pytest.mark.unit
class TestPushOperations:
    """Test push operations to slice branch."""

    def test_build_push_command(self):
        """Should build correct git push command."""
        from i2code.implement.pr_helpers import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup")

        assert cmd == ["git", "push", "origin", "idea/my-feature/01-setup"]

    def test_build_push_command_with_force(self):
        """Should include --force-with-lease when requested."""
        from i2code.implement.pr_helpers import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup", force=True)

        assert "--force-with-lease" in cmd


@pytest.mark.unit
class TestPRReadyForReview:
    """Test marking PR as ready for review."""

    def test_mark_pr_ready_calls_gh_pr_ready(self, mocker):
        """Should call gh pr ready with PR number."""
        from i2code.implement.pr_helpers import mark_pr_ready

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0

        result = mark_pr_ready(123)

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "pr" in call_args
        assert "ready" in call_args
        assert "123" in call_args

    def test_mark_pr_ready_returns_false_on_failure(self, mocker):
        """Should return False when gh pr ready fails."""
        from i2code.implement.pr_helpers import mark_pr_ready

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 1

        result = mark_pr_ready(123)

        assert result is False


@pytest.mark.unit
class TestPRPolling:
    """Test PR polling for feedback."""

    def test_get_pr_state_returns_open(self, mocker):
        """Should return PR state from GitHub."""
        from i2code.implement.pr_helpers import get_pr_state

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "OPEN"}'

        state = get_pr_state(123)

        assert state == "OPEN"

    def test_get_pr_state_returns_merged(self, mocker):
        """Should return MERGED state when PR is merged."""
        from i2code.implement.pr_helpers import get_pr_state

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "MERGED"}'

        state = get_pr_state(123)

        assert state == "MERGED"

    def test_get_pr_state_returns_closed(self, mocker):
        """Should return CLOSED state when PR is closed."""
        from i2code.implement.pr_helpers import get_pr_state

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "CLOSED"}'

        state = get_pr_state(123)

        assert state == "CLOSED"

    def test_is_pr_complete_true_when_merged(self):
        """Should return True when PR is merged."""
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("MERGED") is True

    def test_is_pr_complete_true_when_closed(self):
        """Should return True when PR is closed."""
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("CLOSED") is True

    def test_is_pr_complete_false_when_open(self):
        """Should return False when PR is still open."""
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("OPEN") is False


