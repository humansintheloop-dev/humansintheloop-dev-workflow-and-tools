"""Tests for update_claude_files: validates directories, validates Claude files exist,
template variables correct, Claude invoked interactively."""

import os
import tempfile

import pytest

from i2code.improve.update_claude_files import update_claude_files


def _create_project_with_claude_files(tmpdir, *, claude_md=True, settings=True):
    """Create a project directory with Claude files."""
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)

    if claude_md:
        with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
            f.write("# Project CLAUDE.md\n")

    if settings:
        claude_dir = os.path.join(project_dir, ".claude")
        os.makedirs(claude_dir)
        with open(os.path.join(claude_dir, "settings.local.json"), "w") as f:
            f.write("{}\n")

    return project_dir


def _create_config_dir(tmpdir):
    """Create a config directory with CLAUDE.md and settings.local.json."""
    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    with open(os.path.join(config_dir, "CLAUDE.md"), "w") as f:
        f.write("# Config CLAUDE.md\n")
    with open(os.path.join(config_dir, "settings.local.json"), "w") as f:
        f.write("{}\n")
    return config_dir


@pytest.mark.unit
class TestValidation:

    def test_raises_when_project_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = _create_config_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_claude_files("/nonexistent/project", config_dir, fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_config_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            with pytest.raises(SystemExit):
                update_claude_files(project_dir, "/nonexistent/config", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_no_claude_files_in_project(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = os.path.join(tmpdir, "empty-project")
            os.makedirs(project_dir)
            config_dir = _create_config_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_succeeds_with_only_claude_md(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir, claude_md=True, settings=False)
            config_dir = _create_config_dir(tmpdir)
            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 1

    def test_succeeds_with_only_settings(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir, claude_md=False, settings=True)
            config_dir = _create_config_dir(tmpdir)
            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 1


@pytest.mark.unit
class TestTemplateRendering:

    def test_renders_update_claude_files_template(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            template_name, _ = fake_renderer.calls[0]
            assert template_name == "update-claude-files-from-project.md"

    def test_template_receives_project_dir(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert variables["PROJECT_DIR"] == project_dir

    def test_template_receives_project_claude_md(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            expected = os.path.join(project_dir, "CLAUDE.md")
            assert variables["PROJECT_CLAUDE_MD"] == expected

    def test_template_receives_project_settings(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            expected = os.path.join(project_dir, ".claude", "settings.local.json")
            assert variables["PROJECT_SETTINGS"] == expected

    def test_template_receives_config_claude_md(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            expected = os.path.join(config_dir, "CLAUDE.md")
            assert variables["CONFIG_CLAUDE_MD"] == expected

    def test_template_receives_config_settings(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            expected = os.path.join(config_dir, "settings.local.json")
            assert variables["CONFIG_SETTINGS"] == expected

    def test_template_receives_all_five_variables(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            expected_keys = {"PROJECT_DIR", "PROJECT_CLAUDE_MD", "PROJECT_SETTINGS",
                             "CONFIG_CLAUDE_MD", "CONFIG_SETTINGS"}
            assert set(variables.keys()) == expected_keys


@pytest.mark.unit
class TestClaudeInvocation:

    def test_invokes_claude_interactively(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            method, _, _ = fake_runner.calls[0]
            assert method == "run_interactive"

    def test_claude_command_starts_with_claude(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            assert cmd[0] == "claude"

    def test_claude_receives_rendered_prompt(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            assert "template=update-claude-files-from-project.md" in cmd[1]

    def test_returns_claude_result(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_with_claude_files(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            fake_runner.set_result(ClaudeResult(returncode=0))
            result = update_claude_files(project_dir, config_dir, fake_runner, fake_renderer)

            assert result.returncode == 0
