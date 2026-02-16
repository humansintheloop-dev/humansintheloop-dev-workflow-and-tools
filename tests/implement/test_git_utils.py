"""Tests for git_utils module."""

import subprocess

import pytest

from i2code.implement.git_utils import get_default_branch


@pytest.mark.unit
class TestGetDefaultBranch:

    def test_returns_default_branch_name(self, monkeypatch):
        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = "master\n"
                returncode = 0
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)
        assert get_default_branch() == "master"

    def test_raises_on_gh_failure(self, monkeypatch):
        def mock_run(*args, **kwargs):
            class MockResult:
                stdout = ""
                stderr = "not a GitHub repository"
                returncode = 1
            return MockResult()

        monkeypatch.setattr(subprocess, "run", mock_run)
        with pytest.raises(RuntimeError, match="Failed to detect default branch"):
            get_default_branch()
