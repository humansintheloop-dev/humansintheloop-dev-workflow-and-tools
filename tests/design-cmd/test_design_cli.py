"""CLI integration tests for i2code design create."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.mark.unit
class TestDesignCreateCommandRegistered:

    def test_design_create_listed_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["design", "create", "--help"])
        assert result.exit_code == 0
        assert "directory" in result.output.lower()

    def test_design_create_requires_directory_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["design", "create"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestDesignCreateCommandInvocation:

    def test_invokes_create_design_for_existing_directory(self, tmp_path):
        with patch("i2code.design_cmd.cli.create_design") as mock_fn, \
             patch("i2code.design_cmd.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            result = runner.invoke(main, ["design", "create", str(tmp_path)])
            assert result.exit_code == 0
            mock_fn.assert_called_once()

    def test_constructs_idea_project_with_directory(self, tmp_path):
        with patch("i2code.design_cmd.cli.create_design") as mock_fn, \
             patch("i2code.design_cmd.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, ["design", "create", str(tmp_path)])
            project = mock_fn.call_args[0][0]
            assert project.directory == str(tmp_path)

    def test_passes_claude_runner_instance(self, tmp_path):
        with patch("i2code.design_cmd.cli.create_design") as mock_fn, \
             patch("i2code.design_cmd.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, ["design", "create", str(tmp_path)])
            assert mock_fn.call_args[0][1] is mock_runner
