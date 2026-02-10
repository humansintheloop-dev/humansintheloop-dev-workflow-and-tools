"""Integration tests for implement CLI.

These tests run the actual i2code implement command and verify its behavior.
"""

import subprocess

import pytest

from conftest import SCRIPT_CMD


@pytest.mark.integration
class TestCLINoArguments:
    """Test CLI behavior when run with no arguments."""

    def test_no_arguments_shows_usage_error(self):
        """Running script with no arguments should show usage error and exit non-zero."""
        result = subprocess.run(
            SCRIPT_CMD,
            capture_output=True,
            text=True
        )

        # Should exit with non-zero code
        assert result.returncode != 0

        # Click shows "Usage:" and mentions the required argument
        assert "usage:" in result.stderr.lower() or "error:" in result.stderr.lower()
        assert "idea-directory" in result.stderr.lower() or "idea_directory" in result.stderr.lower()


@pytest.mark.integration
class TestCLIHelpFlag:
    """Test CLI --help flag behavior."""

    def test_help_flag_shows_help_text(self):
        """Running script with --help should show help text and exit zero."""
        result = subprocess.run(
            SCRIPT_CMD + ['--help'],
            capture_output=True,
            text=True
        )

        # Should exit with zero code
        assert result.returncode == 0

        # Should show help information in stdout
        assert "idea-directory" in result.stdout.lower() or "idea_directory" in result.stdout.lower()
        assert "--cleanup" in result.stdout
        # Should include description
        assert "worktree" in result.stdout.lower() or "draft pr" in result.stdout.lower()
