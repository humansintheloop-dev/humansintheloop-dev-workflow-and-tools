"""Tests for update_project input validation: project_dir and config_dir must exist."""

import tempfile

import pytest

from i2code.setup_cmd.update_project import update_project

from _update_project_helpers import create_config_dir, create_project_dir


@pytest.mark.unit
class TestValidation:

    def test_raises_when_project_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = create_config_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_project("/nonexistent/project", config_dir, fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_config_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_project(project_dir, "/nonexistent/config", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0
