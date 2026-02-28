"""Tests for PR helper functions in implement-with-worktree."""

import os
import tempfile
from contextlib import contextmanager

import pytest


@contextmanager
def _idea_dir_env(idea_name="my-feature", idea_content=None):
    """Create a temporary idea directory, optionally writing an idea file.

    Yields (idea_dir, idea_name).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, idea_name)
        os.makedirs(idea_dir)
        if idea_content is not None:
            idea_file = os.path.join(idea_dir, f"{idea_name}-idea.md")
            with open(idea_file, "w") as f:
                f.write(idea_content)
        yield idea_dir, idea_name


@pytest.mark.unit
class TestExtractTitleFromIdeaFile:
    """Test extracting title from idea file heading."""

    def test_extracts_heading_from_idea_file(self):
        from i2code.implement.pr_helpers import extract_title_from_idea_file

        with _idea_dir_env(idea_content="# My Great Feature\n\nSome description.\n") as (idea_dir, idea_name):
            assert extract_title_from_idea_file(idea_dir, idea_name) == "My Great Feature"

    def test_falls_back_to_idea_name_when_no_heading(self):
        from i2code.implement.pr_helpers import extract_title_from_idea_file

        with _idea_dir_env(idea_content="No heading here, just text.\n") as (idea_dir, idea_name):
            assert extract_title_from_idea_file(idea_dir, idea_name) == "my-feature"

    def test_falls_back_to_idea_name_when_file_missing(self):
        from i2code.implement.pr_helpers import extract_title_from_idea_file

        with _idea_dir_env() as (idea_dir, idea_name):
            assert extract_title_from_idea_file(idea_dir, idea_name) == "my-feature"


@pytest.mark.unit
class TestPRTitleGeneration:
    """Test PR title generation from idea name and directory."""

    def test_generate_pr_title_uses_idea_file_heading(self):
        from i2code.implement.pr_helpers import generate_pr_title

        with _idea_dir_env(idea_content="# My Great Feature\n\nDescription.\n") as (idea_dir, idea_name):
            assert generate_pr_title(idea_name, idea_dir) == "My Great Feature"

    def test_generate_pr_title_falls_back_to_idea_name(self):
        from i2code.implement.pr_helpers import generate_pr_title

        with _idea_dir_env() as (idea_dir, idea_name):
            assert generate_pr_title(idea_name, idea_dir) == "my-feature"


@pytest.mark.unit
class TestPRBodyGeneration:
    """Test PR body generation."""

    def test_generate_pr_body_minimal_format(self):
        from i2code.implement.pr_helpers import generate_pr_body

        body = generate_pr_body(idea_directory="docs/features/my-feature")
        assert body == "**Idea directory:** `docs/features/my-feature`"


_GH_SUBPROCESS_PATH = "i2code.implement.github_client.subprocess.run"


def _mock_gh_subprocess(mocker, returncode=0, stdout=""):
    """Patch github_client subprocess.run and return the mock."""
    mock_run = mocker.patch(_GH_SUBPROCESS_PATH)
    mock_run.return_value.returncode = returncode
    mock_run.return_value.stdout = stdout
    return mock_run


@pytest.mark.unit
class TestPushOperations:
    """Test push operations to slice branch."""

    def test_build_push_command(self):
        from i2code.implement.pr_helpers import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup")
        assert cmd == ["git", "push", "origin", "idea/my-feature/01-setup"]

    def test_build_push_command_with_force(self):
        from i2code.implement.pr_helpers import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup", force=True)
        assert "--force-with-lease" in cmd


@pytest.mark.unit
class TestPRReadyForReview:
    """Test marking PR as ready for review."""

    def test_mark_pr_ready_calls_gh_pr_ready(self, mocker):
        from i2code.implement.pr_helpers import mark_pr_ready

        mock_run = _mock_gh_subprocess(mocker)
        result = mark_pr_ready(123)
        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "pr" in call_args
        assert "ready" in call_args
        assert "123" in call_args

    def test_mark_pr_ready_returns_false_on_failure(self, mocker):
        from i2code.implement.pr_helpers import mark_pr_ready

        _mock_gh_subprocess(mocker, returncode=1)
        assert mark_pr_ready(123) is False


@pytest.mark.unit
class TestPRPolling:
    """Test PR polling for feedback."""

    def test_get_pr_state_returns_open(self, mocker):
        from i2code.implement.pr_helpers import get_pr_state

        _mock_gh_subprocess(mocker, stdout='{"state": "OPEN"}')
        assert get_pr_state(123) == "OPEN"

    def test_get_pr_state_returns_merged(self, mocker):
        from i2code.implement.pr_helpers import get_pr_state

        _mock_gh_subprocess(mocker, stdout='{"state": "MERGED"}')
        assert get_pr_state(123) == "MERGED"

    def test_get_pr_state_returns_closed(self, mocker):
        from i2code.implement.pr_helpers import get_pr_state

        _mock_gh_subprocess(mocker, stdout='{"state": "CLOSED"}')
        assert get_pr_state(123) == "CLOSED"

    def test_is_pr_complete_true_when_merged(self):
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("MERGED") is True

    def test_is_pr_complete_true_when_closed(self):
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("CLOSED") is True

    def test_is_pr_complete_false_when_open(self):
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("OPEN") is False
