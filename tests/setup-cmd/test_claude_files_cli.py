import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from i2code.cli import main


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "i2code" / "scripts"


class TestClaudeFilesInvokesBundledScript:
    def test_invokes_setup_claude_files_sh_with_config_dir(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(
                main,
                [
                    "setup",
                    "claude-files",
                    "--config-dir",
                    "/path/to/config-files",
                ],
            )

            assert result.exit_code == 0
            mock_subprocess.run.assert_called_once()
            call_args = mock_subprocess.run.call_args[0][0]
            assert Path(call_args[0]) == SCRIPTS_DIR / "setup-claude-files.sh"
            assert call_args[1:] == [
                "--config-dir",
                "/path/to/config-files",
            ]

    def test_propagates_script_exit_code(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=42
            )
            result = runner.invoke(
                main,
                [
                    "setup",
                    "claude-files",
                    "--config-dir",
                    "/path/to/config-files",
                ],
            )

            assert result.exit_code == 42

    def test_forwards_all_args(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(
                main,
                [
                    "setup",
                    "claude-files",
                    "--config-dir",
                    "/path/to/config-files",
                    "--extra-flag",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_subprocess.run.call_args[0][0]
            assert call_args[1:] == [
                "--config-dir",
                "/path/to/config-files",
                "--extra-flag",
            ]


class TestClaudeFilesInHelp:
    def test_setup_listed_in_main_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "setup" in result.output

    def test_claude_files_listed_in_setup_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "--help"])
        assert result.exit_code == 0
        assert "claude-files" in result.output
