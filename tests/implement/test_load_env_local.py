"""Tests for .env.local loading in ImplementCommand."""

import os

import pytest
from unittest.mock import MagicMock

from i2code.implement.implement_command import ImplementCommand
from i2code.implement.implement_opts import ImplementOpts

from fake_idea_project import FakeIdeaProject


def _make_command(**opt_overrides):
    defaults = dict(idea_directory="/tmp/fake-idea", dry_run=True)
    defaults.update(opt_overrides)
    opts = ImplementOpts(**defaults)
    project = FakeIdeaProject()
    git_repo = MagicMock()
    mode_factory = MagicMock()
    return ImplementCommand(opts, project, git_repo, mode_factory)


@pytest.mark.unit
class TestLoadEnvLocal:
    """ImplementCommand.execute() loads .env.local from CWD before proceeding."""

    def test_execute_loads_env_local(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env.local"
        env_file.write_text("TEST_ENV_LOCAL_VAR=loaded_value\n")
        monkeypatch.delenv("TEST_ENV_LOCAL_VAR", raising=False)
        monkeypatch.chdir(tmp_path)

        cmd = _make_command()
        cmd.execute()

        assert os.environ["TEST_ENV_LOCAL_VAR"] == "loaded_value"

    def test_shell_env_vars_take_precedence_over_env_local(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TEST_EXISTING_VAR", "shell-value")
        env_file = tmp_path / ".env.local"
        env_file.write_text("TEST_EXISTING_VAR=file-value\n")
        monkeypatch.chdir(tmp_path)

        cmd = _make_command()
        cmd.execute()

        assert os.environ["TEST_EXISTING_VAR"] == "shell-value"

    def test_isolate_mode_does_not_load_env_local(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env.local"
        env_file.write_text("TEST_ISOLATE_VAR=should_not_load\n")
        monkeypatch.delenv("TEST_ISOLATE_VAR", raising=False)
        monkeypatch.chdir(tmp_path)

        cmd = _make_command(isolate=True)
        cmd.execute()

        assert "TEST_ISOLATE_VAR" not in os.environ

    def test_execute_succeeds_without_env_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env_before = dict(os.environ)

        cmd = _make_command()
        cmd.execute()

        assert dict(os.environ) == env_before
