"""CLI integration tests for i2code setup subcommands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.mark.unit
class TestClaudeFilesCommandRegistered:

    def test_listed_in_setup_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "--help"])
        assert "claude-files" in result.output

    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "claude-files", "--help"])
        assert result.exit_code == 0
        assert "config-dir" in result.output.lower()

    def test_requires_config_dir_option(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "claude-files"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestClaudeFilesCommandInvocation:

    def test_invokes_setup_claude_files(self, tmp_path):
        with patch("i2code.setup_cmd.cli.setup_claude_files") as mock_fn:
            runner = CliRunner()
            result = runner.invoke(main, [
                "setup", "claude-files",
                "--config-dir", str(tmp_path),
            ])
            assert result.exit_code == 0
            mock_fn.assert_called_once()

    def test_passes_config_dir(self, tmp_path):
        with patch("i2code.setup_cmd.cli.setup_claude_files") as mock_fn:
            runner = CliRunner()
            runner.invoke(main, [
                "setup", "claude-files",
                "--config-dir", str(tmp_path),
            ])
            assert mock_fn.call_args[0][0] == str(tmp_path)


@pytest.mark.unit
class TestUpdateProjectCommandRegistered:

    def test_listed_in_setup_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "--help"])
        assert "update-project" in result.output

    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "update-project", "--help"])
        assert result.exit_code == 0
        assert "project_dir" in result.output.lower()

    def test_requires_project_dir_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "update-project"])
        assert result.exit_code != 0

    def test_requires_config_dir_option(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "update-project", "/tmp/proj"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestUpdateProjectCommandInvocation:

    def test_invokes_update_project(self, tmp_path):
        with patch("i2code.setup_cmd.cli.update_project") as mock_fn, \
             patch("i2code.setup_cmd.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            result = runner.invoke(main, [
                "setup", "update-project", str(tmp_path),
                "--config-dir", "/tmp/config",
            ])
            assert result.exit_code == 0
            mock_fn.assert_called_once()

    def test_passes_project_dir_and_config_dir(self, tmp_path):
        with patch("i2code.setup_cmd.cli.update_project") as mock_fn, \
             patch("i2code.setup_cmd.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, [
                "setup", "update-project", str(tmp_path),
                "--config-dir", "/tmp/config",
            ])
            assert mock_fn.call_args[0][0] == str(tmp_path)
            assert mock_fn.call_args[0][1] == "/tmp/config"

    def test_passes_claude_runner(self, tmp_path):
        with patch("i2code.setup_cmd.cli.update_project") as mock_fn, \
             patch("i2code.setup_cmd.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, [
                "setup", "update-project", str(tmp_path),
                "--config-dir", "/tmp/config",
            ])
            assert mock_fn.call_args[0][2] is mock_runner

    def test_passes_render_template(self, tmp_path):
        with patch("i2code.setup_cmd.cli.update_project") as mock_fn, \
             patch("i2code.setup_cmd.cli.ClaudeRunner") as mock_runner_cls, \
             patch("i2code.setup_cmd.cli.render_template") as mock_renderer:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, [
                "setup", "update-project", str(tmp_path),
                "--config-dir", "/tmp/config",
            ])
            assert mock_fn.call_args[0][3] is mock_renderer
