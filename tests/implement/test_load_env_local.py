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

    def test_execute_succeeds_without_env_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env_before = dict(os.environ)

        cmd = _make_command()
        cmd.execute()

        assert dict(os.environ) == env_before
