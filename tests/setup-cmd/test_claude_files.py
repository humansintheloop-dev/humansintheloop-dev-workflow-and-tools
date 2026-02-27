"""Tests for setup_claude_files: copies CLAUDE.md and settings.local.json
into the current project directory."""

import os
import tempfile

import pytest

from i2code.setup_cmd.claude_files import setup_claude_files


def _create_config_dir(tmpdir, *, claude_md=True, settings=True):
    """Create a config directory with optional CLAUDE.md and settings.local.json."""
    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    if claude_md:
        with open(os.path.join(config_dir, "CLAUDE.md"), "w") as f:
            f.write("# Config CLAUDE.md\n")
    if settings:
        with open(os.path.join(config_dir, "settings.local.json"), "w") as f:
            f.write('{"key": "value"}\n')
    return config_dir


def _setup_dirs(tmpdir, *, claude_md=True, settings=True):
    """Create both config and target directories, returning (config_dir, target_dir)."""
    config_dir = _create_config_dir(tmpdir, claude_md=claude_md, settings=settings)
    target_dir = os.path.join(tmpdir, "project")
    os.makedirs(target_dir, exist_ok=True)
    return config_dir, target_dir


@pytest.mark.unit
class TestCopiesFiles:

    def test_copies_claude_md_to_target_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir, target_dir = _setup_dirs(tmpdir)
            setup_claude_files(config_dir, target_dir=target_dir)

            copied = os.path.join(target_dir, "CLAUDE.md")
            assert os.path.isfile(copied)
            with open(copied) as f:
                assert f.read() == "# Config CLAUDE.md\n"

    def test_creates_dot_claude_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir, target_dir = _setup_dirs(tmpdir)
            setup_claude_files(config_dir, target_dir=target_dir)

            assert os.path.isdir(os.path.join(target_dir, ".claude"))

    def test_copies_settings_local_json_into_dot_claude(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir, target_dir = _setup_dirs(tmpdir)
            setup_claude_files(config_dir, target_dir=target_dir)

            settings = os.path.join(target_dir, ".claude", "settings.local.json")
            assert os.path.isfile(settings)
            with open(settings) as f:
                assert f.read() == '{"key": "value"}\n'

    def test_dot_claude_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir, target_dir = _setup_dirs(tmpdir)
            os.makedirs(os.path.join(target_dir, ".claude"))

            setup_claude_files(config_dir, target_dir=target_dir)

            settings = os.path.join(target_dir, ".claude", "settings.local.json")
            assert os.path.isfile(settings)


@pytest.mark.unit
class TestValidation:

    def test_raises_when_config_dir_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = os.path.join(tmpdir, "project")
            os.makedirs(target_dir)
            with pytest.raises(SystemExit):
                setup_claude_files("/nonexistent/config", target_dir=target_dir)

    def test_raises_when_claude_md_missing_from_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir, target_dir = _setup_dirs(tmpdir, claude_md=False)
            with pytest.raises(SystemExit):
                setup_claude_files(config_dir, target_dir=target_dir)

    def test_raises_when_settings_missing_from_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir, target_dir = _setup_dirs(tmpdir, settings=False)
            with pytest.raises(SystemExit):
                setup_claude_files(config_dir, target_dir=target_dir)
